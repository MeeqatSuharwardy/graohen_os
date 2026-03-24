"""
SSH Key Service - Encrypted storage and verification for browser-based SSH login.

SSH public keys are encrypted at rest. Decryption happens only in-memory during
signature verification. No one can decrypt without the server's SECRET_KEY.

Designed for frontend: user generates key pair in browser, uploads public key.
For login: challenge-response with signature verification.
"""

import json
import base64
import hashlib
from typing import Optional, Dict, Any, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.exceptions import InvalidSignature

from app.config import settings
from app.core import database
from app.core.encryption import encrypt_bytes, decrypt_bytes, EncryptionError
from app.models.user_ssh_key import UserSSHKey
from sqlalchemy import select

import logging

logger = logging.getLogger(__name__)

# Redis key for SSH login challenges
REDIS_SSH_CHALLENGE_PREFIX = "auth:ssh_challenge:"
SSH_CHALLENGE_EXPIRE = 120  # 2 minutes


def _ssh_key_encryption_key() -> bytes:
    """Derive encryption key for SSH public keys from SECRET_KEY. Never expose."""
    return hashlib.sha256(
        (settings.SECRET_KEY + ":ssh-key-encryption:v1").encode()
    ).digest()


def _fingerprint(public_key_pem: bytes) -> str:
    """SHA256 fingerprint of public key (hex)."""
    return hashlib.sha256(public_key_pem).hexdigest()


def _get_key_type(public_key_pem: bytes) -> str:
    """Determine key type from PEM bytes."""
    try:
        key = serialization.load_ssh_public_key(public_key_pem)
        if isinstance(key, Ed25519PublicKey):
            return "ed25519"
        if isinstance(key, rsa.RSAPublicKey):
            return "rsa"
        if isinstance(key, ec.EllipticCurvePublicKey):
            return "ecdsa"
        return "unknown"
    except Exception:
        return "unknown"


def encrypt_ssh_public_key(public_key_pem: bytes) -> Dict[str, str]:
    """
    Encrypt SSH public key for storage. Returns dict with ciphertext, nonce, tag.
    Only decrypt_ssh_public_key (with server key) can reverse this.
    """
    key = _ssh_key_encryption_key()
    payload = encrypt_bytes(public_key_pem, key)
    key = b"\x00" * len(key)
    return payload


def decrypt_ssh_public_key(encrypted_payload: Dict[str, str]) -> bytes:
    """
    Decrypt stored SSH public key. Use only for verification; never expose result.
    """
    key = _ssh_key_encryption_key()
    try:
        plaintext = decrypt_bytes(encrypted_payload, key)
        key = b"\x00" * len(key)
        return plaintext
    except EncryptionError as e:
        logger.warning(f"SSH key decryption failed: {e}")
        raise


async def store_ssh_key(user_id: int, public_key_pem: str) -> str:
    """
    Validate, encrypt, and store SSH public key. Returns fingerprint.
    public_key_pem: OpenSSH format string, e.g. "ssh-ed25519 AAAA..."
    """
    try:
        # Accept both raw bytes and string
        if isinstance(public_key_pem, str):
            key_bytes = public_key_pem.encode("utf-8")
        else:
            key_bytes = public_key_pem

        # Validate it's a proper SSH public key
        key = serialization.load_ssh_public_key(key_bytes)
        fingerprint = _fingerprint(key_bytes)
        key_type = _get_key_type(key_bytes)

        # Encrypt for storage
        encrypted = encrypt_ssh_public_key(key_bytes)
        encrypted_json = json.dumps(encrypted)

        if database.AsyncSessionLocal is None:
            raise RuntimeError("Database not initialized")

        async with database.AsyncSessionLocal() as session:
            # Check if fingerprint already exists (same key, different user)
            existing = await session.execute(
                select(UserSSHKey).where(UserSSHKey.key_fingerprint == fingerprint)
            )
            if existing.scalar_one_or_none():
                raise ValueError("This SSH key is already registered to another account")

            # Check user doesn't already have this key
            dup = await session.execute(
                select(UserSSHKey).where(
                    UserSSHKey.user_id == user_id,
                    UserSSHKey.key_fingerprint == fingerprint,
                )
            )
            if dup.scalar_one_or_none():
                raise ValueError("You have already registered this SSH key")

            record = UserSSHKey(
                user_id=user_id,
                key_fingerprint=fingerprint,
                encrypted_public_key=encrypted_json,
                key_type=key_type,
            )
            session.add(record)
            await session.commit()

        logger.info(f"SSH key stored for user {user_id}, fingerprint {fingerprint[:16]}...")
        return fingerprint

    except Exception as e:
        logger.error(f"Failed to store SSH key: {e}", exc_info=True)
        raise


async def get_ssh_key_by_email(email: str) -> Optional[Tuple[int, Dict[str, str], str]]:
    """
    Get encrypted SSH key for user by email. Returns (user_id, encrypted_payload, key_type) or None.
    """
    from app.services.user_service import get_user_service

    user_service = get_user_service()
    user = await user_service.get_user_by_email(email)
    if not user:
        return None

    if database.AsyncSessionLocal is None:
        return None

    async with database.AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserSSHKey).where(UserSSHKey.user_id == int(user["id"])).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None

        payload = json.loads(row.encrypted_public_key)
        return (int(user["id"]), payload, row.key_type)


async def verify_ssh_signature(
    user_id: int,
    challenge: str,
    signature_b64: str,
) -> bool:
    """
    Decrypt user's stored public key and verify signature over challenge.
    challenge: raw challenge string (from Redis)
    signature_b64: base64-encoded signature from frontend
    """
    if database.AsyncSessionLocal is None:
        return False

    async with database.AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserSSHKey).where(UserSSHKey.user_id == user_id).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False

        try:
            payload = json.loads(row.encrypted_public_key)
            public_key_pem = decrypt_ssh_public_key(payload)
            key = serialization.load_ssh_public_key(public_key_pem)
        except Exception as e:
            logger.warning(f"Failed to load SSH key for verification: {e}")
            return False

        try:
            challenge_bytes = challenge.encode("utf-8")
            signature = base64.b64decode(signature_b64)
        except Exception as e:
            logger.warning(f"Invalid challenge/signature encoding: {e}")
            return False

        try:
            if isinstance(key, Ed25519PublicKey):
                key.verify(signature, challenge_bytes)
                return True
            if isinstance(key, rsa.RSAPublicKey):
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import padding
                key.verify(signature, challenge_bytes, padding.PKCS1v15(), hashes.SHA256())
                return True
            if isinstance(key, ec.EllipticCurvePublicKey):
                from cryptography.hazmat.primitives import hashes
                key.verify(signature, challenge_bytes, ec.ECDSA(hashes.SHA256()))
                return True
        except InvalidSignature:
            logger.warning("SSH signature verification failed")
            return False
        except Exception as e:
            logger.warning(f"SSH verification error: {e}")
            return False

    return False


async def store_ssh_challenge(email: str, challenge: str) -> None:
    """Store challenge in Redis for SSH login. Call from Redis when available."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        key = f"{REDIS_SSH_CHALLENGE_PREFIX}{email}"
        await redis.setex(key, SSH_CHALLENGE_EXPIRE, challenge)
    except Exception as e:
        logger.warning(f"Redis not available for SSH challenge: {e}")


async def get_and_consume_ssh_challenge(email: str) -> Optional[str]:
    """Get and consume (delete) SSH challenge. Returns challenge or None."""
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        key = f"{REDIS_SSH_CHALLENGE_PREFIX}{email}"
        raw = await redis.get(key)
        await redis.delete(key)
        if raw is None:
            return None
        return raw.decode("utf-8") if isinstance(raw, bytes) else raw
    except Exception as e:
        logger.warning(f"Redis not available for SSH challenge: {e}")
        return None

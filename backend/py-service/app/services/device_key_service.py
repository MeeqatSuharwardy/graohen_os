"""
Device key service - stores and retrieves device seeds for time-based auth.
"""

import json
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any

from app.core.redis_client import get_redis
from app.core.device_key import (
    generate_device_seed,
    verify_device_proof,
)
from app.core.secure_derivation import (
    derive_device_time_key,
    get_valid_time_slots,
)
from app.core.encryption import encrypt_bytes, decrypt_bytes, KEY_SIZE
from app.core.key_manager import derive_key_from_passcode
from app.config import settings

import logging

logger = logging.getLogger(__name__)

REDIS_DEVICE_SEED_PREFIX = "auth:device_seed:"
REDIS_CHALLENGE_PREFIX = "auth:challenge:"
CHALLENGE_EXPIRE_SECONDS = 120  # 2 min


def _server_seed_encryption_key() -> bytes:
    """Derive key for encrypting device seeds at rest (server-side)."""
    salt = hashlib.sha256(settings.SECRET_KEY.encode()).digest()[:16]
    return derive_key_from_passcode(settings.SECRET_KEY, salt)


async def store_device_seed(user_id: str, device_id: str, device_seed: bytes) -> None:
    """Store device seed encrypted at rest."""
    redis = await get_redis()
    key_bytes = _server_seed_encryption_key()
    payload = encrypt_bytes(device_seed, key_bytes)
    data = json.dumps(payload)
    redis_key = f"{REDIS_DEVICE_SEED_PREFIX}{user_id}:{device_id}"
    await redis.set(redis_key, data)
    key_bytes = b"\x00" * len(key_bytes)


async def user_has_any_device_seed(user_id: str) -> bool:
    """Check if user has any device seed registered."""
    redis = await get_redis()
    pattern = f"{REDIS_DEVICE_SEED_PREFIX}{user_id}:*"
    async for _ in redis.scan_iter(match=pattern, count=1):
        return True
    return False


async def get_device_seed(user_id: str, device_id: str) -> Optional[bytes]:
    """Retrieve and decrypt device seed."""
    redis = await get_redis()
    redis_key = f"{REDIS_DEVICE_SEED_PREFIX}{user_id}:{device_id}"
    data = await redis.get(redis_key)
    if not data:
        return None
    try:
        payload = json.loads(data)
        key_bytes = _server_seed_encryption_key()
        seed = decrypt_bytes(payload, key_bytes)
        key_bytes = b"\x00" * len(key_bytes)
        return seed
    except Exception as e:
        logger.warning(f"Failed to decrypt device seed: {e}")
        return None


async def create_device_seed_for_user(user_id: str, device_id: str) -> bytes:
    """Create and store new device seed. Returns plain seed for initial response."""
    seed = generate_device_seed()
    await store_device_seed(user_id, device_id, seed)
    return seed


def encrypt_seed_for_device_download(device_seed: bytes, password: str) -> Dict[str, str]:
    """
    Encrypt device seed for download. Device decrypts with password.
    Uses Argon2id - same strength as device key derivation.
    """
    salt = secrets.token_bytes(16)  # KeyManager salt_size
    key = derive_key_from_passcode(password, salt)
    payload = encrypt_bytes(device_seed, key)
    key = b"\x00" * len(key)
    return {
        "ciphertext": payload["ciphertext"],
        "nonce": payload["nonce"],
        "tag": payload["tag"],
        "salt": base64.b64encode(salt).decode("utf-8"),
    }


def decrypt_seed_from_device(encrypted_blob: Dict[str, str], password: str) -> bytes:
    """Decrypt device seed from downloaded blob (for server-side verification)."""
    salt = base64.b64decode(encrypted_blob["salt"])
    key = derive_key_from_passcode(password, salt)
    payload = {
        "ciphertext": encrypted_blob["ciphertext"],
        "nonce": encrypted_blob["nonce"],
        "tag": encrypted_blob["tag"],
    }
    return decrypt_bytes(payload, key)


async def store_challenge(email: str, device_id: str, challenge: str) -> None:
    """Store login challenge for verification."""
    redis = await get_redis()
    key = f"{REDIS_CHALLENGE_PREFIX}{email}:{device_id}"
    await redis.setex(key, CHALLENGE_EXPIRE_SECONDS, challenge)


async def get_and_consume_challenge(email: str, device_id: str) -> Optional[str]:
    """Get challenge and delete it (one-time use)."""
    redis = await get_redis()
    key = f"{REDIS_CHALLENGE_PREFIX}{email}:{device_id}"
    challenge = await redis.get(key)
    await redis.delete(key)
    return challenge


async def verify_device_login_proof(
    user_id: str,
    device_id: str,
    challenge: str,
    proof: str,
    client_time_slot: Optional[int] = None,
) -> bool:
    """
    Verify device proof. Accepts current, prev, next time slots for clock skew.
    """
    seed = await get_device_seed(user_id, device_id)
    if not seed:
        return False

    slots = get_valid_time_slots()
    slots_to_try = [client_time_slot] if client_time_slot is not None else list(slots)
    slots_to_try = list(dict.fromkeys(slots_to_try + list(slots)))  # dedupe, prefer client

    for slot in slots_to_try:
        key = derive_device_time_key(seed, device_id, slot)
        if verify_device_proof(key, challenge, proof):
            return True
    return False

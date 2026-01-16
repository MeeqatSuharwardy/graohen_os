"""Email Service with End-to-End Encryption

This service handles encrypted email storage and retrieval with support for:
- Content encryption with random keys
- Key encryption using user keys or passcode-derived keys
- Public access tokens for encrypted emails
- Expiring access support
- Two modes: authenticated auto-decrypt or passcode-protected
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal
from enum import Enum

from app.core.encryption import (
    encrypt_bytes,
    decrypt_bytes,
    generate_key,
    EncryptionError,
    KEY_SIZE,
)
from app.core.key_manager import (
    KeyManager,
    derive_key_from_passcode,
    generate_salt_for_identifier,
    get_key_manager,
)
from app.core.redis_client import get_redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Email domain (from config)
EMAIL_DOMAIN = settings.EMAIL_DOMAIN

# Redis key prefixes
REDIS_EMAIL_PREFIX = "email:"
REDIS_ACCESS_TOKEN_PREFIX = "email:access:"
REDIS_PASSCODE_SALT_PREFIX = "email:passcode_salt:"

# Public access token settings
ACCESS_TOKEN_SIZE = 32  # bytes
ACCESS_TOKEN_EXPIRE_HOURS = 168  # 7 days default


class EncryptionMode(str, Enum):
    """Email encryption modes"""
    AUTHENTICATED = "authenticated"  # Auto-decrypt for authenticated users
    PASSCODE_PROTECTED = "passcode_protected"  # Requires passcode to unlock


class EmailEncryptionError(Exception):
    """Custom exception for email encryption errors"""
    pass


class EmailService:
    """Service for encrypted email operations"""
    
    def __init__(self):
        self.key_manager = get_key_manager()
    
    def generate_public_access_token(self) -> str:
        """
        Generate a secure public access token for email access.
        
        Returns:
            Base64-encoded access token
        """
        token_bytes = secrets.token_bytes(ACCESS_TOKEN_SIZE)
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8").rstrip("=")
        return token
    
    async def encrypt_email_content(
        self,
        email_body: bytes,
        user_email: Optional[str] = None,
        passcode: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Encrypt email body with a random content key.
        
        The content key is encrypted using either:
        - User's derived key (from user_email) if authenticated mode
        - Passcode-derived key if passcode is provided
        
        Args:
            email_body: Raw email body bytes
            user_email: User email for authenticated mode (optional)
            passcode: Passcode for passcode-protected mode (optional)
            expires_in_hours: Access expiration in hours (optional)
        
        Returns:
            Dictionary containing encrypted payload:
            {
                "encrypted_content": {...},  # Encrypted email body
                "encrypted_content_key": {...},  # Encrypted content key
                "access_token": "public-access-token",
                "encryption_mode": "authenticated" | "passcode_protected",
                "expires_at": "ISO timestamp" (if expires_in_hours provided)
            }
        
        Raises:
            EmailEncryptionError: If encryption fails
        """
        try:
            # Generate random content key
            content_key = generate_key()
            
            # Encrypt email body with content key
            encrypted_content = encrypt_bytes(email_body, content_key)
            
            # Determine encryption mode
            if passcode:
                encryption_mode = EncryptionMode.PASSCODE_PROTECTED
                # Derive key from passcode
                # Use email as salt identifier for deterministic salt generation
                if user_email:
                    salt = generate_salt_for_identifier(user_email)
                else:
                    # Generate random salt if no user email
                    salt = self.key_manager.generate_salt()
                
                # Derive key from passcode
                passcode_key = derive_key_from_passcode(passcode, salt)
                
                # Encrypt content key with passcode-derived key
                encrypted_content_key = encrypt_bytes(content_key, passcode_key)
                
                # Store salt in Redis for later retrieval
                # We'll use the access token to retrieve it
                # For now, we'll include salt in the response (encrypted)
                # In production, store salt separately with access token
                
            elif user_email:
                encryption_mode = EncryptionMode.AUTHENTICATED
                # Derive user key from email (using email as identifier)
                user_salt = generate_salt_for_identifier(user_email)
                # For authenticated mode, we use a default passcode or user-specific key
                # In a real system, you'd retrieve the user's master key
                # For now, we'll use a derivation based on email
                # TODO: Replace with actual user key retrieval
                user_key = derive_key_from_passcode(user_email, user_salt)  # Temporary
                
                # Encrypt content key with user key
                encrypted_content_key = encrypt_bytes(content_key, user_key)
                
            else:
                raise EmailEncryptionError("Either user_email or passcode must be provided")
            
            # Generate public access token
            access_token = self.generate_public_access_token()
            
            # Calculate expiration
            expires_at = None
            expires_seconds = None
            if expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
                expires_seconds = int(expires_in_hours * 3600)
            
            # Store encrypted email data in Redis
            await self.store_encrypted_email(
                access_token=access_token,
                encrypted_content=encrypted_content,
                encrypted_content_key=encrypted_content_key,
                expires_in_seconds=expires_seconds,
            )
            
            # Store metadata in Redis
            await self._store_email_metadata(
                access_token=access_token,
                encryption_mode=encryption_mode.value,
                user_email=user_email,
                has_passcode=passcode is not None,
                expires_in_seconds=expires_seconds,
            )
            
            # Store passcode salt if passcode mode
            if passcode:
                if user_email:
                    salt_base64 = base64.b64encode(salt).decode("utf-8")
                else:
                    # If no user_email, use the generated random salt
                    salt_base64 = base64.b64encode(salt).decode("utf-8")
                await self._store_passcode_salt(access_token, salt_base64, expires_seconds)
            
            # Return only encrypted payloads (no plaintext)
            result = {
                "encrypted_content": encrypted_content,
                "encrypted_content_key": encrypted_content_key,
                "access_token": access_token,
                "encryption_mode": encryption_mode.value,
            }
            
            if expires_at:
                result["expires_at"] = expires_at.isoformat()
            
            logger.info(
                f"Email encrypted: mode={encryption_mode.value}, "
                f"token={access_token[:8]}..., expires={expires_at}"
            )
            
            return result
            
        except EncryptionError as e:
            logger.error(f"Email encryption failed: {e}", exc_info=True)
            raise EmailEncryptionError(f"Encryption failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Email encryption failed: {e}", exc_info=True)
            raise EmailEncryptionError(f"Unexpected error: {str(e)}") from e
        finally:
            # Securely overwrite sensitive data
            if 'content_key' in locals():
                content_key = b"\x00" * len(content_key)
            if 'passcode_key' in locals():
                passcode_key = b"\x00" * len(passcode_key) if passcode_key else b""
            if 'user_key' in locals():
                user_key = b"\x00" * len(user_key) if user_key else b""
    
    async def decrypt_email_for_authenticated_user(
        self,
        access_token: str,
        user_email: str,
    ) -> bytes:
        """
        Decrypt email for authenticated user (no passcode required).
        
        Args:
            access_token: Public access token
            user_email: Authenticated user's email
        
        Returns:
            Decrypted email body bytes
        
        Raises:
            EmailEncryptionError: If decryption fails or access denied
        """
        try:
            # Get email metadata
            metadata = await self._get_email_metadata(access_token)
            if not metadata:
                raise EmailEncryptionError("Email not found or expired")
            
            # Verify encryption mode
            if metadata["encryption_mode"] != EncryptionMode.AUTHENTICATED.value:
                raise EmailEncryptionError("Email requires passcode unlock")
            
            # Verify user access
            if metadata.get("user_email") and metadata["user_email"] != user_email.lower():
                raise EmailEncryptionError("Access denied: email belongs to different user")
            
            # Get encrypted data from storage
            encrypted_data = await self._get_encrypted_email(access_token)
            if not encrypted_data:
                raise EmailEncryptionError("Encrypted email data not found")
            
            encrypted_content = encrypted_data["encrypted_content"]
            encrypted_content_key = encrypted_data["encrypted_content_key"]
            
            # Derive user key (same as encryption)
            user_salt = generate_salt_for_identifier(user_email)
            # TODO: Replace with actual user key retrieval
            user_key = derive_key_from_passcode(user_email, user_salt)  # Temporary
            
            # Decrypt content key
            try:
                content_key = decrypt_bytes(encrypted_content_key, user_key)
            except EncryptionError as e:
                raise EmailEncryptionError(f"Failed to decrypt content key: {str(e)}")
            
            # Decrypt email content
            try:
                email_body = decrypt_bytes(encrypted_content, content_key)
            except EncryptionError as e:
                raise EmailEncryptionError(f"Failed to decrypt email content: {str(e)}")
            
            # Securely overwrite
            content_key = b"\x00" * len(content_key)
            user_key = b"\x00" * len(user_key)
            
            logger.info(f"Email decrypted for authenticated user: {user_email}, token={access_token[:8]}...")
            
            return email_body
            
        except EmailEncryptionError:
            raise
        except Exception as e:
            logger.error(f"Email decryption failed: {e}", exc_info=True)
            raise EmailEncryptionError(f"Decryption failed: {str(e)}") from e
    
    async def decrypt_email_with_passcode(
        self,
        access_token: str,
        passcode: str,
    ) -> bytes:
        """
        Decrypt email using passcode.
        
        Args:
            access_token: Public access token
            passcode: Passcode used for encryption
        
        Returns:
            Decrypted email body bytes
        
        Raises:
            EmailEncryptionError: If decryption fails or passcode incorrect
        """
        try:
            # Get email metadata
            metadata = await self._get_email_metadata(access_token)
            if not metadata:
                raise EmailEncryptionError("Email not found or expired")
            
            # Verify encryption mode
            if metadata["encryption_mode"] != EncryptionMode.PASSCODE_PROTECTED.value:
                raise EmailEncryptionError("Email does not require passcode")
            
            if not metadata.get("has_passcode"):
                raise EmailEncryptionError("Email was not encrypted with passcode")
            
            # Get encrypted data
            encrypted_data = await self._get_encrypted_email(access_token)
            if not encrypted_data:
                raise EmailEncryptionError("Encrypted email data not found")
            
            encrypted_content = encrypted_data["encrypted_content"]
            encrypted_content_key = encrypted_data["encrypted_content_key"]
            
            # Get passcode salt
            user_email = metadata.get("user_email")
            if user_email:
                salt_base64 = await self._get_passcode_salt(access_token)
                if salt_base64:
                    salt = base64.b64decode(salt_base64)
                else:
                    # Fallback: generate deterministic salt from email
                    salt = generate_salt_for_identifier(user_email)
            else:
                # No user email, try to get stored salt
                salt_base64 = await self._get_passcode_salt(access_token)
                if not salt_base64:
                    raise EmailEncryptionError("Passcode salt not found")
                salt = base64.b64decode(salt_base64)
            
            # Derive key from passcode
            passcode_key = derive_key_from_passcode(passcode, salt)
            
            # Decrypt content key
            try:
                content_key = decrypt_bytes(encrypted_content_key, passcode_key)
            except EncryptionError:
                # Invalid passcode
                raise EmailEncryptionError("Incorrect passcode")
            
            # Decrypt email content
            try:
                email_body = decrypt_bytes(encrypted_content, content_key)
            except EncryptionError as e:
                raise EmailEncryptionError(f"Failed to decrypt email content: {str(e)}")
            
            # Securely overwrite
            content_key = b"\x00" * len(content_key)
            passcode_key = b"\x00" * len(passcode_key)
            
            logger.info(f"Email decrypted with passcode: token={access_token[:8]}...")
            
            return email_body
            
        except EmailEncryptionError:
            raise
        except Exception as e:
            logger.error(f"Email decryption failed: {e}", exc_info=True)
            raise EmailEncryptionError(f"Decryption failed: {str(e)}") from e
    
    async def store_encrypted_email(
        self,
        access_token: str,
        encrypted_content: Dict[str, str],
        encrypted_content_key: Dict[str, str],
        expires_in_seconds: Optional[int] = None,
    ) -> None:
        """
        Store encrypted email data in Redis.
        
        Args:
            access_token: Public access token
            encrypted_content: Encrypted content payload
            encrypted_content_key: Encrypted content key payload
            expires_in_seconds: Expiration time in seconds (optional)
        """
        redis = await get_redis()
        
        email_data = {
            "encrypted_content": encrypted_content,
            "encrypted_content_key": encrypted_content_key,
            "stored_at": datetime.utcnow().isoformat(),
        }
        
        # Convert to JSON string for storage
        import json
        email_json = json.dumps(email_data)
        
        key = f"{REDIS_EMAIL_PREFIX}{access_token}"
        
        if expires_in_seconds:
            await redis.setex(key, expires_in_seconds, email_json)
        else:
            await redis.set(key, email_json)
        
        logger.debug(f"Encrypted email stored: token={access_token[:8]}...")
    
    async def _store_email_metadata(
        self,
        access_token: str,
        encryption_mode: str,
        user_email: Optional[str],
        has_passcode: bool,
        expires_in_seconds: Optional[int] = None,
    ) -> None:
        """Store email metadata in Redis"""
        redis = await get_redis()
        
        metadata = {
            "encryption_mode": encryption_mode,
            "user_email": user_email.lower() if user_email else None,
            "has_passcode": has_passcode,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        import json
        metadata_json = json.dumps(metadata)
        
        key = f"{REDIS_ACCESS_TOKEN_PREFIX}{access_token}"
        
        if expires_in_seconds:
            await redis.setex(key, expires_in_seconds, metadata_json)
        else:
            await redis.set(key, metadata_json)
    
    async def _get_email_metadata(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get email metadata from Redis"""
        redis = await get_redis()
        key = f"{REDIS_ACCESS_TOKEN_PREFIX}{access_token}"
        
        metadata_json = await redis.get(key)
        if not metadata_json:
            return None
        
        import json
        try:
            return json.loads(metadata_json)
        except json.JSONDecodeError:
            return None
    
    async def _get_encrypted_email(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get encrypted email data from Redis"""
        redis = await get_redis()
        key = f"{REDIS_EMAIL_PREFIX}{access_token}"
        
        email_json = await redis.get(key)
        if not email_json:
            return None
        
        import json
        try:
            return json.loads(email_json)
        except json.JSONDecodeError:
            return None
    
    async def _store_passcode_salt(
        self,
        access_token: str,
        salt_base64: str,
        expires_in_seconds: Optional[int] = None,
    ) -> None:
        """Store passcode salt in Redis"""
        redis = await get_redis()
        key = f"{REDIS_PASSCODE_SALT_PREFIX}{access_token}"
        
        if expires_in_seconds:
            await redis.setex(key, expires_in_seconds, salt_base64)
        else:
            await redis.set(key, salt_base64)
    
    async def _get_passcode_salt(self, access_token: str) -> Optional[str]:
        """Get passcode salt from Redis"""
        redis = await get_redis()
        key = f"{REDIS_PASSCODE_SALT_PREFIX}{access_token}"
        return await redis.get(key)
    
    async def delete_email(self, access_token: str) -> bool:
        """
        Delete encrypted email and all associated data.
        
        Returns:
            True if deleted, False if not found
        """
        redis = await get_redis()
        
        deleted = 0
        
        # Delete encrypted email
        email_key = f"{REDIS_EMAIL_PREFIX}{access_token}"
        if await redis.delete(email_key):
            deleted += 1
        
        # Delete metadata
        metadata_key = f"{REDIS_ACCESS_TOKEN_PREFIX}{access_token}"
        if await redis.delete(metadata_key):
            deleted += 1
        
        # Delete passcode salt
        salt_key = f"{REDIS_PASSCODE_SALT_PREFIX}{access_token}"
        if await redis.delete(salt_key):
            deleted += 1
        
        if deleted > 0:
            logger.info(f"Email deleted: token={access_token[:8]}...")
        
        return deleted > 0
    
    def generate_email_address(self, access_token: str) -> str:
        """
        Generate email address for sending encrypted emails.
        
        Args:
            access_token: Public access token
        
        Returns:
            Email address in format: {token}@{EMAIL_DOMAIN}
        """
        return f"{access_token}@{EMAIL_DOMAIN}"


# Global service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the global EmailService instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


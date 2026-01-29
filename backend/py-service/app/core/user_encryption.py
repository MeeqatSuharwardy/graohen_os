"""User Data Encryption Utilities

Encrypts and decrypts user data (email, full_name) before storing in database.
Uses multi-layer encryption for maximum security.
"""

import hashlib
import json
import secrets
import base64
from typing import Dict, Optional, Tuple
from app.core.strong_encryption import (
    encrypt_multi_layer,
    decrypt_multi_layer,
    generate_strong_key,
    StrongEncryptionError,
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Master encryption key derived from SECRET_KEY
# In production, this should be stored separately and rotated regularly
_MASTER_KEY_CACHE: Optional[bytes] = None


def get_master_encryption_key() -> bytes:
    """
    Get or generate master encryption key for user data.
    
    Derives a consistent key from SECRET_KEY for encrypting user data.
    In production, consider using a dedicated key management service.
    
    Returns:
        32-byte encryption key
    """
    global _MASTER_KEY_CACHE
    
    if _MASTER_KEY_CACHE is None:
        # Derive master key from SECRET_KEY using SHA-256
        # This ensures consistent key generation
        secret_bytes = settings.SECRET_KEY.encode('utf-8')
        _MASTER_KEY_CACHE = hashlib.sha256(secret_bytes).digest()
        
        # Ensure it's exactly 32 bytes
        if len(_MASTER_KEY_CACHE) < 32:
            _MASTER_KEY_CACHE = hashlib.sha256(_MASTER_KEY_CACHE + secret_bytes).digest()[:32]
        elif len(_MASTER_KEY_CACHE) > 32:
            _MASTER_KEY_CACHE = _MASTER_KEY_CACHE[:32]
    
    return _MASTER_KEY_CACHE


def generate_user_encryption_keys() -> Tuple[bytes, bytes]:
    """
    Generate encryption keys for a user.
    
    Returns:
        Tuple of (primary_key, secondary_key) for multi-layer encryption
    """
    primary_key = generate_strong_key()
    secondary_key = generate_strong_key()
    return primary_key, secondary_key


def encrypt_user_data(
    data: str,
    primary_key: Optional[bytes] = None,
    secondary_key: Optional[bytes] = None
) -> Tuple[bytes, Dict[str, any]]:
    """
    Encrypt user data (email, full_name) with multi-layer encryption.
    
    Args:
        data: Plaintext string to encrypt
        primary_key: Optional primary encryption key (generated if not provided)
        secondary_key: Optional secondary encryption key (generated if not provided)
    
    Returns:
        Tuple of (encrypted_bytes, encryption_metadata_dict)
    """
    if not data:
        return b'', {}
    
    try:
        # Generate keys if not provided
        if primary_key is None:
            primary_key = generate_strong_key()
        if secondary_key is None:
            secondary_key = generate_strong_key()
        
        # Encrypt data
        data_bytes = data.encode('utf-8')
        encrypted_result = encrypt_multi_layer(
            data=data_bytes,
            primary_key=primary_key,
            secondary_key=secondary_key,
            layers=3
        )
        
        # Create metadata
        metadata = {
            "primary_key_salt": secrets.token_bytes(16).hex(),  # Store salt, not key
            "secondary_key_salt": secrets.token_bytes(16).hex(),
            "encryption_result": encrypted_result,
        }
        
        # Encrypt the keys themselves with master key (for storage)
        master_key = get_master_encryption_key()
        encrypted_primary = encrypt_multi_layer(
            data=primary_key,
            primary_key=master_key,
            layers=2
        )
        encrypted_secondary = encrypt_multi_layer(
            data=secondary_key,
            primary_key=master_key,
            layers=2
        )
        
        metadata["encrypted_primary_key"] = encrypted_primary
        metadata["encrypted_secondary_key"] = encrypted_secondary
        
        # Store encryption_result in metadata for decryption
        metadata["encryption_result"] = encrypted_result
        
        # Return encrypted bytes (base64-decoded ciphertext) and metadata
        encrypted_data_bytes = base64.b64decode(encrypted_result["ciphertext"])
        
        return encrypted_data_bytes, metadata
        
    except Exception as e:
        logger.error(f"Failed to encrypt user data: {e}", exc_info=True)
        raise StrongEncryptionError(f"User data encryption failed: {str(e)}") from e


def decrypt_user_data(
    encrypted_bytes: bytes,
    encryption_metadata: Optional[str] = None
) -> str:
    """
    Decrypt user data from encryption metadata.
    
    Args:
        encrypted_bytes: Not used (kept for compatibility)
        encryption_metadata: JSON string with encryption metadata
    
    Returns:
        Decrypted plaintext string
    """
    if not encryption_metadata:
        return ""
    
    try:
        # Parse metadata
        metadata = json.loads(encryption_metadata)
        
        # Decrypt the keys using master key
        master_key = get_master_encryption_key()
        encrypted_primary = metadata["encrypted_primary_key"]
        encrypted_secondary = metadata["encrypted_secondary_key"]
        
        primary_key = decrypt_multi_layer(
            encrypted_data=encrypted_primary,
            primary_key=master_key
        )
        secondary_key = decrypt_multi_layer(
            encrypted_data=encrypted_secondary,
            primary_key=master_key
        )
        
        # Get encryption_result from metadata
        encryption_result = metadata.get("encryption_result")
        if not encryption_result:
            raise StrongEncryptionError("Encryption metadata missing encryption_result")
        
        # Decrypt using the encryption_result
        decrypted_bytes = decrypt_multi_layer(
            encrypted_data=encryption_result,
            primary_key=primary_key,
            secondary_key=secondary_key
        )
        
        return decrypted_bytes.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Failed to decrypt user data: {e}", exc_info=True)
        raise StrongEncryptionError(f"User data decryption failed: {str(e)}") from e


def hash_email_for_lookup(email: str) -> str:
    """
    Create a hash of email for database lookup.
    
    Uses SHA-256 to create a consistent hash for indexing.
    
    Args:
        email: Email address
    
    Returns:
        SHA-256 hex digest
    """
    email_lower = email.lower().strip()
    return hashlib.sha256(email_lower.encode('utf-8')).hexdigest()

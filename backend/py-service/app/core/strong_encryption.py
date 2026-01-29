"""Strong Multi-Layer Encryption

Provides multiple layers of encryption to make decryption extremely difficult.
Uses multiple encryption passes with different keys and algorithms.
"""

import secrets
import hashlib
import base64
from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import logging

logger = logging.getLogger(__name__)

# Encryption constants
NONCE_SIZE = 12  # 96 bits for GCM
KEY_SIZE = 32  # 256 bits
TAG_SIZE = 16  # 128-bit authentication tag


class StrongEncryptionError(Exception):
    """Custom exception for strong encryption errors"""
    pass


def derive_master_key(password: bytes, salt: bytes, iterations: int = 1000000) -> bytes:
    """
    Derive a master key using PBKDF2 with high iteration count.
    
    Args:
        password: Password bytes
        salt: Salt bytes
        iterations: Number of iterations (default: 1,000,000 for high security)
    
    Returns:
        32-byte derived key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA512(),  # Use SHA-512 for stronger hashing
        length=KEY_SIZE,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    return kdf.derive(password)


def derive_scrypt_key(password: bytes, salt: bytes) -> bytes:
    """
    Derive a key using Scrypt (memory-hard KDF).
    
    Args:
        password: Password bytes
        salt: Salt bytes
    
    Returns:
        32-byte derived key
    """
    kdf = Scrypt(
        salt=salt,
        length=KEY_SIZE,
        n=2**20,  # CPU/memory cost parameter (1,048,576)
        r=8,  # Block size parameter
        p=1,  # Parallelization parameter
        backend=default_backend()
    )
    return kdf.derive(password)


def encrypt_multi_layer(
    data: bytes,
    primary_key: bytes,
    secondary_key: Optional[bytes] = None,
    layers: int = 3
) -> Dict[str, str]:
    """
    Encrypt data with multiple layers of encryption.
    
    Layer 1: AES-256-GCM with primary key
    Layer 2: ChaCha20-Poly1305 with secondary key (if provided)
    Layer 3: AES-256-GCM again with derived key
    
    This makes decryption extremely difficult even if one layer is compromised.
    
    Args:
        data: Plaintext data to encrypt
        primary_key: Primary encryption key (32 bytes)
        secondary_key: Optional secondary key (32 bytes)
        layers: Number of encryption layers (1-3, default: 3)
    
    Returns:
        Dictionary containing encrypted data and metadata
    """
    if len(primary_key) != KEY_SIZE:
        raise StrongEncryptionError(f"Primary key must be {KEY_SIZE} bytes")
    
    if secondary_key and len(secondary_key) != KEY_SIZE:
        raise StrongEncryptionError(f"Secondary key must be {KEY_SIZE} bytes")
    
    try:
        current_data = data
        encryption_metadata = []
        
        # Layer 1: AES-256-GCM
        if layers >= 1:
            nonce1 = secrets.token_bytes(NONCE_SIZE)
            aesgcm1 = AESGCM(primary_key)
            encrypted1 = aesgcm1.encrypt(nonce1, current_data, None)
            
            ciphertext1 = encrypted1[:-TAG_SIZE]
            tag1 = encrypted1[-TAG_SIZE:]
            
            current_data = encrypted1  # Use full encrypted data for next layer
            encryption_metadata.append({
                "algorithm": "AES-256-GCM",
                "nonce": base64.b64encode(nonce1).decode("utf-8"),
                "tag": base64.b64encode(tag1).decode("utf-8"),
            })
        
        # Layer 2: ChaCha20-Poly1305 (if secondary key provided and layers >= 2)
        if layers >= 2 and secondary_key:
            nonce2 = secrets.token_bytes(12)  # ChaCha20 uses 12-byte nonce
            chacha = ChaCha20Poly1305(secondary_key)
            encrypted2 = chacha.encrypt(nonce2, current_data, None)
            
            ciphertext2 = encrypted2[:-TAG_SIZE]
            tag2 = encrypted2[-TAG_SIZE:]
            
            current_data = encrypted2
            encryption_metadata.append({
                "algorithm": "ChaCha20-Poly1305",
                "nonce": base64.b64encode(nonce2).decode("utf-8"),
                "tag": base64.b64encode(tag2).decode("utf-8"),
            })
        
        # Layer 3: AES-256-GCM with derived key
        if layers >= 3:
            # Derive a third key from primary and secondary keys
            if secondary_key:
                combined_keys = primary_key + secondary_key
            else:
                combined_keys = primary_key + primary_key
            
            # Use Scrypt to derive third key
            salt3 = secrets.token_bytes(16)
            key3 = derive_scrypt_key(combined_keys, salt3)
            
            nonce3 = secrets.token_bytes(NONCE_SIZE)
            aesgcm3 = AESGCM(key3)
            encrypted3 = aesgcm3.encrypt(nonce3, current_data, None)
            
            ciphertext3 = encrypted3[:-TAG_SIZE]
            tag3 = encrypted3[-TAG_SIZE:]
            
            current_data = encrypted3
            encryption_metadata.append({
                "algorithm": "AES-256-GCM-Scrypt",
                "nonce": base64.b64encode(nonce3).decode("utf-8"),
                "tag": base64.b64encode(tag3).decode("utf-8"),
                "salt": base64.b64encode(salt3).decode("utf-8"),
            })
        
        # Final encrypted data
        final_ciphertext = base64.b64encode(current_data).decode("utf-8")
        
        return {
            "ciphertext": final_ciphertext,
            "layers": len(encryption_metadata),
            "metadata": encryption_metadata,
        }
        
    except Exception as e:
        logger.error(f"Multi-layer encryption failed: {e}", exc_info=True)
        raise StrongEncryptionError(f"Encryption failed: {str(e)}") from e


def decrypt_multi_layer(
    encrypted_data: Dict[str, str],
    primary_key: bytes,
    secondary_key: Optional[bytes] = None
) -> bytes:
    """
    Decrypt multi-layer encrypted data.
    
    Must decrypt in reverse order of encryption.
    
    Args:
        encrypted_data: Dictionary containing encrypted data and metadata
        primary_key: Primary decryption key (32 bytes)
        secondary_key: Optional secondary key (32 bytes)
    
    Returns:
        Decrypted plaintext data
    """
    if len(primary_key) != KEY_SIZE:
        raise StrongEncryptionError(f"Primary key must be {KEY_SIZE} bytes")
    
    if secondary_key and len(secondary_key) != KEY_SIZE:
        raise StrongEncryptionError(f"Secondary key must be {KEY_SIZE} bytes")
    
    try:
        # Get encrypted data and metadata
        ciphertext = base64.b64decode(encrypted_data["ciphertext"])
        metadata_list = encrypted_data.get("metadata", [])
        layers = len(metadata_list)
        
        # The ciphertext already includes all tags from all layers
        # We need to extract and verify tags in reverse order
        current_data = ciphertext
        
        # Decrypt in reverse order (Layer 3 -> Layer 2 -> Layer 1)
        for i in range(layers - 1, -1, -1):
            layer_meta = metadata_list[i]
            algorithm = layer_meta["algorithm"]
            nonce = base64.b64decode(layer_meta["nonce"])
            expected_tag = base64.b64decode(layer_meta["tag"])
            
            if algorithm == "AES-256-GCM-Scrypt":
                # Layer 3: Derive key and decrypt
                salt = base64.b64decode(layer_meta["salt"])
                if secondary_key:
                    combined_keys = primary_key + secondary_key
                else:
                    combined_keys = primary_key + primary_key
                key3 = derive_scrypt_key(combined_keys, salt)
                
                # Verify current_data has tag appended (should be at least TAG_SIZE bytes)
                if len(current_data) < TAG_SIZE:
                    raise StrongEncryptionError(f"Invalid ciphertext length for layer 3: {len(current_data)} bytes (expected at least {TAG_SIZE} bytes)")
                
                # GCM decrypt expects ciphertext + tag concatenated
                # current_data already has the tag appended from encryption
                aesgcm3 = AESGCM(key3)
                try:
                    current_data = aesgcm3.decrypt(nonce, current_data, None)
                except Exception as e:
                    # Log detailed error information for debugging
                    logger.error(
                        f"Layer 3 (AES-256-GCM-Scrypt) decryption failed: "
                        f"nonce_len={len(nonce)}, data_len={len(current_data)}, "
                        f"expected_tag_len={len(expected_tag)}, salt_len={len(salt)}, "
                        f"key3_len={len(key3) if 'key3' in locals() else 'N/A'}"
                    )
                    raise StrongEncryptionError(f"Layer 3 decryption failed: Invalid authentication tag. This may indicate wrong key or corrupted data.") from e
                
            elif algorithm == "ChaCha20-Poly1305":
                # Layer 2: Decrypt with secondary key
                if not secondary_key:
                    raise StrongEncryptionError("Secondary key required for ChaCha20-Poly1305 layer")
                
                chacha = ChaCha20Poly1305(secondary_key)
                current_data = chacha.decrypt(nonce, current_data, None)
                
            elif algorithm == "AES-256-GCM":
                # Layer 1: Decrypt with primary key
                aesgcm1 = AESGCM(primary_key)
                current_data = aesgcm1.decrypt(nonce, current_data, None)
            
            else:
                raise StrongEncryptionError(f"Unknown algorithm: {algorithm}")
        
        return current_data
        
    except Exception as e:
        logger.error(f"Multi-layer decryption failed: {e}", exc_info=True)
        raise StrongEncryptionError(f"Decryption failed: {str(e)}") from e


def generate_strong_key() -> bytes:
    """Generate a cryptographically secure random 256-bit key"""
    return secrets.token_bytes(KEY_SIZE)


def hash_for_storage(data: bytes) -> str:
    """
    Create a secure hash for storage/indexing purposes.
    Uses SHA-256 for fast hashing.
    """
    return hashlib.sha256(data).hexdigest()

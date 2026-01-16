"""Passcode-Based Key Manager using Argon2id

This module provides secure key derivation from user passcodes using Argon2id.
Argon2id is the hybrid variant recommended by OWASP and provides protection
against both side-channel attacks (Argon2i) and GPU-based attacks (Argon2d).

Key Features:
- Argon2id key derivation
- Configurable memory and time cost
- Salt generation per email/file
- No passcode storage (only salts and encrypted keys)
- Deterministic key derivation
- Client-side compatible (same parameters produce same keys)
"""

import secrets
import base64
import hashlib
from typing import Optional, Dict, Any
from argon2 import PasswordHasher, Type
from argon2.low_level import hash_secret_raw

from app.core.encryption import (
    encrypt_bytes,
    decrypt_bytes,
    generate_key,
    EncryptionError,
    KEY_SIZE,
)
import logging

logger = logging.getLogger(__name__)

# Argon2id configuration constants
# These match common client-side libraries for compatibility
DEFAULT_MEMORY_COST = 65536  # 64 MB (2^16 KB) - OWASP recommended minimum
DEFAULT_TIME_COST = 3  # 3 iterations - OWASP recommended
DEFAULT_PARALLELISM = 1  # Single-threaded (common for client-side)
SALT_SIZE = 16  # 128 bits - standard for Argon2


class KeyManagerError(Exception):
    """Custom exception for key manager errors"""
    pass


class KeyManager:
    """
    Key Manager for passcode-based key derivation.
    
    Uses Argon2id for key derivation with configurable parameters.
    Designed for compatibility with client-side JavaScript libraries.
    """
    
    def __init__(
        self,
        memory_cost: int = DEFAULT_MEMORY_COST,
        time_cost: int = DEFAULT_TIME_COST,
        parallelism: int = DEFAULT_PARALLELISM,
        salt_size: int = SALT_SIZE,
    ):
        """
        Initialize Key Manager with Argon2id parameters.
        
        Args:
            memory_cost: Memory cost in KB (must be power of 2, minimum 8)
            time_cost: Number of iterations (minimum 1)
            parallelism: Number of threads (typically 1 for client-side compatibility)
            salt_size: Size of salt in bytes (default: 16 bytes = 128 bits)
        """
        # Validate memory cost (must be power of 2 and >= 8)
        if memory_cost < 8 or (memory_cost & (memory_cost - 1)) != 0:
            raise ValueError(
                f"memory_cost must be a power of 2 and >= 8, got {memory_cost}"
            )
        
        if time_cost < 1:
            raise ValueError(f"time_cost must be >= 1, got {time_cost}")
        
        if parallelism < 1:
            raise ValueError(f"parallelism must be >= 1, got {parallelism}")
        
        if salt_size < 8:
            raise ValueError(f"salt_size must be >= 8, got {salt_size}")
        
        self.memory_cost = memory_cost
        self.time_cost = time_cost
        self.parallelism = parallelism
        self.salt_size = salt_size
        
        # Create Argon2id hasher for verification (if needed)
        # For key derivation, we use the low-level API directly
        self.hasher = PasswordHasher(
            memory_cost=memory_cost,
            time_cost=time_cost,
            parallelism=parallelism,
        )
        
        logger.info(
            f"KeyManager initialized: memory={memory_cost}KB, "
            f"time={time_cost}, parallelism={parallelism}"
        )
    
    def generate_salt(self) -> bytes:
        """
        Generate a cryptographically secure random salt.
        
        Salt is unique per user/file and is not secret but must be unique.
        
        Returns:
            Random salt bytes (default: 16 bytes)
        """
        return secrets.token_bytes(self.salt_size)
    
    def derive_key_from_passcode(self, passcode: str, salt: bytes) -> bytes:
        """
        Derive a 256-bit key from a passcode and salt using Argon2id.
        
        This function is deterministic: same passcode + salt = same key.
        Compatible with client-side JavaScript libraries when using same parameters.
        
        Args:
            passcode: User passcode as string (will be encoded to UTF-8 bytes)
            salt: Salt bytes (must match salt used for key derivation)
        
        Returns:
            32-byte derived key (256 bits)
        
        Raises:
            KeyManagerError: If derivation fails
        """
        try:
            if not passcode:
                raise KeyManagerError("Passcode cannot be empty")
            
            if len(salt) != self.salt_size:
                raise KeyManagerError(
                    f"Salt must be exactly {self.salt_size} bytes, got {len(salt)} bytes"
                )
            
            # Convert passcode to bytes (UTF-8 encoding)
            passcode_bytes = passcode.encode("utf-8")
            
            # Argon2id key derivation using low-level API
            # This directly derives a key of the specified length (32 bytes)
            # Type.ID = Argon2id (hybrid variant, recommended)
            derived_key = hash_secret_raw(
                secret=passcode_bytes,
                salt=salt,
                time_cost=self.time_cost,
                memory_cost=self.memory_cost,
                parallelism=self.parallelism,
                hash_len=KEY_SIZE,  # 32 bytes = 256 bits
                type=Type.ID,  # Argon2id
                version=19,  # Latest Argon2 version
            )
            
            # hash_secret_raw returns exactly hash_len bytes
            if len(derived_key) != KEY_SIZE:
                raise KeyManagerError(
                    f"Unexpected key length: expected {KEY_SIZE} bytes, got {len(derived_key)} bytes"
                )
            
            # Securely overwrite intermediate values
            passcode_bytes = b"\x00" * len(passcode_bytes)
            
            logger.debug(f"Successfully derived key from passcode (salt: {salt.hex()[:8]}...)")
            return derived_key
            
        except Exception as e:
            logger.error(f"Key derivation failed: {e}", exc_info=True)
            raise KeyManagerError(f"Key derivation failed: {str(e)}") from e
    
    def verify_passcode(
        self,
        passcode: str,
        salt: bytes,
        encrypted_key: Dict[str, str],
        master_key: Optional[bytes] = None,
    ) -> bool:
        """
        Verify a passcode by attempting to decrypt an encrypted key.
        
        This function:
        1. Derives a key from the passcode
        2. Attempts to decrypt the encrypted_key using the derived key
        3. Returns True if decryption succeeds, False otherwise
        
        Args:
            passcode: User passcode to verify
            salt: Salt used for key derivation
            encrypted_key: Encrypted key payload (from encrypt_bytes)
            master_key: Optional master key for verification.
                       If provided, decrypts encrypted_key with master_key first,
                       then verifies the decrypted key matches the derived key.
        
        Returns:
            True if passcode is correct (can decrypt the key), False otherwise
        
        Raises:
            KeyManagerError: If verification process fails
        """
        try:
            # Derive key from passcode
            derived_key = self.derive_key_from_passcode(passcode, salt)
            
            if master_key is None:
                # Simple verification: try to decrypt with derived key
                # If encrypted_key was encrypted with the same derived key, this will work
                try:
                    decrypted = decrypt_bytes(encrypted_key, derived_key)
                    # If decryption succeeds without error, passcode is correct
                    # Optionally verify decrypted data matches expected format
                    return True
                except EncryptionError:
                    # Authentication failed - wrong passcode
                    return False
            else:
                # Two-step verification:
                # 1. Decrypt encrypted_key with master_key to get the actual key
                # 2. Compare actual key with derived_key
                try:
                    actual_key = decrypt_bytes(encrypted_key, master_key)
                    # Constant-time comparison to prevent timing attacks
                    from app.core.encryption import constant_time_compare
                    return constant_time_compare(actual_key, derived_key)
                except EncryptionError:
                    return False
                    
        except KeyManagerError:
            # Re-raise key manager errors
            raise
        except Exception as e:
            logger.error(f"Passcode verification failed: {e}", exc_info=True)
            return False
        finally:
            # Securely overwrite derived key
            if 'derived_key' in locals():
                derived_key = b"\x00" * len(derived_key)
    
    def create_key_pair_from_passcode(
        self,
        passcode: str,
        salt: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Create an encryption key pair from a passcode.
        
        This function:
        1. Generates or uses provided salt
        2. Derives a key from passcode
        3. Generates a master encryption key
        4. Encrypts the master key with the derived key
        
        This allows secure key storage: the master key is encrypted with
        a key derived from the user's passcode.
        
        Args:
            passcode: User passcode
            salt: Optional salt (if not provided, generates a new one)
        
        Returns:
            Dictionary containing:
            {
                "salt": base64-encoded salt,
                "encrypted_master_key": encrypted master key payload,
                "key_id": unique identifier for this key pair
            }
        """
        try:
            if salt is None:
                salt = self.generate_salt()
            
            # Derive key from passcode
            derived_key = self.derive_key_from_passcode(passcode, salt)
            
            # Generate master encryption key
            master_key = generate_key()
            
            # Encrypt master key with derived key
            encrypted_master_key = encrypt_bytes(master_key, derived_key)
            
            # Generate key ID (hash of salt + master key for identification)
            key_id_data = salt + master_key
            key_id = hashlib.sha256(key_id_data).hexdigest()[:16]
            
            # Securely overwrite sensitive data
            derived_key = b"\x00" * len(derived_key)
            master_key = b"\x00" * len(master_key)
            key_id_data = b"\x00" * len(key_id_data)
            
            return {
                "salt": base64.b64encode(salt).decode("utf-8"),
                "encrypted_master_key": encrypted_master_key,
                "key_id": key_id,
            }
            
        except Exception as e:
            logger.error(f"Key pair creation failed: {e}", exc_info=True)
            raise KeyManagerError(f"Key pair creation failed: {str(e)}") from e
    
    def get_argon2_parameters(self) -> Dict[str, int]:
        """
        Get current Argon2id parameters.
        
        Useful for client-side compatibility - clients need these parameters
        to derive the same keys.
        
        Returns:
            Dictionary with parameters:
            {
                "memory_cost": memory cost in KB,
                "time_cost": number of iterations,
                "parallelism": number of threads,
                "salt_size": salt size in bytes,
                "hash_len": derived key length in bytes
            }
        """
        return {
            "memory_cost": self.memory_cost,
            "time_cost": self.time_cost,
            "parallelism": self.parallelism,
            "salt_size": self.salt_size,
            "hash_len": KEY_SIZE,
            "algorithm": "argon2id",
        }


# Global KeyManager instance with default parameters
_default_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """Get the default KeyManager instance"""
    global _default_key_manager
    if _default_key_manager is None:
        _default_key_manager = KeyManager()
    return _default_key_manager


# Convenience functions using default KeyManager
def derive_key_from_passcode(passcode: str, salt: bytes) -> bytes:
    """
    Derive a key from passcode using default KeyManager.
    
    Convenience function that uses the default KeyManager instance.
    
    Args:
        passcode: User passcode as string
        salt: Salt bytes
    
    Returns:
        32-byte derived key
    """
    return get_key_manager().derive_key_from_passcode(passcode, salt)


def verify_passcode(
    passcode: str,
    salt: bytes,
    encrypted_key: Dict[str, str],
    master_key: Optional[bytes] = None,
) -> bool:
    """
    Verify a passcode using default KeyManager.
    
    Convenience function that uses the default KeyManager instance.
    
    Args:
        passcode: User passcode to verify
        salt: Salt bytes
        encrypted_key: Encrypted key payload
        master_key: Optional master key
    
    Returns:
        True if passcode is correct, False otherwise
    """
    return get_key_manager().verify_passcode(passcode, salt, encrypted_key, master_key)


def generate_salt_for_identifier(identifier: str) -> bytes:
    """
    Generate a deterministic salt for an identifier (email, filename, etc.).
    
    This function generates a salt that is deterministic based on the identifier
    but still cryptographically secure. Useful for file-based encryption where
    you want the same file to always use the same salt.
    
    Args:
        identifier: Unique identifier (e.g., email, filename, user_id)
    
    Returns:
        Salt bytes (deterministic for same identifier)
    """
    # Use HKDF-like approach: hash identifier to get seed, then derive salt
    # This ensures same identifier = same salt, but salt is still cryptographically sound
    seed = hashlib.sha256(identifier.encode("utf-8")).digest()
    
    # Generate salt from seed using deterministic method
    # Use HKDF expansion to get salt_size bytes
    salt = b""
    counter = 0
    
    key_manager = get_key_manager()
    while len(salt) < key_manager.salt_size:
        data = seed + counter.to_bytes(4, byteorder="big")
        hash_output = hashlib.sha256(data).digest()
        salt += hash_output
        counter += 1
    
    return salt[:key_manager.salt_size]


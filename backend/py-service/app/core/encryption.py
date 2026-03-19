"""Secure Encryption Engine using AES-256-GCM

This module provides authenticated encryption using AES-256-GCM with:
- Secure random nonce generation
- Authenticated encryption (prevents tampering)
- Base64 encoding for safe transport
- Streaming support for large files
- Constant-time operations
- Secure memory handling
"""

import base64
import secrets
from typing import Dict, Optional, BinaryIO, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import logging

logger = logging.getLogger(__name__)

# AES-256-GCM constants
NONCE_SIZE = 12  # 96 bits (recommended for GCM)
KEY_SIZE = 32  # 256 bits for AES-256
TAG_SIZE = 16  # 128-bit authentication tag (GCM standard)


class EncryptionError(Exception):
    """Custom exception for encryption errors"""
    pass


def derive_key_from_password(password: bytes, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Derive a 256-bit key from a password using PBKDF2.
    
    Args:
        password: Password as bytes
        salt: Optional salt. If not provided, a random salt is generated.
    
    Returns:
        Tuple of (key, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=100000,  # OWASP recommended minimum
        backend=default_backend()
    )
    
    key = kdf.derive(password)
    return key, salt


def generate_key() -> bytes:
    """
    Generate a cryptographically secure random 256-bit key.
    
    Returns:
        32-byte random key suitable for AES-256
    """
    return secrets.token_bytes(KEY_SIZE)


def encrypt_bytes(data: bytes, key: bytes) -> Dict[str, str]:
    """
    Encrypt data using AES-256-GCM with authenticated encryption.
    
    This function provides:
    - Authenticated encryption (detects tampering)
    - Random nonce for each encryption
    - Base64 encoding for safe transport
    - Constant-time operations
    
    Args:
        data: Plaintext data to encrypt (bytes)
        key: 32-byte encryption key (must be exactly 32 bytes)
    
    Returns:
        Dictionary containing:
        {
            "ciphertext": base64-encoded encrypted data,
            "nonce": base64-encoded nonce,
            "tag": base64-encoded authentication tag (included in ciphertext for GCM)
        }
    
    Raises:
        EncryptionError: If encryption fails or key is invalid
    """
    try:
        # Validate key length
        if len(key) != KEY_SIZE:
            raise EncryptionError(f"Key must be exactly {KEY_SIZE} bytes, got {len(key)} bytes")
        
        # Generate random nonce (96 bits for GCM)
        nonce = secrets.token_bytes(NONCE_SIZE)
        
        # Create AES-GCM cipher
        aesgcm = AESGCM(key)
        
        # Encrypt with authentication (GCM mode)
        # GCM automatically includes authentication tag
        ciphertext = aesgcm.encrypt(nonce, data, None)
        
        # GCM returns ciphertext + tag concatenated
        # Separate them for clarity in the response
        # For GCM, tag is always last 16 bytes
        actual_ciphertext = ciphertext[:-TAG_SIZE]
        tag = ciphertext[-TAG_SIZE:]
        
        # Encode to base64 for safe transport
        result = {
            "ciphertext": base64.b64encode(actual_ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8"),
        }
        
        # Securely overwrite sensitive data in memory
        # Note: This is best-effort; Python GC makes true zeroization difficult
        nonce = b"\x00" * len(nonce)
        actual_ciphertext = b"\x00" * len(actual_ciphertext)
        
        logger.debug(f"Encrypted {len(data)} bytes of data")
        return result
        
    except Exception as e:
        logger.error(f"Encryption failed: {e}", exc_info=True)
        raise EncryptionError(f"Encryption failed: {str(e)}") from e


def decrypt_bytes(payload: Dict[str, str], key: bytes) -> bytes:
    """
    Decrypt data encrypted with encrypt_bytes().
    
    This function provides:
    - Authenticated decryption (verifies data integrity)
    - Constant-time verification (prevents timing attacks)
    - Secure memory handling
    
    Args:
        payload: Dictionary containing:
            - "ciphertext": base64-encoded encrypted data
            - "nonce": base64-encoded nonce
            - "tag": base64-encoded authentication tag
        key: 32-byte decryption key (must match encryption key)
    
    Returns:
        Decrypted plaintext data (bytes)
    
    Raises:
        EncryptionError: If decryption fails, authentication fails, or key is invalid
    """
    try:
        # Validate key length
        if len(key) != KEY_SIZE:
            raise EncryptionError(f"Key must be exactly {KEY_SIZE} bytes, got {len(key)} bytes")
        
        # Validate payload structure
        required_fields = ["ciphertext", "nonce", "tag"]
        for field in required_fields:
            if field not in payload:
                raise EncryptionError(f"Missing required field: {field}")
        
        # Decode from base64
        try:
            ciphertext = base64.b64decode(payload["ciphertext"])
            nonce = base64.b64decode(payload["nonce"])
            tag = base64.b64decode(payload["tag"])
        except Exception as e:
            raise EncryptionError(f"Invalid base64 encoding: {str(e)}") from e
        
        # Validate nonce length
        if len(nonce) != NONCE_SIZE:
            raise EncryptionError(f"Invalid nonce length: expected {NONCE_SIZE} bytes, got {len(nonce)}")
        
        # Validate tag length
        if len(tag) != TAG_SIZE:
            raise EncryptionError(f"Invalid tag length: expected {TAG_SIZE} bytes, got {len(tag)}")
        
        # Reconstruct ciphertext + tag (GCM format)
        # GCM expects ciphertext and tag concatenated
        full_ciphertext = ciphertext + tag
        
        # Create AES-GCM cipher
        aesgcm = AESGCM(key)
        
        # Decrypt with authentication verification
        # GCM will raise an exception if authentication fails
        plaintext = aesgcm.decrypt(nonce, full_ciphertext, None)
        
        logger.debug(f"Decrypted {len(plaintext)} bytes of data")
        return plaintext
        
    except EncryptionError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch authentication failures and other errors
        error_msg = str(e).lower()
        if "authentication" in error_msg or "tag" in error_msg:
            logger.warning("Decryption failed: Authentication failed (data may be tampered)")
            raise EncryptionError("Authentication failed: Data may have been tampered with")
        else:
            logger.error(f"Decryption failed: {e}", exc_info=True)
            raise EncryptionError(f"Decryption failed: {str(e)}") from e
    finally:
        # Best-effort secure memory cleanup
        if 'ciphertext' in locals():
            ciphertext = b"\x00" * len(ciphertext) if ciphertext else b""
        if 'nonce' in locals():
            nonce = b"\x00" * len(nonce) if nonce else b""
        if 'tag' in locals():
            tag = b"\x00" * len(tag) if tag else b""


def encrypt_stream(
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    key: bytes,
    chunk_size: int = 64 * 1024
) -> Dict[str, str]:
    """
    Encrypt a stream of data (for large files).
    
    This function encrypts data in chunks to handle large files efficiently
    while maintaining security. Each chunk is encrypted independently with
    a unique nonce derived from the main nonce.
    
    Args:
        input_stream: Readable binary stream (file-like object)
        output_stream: Writable binary stream (file-like object)
        key: 32-byte encryption key
        chunk_size: Size of each chunk to process (default: 64KB)
    
    Returns:
        Dictionary containing encryption metadata:
        {
            "nonce": base64-encoded main nonce,
            "chunk_count": number of chunks encrypted,
            "total_size": total bytes encrypted
        }
    
    Raises:
        EncryptionError: If encryption fails
    """
    try:
        if len(key) != KEY_SIZE:
            raise EncryptionError(f"Key must be exactly {KEY_SIZE} bytes")
        
        # Generate main nonce
        main_nonce = secrets.token_bytes(NONCE_SIZE)
        
        # Write nonce to output stream
        output_stream.write(base64.b64encode(main_nonce).decode("utf-8").encode("utf-8") + b"\n")
        
        aesgcm = AESGCM(key)
        chunk_count = 0
        total_size = 0
        
        # Process data in chunks
        while True:
            chunk = input_stream.read(chunk_size)
            if not chunk:
                break
            
            # Derive unique nonce for this chunk
            # Use counter-based nonce derivation (nonce + chunk counter)
            chunk_nonce = _derive_chunk_nonce(main_nonce, chunk_count)
            
            # Encrypt chunk
            encrypted_chunk = aesgcm.encrypt(chunk_nonce, chunk, None)
            
            # Write encrypted chunk (base64 encoded, one per line)
            encoded = base64.b64encode(encrypted_chunk).decode("utf-8")
            output_stream.write(encoded.encode("utf-8") + b"\n")
            
            chunk_count += 1
            total_size += len(chunk)
            
            # Securely overwrite chunk in memory
            chunk = b"\x00" * len(chunk)
        
        logger.info(f"Encrypted stream: {chunk_count} chunks, {total_size} bytes")
        
        # Return metadata (nonce is already written to stream)
        result = {
            "nonce": base64.b64encode(main_nonce).decode("utf-8"),
            "chunk_count": chunk_count,
            "total_size": total_size,
        }
        
        # Securely overwrite main nonce after encoding
        main_nonce = b"\x00" * len(main_nonce)
        
        return result
        
    except Exception as e:
        logger.error(f"Stream encryption failed: {e}", exc_info=True)
        raise EncryptionError(f"Stream encryption failed: {str(e)}") from e


def decrypt_stream(
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    key: bytes
) -> int:
    """
    Decrypt a stream of data encrypted with encrypt_stream().
    
    Args:
        input_stream: Readable binary stream containing encrypted data
        output_stream: Writable binary stream for decrypted data
        key: 32-byte decryption key (must match encryption key)
    
    Returns:
        Total bytes decrypted
    
    Raises:
        EncryptionError: If decryption or authentication fails
    """
    try:
        if len(key) != KEY_SIZE:
            raise EncryptionError(f"Key must be exactly {KEY_SIZE} bytes")
        
        # Read main nonce (first line)
        nonce_line = input_stream.readline().strip()
        if not nonce_line:
            raise EncryptionError("Stream is empty or missing nonce")
        
        main_nonce = base64.b64decode(nonce_line)
        if len(main_nonce) != NONCE_SIZE:
            raise EncryptionError(f"Invalid nonce length: {len(main_nonce)}")
        
        aesgcm = AESGCM(key)
        chunk_count = 0
        total_size = 0
        
        # Process encrypted chunks
        for line in input_stream:
            line = line.strip()
            if not line:
                continue
            
            # Decode base64
            encrypted_chunk = base64.b64decode(line)
            
            # Derive nonce for this chunk
            chunk_nonce = _derive_chunk_nonce(main_nonce, chunk_count)
            
            # Decrypt chunk (GCM verifies authentication)
            decrypted_chunk = aesgcm.decrypt(chunk_nonce, encrypted_chunk, None)
            
            # Write decrypted chunk
            output_stream.write(decrypted_chunk)
            
            chunk_count += 1
            total_size += len(decrypted_chunk)
            
            # Securely overwrite
            decrypted_chunk = b"\x00" * len(decrypted_chunk)
            encrypted_chunk = b"\x00" * len(encrypted_chunk)
        
        # Securely overwrite main nonce
        main_nonce = b"\x00" * len(main_nonce)
        
        logger.info(f"Decrypted stream: {chunk_count} chunks, {total_size} bytes")
        return total_size
        
    except EncryptionError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "authentication" in error_msg or "tag" in error_msg:
            raise EncryptionError("Stream authentication failed: Data may have been tampered with")
        else:
            logger.error(f"Stream decryption failed: {e}", exc_info=True)
            raise EncryptionError(f"Stream decryption failed: {str(e)}") from e


def _derive_chunk_nonce(main_nonce: bytes, chunk_index: int) -> bytes:
    """
    Derive a unique nonce for a chunk using the main nonce and chunk index.
    
    This ensures each chunk has a unique nonce while maintaining determinism.
    Uses first 8 bytes of nonce + 4-byte chunk counter (big-endian).
    
    Args:
        main_nonce: Main nonce (12 bytes)
        chunk_index: Chunk index (0-based)
    
    Returns:
        12-byte nonce for the chunk
    """
    if len(main_nonce) != NONCE_SIZE:
        raise ValueError(f"Main nonce must be {NONCE_SIZE} bytes")
    
    # Use first 8 bytes of main nonce + 4-byte counter
    # This gives us 96 bits total (GCM requirement)
    chunk_counter = chunk_index.to_bytes(4, byteorder="big")
    chunk_nonce = main_nonce[:8] + chunk_counter
    
    return chunk_nonce


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """
    Constant-time comparison of two byte strings.
    
    This prevents timing attacks when comparing sensitive data.
    
    Args:
        a: First byte string
        b: Second byte string
    
    Returns:
        True if strings are equal, False otherwise
    """
    if len(a) != len(b):
        return False
    
    # Use secrets.compare_digest for constant-time comparison
    return secrets.compare_digest(a, b)


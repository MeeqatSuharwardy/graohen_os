"""Example usage of encryption module

This file demonstrates how to use the encryption functions.
It can be deleted or used as reference.
"""

from app.core.encryption import (
    encrypt_bytes,
    decrypt_bytes,
    encrypt_stream,
    decrypt_stream,
    generate_key,
    derive_key_from_password,
)
import io


def example_basic_encryption():
    """Example: Basic byte encryption"""
    # Generate a random key (or derive from password)
    key = generate_key()
    
    # Data to encrypt
    sensitive_data = b"This is sensitive information that needs encryption"
    
    # Encrypt
    encrypted_payload = encrypt_bytes(sensitive_data, key)
    print("Encrypted payload:", encrypted_payload)
    
    # Decrypt
    decrypted_data = decrypt_bytes(encrypted_payload, key)
    print("Decrypted data:", decrypted_data.decode("utf-8"))
    assert decrypted_data == sensitive_data


def example_password_based_encryption():
    """Example: Password-based key derivation"""
    # User password
    password = b"my_secret_password"
    
    # Derive key from password
    key, salt = derive_key_from_password(password)
    
    # Encrypt data
    data = b"Sensitive data"
    payload = encrypt_bytes(data, key)
    
    # To decrypt later, you need to re-derive the key with same password and salt
    # (In practice, store salt securely alongside encrypted data)
    key2, _ = derive_key_from_password(password, salt)
    decrypted = decrypt_bytes(payload, key2)
    
    assert decrypted == data


def example_stream_encryption():
    """Example: Streaming encryption for large files"""
    key = generate_key()
    
    # Create a large file-like object
    large_data = b"X" * (5 * 1024 * 1024)  # 5 MB
    input_stream = io.BytesIO(large_data)
    output_stream = io.BytesIO()
    
    # Encrypt stream
    metadata = encrypt_stream(input_stream, output_stream, key, chunk_size=64 * 1024)
    print(f"Encrypted {metadata['total_size']} bytes in {metadata['chunk_count']} chunks")
    
    # Reset streams for decryption
    output_stream.seek(0)
    decrypted_stream = io.BytesIO()
    
    # Decrypt stream
    decrypted_size = decrypt_stream(output_stream, decrypted_stream, key)
    print(f"Decrypted {decrypted_size} bytes")
    
    # Verify
    decrypted_stream.seek(0)
    decrypted_data = decrypted_stream.read()
    assert decrypted_data == large_data


def example_file_encryption():
    """Example: Encrypting actual files"""
    key = generate_key()
    
    # Encrypt a file
    with open("sensitive_file.txt", "rb") as infile:
        with open("encrypted_file.enc", "wb") as outfile:
            metadata = encrypt_stream(infile, outfile, key)
    
    # Decrypt the file
    with open("encrypted_file.enc", "rb") as infile:
        with open("decrypted_file.txt", "wb") as outfile:
            decrypt_stream(infile, outfile, key)


if __name__ == "__main__":
    print("Example 1: Basic encryption")
    example_basic_encryption()
    print("\nExample 2: Password-based encryption")
    example_password_based_encryption()
    print("\nExample 3: Stream encryption")
    example_stream_encryption()
    print("\nAll examples completed successfully!")


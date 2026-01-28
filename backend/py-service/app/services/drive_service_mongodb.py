"""Drive Service with MongoDB and Strong Encryption

This service handles encrypted file storage in MongoDB with multi-layer encryption.
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.core.encryption import (
    generate_key,
    KEY_SIZE,
)
from app.core.strong_encryption import (
    encrypt_multi_layer,
    decrypt_multi_layer,
    generate_strong_key,
    StrongEncryptionError,
)
from app.core.key_manager import (
    derive_key_from_passcode,
    generate_salt_for_identifier,
    get_key_manager,
)
from app.core.mongodb import get_mongodb
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class DriveEncryptionError(Exception):
    """Custom exception for drive encryption errors"""
    pass


class DriveServiceMongoDB:
    """Drive service using MongoDB with strong multi-layer encryption"""
    
    def __init__(self):
        self.key_manager = get_key_manager()
    
    async def encrypt_and_store_file(
        self,
        file_content: bytes,
        filename: str,
        file_size: int,
        owner_email: str,
        content_type: Optional[str] = None,
        passcode: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Encrypt file with multi-layer encryption and store in MongoDB.
        
        Uses 3 layers of encryption for maximum security.
        """
        try:
            # Generate file ID
            file_id = secrets.token_urlsafe(32)
            
            # Generate content key
            content_key = generate_strong_key()
            
            # Determine encryption keys
            if passcode:
                # Generate salt for passcode
                salt = self.key_manager.generate_salt()
                passcode_key = derive_key_from_passcode(passcode, salt)
                
                # Use passcode key as primary, derive secondary
                primary_key = passcode_key
                secondary_key_data = passcode.encode() + salt
                secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
                
                passcode_salt_b64 = base64.b64encode(salt).decode("utf-8")
                passcode_protected = True
            else:
                # Derive keys from user email
                user_salt = generate_salt_for_identifier(owner_email)
                primary_key = derive_key_from_passcode(owner_email, user_salt)
                
                # Secondary key derived from user email + salt hash
                secondary_key_data = owner_email.encode() + user_salt
                secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
                
                passcode_salt_b64 = None
                passcode_protected = False
            
            # Encrypt file content with multi-layer encryption
            encrypted_content = encrypt_multi_layer(
                file_content,
                primary_key=content_key,
                secondary_key=secondary_key,
                layers=3  # Maximum security: 3 layers
            )
            
            # Encrypt content key with multi-layer encryption
            encrypted_content_key = encrypt_multi_layer(
                content_key,
                primary_key=primary_key,
                secondary_key=secondary_key,
                layers=3
            )
            
            # Calculate expiration
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            # Store in MongoDB
            db = get_mongodb()
            files_collection = db.files
            
            file_doc = {
                "file_id": file_id,
                "owner_email": owner_email.lower(),
                "filename": filename,
                "size": file_size,
                "content_type": content_type,
                "encrypted_content": encrypted_content,
                "encrypted_content_key": encrypted_content_key,
                "passcode_protected": passcode_protected,
                "passcode_salt": passcode_salt_b64,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
            }
            
            await files_collection.insert_one(file_doc)
            
            logger.info(f"File stored in MongoDB: {file_id[:8]}...")
            
            return {
                "file_id": file_id,
                "encrypted_content": encrypted_content,
                "encrypted_content_key": encrypted_content_key,
                "passcode_protected": passcode_protected,
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt and store file: {e}", exc_info=True)
            raise DriveEncryptionError(f"Failed to encrypt file: {str(e)}") from e
    
    async def get_file_from_mongodb(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file document from MongoDB"""
        try:
            db = get_mongodb()
            files_collection = db.files
            
            file_doc = await files_collection.find_one({"file_id": file_id})
            return file_doc
            
        except Exception as e:
            logger.error(f"Failed to get file from MongoDB: {e}", exc_info=True)
            return None
    
    async def decrypt_file_for_authenticated_user(
        self,
        file_id: str,
        user_email: str,
    ) -> bytes:
        """Decrypt file for authenticated user"""
        try:
            # Get file from MongoDB
            file_doc = await self.get_file_from_mongodb(file_id)
            if not file_doc:
                raise DriveEncryptionError("File not found")
            
            # Check expiration
            if file_doc.get("expires_at"):
                expires_at = file_doc["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.utcnow() > expires_at:
                    raise DriveEncryptionError("File has expired")
            
            # Check if passcode protected
            if file_doc.get("passcode_protected"):
                raise DriveEncryptionError("File requires passcode unlock")
            
            # Derive keys from user email
            user_salt = generate_salt_for_identifier(user_email)
            primary_key = derive_key_from_passcode(user_email, user_salt)
            secondary_key_data = user_email.encode() + user_salt
            secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
            
            # Decrypt content key
            encrypted_content_key = file_doc["encrypted_content_key"]
            content_key = decrypt_multi_layer(
                encrypted_content_key,
                primary_key=primary_key,
                secondary_key=secondary_key,
            )
            
            # Decrypt file content
            encrypted_content = file_doc["encrypted_content"]
            file_content = decrypt_multi_layer(
                encrypted_content,
                primary_key=content_key,
                secondary_key=secondary_key,
            )
            
            return file_content
            
        except StrongEncryptionError as e:
            raise DriveEncryptionError(f"Decryption failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to decrypt file: {e}", exc_info=True)
            raise DriveEncryptionError(f"Failed to decrypt file: {str(e)}") from e
    
    async def decrypt_file_with_passcode(
        self,
        file_id: str,
        passcode: str,
    ) -> bytes:
        """Decrypt file with passcode"""
        try:
            # Get file from MongoDB
            file_doc = await self.get_file_from_mongodb(file_id)
            if not file_doc:
                raise DriveEncryptionError("File not found")
            
            # Check expiration
            if file_doc.get("expires_at"):
                expires_at = file_doc["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.utcnow() > expires_at:
                    raise DriveEncryptionError("File has expired")
            
            # Get salt
            passcode_salt_b64 = file_doc.get("passcode_salt")
            if not passcode_salt_b64:
                raise DriveEncryptionError("File does not have passcode protection")
            
            salt = base64.b64decode(passcode_salt_b64)
            
            # Derive keys from passcode
            primary_key = derive_key_from_passcode(passcode, salt)
            secondary_key_data = passcode.encode() + salt
            secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
            
            # Decrypt content key
            encrypted_content_key = file_doc["encrypted_content_key"]
            content_key = decrypt_multi_layer(
                encrypted_content_key,
                primary_key=primary_key,
                secondary_key=secondary_key,
            )
            
            # Decrypt file content
            encrypted_content = file_doc["encrypted_content"]
            file_content = decrypt_multi_layer(
                encrypted_content,
                primary_key=content_key,
                secondary_key=secondary_key,
            )
            
            return file_content
            
        except StrongEncryptionError as e:
            raise DriveEncryptionError(f"Decryption failed: Incorrect passcode") from e
        except Exception as e:
            logger.error(f"Failed to decrypt file: {e}", exc_info=True)
            raise DriveEncryptionError(f"Failed to decrypt file: {str(e)}") from e
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from MongoDB"""
        try:
            db = get_mongodb()
            files_collection = db.files
            
            result = await files_collection.delete_one({"file_id": file_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}", exc_info=True)
            return False


# Global service instance
_drive_service_mongodb: Optional[DriveServiceMongoDB] = None


def get_drive_service_mongodb() -> DriveServiceMongoDB:
    """Get global drive service instance"""
    global _drive_service_mongodb
    if _drive_service_mongodb is None:
        _drive_service_mongodb = DriveServiceMongoDB()
    return _drive_service_mongodb

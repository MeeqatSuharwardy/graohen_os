"""User Service with MongoDB and Strong Encryption

This service handles encrypted user storage in MongoDB with multi-layer encryption.
"""

import secrets
import hashlib
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from app.core.user_encryption import (
    encrypt_user_data,
    decrypt_user_data,
    hash_email_for_lookup,
    generate_user_encryption_keys,
)
from app.core.security import hash_password, verify_password
from app.core.mongodb import get_mongodb
import logging

logger = logging.getLogger(__name__)


class UserServiceMongoDB:
    """User service using MongoDB with strong multi-layer encryption"""
    
    def __init__(self):
        try:
            self.db = get_mongodb()
            self.users_collection = self.db["users"]
        except RuntimeError as e:
            logger.error(f"MongoDB not initialized: {e}")
            raise RuntimeError("MongoDB not initialized. Call init_mongodb() first.") from e
    
    async def create_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user with encrypted data.
        
        Encrypts email and full_name before storing in MongoDB.
        """
        try:
            # Check if user already exists
            existing = await self.get_user_by_email(email)
            if existing:
                raise ValueError("Email already registered")
            
            # Hash password
            hashed_password = hash_password(password)
            
            # Encrypt email (generate keys once, reuse for full_name)
            primary_key, secondary_key = generate_user_encryption_keys()
            encrypted_email_bytes, email_metadata = encrypt_user_data(
                email.lower(),
                primary_key=primary_key,
                secondary_key=secondary_key
            )
            
            # Encrypt full_name if provided (reuse same keys)
            encrypted_full_name_bytes = None
            if full_name:
                encrypted_full_name_bytes, _ = encrypt_user_data(
                    full_name,
                    primary_key=primary_key,
                    secondary_key=secondary_key
                )
            
            # Create email hash for lookup
            email_hash = hash_email_for_lookup(email)
            
            # Create user document
            user_doc = {
                "encrypted_email": encrypted_email_bytes,
                "email_hash": email_hash,
                "hashed_password": hashed_password,
                "encrypted_full_name": encrypted_full_name_bytes,
                "encryption_metadata": json.dumps(email_metadata),
                "is_active": True,
                "is_verified": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            # Insert into MongoDB
            result = await self.users_collection.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            # Return user dict (for compatibility)
            return {
                "id": user_id,
                "email": email.lower(),
                "hashed_password": hashed_password,
                "full_name": full_name,
                "is_active": True,
                "is_verified": False,
                "created_at": user_doc["created_at"],
                "updated_at": user_doc["updated_at"],
            }
            
        except ValueError as e:
            # Re-raise ValueError (email already exists)
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}", exc_info=True)
            raise Exception(f"Failed to create user account: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email from MongoDB.
        
        Uses email hash for lookup, then decrypts email for verification.
        """
        try:
            # Hash email for lookup
            email_hash = hash_email_for_lookup(email)
            
            # Query MongoDB by email hash
            user_doc = await self.users_collection.find_one({"email_hash": email_hash})
            
            if not user_doc:
                return None
            
            # Decrypt email using metadata
            encryption_metadata = user_doc.get("encryption_metadata")
            if not encryption_metadata:
                logger.error("User document missing encryption_metadata")
                return None
            
            # Parse metadata
            if isinstance(encryption_metadata, str):
                metadata = json.loads(encryption_metadata)
            else:
                metadata = encryption_metadata
            
            # Decrypt email
            decrypted_email = decrypt_user_data(
                user_doc.get("encrypted_email"),
                json.dumps(metadata) if not isinstance(encryption_metadata, str) else encryption_metadata
            )
            
            # Verify email matches (double-check)
            if decrypted_email.lower() != email.lower():
                logger.warning(f"Email hash collision detected for hash: {email_hash[:8]}...")
                return None
            
            # Decrypt full_name if present
            decrypted_full_name = None
            encrypted_full_name = user_doc.get("encrypted_full_name")
            if encrypted_full_name:
                try:
                    decrypted_full_name = decrypt_user_data(
                        encrypted_full_name,
                        json.dumps(metadata) if not isinstance(encryption_metadata, str) else encryption_metadata
                    )
                except Exception as e:
                    logger.warning(f"Failed to decrypt full_name: {e}")
            
            # Convert created_at/updated_at to datetime if needed
            created_at = user_doc.get("created_at")
            updated_at = user_doc.get("updated_at")
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            # Return user dict
            return {
                "id": str(user_doc["_id"]),
                "email": decrypted_email.lower(),
                "hashed_password": user_doc.get("hashed_password"),
                "full_name": decrypted_full_name,
                "is_active": user_doc.get("is_active", True),
                "is_verified": user_doc.get("is_verified", False),
                "created_at": created_at,
                "updated_at": updated_at,
            }
            
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}", exc_info=True)
            return None
    
    async def verify_user_password(self, email: str, password: str) -> bool:
        """Verify user password"""
        user = await self.get_user_by_email(email)
        if not user:
            return False
        
        return verify_password(password, user["hashed_password"])
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user_doc = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                return None
            
            # Decrypt email
            encryption_metadata = user_doc.get("encryption_metadata")
            if not encryption_metadata:
                return None
            
            if isinstance(encryption_metadata, str):
                metadata = json.loads(encryption_metadata)
            else:
                metadata = encryption_metadata
            
            encrypted_email = user_doc.get("encrypted_email")
            decrypted_email = decrypt_user_data(
                encrypted_email,
                json.dumps(metadata) if not isinstance(encryption_metadata, str) else encryption_metadata
            )
            
            # Decrypt full_name
            decrypted_full_name = None
            encrypted_full_name = user_doc.get("encrypted_full_name")
            if encrypted_full_name:
                try:
                    decrypted_full_name = decrypt_user_data(
                        encrypted_full_name,
                        json.dumps(metadata) if not isinstance(encryption_metadata, str) else encryption_metadata
                    )
                except Exception as e:
                    logger.warning(f"Failed to decrypt full_name: {e}")
            
            created_at = user_doc.get("created_at")
            updated_at = user_doc.get("updated_at")
            
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            return {
                "id": str(user_doc["_id"]),
                "email": decrypted_email.lower(),
                "hashed_password": user_doc.get("hashed_password"),
                "full_name": decrypted_full_name,
                "is_active": user_doc.get("is_active", True),
                "is_verified": user_doc.get("is_verified", False),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}", exc_info=True)
            return None


# Global service instance
_user_service: Optional[UserServiceMongoDB] = None


def get_user_service() -> UserServiceMongoDB:
    """Get user service instance"""
    global _user_service
    if _user_service is None:
        _user_service = UserServiceMongoDB()
    return _user_service

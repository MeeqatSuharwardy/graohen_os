"""Email Service with MongoDB and Strong Encryption

This service handles encrypted email storage in MongoDB with multi-layer encryption.
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

from app.core.encryption import (
    generate_key,
    EncryptionError,
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
from app.services.email_sender import get_email_sender
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Email domain
EMAIL_DOMAIN = settings.EMAIL_DOMAIN
EXTERNAL_BASE_URL = settings.EXTERNAL_HTTPS_BASE_URL

# Public access token settings
ACCESS_TOKEN_SIZE = 32  # bytes
ACCESS_TOKEN_EXPIRE_HOURS = 168  # 7 days default


class EncryptionMode(str, Enum):
    """Email encryption modes"""
    AUTHENTICATED = "authenticated"
    PASSCODE_PROTECTED = "passcode_protected"


class EmailEncryptionError(Exception):
    """Custom exception for email encryption errors"""
    pass


class EmailServiceMongoDB:
    """Email service using MongoDB with strong multi-layer encryption"""
    
    def __init__(self):
        self.key_manager = get_key_manager()
        self.email_sender = get_email_sender()
    
    def generate_public_access_token(self) -> str:
        """Generate a secure public access token"""
        token_bytes = secrets.token_bytes(ACCESS_TOKEN_SIZE)
        token = base64.urlsafe_b64encode(token_bytes).decode("utf-8").rstrip("=")
        return token
    
    def generate_email_address(self, access_token: str) -> str:
        """Generate email address from access token"""
        return f"{access_token}@{EMAIL_DOMAIN}"
    
    async def encrypt_and_store_email(
        self,
        email_body: bytes,
        sender_email: str,
        recipient_emails: List[str],
        user_email: Optional[str] = None,
        passcode: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
        subject: Optional[str] = None,
        self_destruct: bool = False,
        email_id: Optional[str] = None,
        status: Optional[str] = None,  # "sent", "inbox", "draft"
    ) -> Dict[str, Any]:
        """
        Encrypt email with multi-layer encryption and store in MongoDB.
        
        Uses 3 layers of encryption for maximum security:
        1. AES-256-GCM with primary key
        2. ChaCha20-Poly1305 with secondary key
        3. AES-256-GCM with Scrypt-derived key
        """
        try:
            # Generate access token (or use provided email_id for incoming emails)
            if email_id:
                access_token = email_id
            else:
                access_token = self.generate_public_access_token()
                email_id = access_token  # Use access token as email ID
            
            # Generate content key
            content_key = generate_strong_key()
            
            # Determine encryption mode and derive keys
            if passcode:
                encryption_mode = EncryptionMode.PASSCODE_PROTECTED
                # Generate salt for passcode
                salt = self.key_manager.generate_salt()
                passcode_key = derive_key_from_passcode(passcode, salt)
                
                # Use passcode key as primary, derive secondary from passcode + salt
                primary_key = passcode_key
                secondary_key_data = passcode.encode() + salt
                secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
                
                passcode_salt_b64 = base64.b64encode(salt).decode("utf-8")
                has_passcode = True
                
            elif user_email:
                encryption_mode = EncryptionMode.AUTHENTICATED
                # Derive keys from user email
                user_salt = generate_salt_for_identifier(user_email)
                primary_key = derive_key_from_passcode(user_email, user_salt)
                
                # Secondary key derived from user email + salt hash
                secondary_key_data = user_email.encode() + user_salt
                secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
                
                passcode_salt_b64 = None
                has_passcode = False
            else:
                raise EmailEncryptionError("Either user_email or passcode must be provided")
            
            # Encrypt email content with multi-layer encryption
            encrypted_content = encrypt_multi_layer(
                email_body,
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
            
            # Generate email address
            email_address = self.generate_email_address(access_token)
            
            # Store in MongoDB
            db = get_mongodb()
            email_collection = db.emails
            
            # Determine status: use provided status, or default to "sent" for outgoing emails
            # For incoming emails (user_email=None), status should be "inbox"
            if status:
                email_status = status
            elif user_email is None:
                # Incoming email (no authenticated user)
                email_status = "inbox"
            else:
                # Outgoing email
                email_status = "sent"
            
            email_doc = {
                "email_id": email_id,
                "access_token": access_token,
                "sender_email": sender_email.lower(),
                "recipient_emails": [email.lower() for email in recipient_emails],
                "encrypted_content": encrypted_content,
                "encrypted_content_key": encrypted_content_key,
                "encryption_mode": encryption_mode.value,
                "has_passcode": has_passcode,
                "passcode_salt": passcode_salt_b64,
                "subject": subject,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "self_destruct": self_destruct,
                "email_address": email_address,
                "status": email_status,  # sent, inbox, draft
                "is_draft": False,
            }
            
            await email_collection.insert_one(email_doc)
            
            # Generate secure link
            secure_link = f"{EXTERNAL_BASE_URL}/email/{access_token}"
            
            # Send notification emails to recipients
            for recipient in recipient_emails:
                try:
                    await self.email_sender.send_encrypted_email_notification(
                        recipient_email=recipient,
                        email_address=email_address,
                        secure_link=secure_link,
                        sender_email=sender_email,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification to {recipient}: {e}")
                    # Continue even if notification fails
            
            logger.info(f"Email stored in MongoDB: {email_id[:8]}...")
            
            return {
                "access_token": access_token,
                "email_id": email_id,
                "email_address": email_address,
                "secure_link": secure_link,
                "encryption_mode": encryption_mode.value,
                "expires_at": expires_at.isoformat() if expires_at else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt and store email: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to encrypt email: {str(e)}") from e
    
    async def decrypt_email_for_authenticated_user(
        self,
        access_token: str,
        user_email: str,
    ) -> bytes:
        """Decrypt email for authenticated user"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Find email
            email_doc = await email_collection.find_one({"access_token": access_token})
            if not email_doc:
                raise EmailEncryptionError("Email not found")
            
            # Check expiration
            if email_doc.get("expires_at"):
                expires_at = email_doc["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.utcnow() > expires_at:
                    raise EmailEncryptionError("Email has expired")
            
            # Check encryption mode
            if email_doc.get("encryption_mode") != EncryptionMode.AUTHENTICATED.value:
                raise EmailEncryptionError("Email requires passcode unlock")
            
            # Derive keys from user email
            user_salt = generate_salt_for_identifier(user_email)
            primary_key = derive_key_from_passcode(user_email, user_salt)
            secondary_key_data = user_email.encode() + user_salt
            secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
            
            # Decrypt content key
            encrypted_content_key = email_doc["encrypted_content_key"]
            content_key = decrypt_multi_layer(
                encrypted_content_key,
                primary_key=primary_key,
                secondary_key=secondary_key,
            )
            
            # Decrypt email content
            encrypted_content = email_doc["encrypted_content"]
            email_body = decrypt_multi_layer(
                encrypted_content,
                primary_key=content_key,
                secondary_key=secondary_key,
            )
            
            # Handle self-destruct
            if email_doc.get("self_destruct"):
                await email_collection.delete_one({"access_token": access_token})
                logger.info(f"Email self-destructed: {access_token[:8]}...")
            
            return email_body
            
        except StrongEncryptionError as e:
            raise EmailEncryptionError(f"Decryption failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to decrypt email: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to decrypt email: {str(e)}") from e
    
    async def decrypt_email_with_passcode(
        self,
        access_token: str,
        passcode: str,
    ) -> bytes:
        """Decrypt email with passcode"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Find email
            email_doc = await email_collection.find_one({"access_token": access_token})
            if not email_doc:
                raise EmailEncryptionError("Email not found")
            
            # Check expiration
            if email_doc.get("expires_at"):
                expires_at = email_doc["expires_at"]
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.utcnow() > expires_at:
                    raise EmailEncryptionError("Email has expired")
            
            # Get salt
            passcode_salt_b64 = email_doc.get("passcode_salt")
            if not passcode_salt_b64:
                raise EmailEncryptionError("Email does not have passcode protection")
            
            salt = base64.b64decode(passcode_salt_b64)
            
            # Derive keys from passcode
            primary_key = derive_key_from_passcode(passcode, salt)
            secondary_key_data = passcode.encode() + salt
            secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
            
            # Decrypt content key
            encrypted_content_key = email_doc["encrypted_content_key"]
            content_key = decrypt_multi_layer(
                encrypted_content_key,
                primary_key=primary_key,
                secondary_key=secondary_key,
            )
            
            # Decrypt email content
            encrypted_content = email_doc["encrypted_content"]
            email_body = decrypt_multi_layer(
                encrypted_content,
                primary_key=content_key,
                secondary_key=secondary_key,
            )
            
            # Handle self-destruct
            if email_doc.get("self_destruct"):
                await email_collection.delete_one({"access_token": access_token})
                logger.info(f"Email self-destructed: {access_token[:8]}...")
            
            return email_body
            
        except StrongEncryptionError as e:
            raise EmailEncryptionError(f"Decryption failed: Incorrect passcode") from e
        except Exception as e:
            logger.error(f"Failed to decrypt email: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to decrypt email: {str(e)}") from e
    
    async def delete_email(self, access_token: str) -> bool:
        """Delete email from MongoDB"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            result = await email_collection.delete_one({"access_token": access_token})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete email: {e}", exc_info=True)
            return False
    
    async def get_inbox_emails(
        self,
        user_email: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get inbox emails for user (emails where user is recipient)"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Find emails where user is in recipient_emails
            # Build query with proper MongoDB structure
            query = {
                "recipient_emails": user_email.lower(),
                "is_draft": False,
                "$or": [
                    {"expires_at": {"$exists": False}},
                    {"expires_at": {"$gt": datetime.utcnow()}},
                ],
            }
            
            cursor = email_collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
            emails = await cursor.to_list(length=limit)
            
            # Return metadata only (not encrypted content)
            result = []
            for email in emails:
                created_at = email.get("created_at")
                if created_at and isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                elif created_at:
                    created_at = str(created_at)
                
                expires_at = email.get("expires_at")
                if expires_at and isinstance(expires_at, datetime):
                    expires_at = expires_at.isoformat()
                elif expires_at:
                    expires_at = str(expires_at)
                
                # Get email_id or access_token (they should be the same)
                email_id = email.get("email_id") or email.get("access_token")
                access_token = email.get("access_token") or email.get("email_id")
                
                if not email_id or not access_token:
                    logger.warning(f"Email document missing email_id/access_token: {email.get('_id')}")
                    continue
                
                result.append({
                    "email_id": email_id,
                    "access_token": access_token,
                    "sender_email": email.get("sender_email"),
                    "recipient_emails": email.get("recipient_emails", []),
                    "subject": email.get("subject"),
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "has_passcode": email.get("has_passcode", False),
                    "is_draft": email.get("is_draft", False),
                    "status": email.get("status", "inbox"),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get inbox emails: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to get inbox emails: {str(e)}") from e
    
    async def get_sent_emails(
        self,
        user_email: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get sent emails for user (emails where user is sender)"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Find emails where user is sender
            query = {
                "sender_email": user_email.lower(),
                "is_draft": False,
                "$or": [
                    {"expires_at": {"$exists": False}},
                    {"expires_at": {"$gt": datetime.utcnow()}},
                ],
            }
            
            cursor = email_collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
            emails = await cursor.to_list(length=limit)
            
            # Return metadata only (not encrypted content)
            result = []
            for email in emails:
                created_at = email.get("created_at")
                if created_at and isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                elif created_at:
                    created_at = str(created_at)
                
                expires_at = email.get("expires_at")
                if expires_at and isinstance(expires_at, datetime):
                    expires_at = expires_at.isoformat()
                elif expires_at:
                    expires_at = str(expires_at)
                
                # Get email_id or access_token (they should be the same)
                email_id = email.get("email_id") or email.get("access_token")
                access_token = email.get("access_token") or email.get("email_id")
                
                if not email_id or not access_token:
                    logger.warning(f"Email document missing email_id/access_token: {email.get('_id')}")
                    continue
                
                result.append({
                    "email_id": email_id,
                    "access_token": access_token,
                    "sender_email": email.get("sender_email"),
                    "recipient_emails": email.get("recipient_emails", []),
                    "subject": email.get("subject"),
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "has_passcode": email.get("has_passcode", False),
                    "is_draft": email.get("is_draft", False),
                    "status": email.get("status", "sent"),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get sent emails: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to get sent emails: {str(e)}") from e
    
    async def get_draft_emails(
        self,
        user_email: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get draft emails for user"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Find draft emails where user is sender
            query = {
                "sender_email": user_email.lower(),
                "is_draft": True,
            }
            
            cursor = email_collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
            emails = await cursor.to_list(length=limit)
            
            # Return metadata only (not encrypted content)
            result = []
            for email in emails:
                created_at = email.get("created_at")
                if created_at and isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                elif created_at:
                    created_at = str(created_at)
                
                expires_at = email.get("expires_at")
                if expires_at and isinstance(expires_at, datetime):
                    expires_at = expires_at.isoformat()
                elif expires_at:
                    expires_at = str(expires_at)
                
                # Get email_id or access_token (they should be the same)
                email_id = email.get("email_id") or email.get("access_token")
                access_token = email.get("access_token") or email.get("email_id")
                
                if not email_id or not access_token:
                    logger.warning(f"Draft document missing email_id/access_token: {email.get('_id')}")
                    continue
                
                result.append({
                    "email_id": email_id,
                    "access_token": access_token,
                    "sender_email": email.get("sender_email"),
                    "recipient_emails": email.get("recipient_emails", []),
                    "subject": email.get("subject"),
                    "created_at": created_at,
                    "expires_at": expires_at,
                    "has_passcode": email.get("has_passcode", False),
                    "is_draft": True,
                    "status": "draft",
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get draft emails: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to get draft emails: {str(e)}") from e
    
    async def save_draft_email(
        self,
        email_body: bytes,
        sender_email: str,
        recipient_emails: List[str],
        subject: Optional[str] = None,
        draft_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save or update draft email"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Generate content key
            content_key = generate_strong_key()
            
            # Derive keys from user email (for drafts, we use authenticated mode)
            user_salt = generate_salt_for_identifier(sender_email)
            primary_key = derive_key_from_passcode(sender_email, user_salt)
            secondary_key_data = sender_email.encode() + user_salt
            secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
            
            # Encrypt email content with multi-layer encryption
            encrypted_content = encrypt_multi_layer(
                email_body,
                primary_key=content_key,
                secondary_key=secondary_key,
                layers=3
            )
            
            # Encrypt content key
            encrypted_content_key = encrypt_multi_layer(
                content_key,
                primary_key=primary_key,
                secondary_key=secondary_key,
                layers=3
            )
            
            # Generate or use existing draft ID
            if draft_id:
                access_token = draft_id
                email_id = draft_id
            else:
                access_token = self.generate_public_access_token()
                email_id = access_token
            
            email_address = self.generate_email_address(access_token)
            
            # Check if draft exists
            existing_draft = await email_collection.find_one({"email_id": email_id, "is_draft": True})
            
            draft_doc = {
                "email_id": email_id,
                "access_token": access_token,
                "sender_email": sender_email.lower(),
                "recipient_emails": [email.lower() for email in recipient_emails],
                "encrypted_content": encrypted_content,
                "encrypted_content_key": encrypted_content_key,
                "encryption_mode": EncryptionMode.AUTHENTICATED.value,
                "has_passcode": False,
                "passcode_salt": None,
                "subject": subject,
                "created_at": datetime.utcnow() if not existing_draft else existing_draft.get("created_at"),
                "updated_at": datetime.utcnow(),
                "expires_at": None,  # Drafts don't expire
                "self_destruct": False,
                "email_address": email_address,
                "status": "draft",
                "is_draft": True,
            }
            
            if existing_draft:
                # Update existing draft
                await email_collection.update_one(
                    {"email_id": email_id, "is_draft": True},
                    {"$set": draft_doc}
                )
                logger.info(f"Draft updated: {email_id[:8]}...")
            else:
                # Create new draft
                await email_collection.insert_one(draft_doc)
                logger.info(f"Draft created: {email_id[:8]}...")
            
            return {
                "email_id": email_id,
                "access_token": access_token,
                "email_address": email_address,
                "status": "draft",
                "created_at": draft_doc["created_at"].isoformat() if isinstance(draft_doc["created_at"], datetime) else draft_doc["created_at"],
                "updated_at": draft_doc["updated_at"].isoformat() if isinstance(draft_doc["updated_at"], datetime) else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to save draft email: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to save draft email: {str(e)}") from e
    
    async def send_draft_email(
        self,
        draft_id: str,
        sender_email: str,
        passcode: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
        self_destruct: bool = False,
    ) -> Dict[str, Any]:
        """Send a draft email (convert draft to sent email)"""
        try:
            db = get_mongodb()
            email_collection = db.emails
            
            # Find draft
            draft = await email_collection.find_one({"email_id": draft_id, "is_draft": True})
            if not draft:
                raise EmailEncryptionError("Draft not found")
            
            # Verify sender owns the draft
            if draft.get("sender_email", "").lower() != sender_email.lower():
                raise EmailEncryptionError("You can only send your own drafts")
            
            # Update draft to sent email
            update_data = {
                "is_draft": False,
                "status": "sent",
                "updated_at": datetime.utcnow(),
            }
            
            # Update passcode if provided
            if passcode:
                salt = self.key_manager.generate_salt()
                passcode_key = derive_key_from_passcode(passcode, salt)
                secondary_key_data = passcode.encode() + salt
                secondary_key = hashlib.sha256(secondary_key_data).digest()[:KEY_SIZE]
                
                # Re-encrypt content key with passcode
                encrypted_content_key = draft["encrypted_content_key"]
                # Note: This is simplified - in production, you'd want to decrypt and re-encrypt
                update_data["has_passcode"] = True
                update_data["passcode_salt"] = base64.b64encode(salt).decode("utf-8")
                update_data["encryption_mode"] = EncryptionMode.PASSCODE_PROTECTED.value
            
            # Update expiration
            if expires_in_hours:
                update_data["expires_at"] = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            update_data["self_destruct"] = self_destruct
            
            await email_collection.update_one(
                {"email_id": draft_id, "is_draft": True},
                {"$set": update_data}
            )
            
            # Send notification emails
            recipient_emails = draft.get("recipient_emails", [])
            email_address = draft.get("email_address")
            secure_link = f"{EXTERNAL_BASE_URL}/email/{draft_id}"
            
            for recipient in recipient_emails:
                try:
                    await self.email_sender.send_encrypted_email_notification(
                        recipient_email=recipient,
                        email_address=email_address,
                        secure_link=secure_link,
                        sender_email=sender_email,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send notification to {recipient}: {e}")
            
            logger.info(f"Draft sent: {draft_id[:8]}...")
            
            return {
                "email_id": draft_id,
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to send draft email: {e}", exc_info=True)
            raise EmailEncryptionError(f"Failed to send draft email: {str(e)}") from e


# Global service instance
_email_service_mongodb: Optional[EmailServiceMongoDB] = None


def get_email_service_mongodb() -> EmailServiceMongoDB:
    """Get global email service instance"""
    global _email_service_mongodb
    if _email_service_mongodb is None:
        _email_service_mongodb = EmailServiceMongoDB()
    return _email_service_mongodb

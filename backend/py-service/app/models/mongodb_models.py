"""MongoDB Models for Emails and Files

Database schemas for storing encrypted emails and drive files in MongoDB.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EncryptedEmail(BaseModel):
    """Encrypted email document schema"""
    email_id: str = Field(..., description="Unique email identifier")
    access_token: str = Field(..., description="Public access token")
    sender_email: str = Field(..., description="Sender email address")
    recipient_emails: List[str] = Field(..., description="Recipient email addresses")
    
    # Encrypted data (multi-layer encrypted)
    encrypted_content: Dict[str, Any] = Field(..., description="Multi-layer encrypted email content")
    encrypted_content_key: Dict[str, Any] = Field(..., description="Multi-layer encrypted content key")
    
    # Encryption metadata
    encryption_mode: str = Field(..., description="authenticated or passcode_protected")
    has_passcode: bool = Field(default=False, description="Whether email has passcode protection")
    passcode_salt: Optional[str] = Field(None, description="Salt for passcode derivation (base64)")
    
    # Metadata
    subject: Optional[str] = Field(None, description="Email subject (encrypted)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    self_destruct: bool = Field(default=False, description="Delete after first read")
    
    # Email address for SMTP
    email_address: str = Field(..., description="Generated email address for SMTP")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email_id": "abc123",
                "access_token": "xyz789",
                "sender_email": "sender@example.com",
                "recipient_emails": ["recipient@example.com"],
                "encrypted_content": {
                    "ciphertext": "...",
                    "layers": 3,
                    "metadata": [...]
                },
                "encrypted_content_key": {
                    "ciphertext": "...",
                    "layers": 3,
                    "metadata": [...]
                },
                "encryption_mode": "authenticated",
                "has_passcode": False,
                "created_at": "2026-01-29T00:00:00",
                "email_address": "abc123@fxmail.ai"
            }
        }


class EncryptedFile(BaseModel):
    """Encrypted file document schema"""
    file_id: str = Field(..., description="Unique file identifier")
    owner_email: str = Field(..., description="File owner email address")
    
    # File metadata
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: Optional[str] = Field(None, description="File content type")
    
    # Encrypted data (multi-layer encrypted)
    encrypted_content: Dict[str, Any] = Field(..., description="Multi-layer encrypted file content")
    encrypted_content_key: Dict[str, Any] = Field(..., description="Multi-layer encrypted content key")
    
    # Encryption metadata
    passcode_protected: bool = Field(default=False, description="Whether file has passcode protection")
    passcode_salt: Optional[str] = Field(None, description="Salt for passcode derivation (base64)")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file123",
                "owner_email": "user@example.com",
                "filename": "document.pdf",
                "size": 1048576,
                "content_type": "application/pdf",
                "encrypted_content": {
                    "ciphertext": "...",
                    "layers": 3,
                    "metadata": [...]
                },
                "encrypted_content_key": {
                    "ciphertext": "...",
                    "layers": 3,
                    "metadata": [...]
                },
                "passcode_protected": False,
                "created_at": "2026-01-29T00:00:00"
            }
        }

"""User Model with Encrypted Fields

Stores user data in PostgreSQL with sensitive fields encrypted at rest.
"""

from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.dialects.postgresql import BYTEA
from app.models.base import BaseModel
import logging

logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model with encrypted sensitive fields"""
    
    __tablename__ = "users"
    
    # Encrypted fields (stored as encrypted bytes)
    encrypted_email = Column(BYTEA, nullable=False, unique=True, index=True, comment="Encrypted email address")
    email_hash = Column(String(64), nullable=False, unique=True, index=True, comment="SHA-256 hash of email for lookup")
    
    # Password (hashed, never encrypted - bcrypt is already secure)
    hashed_password = Column(String(255), nullable=False, comment="Bcrypt hashed password")
    
    # Encrypted optional fields
    encrypted_full_name = Column(BYTEA, nullable=True, comment="Encrypted full name")
    
    # Non-sensitive metadata
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether user account is active")
    is_verified = Column(Boolean, default=False, nullable=False, comment="Whether email is verified")
    
    # Encryption metadata (stored as JSON string)
    encryption_metadata = Column(Text, nullable=True, comment="JSON metadata for encryption (salt, algorithm, etc.)")
    
    def __repr__(self):
        return f"<User(id={self.id}, email_hash={self.email_hash[:8]}...)>"

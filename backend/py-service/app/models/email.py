"""Email model for PostgreSQL"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel


class StoredEmail(BaseModel):
    """Stored encrypted email"""

    __tablename__ = "emails"

    email_id = Column(String(64), unique=True, index=True, nullable=False)
    sender_email = Column(String(255), nullable=False, index=True)
    recipient_emails = Column(JSONB, nullable=True)
    encrypted_content = Column(JSONB, nullable=True)
    encrypted_content_key = Column(JSONB, nullable=True)
    encryption_mode = Column(String(32), nullable=True)
    has_passcode = Column(Boolean, default=False, nullable=False)
    is_draft = Column(Boolean, default=False, nullable=False)
    subject = Column(String(512), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    self_destruct = Column(Boolean, default=False, nullable=False)

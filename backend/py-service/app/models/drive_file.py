"""Drive file model for PostgreSQL"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import BaseModel


class DriveFile(BaseModel):
    """Drive file - encrypted storage"""

    __tablename__ = "drive_files"

    file_id = Column(String(64), unique=True, index=True, nullable=False)
    filename = Column(String(512), nullable=False)
    size = Column(Integer, nullable=False)
    content_type = Column(String(128), nullable=True)
    owner_email = Column(String(255), nullable=False, index=True)
    passcode_protected = Column(Boolean, default=False, nullable=False)
    encrypted_content = Column(JSONB, nullable=True)
    encrypted_content_key = Column(JSONB, nullable=True)
    passcode_salt = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

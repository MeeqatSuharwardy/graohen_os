"""PostgreSQL drive service - file storage"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy import select, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import database
from app.models.drive_file import DriveFile
from app.core.encryption import encrypt_bytes, decrypt_bytes, generate_key
from app.core.key_manager import derive_key_from_passcode, generate_salt_for_identifier
from app.core.secure_derivation import derive_user_key_complex
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class DriveEncryptionError(Exception):
    """Drive encryption/decryption error"""
    pass


def _generate_file_id() -> str:
    return secrets.token_urlsafe(32)


async def get_file_metadata(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file metadata from PostgreSQL."""
    if database.AsyncSessionLocal is None:
        return None
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(select(DriveFile).where(DriveFile.file_id == file_id))
        f = result.scalar_one_or_none()
        if not f:
            return None
        return {
            "file_id": f.file_id,
            "filename": f.filename,
            "size": f.size,
            "content_type": f.content_type,
            "owner_email": f.owner_email,
            "passcode_protected": f.passcode_protected,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "expires_at": f.expires_at.isoformat() if f.expires_at else None,
        }


async def get_file_from_db(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file doc (encrypted content, key, etc.) from PostgreSQL."""
    if database.AsyncSessionLocal is None:
        return None
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(select(DriveFile).where(DriveFile.file_id == file_id))
        f = result.scalar_one_or_none()
        if not f:
            return None
        return {
            "encrypted_content": f.encrypted_content,
            "encrypted_content_key": f.encrypted_content_key,
            "passcode_salt": f.passcode_salt,
            "passcode_protected": f.passcode_protected,
            "owner_email": f.owner_email,
            "created_at": f.created_at,
        }


async def get_encrypted_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Get encrypted file data for download. Returns format expected by drive endpoints."""
    doc = await get_file_from_db(file_id)
    if not doc:
        return None
    ca = doc.get("created_at")
    return {
        "encrypted_content": doc.get("encrypted_content"),
        "encrypted_content_key": doc.get("encrypted_content_key"),
        "stored_at": ca.isoformat() if ca else None,
    }


async def encrypt_and_store_file(
    file_content: bytes,
    filename: str,
    file_size: int,
    owner_email: str,
    content_type: Optional[str] = None,
    passcode: Optional[str] = None,
    expires_in_hours: Optional[float] = None,
    never_expire: bool = False,
) -> Dict[str, Any]:
    """Encrypt and store file in PostgreSQL."""
    if database.AsyncSessionLocal is None:
        raise DriveEncryptionError("Database not initialized")
    file_id = _generate_file_id()
    content_key = generate_key()
    encrypted_content = encrypt_bytes(file_content, content_key)
    owner_email_lower = owner_email.lower()
    passcode_protected = bool(passcode)
    passcode_salt_b64 = None
    encrypted_content_key = None
    if passcode_protected and passcode:
        salt = secrets.token_bytes(16)
        passcode_key = derive_user_key_complex(
            derive_key_from_passcode(passcode, salt),
            salt + b"passcode",
        )
        encrypted_content_key = encrypt_bytes(content_key, passcode_key)
        passcode_salt_b64 = __import__("base64").b64encode(salt).decode("utf-8")
    else:
        user_salt = generate_salt_for_identifier(owner_email_lower)
        base_key = derive_key_from_passcode(owner_email_lower, user_salt)
        user_key = derive_user_key_complex(base_key, user_salt + owner_email_lower.encode())
        encrypted_content_key = encrypt_bytes(content_key, user_key)
    expires_at = None
    if not never_expire and expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    async with database.AsyncSessionLocal() as session:
        df = DriveFile(
            file_id=file_id,
            filename=filename,
            size=file_size,
            content_type=content_type,
            owner_email=owner_email_lower,
            passcode_protected=passcode_protected,
            encrypted_content=encrypted_content,
            encrypted_content_key=encrypted_content_key,
            passcode_salt=passcode_salt_b64,
            expires_at=expires_at,
        )
        session.add(df)
        await session.commit()
    return {"file_id": file_id, "passcode_protected": passcode_protected}


async def decrypt_file_for_authenticated_user(file_id: str, user_email: str) -> bytes:
    """Decrypt file for authenticated owner."""
    doc = await get_file_from_db(file_id)
    if not doc or doc.get("passcode_protected"):
        raise DriveEncryptionError("File not found or requires passcode")
    owner = doc.get("owner_email", "").lower()
    if owner != user_email.lower():
        raise DriveEncryptionError("Access denied")
    user_salt = generate_salt_for_identifier(owner)
    base_key = derive_key_from_passcode(owner, user_salt)
    user_key = derive_user_key_complex(base_key, user_salt + owner.encode())
    content_key = decrypt_bytes(doc["encrypted_content_key"], user_key)
    return decrypt_bytes(doc["encrypted_content"], content_key)


async def decrypt_file_with_passcode(file_id: str, passcode: str) -> bytes:
    """Decrypt file with passcode."""
    doc = await get_file_from_db(file_id)
    if not doc or not doc.get("passcode_protected"):
        raise DriveEncryptionError("File not found or does not require passcode")
    salt_b64 = doc.get("passcode_salt")
    if not salt_b64:
        raise DriveEncryptionError("Passcode salt not found")
    import base64
    salt = base64.b64decode(salt_b64)
    passcode_key = derive_user_key_complex(
        derive_key_from_passcode(passcode, salt),
        salt + b"passcode",
    )
    content_key = decrypt_bytes(doc["encrypted_content_key"], passcode_key)
    return decrypt_bytes(doc["encrypted_content"], content_key)


async def delete_file(file_id: str) -> bool:
    """Delete file from PostgreSQL."""
    if database.AsyncSessionLocal is None:
        return False
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(delete(DriveFile).where(DriveFile.file_id == file_id))
        await session.commit()
        return result.rowcount > 0


async def get_user_storage_used(owner_email: str) -> int:
    """Get total storage used by user in bytes."""
    if database.AsyncSessionLocal is None:
        return 0
    async with database.AsyncSessionLocal() as session:
        now = datetime.utcnow()
        result = await session.execute(
            select(func.coalesce(func.sum(DriveFile.size), 0)).where(
                DriveFile.owner_email == owner_email.lower(),
                or_(DriveFile.expires_at.is_(None), DriveFile.expires_at > now),
            )
        )
        return int(result.scalar() or 0)


async def list_user_files(owner_email: str, limit: int = 50, offset: int = 0) -> Tuple[List[Dict], int]:
    """List files for user. Returns (files, total)."""
    if database.AsyncSessionLocal is None:
        return [], 0
    async with database.AsyncSessionLocal() as session:
        now = datetime.utcnow()
        filt = (
            DriveFile.owner_email == owner_email.lower(),
            or_(DriveFile.expires_at.is_(None), DriveFile.expires_at > now),
        )
        total_result = await session.execute(select(func.count(DriveFile.id)).where(*filt))
        total = total_result.scalar() or 0
        result = await session.execute(
            select(DriveFile).where(*filt).order_by(DriveFile.created_at.desc()).offset(offset).limit(limit)
        )
        rows = result.scalars().all()
        files = [
            {
                "file_id": r.file_id,
                "filename": r.filename,
                "size": r.size,
                "content_type": r.content_type,
                "passcode_protected": r.passcode_protected,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rows
        ]
        return files, total


class DriveService:
    """PostgreSQL drive service."""

    async def get_file_from_mongodb(self, file_id: str):
        """Alias for compatibility."""
        return await get_file_from_db(file_id)

    async def encrypt_and_store_file(self, **kwargs):
        return await encrypt_and_store_file(**kwargs)

    async def decrypt_file_for_authenticated_user(self, file_id: str, user_email: str):
        return await decrypt_file_for_authenticated_user(file_id, user_email)

    async def decrypt_file_with_passcode(self, file_id: str, passcode: str):
        return await decrypt_file_with_passcode(file_id, passcode)

    async def delete_file(self, file_id: str):
        return await delete_file(file_id)


_drive_service: Optional[DriveService] = None


def get_drive_service() -> DriveService:
    global _drive_service
    if _drive_service is None:
        _drive_service = DriveService()
    return _drive_service

"""Drive/File Storage API endpoints"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import logging
import io

from app.config import settings
from app.services.email_service import (
    get_email_service,
    EmailEncryptionError,
)
<<<<<<< HEAD
from app.services.drive_service_mongodb import (
    get_drive_service_mongodb,
    DriveEncryptionError,
=======
from app.services.storage_service import (
    check_storage_available,
    add_storage_used,
    subtract_storage_used,
    get_user_storage_used,
    get_user_storage_quota,
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
)
from app.api.v1.endpoints.auth import get_current_user
from app.core.redis_client import get_redis
from app.core.mongodb import get_mongodb
from app.core.encryption import encrypt_bytes, decrypt_bytes, generate_key, KEY_SIZE

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Signed URL settings
SIGNED_URL_EXPIRE_MINUTES = 60  # 1 hour default
SIGNED_URL_SECRET_KEY = settings.SECRET_KEY  # Use same secret as JWT

# Redis key prefixes
REDIS_FILE_PREFIX = "drive:file:"
REDIS_FILE_METADATA_PREFIX = "drive:metadata:"
REDIS_SIGNED_URL_PREFIX = "drive:signed:"
REDIS_RATE_LIMIT_UNLOCK_PREFIX = "drive:rate_limit:unlock:"
REDIS_USER_STORAGE_PREFIX = "drive:storage:"
REDIS_USER_FILES_PREFIX = "drive:user_files:"

# Storage quota settings
DEFAULT_STORAGE_QUOTA_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB per user
STORAGE_QUOTA_KEY = "drive:quota:default"  # Default quota in bytes

# Rate limiting for unlock
MAX_UNLOCK_ATTEMPTS = 5
UNLOCK_RATE_LIMIT_WINDOW = 3600  # 1 hour
LOCKOUT_DURATION = 3600  # 1 hour lockout


# Pydantic Models
class FileUploadResponse(BaseModel):
    """File upload response"""
    file_id: str
    filename: str
    size: int
    content_type: Optional[str] = None
    passcode_protected: bool
    expires_at: Optional[str] = None
    created_at: str


class FileInfoResponse(BaseModel):
    """File information response"""
    file_id: str
    filename: str
    size: int
    content_type: Optional[str] = None
    passcode_protected: bool
    owner_email: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str
    signed_url: Optional[str] = None
    signed_url_expires_at: Optional[str] = None


class FileUnlockRequest(BaseModel):
    """File unlock request"""
    passcode: str = Field(..., min_length=1)


class FileUnlockResponse(BaseModel):
    """File unlock response"""
    file_id: str
    signed_url: str
    signed_url_expires_at: str
    unlocked_at: str


class FileDeleteResponse(BaseModel):
    """File delete response"""
    file_id: str
    deleted: bool
    message: str


<<<<<<< HEAD
class StorageQuotaResponse(BaseModel):
    """Storage quota response"""
    used_bytes: int
    quota_bytes: int
    used_gb: float
    quota_gb: float
    available_bytes: int
    available_gb: float
    percentage_used: float


class FileListItem(BaseModel):
    """File list item (metadata only, no encrypted content)"""
    file_id: str
    filename: str
    size: int
    content_type: Optional[str] = None
    passcode_protected: bool
    created_at: str
    expires_at: Optional[str] = None


class FileListResponse(BaseModel):
    """File list response"""
    files: List[FileListItem]
    total: int
    limit: int
    offset: int


class EncryptedFileDownloadResponse(BaseModel):
    """Response for downloading encrypted file with key for client-side decryption"""
    file_id: str
    filename: str
    size: int
    content_type: Optional[str] = None
    encrypted_content: Dict[str, str] = Field(
        ...,
        description="Encrypted file content. Format: {ciphertext, nonce, tag}. Decrypt on client using device key."
    )
    encrypted_content_key: Dict[str, str] = Field(
        ...,
        description="Encrypted content key. Format: {ciphertext, nonce, tag}. Decrypt on client using device key to get the content key, then decrypt encrypted_content."
    )
    passcode_protected: bool
    created_at: str
    expires_at: Optional[str] = None
    message: str = Field(
        default="File downloaded. Decrypt encrypted_content_key using your device key, then decrypt encrypted_content using the decrypted content key."
    )


class FileUploadEncryptedRequest(BaseModel):
    """File upload request with pre-encrypted content (client-side encryption)"""
    filename: str = Field(..., description="Original filename")
    encrypted_content: Dict[str, str] = Field(
        ...,
        description="Encrypted file content (encrypted on client-side). Format: {ciphertext, nonce, tag}"
    )
    encrypted_content_key: Dict[str, str] = Field(
        ...,
        description="Encrypted content key (encrypted with user's device key on client-side). Format: {ciphertext, nonce, tag}"
    )
    content_type: Optional[str] = Field(None, description="File content type (e.g., application/pdf, application/msword, text/plain, etc.)")
    size: int = Field(..., description="Original file size in bytes")
    passcode: Optional[str] = Field(None, description="Optional passcode for additional protection")
    never_expire: bool = Field(False, description="If True, file never expires. If False, use expires_in_hours or expires_in_days")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760, description="Expiration time in hours (only used if never_expire=False)")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Expiration time in days (only used if never_expire=False, takes precedence over expires_in_hours)")
=======
class StorageInfoResponse(BaseModel):
    """Storage quota info for current user"""
    used_bytes: int
    quota_bytes: int
    used_mb: float
    quota_gb: float
    percent_used: float
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)


def generate_file_id() -> str:
    """Generate a unique file ID"""
    return secrets.token_urlsafe(32)


def generate_signed_url_token(file_id: str, expires_in_minutes: int = SIGNED_URL_EXPIRE_MINUTES) -> str:
    """
    Generate a signed URL token for secure file access.
    
    Token format: base64(file_id:expires_at:signature)
    """
    expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    expires_timestamp = int(expires_at.timestamp())
    
    # Create signature
    message = f"{file_id}:{expires_timestamp}"
    signature = hashlib.sha256(f"{message}:{SIGNED_URL_SECRET_KEY}".encode()).hexdigest()[:16]
    
    # Combine: file_id:expires:signature
    token_data = f"{file_id}:{expires_timestamp}:{signature}"
    token = base64.urlsafe_b64encode(token_data.encode()).decode().rstrip("=")
    
    return token, expires_at


def verify_signed_url_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode signed URL token.
    
    Returns:
        Dictionary with file_id and expires_at if valid, None otherwise
    """
    try:
        # Decode token
        token_data = base64.urlsafe_b64decode(token + "==").decode()
        parts = token_data.split(":")
        
        if len(parts) != 3:
            return None
        
        file_id, expires_timestamp_str, signature = parts
        
        # Verify signature
        expected_message = f"{file_id}:{expires_timestamp_str}"
        expected_signature = hashlib.sha256(f"{expected_message}:{SIGNED_URL_SECRET_KEY}".encode()).hexdigest()[:16]
        
        if signature != expected_signature:
            return None
        
        # Check expiration
        expires_timestamp = int(expires_timestamp_str)
        expires_at = datetime.fromtimestamp(expires_timestamp)
        
        if datetime.utcnow() > expires_at:
            return None
        
        return {
            "file_id": file_id,
            "expires_at": expires_at,
        }
    except Exception as e:
        logger.warning(f"Failed to verify signed URL token: {e}")
        return None


async def store_file_metadata(
    file_id: str,
    filename: str,
    size: int,
    content_type: Optional[str],
    owner_email: str,
    passcode_protected: bool,
    expires_in_seconds: Optional[int] = None,
) -> None:
    """Store file metadata in Redis"""
    redis = await get_redis()
    
    metadata = {
        "file_id": file_id,
        "filename": filename,
        "size": size,
        "content_type": content_type,
        "owner_email": owner_email.lower(),
        "passcode_protected": passcode_protected,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    import json
    metadata_json = json.dumps(metadata)
    
    key = f"{REDIS_FILE_METADATA_PREFIX}{file_id}"
    
    if expires_in_seconds:
        await redis.setex(key, expires_in_seconds, metadata_json)
    else:
        await redis.set(key, metadata_json)


async def get_file_metadata(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file metadata from MongoDB"""
    try:
        db = get_mongodb()
        files_collection = db.files
        
        file_doc = await files_collection.find_one({"file_id": file_id})
        if not file_doc:
            return None
        
        # Convert MongoDB document to metadata format
        metadata = {
            "file_id": file_doc.get("file_id"),
            "filename": file_doc.get("filename"),
            "size": file_doc.get("size"),
            "content_type": file_doc.get("content_type"),
            "owner_email": file_doc.get("owner_email"),
            "passcode_protected": file_doc.get("passcode_protected", False),
            "created_at": file_doc.get("created_at").isoformat() if file_doc.get("created_at") else None,
            "expires_at": file_doc.get("expires_at").isoformat() if file_doc.get("expires_at") else None,
        }
        
        return metadata
    except Exception as e:
        logger.error(f"Failed to get file metadata from MongoDB: {e}", exc_info=True)
        return None


async def store_encrypted_file(
    file_id: str,
    encrypted_content: Dict[str, str],
    encrypted_content_key: Dict[str, str],
    expires_in_seconds: Optional[int] = None,
) -> None:
    """Store encrypted file data in Redis"""
    redis = await get_redis()
    
    file_data = {
        "encrypted_content": encrypted_content,
        "encrypted_content_key": encrypted_content_key,
        "stored_at": datetime.utcnow().isoformat(),
    }
    
    import json
    file_json = json.dumps(file_data)
    
    key = f"{REDIS_FILE_PREFIX}{file_id}"
    
    if expires_in_seconds:
        await redis.setex(key, expires_in_seconds, file_json)
    else:
        await redis.set(key, file_json)


async def get_encrypted_file(file_id: str) -> Optional[Dict[str, Any]]:
    """Get encrypted file data from MongoDB"""
    try:
        drive_service = get_drive_service_mongodb()
        file_doc = await drive_service.get_file_from_mongodb(file_id)
        
        if not file_doc:
            return None
        
        # Return encrypted data in expected format
        return {
            "encrypted_content": file_doc.get("encrypted_content"),
            "encrypted_content_key": file_doc.get("encrypted_content_key"),
            "stored_at": file_doc.get("created_at").isoformat() if file_doc.get("created_at") else None,
        }
    except Exception as e:
        logger.error(f"Failed to get encrypted file from MongoDB: {e}", exc_info=True)
        return None


async def store_passcode_salt(file_id: str, salt_base64: str, expires_in_seconds: Optional[int] = None) -> None:
    """Store passcode salt for file"""
    redis = await get_redis()
    key = f"drive:passcode_salt:{file_id}"
    
    if expires_in_seconds:
        await redis.setex(key, expires_in_seconds, salt_base64)
    else:
        await redis.set(key, salt_base64)


async def get_passcode_salt(file_id: str) -> Optional[str]:
    """Get passcode salt for file"""
    redis = await get_redis()
    key = f"drive:passcode_salt:{file_id}"
    return await redis.get(key)


async def check_ownership(file_id: str, user_email: str) -> bool:
    """Check if user owns the file"""
    metadata = await get_file_metadata(file_id)
    if not metadata:
        return False
    
    owner_email = metadata.get("owner_email", "").lower()
    return owner_email == user_email.lower()


async def increment_unlock_attempt(file_id: str) -> int:
    """Increment unlock attempt counter for file"""
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_UNLOCK_PREFIX}{file_id}"
    
    current_count = await redis.incr(key)
    
    if current_count == 1:
        await redis.expire(key, UNLOCK_RATE_LIMIT_WINDOW)
    
    if current_count >= MAX_UNLOCK_ATTEMPTS:
        await redis.expire(key, LOCKOUT_DURATION)
    
    return current_count


async def get_unlock_attempts_remaining(file_id: str) -> int:
    """Get remaining unlock attempts"""
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_UNLOCK_PREFIX}{file_id}"
    
    current_count = await redis.get(key)
    if current_count is None:
        return MAX_UNLOCK_ATTEMPTS
    
    count = int(current_count)
    
    if count >= MAX_UNLOCK_ATTEMPTS:
        ttl = await redis.ttl(key)
        if ttl > 0:
            return 0
    
    return max(0, MAX_UNLOCK_ATTEMPTS - count)


async def reset_unlock_attempts(file_id: str) -> None:
    """Reset unlock attempt counter"""
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_UNLOCK_PREFIX}{file_id}"
    await redis.delete(key)


<<<<<<< HEAD
async def get_user_storage_used(user_email: str) -> int:
    """Get total storage used by user in bytes"""
    redis = await get_redis()
    storage_key = f"{REDIS_USER_STORAGE_PREFIX}{user_email.lower()}"
    storage_bytes = await redis.get(storage_key)
    return int(storage_bytes) if storage_bytes else 0


async def get_user_storage_quota(user_email: str) -> int:
    """Get storage quota for user in bytes (default: 5GB)"""
    redis = await get_redis()
    quota_key = f"{REDIS_USER_STORAGE_PREFIX}{user_email.lower()}:quota"
    quota_bytes = await redis.get(quota_key)
    if quota_bytes:
        return int(quota_bytes)
    # Return default quota
    return DEFAULT_STORAGE_QUOTA_BYTES


async def increment_user_storage(user_email: str, bytes_to_add: int) -> None:
    """Increment user storage usage"""
    redis = await get_redis()
    storage_key = f"{REDIS_USER_STORAGE_PREFIX}{user_email.lower()}"
    await redis.incrby(storage_key, bytes_to_add)
    # Set expiration to match message expiration (30 days)
    await redis.expire(storage_key, 30 * 24 * 3600)


async def decrement_user_storage(user_email: str, bytes_to_remove: int) -> None:
    """Decrement user storage usage"""
    redis = await get_redis()
    storage_key = f"{REDIS_USER_STORAGE_PREFIX}{user_email.lower()}"
    current = await get_user_storage_used(user_email)
    new_value = max(0, current - bytes_to_remove)
    await redis.set(storage_key, str(new_value))
    await redis.expire(storage_key, 30 * 24 * 3600)


async def check_storage_quota(user_email: str, file_size: int) -> bool:
    """Check if user has enough storage quota for file"""
    current_used = await get_user_storage_used(user_email)
    quota = await get_user_storage_quota(user_email)
    return (current_used + file_size) <= quota


async def add_user_file(user_email: str, file_id: str) -> None:
    """Add file ID to user's file list"""
    redis = await get_redis()
    user_files_key = f"{REDIS_USER_FILES_PREFIX}{user_email.lower()}"
    await redis.sadd(user_files_key, file_id)
    await redis.expire(user_files_key, 30 * 24 * 3600)


async def remove_user_file(user_email: str, file_id: str) -> None:
    """Remove file ID from user's file list"""
    redis = await get_redis()
    user_files_key = f"{REDIS_USER_FILES_PREFIX}{user_email.lower()}"
    await redis.srem(user_files_key, file_id)
=======
@router.get("/storage", response_model=StorageInfoResponse)
async def get_storage_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get current user's storage usage and quota (5GB free tier)."""
    user_email = current_user.get("email")
    used = await get_user_storage_used(user_email)
    quota = await get_user_storage_quota(user_email)
    return StorageInfoResponse(
        used_bytes=used,
        quota_bytes=quota,
        used_mb=round(used / (1024 * 1024), 2),
        quota_gb=round(quota / (1024 * 1024 * 1024), 2),
        percent_used=round((used / quota * 100), 2) if quota else 0,
    )
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    passcode: Optional[str] = Form(None),
    never_expire: bool = Form(False, description="If True, file never expires"),
    expires_in_hours: Optional[int] = Form(None, ge=1, le=8760, description="Expiration in hours (only if never_expire=False)"),
    expires_in_days: Optional[int] = Form(None, ge=1, le=365, description="Expiration in days (only if never_expire=False, takes precedence over hours)"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload and encrypt a file.
    
    File is encrypted with a random content key, which is then encrypted
    with either user key (authenticated) or passcode-derived key (if passcode provided).
    """
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size (e.g., max 100MB)
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
<<<<<<< HEAD
        
        # Check storage quota (5GB per user)
        user_email = current_user.get("email")
        if not await check_storage_quota(user_email, file_size):
            current_used = await get_user_storage_used(user_email)
            quota = await get_user_storage_quota(user_email)
            available = quota - current_used
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Storage quota exceeded. Used: {current_used / (1024**3):.2f}GB / {quota / (1024**3):.2f}GB. Available: {available / (1024**3):.2f}GB"
            )
=======

        # Check storage quota (5GB free tier, admin can increase)
        user_email = current_user.get("email")
        if not await check_storage_available(user_email, file_size):
            used = await get_user_storage_used(user_email)
            quota = await get_user_storage_quota(user_email)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Storage quota exceeded. Used: {used / (1024*1024):.1f}MB, Quota: {quota / (1024*1024*1024):.1f}GB"
            )

        # Generate file ID
        file_id = generate_file_id()
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
        
        # Use MongoDB drive service with strong encryption
        drive_service = get_drive_service_mongodb()
        user_email = current_user.get("email")
        
        # Calculate expiration based on never_expire flag
        expires_in_hours_calculated = None
        if not never_expire:
            if expires_in_days:
                expires_in_hours_calculated = expires_in_days * 24
            elif expires_in_hours:
                expires_in_hours_calculated = expires_in_hours
        
        # Encrypt and store file in MongoDB with multi-layer encryption
        result = await drive_service.encrypt_and_store_file(
            file_content=file_content,
            filename=file.filename or "unnamed",
            file_size=file_size,
            owner_email=user_email,
            content_type=file.content_type,
            passcode=passcode,
            expires_in_hours=expires_in_hours_calculated,
            never_expire=never_expire,
        )
        
        file_id = result["file_id"]
        passcode_protected = result["passcode_protected"]
        
<<<<<<< HEAD
        # Calculate expiration for response
        expires_at = None
        if not never_expire and expires_in_hours_calculated:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours_calculated)
        
        # Update user storage usage
        await increment_user_storage(user_email, file_size)
        await add_user_file(user_email, file_id)
        
        # Passcode salt is stored in MongoDB by drive service
        # No need for separate Redis storage
=======
        # Generate and store session key for device-local access
        # Session key is the content key (decrypted) - stored for device biometric access
        # For authenticated files (no passcode), we can decrypt and store the content key now
        if not passcode_protected:
            try:
                from app.api.v1.endpoints.public import store_session_key
                user_email = current_user.get("email")
                from app.core.key_manager import derive_key_from_passcode, generate_salt_for_identifier
                from app.core.encryption import decrypt_bytes
                from app.core.secure_derivation import derive_user_key_complex
                
                user_salt = generate_salt_for_identifier(user_email)
                base_key = derive_key_from_passcode(user_email, user_salt)
                user_key = derive_user_key_complex(base_key, user_salt + user_email.encode())
                
                # Decrypt content key to get session key
                session_key = decrypt_bytes(encrypted_content_key, user_key)
                
                # Store session key for device access (7 days default, or match file expiration)
                session_expire_hours = expires_in_hours if expires_in_hours else 168
                await store_session_key(file_id, session_key, session_expire_hours)
                
                # Securely overwrite
                user_key = b"\x00" * len(user_key)
                session_key = b"\x00" * len(session_key)
                
                logger.info(f"Session key stored for file: {file_id[:8]}...")
            except Exception as e:
                logger.warning(f"Failed to store session key for file {file_id}: {e}")
                # Non-critical - file upload still succeeds
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
        
        # Update storage usage
        await add_storage_used(user_email, file_size)

        logger.info(
            f"File uploaded: id={file_id[:8]}..., "
            f"filename={file.filename}, size={file_size}, "
            f"passcode_protected={passcode_protected}"
        )
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename or "unnamed",
            size=file_size,
            content_type=file.content_type,
            passcode_protected=passcode_protected,
            expires_at=expires_at.isoformat() if expires_at else None,
            created_at=datetime.utcnow().isoformat(),
        )
        
    except HTTPException:
        raise
    except EmailEncryptionError as e:
        logger.error(f"File encryption failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"File upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )


@router.get("/file/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str,
    signed_url_expires_minutes: Optional[int] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Get file information and generate signed download URL.
    
    Requires authentication unless valid signed URL token provided.
    """
    try:
        # Get file metadata
        metadata = await get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or expired"
            )
        
        # Check ownership (authenticated users can only access their own files)
        owner_email = metadata.get("owner_email")
        user_email = current_user.get("email") if current_user else None
        
        if user_email and owner_email and owner_email.lower() != user_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file"
            )
        
        # Generate signed URL
        expires_minutes = signed_url_expires_minutes or SIGNED_URL_EXPIRE_MINUTES
        signed_token, signed_url_expires_at = generate_signed_url_token(file_id, expires_minutes)
        
        # Build signed URL
        signed_url = f"/api/v1/drive/file/{file_id}/download?token={signed_token}"
        
        return FileInfoResponse(
            file_id=file_id,
            filename=metadata["filename"],
            size=metadata["size"],
            content_type=metadata.get("content_type"),
            passcode_protected=metadata.get("passcode_protected", False),
            owner_email=owner_email if user_email == owner_email else None,
            expires_at=metadata.get("expires_at"),
            created_at=metadata["created_at"],
            signed_url=signed_url,
            signed_url_expires_at=signed_url_expires_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File info retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve file information"
        )


@router.get("/file/{file_id}/download")
async def download_file(
    file_id: str,
    token: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Download encrypted file.
    
    Requires either:
    - Valid signed URL token (time-limited), OR
    - Authentication and file ownership
    """
    try:
        # Verify access: either signed token or authenticated owner
        has_valid_token = False
        
        if token:
            token_data = verify_signed_url_token(token)
            if token_data and token_data["file_id"] == file_id:
                has_valid_token = True
        
        if not has_valid_token:
            # Check authenticated access
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required or valid signed URL token"
                )
            
            # Verify ownership
            if not await check_ownership(file_id, current_user.get("email")):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Get file metadata
        metadata = await get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or expired"
            )
        
        # Check if passcode-protected
        if metadata.get("passcode_protected"):
            # Check if file was unlocked via signed URL
            redis = await get_redis()
            if token:
                unlocked_key = f"drive:unlocked:{file_id}:{token}"
                is_unlocked = await redis.get(unlocked_key)
                if not is_unlocked:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="File requires passcode unlock. Use /unlock endpoint first."
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="File requires passcode unlock. Use /unlock endpoint first."
                )
        
        # Get encrypted file data
        file_data = await get_encrypted_file(file_id)
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File data not found or expired"
            )
        
        encrypted_content = file_data["encrypted_content"]
        encrypted_content_key = file_data["encrypted_content_key"]
        
        # Determine decryption method
        is_passcode_protected = metadata.get("passcode_protected", False)
        
        # Use MongoDB drive service to decrypt
        drive_service = get_drive_service_mongodb()
        user_email = current_user.get("email") if current_user else metadata.get("owner_email")
        
        if is_passcode_protected and token:
            # File was unlocked via passcode - check if unlocked flag exists
            redis = await get_redis()
            unlocked_key = f"drive:unlocked:{file_id}:{token}"
            is_unlocked = await redis.get(unlocked_key)
            
            if not is_unlocked:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="File requires passcode unlock. Use /unlock endpoint first."
                )
            
            # For passcode-protected files unlocked via token, we need to re-decrypt
            # This requires the passcode, so we can't decrypt here
            # In production, store decrypted content key temporarily after unlock
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Download of passcode-protected files via signed URL requires session management (to be implemented)"
            )
        elif not is_passcode_protected:
            # Authenticated mode - decrypt with user key using MongoDB service
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for file decryption"
                )
            
<<<<<<< HEAD
=======
            # Decrypt content key using user key (complex derivation)
            from app.core.key_manager import derive_key_from_passcode, generate_salt_for_identifier
            from app.core.secure_derivation import derive_user_key_complex
            
            user_salt = generate_salt_for_identifier(user_email)
            base_key = derive_key_from_passcode(user_email, user_salt)
            user_key = derive_user_key_complex(base_key, user_salt + user_email.encode())
            
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
            try:
                decrypted_content = await drive_service.decrypt_file_for_authenticated_user(
                    file_id=file_id,
                    user_email=user_email,
                )
            except DriveEncryptionError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to decrypt file: {str(e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="File requires passcode unlock"
            )(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="File requires passcode unlock"
            )
        
        # Create file-like object for streaming
        file_stream = io.BytesIO(decrypted_content)
        
        # Determine content type
        content_type = metadata.get("content_type") or "application/octet-stream"
        filename = metadata.get("filename", "file")
        
        logger.info(f"File downloaded: id={file_id[:8]}..., filename={filename}")
        
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(decrypted_content)),
            }
        )
        
    except HTTPException:
        raise
    except EmailEncryptionError as e:
        logger.error(f"File decryption failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt file: {str(e)}"
        )
    except Exception as e:
        logger.error(f"File download failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )


@router.post("/file/{file_id}/unlock", response_model=FileUnlockResponse)
async def unlock_file(
    file_id: str,
    unlock_data: FileUnlockRequest,
    signed_url_expires_minutes: Optional[int] = None,
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
):
    """
    Unlock passcode-protected file and get signed download URL.
    
    Rate-limited: Max 5 attempts per hour per file.
    """
    try:
        # Check rate limit
        attempts_remaining = await get_unlock_attempts_remaining(file_id)
        
        if attempts_remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many unlock attempts",
                    "message": "File is temporarily locked. Please try again later.",
                    "lockout_duration_seconds": LOCKOUT_DURATION,
                }
            )
        
        # Get file metadata
        metadata = await get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or expired"
            )
        
        if not metadata.get("passcode_protected"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File does not require passcode unlock"
            )
        
<<<<<<< HEAD
        # Use MongoDB drive service to decrypt with passcode
        drive_service = get_drive_service_mongodb()
=======
        # Get encrypted file data
        file_data = await get_encrypted_file(file_id)
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File data not found or expired"
            )
        
        # Get passcode salt
        salt_base64 = await get_passcode_salt(file_id)
        if not salt_base64:
            # Try to get salt from email service metadata if available
            owner_email = metadata.get("owner_email")
            if owner_email:
                from app.core.key_manager import generate_salt_for_identifier
                salt = generate_salt_for_identifier(owner_email)
                salt_base64 = base64.b64encode(salt).decode("utf-8")
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Passcode salt not found"
                )
        
        # Decrypt using passcode (complex derivation)
        encrypted_content_key = file_data["encrypted_content_key"]
        
        from app.core.key_manager import derive_key_from_passcode
        from app.core.secure_derivation import derive_user_key_complex
        salt = base64.b64decode(salt_base64)
        base_key = derive_key_from_passcode(unlock_data.passcode, salt)
        ctx = salt + (owner_email.encode() if owner_email else b"passcode")
        passcode_key = derive_user_key_complex(base_key, ctx)
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
        
        try:
            # Decrypt file with passcode (service handles all decryption)
            file_content = await drive_service.decrypt_file_with_passcode(
                file_id=file_id,
                passcode=unlock_data.passcode,
            )
        except DriveEncryptionError as e:
            # Increment failed attempt
            current_count = await increment_unlock_attempt(file_id)
            attempts_remaining = max(0, MAX_UNLOCK_ATTEMPTS - current_count)
            
            error_msg = str(e).lower()
            if "incorrect passcode" in error_msg or "decryption failed" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "Incorrect passcode",
                        "attempts_remaining": attempts_remaining,
                        "message": f"Incorrect passcode. {attempts_remaining} attempts remaining." if attempts_remaining > 0 else "File is now locked due to too many failed attempts."
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        # Success - reset rate limit
        await reset_unlock_attempts(file_id)
        
        # Generate signed URL for download
        expires_minutes = signed_url_expires_minutes or SIGNED_URL_EXPIRE_MINUTES
        signed_token, signed_url_expires_at = generate_signed_url_token(file_id, expires_minutes)
        signed_url = f"/api/v1/drive/file/{file_id}/download?token={signed_token}"
        
        # Store unlocked flag (temporary, expires with signed URL)
        # Note: For passcode-protected files, we store a flag that allows download
        redis = await get_redis()
        unlocked_key = f"drive:unlocked:{file_id}:{signed_token}"
        await redis.setex(unlocked_key, expires_minutes * 60, "1")
        
        # Store decrypted content temporarily for download (encrypted with session key)
        # In production, consider re-encrypting with a session key
        # For now, we'll use the signed URL as proof of unlock
        
        logger.info(f"File unlocked: id={file_id[:8]}...")
        
        return FileUnlockResponse(
            file_id=file_id,
            signed_url=signed_url,
            signed_url_expires_at=signed_url_expires_at.isoformat(),
            unlocked_at=datetime.utcnow().isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File unlock failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock file"
        )


@router.get("/storage/quota", response_model=StorageQuotaResponse)
async def get_storage_quota(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get storage quota information for the current user.
    
    Returns:
    - Used storage in bytes and GB
    - Total quota in bytes and GB (default: 5GB)
    - Available storage
    - Percentage used
    """
    try:
        user_email = current_user.get("email")
        used_bytes = await get_user_storage_used(user_email)
        quota_bytes = await get_user_storage_quota(user_email)
        available_bytes = max(0, quota_bytes - used_bytes)
        
        used_gb = used_bytes / (1024 ** 3)
        quota_gb = quota_bytes / (1024 ** 3)
        available_gb = available_bytes / (1024 ** 3)
        percentage_used = (used_bytes / quota_bytes * 100) if quota_bytes > 0 else 0
        
        return StorageQuotaResponse(
            used_bytes=used_bytes,
            quota_bytes=quota_bytes,
            used_gb=round(used_gb, 2),
            quota_gb=round(quota_gb, 2),
            available_bytes=available_bytes,
            available_gb=round(available_gb, 2),
            percentage_used=round(percentage_used, 2),
        )
    except Exception as e:
        logger.error(f"Failed to get storage quota: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve storage quota"
        )


@router.post("/upload-encrypted", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_encrypted_file(
    file_data: FileUploadEncryptedRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Upload a file that is already encrypted on the client-side.
    
    Supports ALL file types: PDF, Word documents (.doc, .docx), text files (.txt),
    images (.png, .jpg, .gif, etc.), spreadsheets (.xls, .xlsx), and any other file format.
    
    IMPORTANT: This endpoint expects pre-encrypted content from the client.
    The client must:
    1. Encrypt the file content with a random key
    2. Encrypt the content key with the user's device encryption key
    3. Send only the encrypted payloads
    
    The server never sees:
    - Plaintext file content
    - Encryption keys
    - Decryption keys
    
    Only the user (with their device key) can decrypt the file.
    
    This ensures true end-to-end encryption where the server cannot access file contents.
    
    Expiration Options:
    - never_expire=True: File never expires (no expiration date)
    - never_expire=False: Use expires_in_days (takes precedence) or expires_in_hours
    """
    try:
        user_email = current_user.get("email")
        file_size = file_data.size
        
        # Validate encrypted content structure
        required_fields = ["ciphertext", "nonce", "tag"]
        for field in required_fields:
            if field not in file_data.encrypted_content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field in encrypted_content: {field}"
                )
            if field not in file_data.encrypted_content_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field in encrypted_content_key: {field}"
                )
        
        # Check storage quota (5GB per user)
        if not await check_storage_quota(user_email, file_size):
            current_used = await get_user_storage_used(user_email)
            quota = await get_user_storage_quota(user_email)
            available = quota - current_used
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Storage quota exceeded. Used: {current_used / (1024**3):.2f}GB / {quota / (1024**3):.2f}GB. Available: {available / (1024**3):.2f}GB"
            )
        
        # Generate file ID
        file_id = generate_file_id()
        
        # If passcode is provided, re-encrypt the content key with passcode-derived key
        # This allows both device key and passcode to decrypt (dual encryption)
        encrypted_content_key = file_data.encrypted_content_key
        passcode_protected = False
        
        if file_data.passcode:
            # Re-encrypt content key with passcode
            # First, we need to decrypt with device key (client-side), then re-encrypt with passcode
            # For now, we'll store both encrypted keys
            # In production, client should send both encrypted versions
            passcode_protected = True
            
            # Store passcode salt
            from app.core.key_manager import generate_salt_for_identifier
            salt = generate_salt_for_identifier(user_email)
            salt_base64 = base64.b64encode(salt).decode("utf-8")
            
            expires_in_seconds = None
            if not file_data.never_expire:
                if file_data.expires_in_days:
                    expires_in_seconds = int(file_data.expires_in_days * 24 * 3600)
                elif file_data.expires_in_hours:
                    expires_in_seconds = int(file_data.expires_in_hours * 3600)
            
            await store_passcode_salt(file_id, salt_base64, expires_in_seconds)
        
        # Calculate expiration based on never_expire flag
        expires_in_seconds = None
        expires_at = None
        if not file_data.never_expire:
            if file_data.expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=file_data.expires_in_days)
                expires_in_seconds = int(file_data.expires_in_days * 24 * 3600)
            elif file_data.expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=file_data.expires_in_hours)
                expires_in_seconds = int(file_data.expires_in_hours * 3600)
        
        # Store encrypted file data (server never decrypts)
        # Note: For encrypted uploads, we store in MongoDB via drive service
        # But for now, we'll use the existing Redis storage for compatibility
        await store_encrypted_file(
            file_id=file_id,
            encrypted_content=file_data.encrypted_content,
            encrypted_content_key=encrypted_content_key,
            expires_in_seconds=expires_in_seconds,
        )
        
        # Store file metadata
        await store_file_metadata(
            file_id=file_id,
            filename=file_data.filename,
            size=file_size,
            content_type=file_data.content_type,
            owner_email=user_email,
            passcode_protected=passcode_protected,
            expires_in_seconds=expires_in_seconds,
        )
        
        # Update user storage usage
        await increment_user_storage(user_email, file_size)
        await add_user_file(user_email, file_id)
        
        logger.info(
            f"Encrypted file uploaded: id={file_id[:8]}..., "
            f"filename={file_data.filename}, size={file_size}, "
            f"passcode_protected={passcode_protected}"
        )
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file_data.filename,
            size=file_size,
            content_type=file_data.content_type,
            passcode_protected=passcode_protected,
            expires_at=expires_at.isoformat() if expires_at else None,
            created_at=datetime.utcnow().isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Encrypted file upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload encrypted file"
        )


@router.delete("/file/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Delete file and all associated data.
    
    Requires authentication and file ownership.
    """
    try:
        # Check ownership and get metadata BEFORE deletion
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Get metadata first (before deletion)
        metadata = await get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Check ownership
        owner_email = metadata.get("owner_email", "").lower()
        user_email = current_user.get("email", "").lower()
        if owner_email != user_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file"
            )
<<<<<<< HEAD
        
        # Get file size and owner before deletion
        file_size = metadata.get("size", 0)
        
        # Delete file from MongoDB
        drive_service = get_drive_service_mongodb()
        deleted = await drive_service.delete_file(file_id)
        
        # Delete from Redis (cleanup)
=======

        # Get file size before delete for storage quota update
        metadata = await get_file_metadata(file_id)
        file_size = metadata.get("size", 0) if metadata else 0

        # Delete file data and metadata
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
        redis = await get_redis()
        
        # Delete passcode salt (if exists)
        salt_key = f"drive:passcode_salt:{file_id}"
        await redis.delete(salt_key)
        
        # Delete rate limit counter
        rate_limit_key = f"{REDIS_RATE_LIMIT_UNLOCK_PREFIX}{file_id}"
        await redis.delete(rate_limit_key)
        
<<<<<<< HEAD
        # Decrement user storage usage (using metadata we got before deletion)
        if owner_email and file_size > 0:
            await decrement_user_storage(owner_email, file_size)
            await remove_user_file(owner_email, file_id)
        
        if deleted:
=======
        if deleted > 0:
            if file_size > 0:
                await subtract_storage_used(current_user.get("email"), file_size)
>>>>>>> 98a312f (Update database credentials to DigitalOcean PostgreSQL, add SSL CA cert support)
            logger.info(f"File deleted: id={file_id[:8]}...")
            return FileDeleteResponse(
                file_id=file_id,
                deleted=True,
                message="File deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )


@router.get("/files", response_model=FileListResponse)
async def list_files(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List all files for the current user.
    
    Returns file metadata only (no encrypted content).
    Supports pagination with limit and offset.
    """
    try:
        user_email = current_user.get("email")
        
        # Query MongoDB for user's files
        db = get_mongodb()
        files_collection = db.files
        
        # Build query
        query = {
            "owner_email": user_email.lower(),
        }
        
        # Exclude expired files
        query["$or"] = [
            {"expires_at": {"$exists": False}},
            {"expires_at": {"$gt": datetime.utcnow()}},
        ]
        
        # Get total count
        total = await files_collection.count_documents(query)
        
        # Get files with pagination
        cursor = files_collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
        file_docs = await cursor.to_list(length=limit)
        
        # Convert to response format
        files = []
        for file_doc in file_docs:
            expires_at = None
            if file_doc.get("expires_at"):
                expires_at_value = file_doc["expires_at"]
                if isinstance(expires_at_value, datetime):
                    expires_at = expires_at_value.isoformat()
                else:
                    expires_at = expires_at_value
            
            created_at = file_doc.get("created_at")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()
            
            files.append(FileListItem(
                file_id=file_doc.get("file_id"),
                filename=file_doc.get("filename", "unnamed"),
                size=file_doc.get("size", 0),
                content_type=file_doc.get("content_type"),
                passcode_protected=file_doc.get("passcode_protected", False),
                created_at=created_at or datetime.utcnow().isoformat(),
                expires_at=expires_at,
            ))
        
        logger.info(f"Listed {len(files)} files for user: {user_email}")
        
        return FileListResponse(
            files=files,
            total=total,
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Failed to list files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files"
        )


@router.get("/file/{file_id}/download-encrypted", response_model=EncryptedFileDownloadResponse)
async def download_encrypted_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Download encrypted file with encrypted content key for client-side decryption.
    
    This endpoint requires authentication and returns both the encrypted file content
    and the encrypted content key. The client must decrypt both on the device:
    
    1. First, decrypt encrypted_content_key using the device key stored locally
    2. Then, decrypt encrypted_content using the decrypted content key
    
    If the device key is not present locally, the file cannot be decrypted.
    
    Requires:
    - Authentication (Bearer token)
    - File ownership (user must own the file)
    
    Returns:
    - encrypted_content: Encrypted file content (multi-layer encrypted)
    - encrypted_content_key: Encrypted content key (encrypted with user's device key)
    
    The client is responsible for:
    - Storing the device key securely on the device
    - Decrypting encrypted_content_key using device key
    - Decrypting encrypted_content using the decrypted content key
    """
    try:
        # Authentication is required (enforced by get_current_user dependency)
        user_email = current_user.get("email")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Verify ownership
        if not await check_ownership(file_id, user_email):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file"
            )
        
        # Get file metadata
        metadata = await get_file_metadata(file_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or expired"
            )
        
        # Check if file has expired
        expires_at = metadata.get("expires_at")
        if expires_at:
            try:
                if isinstance(expires_at, str):
                    expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                else:
                    expires_at_dt = expires_at
                if datetime.utcnow() > expires_at_dt:
                    raise HTTPException(
                        status_code=status.HTTP_410_GONE,
                        detail="File has expired"
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing expiration date: {e}")
        
        # Get encrypted file data from MongoDB
        file_data = await get_encrypted_file(file_id)
        if not file_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File data not found or expired"
            )
        
        encrypted_content = file_data.get("encrypted_content")
        encrypted_content_key = file_data.get("encrypted_content_key")
        
        if not encrypted_content or not encrypted_content_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File encryption data is incomplete"
            )
        
        # Ensure encrypted_content and encrypted_content_key are in the correct format
        # They should be dictionaries with ciphertext, nonce, tag
        if not isinstance(encrypted_content, dict) or not isinstance(encrypted_content_key, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid encryption data format"
            )
        
        logger.info(
            f"Encrypted file downloaded for client-side decryption: "
            f"id={file_id[:8]}..., filename={metadata.get('filename')}, "
            f"user={user_email}"
        )
        
        return EncryptedFileDownloadResponse(
            file_id=file_id,
            filename=metadata.get("filename", "unnamed"),
            size=metadata.get("size", 0),
            content_type=metadata.get("content_type"),
            encrypted_content=encrypted_content,
            encrypted_content_key=encrypted_content_key,
            passcode_protected=metadata.get("passcode_protected", False),
            created_at=metadata.get("created_at", datetime.utcnow().isoformat()),
            expires_at=expires_at,
            message="File downloaded. Decrypt encrypted_content_key using your device key, then decrypt encrypted_content using the decrypted content key."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download encrypted file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download encrypted file: {str(e)}"
        )


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
from app.api.v1.endpoints.auth import get_current_user
from app.core.redis_client import get_redis
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
    """Get file metadata from Redis"""
    redis = await get_redis()
    key = f"{REDIS_FILE_METADATA_PREFIX}{file_id}"
    
    metadata_json = await redis.get(key)
    if not metadata_json:
        return None
    
    import json
    try:
        return json.loads(metadata_json)
    except json.JSONDecodeError:
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
    """Get encrypted file data from Redis"""
    redis = await get_redis()
    key = f"{REDIS_FILE_PREFIX}{file_id}"
    
    file_json = await redis.get(key)
    if not file_json:
        return None
    
    import json
    try:
        return json.loads(file_json)
    except json.JSONDecodeError:
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


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    passcode: Optional[str] = Form(None),
    expires_in_hours: Optional[int] = Form(None, ge=1, le=8760),
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
        
        # Generate file ID
        file_id = generate_file_id()
        
        # Encrypt file using email service (reuse encryption logic)
        email_service = get_email_service()
        
        # Encrypt file content
        result = await email_service.encrypt_email_content(
            email_body=file_content,
            user_email=current_user.get("email"),
            passcode=passcode,
            expires_in_hours=expires_in_hours,
        )
        
        encrypted_content = result["encrypted_content"]
        encrypted_content_key = result["encrypted_content_key"]
        passcode_protected = result["encryption_mode"] == "passcode_protected"
        
        # Calculate expiration
        expires_in_seconds = None
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            expires_in_seconds = int(expires_in_hours * 3600)
        
        # Store encrypted file data
        await store_encrypted_file(
            file_id=file_id,
            encrypted_content=encrypted_content,
            encrypted_content_key=encrypted_content_key,
            expires_in_seconds=expires_in_seconds,
        )
        
        # Store file metadata
        await store_file_metadata(
            file_id=file_id,
            filename=file.filename or "unnamed",
            size=file_size,
            content_type=file.content_type,
            owner_email=current_user.get("email"),
            passcode_protected=passcode_protected,
            expires_in_seconds=expires_in_seconds,
        )
        
        # Store passcode salt if passcode-protected
        if passcode and passcode_protected:
            # Get salt from email service metadata (same logic)
            from app.services.email_service import REDIS_PASSCODE_SALT_PREFIX
            redis = await get_redis()
            email_salt_key = f"{REDIS_PASSCODE_SALT_PREFIX}{result['access_token']}"
            salt_base64 = await redis.get(email_salt_key)
            
            if salt_base64:
                await store_passcode_salt(file_id, salt_base64, expires_in_seconds)
        
        # Generate and store session key for device-local access
        # Session key is the content key (decrypted) - stored for device biometric access
        # For authenticated files (no passcode), we can decrypt and store the content key now
        if not passcode_protected:
            try:
                from app.api.v1.endpoints.public import store_session_key
                user_email = current_user.get("email")
                from app.core.key_manager import derive_key_from_passcode, generate_salt_for_identifier
                from app.core.encryption import decrypt_bytes
                
                user_salt = generate_salt_for_identifier(user_email)
                user_key = derive_key_from_passcode(user_email, user_salt)
                
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
        
        if is_passcode_protected and token:
            # File was unlocked via passcode - for now, we can't decrypt here
            # This would require storing the decrypted content key temporarily
            # For production, implement session key storage
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Download of passcode-protected files via signed URL requires session management (to be implemented)"
            )
        elif not is_passcode_protected:
            # Authenticated mode - decrypt with user key
            user_email = current_user.get("email") if current_user else metadata.get("owner_email")
            if not user_email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for file decryption"
                )
            
            # Decrypt content key using user key
            from app.core.key_manager import derive_key_from_passcode, generate_salt_for_identifier
            
            user_salt = generate_salt_for_identifier(user_email)
            user_key = derive_key_from_passcode(user_email, user_salt)
            
            try:
                content_key = decrypt_bytes(encrypted_content_key, user_key)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to decrypt file key: {str(e)}"
                )
            
            # Decrypt file content
            try:
                decrypted_content = decrypt_bytes(encrypted_content, content_key)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to decrypt file content: {str(e)}"
                )
            
            # Securely overwrite keys
            content_key = b"\x00" * len(content_key)
            user_key = b"\x00" * len(user_key)
        else:
            raise HTTPException(
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
        
        # Decrypt using passcode
        encrypted_content_key = file_data["encrypted_content_key"]
        
        from app.core.key_manager import derive_key_from_passcode
        salt = base64.b64decode(salt_base64)
        passcode_key = derive_key_from_passcode(unlock_data.passcode, salt)
        
        try:
            content_key = decrypt_bytes(encrypted_content_key, passcode_key)
        except Exception:
            # Increment failed attempt
            current_count = await increment_unlock_attempt(file_id)
            attempts_remaining = max(0, MAX_UNLOCK_ATTEMPTS - current_count)
            
            # Securely overwrite
            passcode_key = b"\x00" * len(passcode_key) if 'passcode_key' in locals() else b""
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Incorrect passcode",
                    "attempts_remaining": attempts_remaining,
                    "message": f"Incorrect passcode. {attempts_remaining} attempts remaining." if attempts_remaining > 0 else "File is now locked due to too many failed attempts."
                }
            )
        
        # Success - reset rate limit
        await reset_unlock_attempts(file_id)
        
        # Store decrypted content key temporarily in Redis for signed URL access
        # In production, consider storing this more securely or re-encrypting with a session key
        # For now, we'll generate signed URL that allows download without re-entering passcode
        # The signed URL itself acts as proof of successful unlock
        
        # Generate signed URL for download
        expires_minutes = signed_url_expires_minutes or SIGNED_URL_EXPIRE_MINUTES
        signed_token, signed_url_expires_at = generate_signed_url_token(file_id, expires_minutes)
        signed_url = f"/api/v1/drive/file/{file_id}/download?token={signed_token}"
        
        # Store unlocked flag (temporary, expires with signed URL)
        redis = await get_redis()
        unlocked_key = f"drive:unlocked:{file_id}:{signed_token}"
        await redis.setex(unlocked_key, expires_minutes * 60, "1")
        
        # Securely overwrite sensitive data
        content_key = b"\x00" * len(content_key)
        passcode_key = b"\x00" * len(passcode_key)
        salt = b"\x00" * len(salt) if 'salt' in locals() else b""
        
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
        # Check ownership
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not await check_ownership(file_id, current_user.get("email")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You don't own this file"
            )
        
        # Delete file data and metadata
        redis = await get_redis()
        
        deleted = 0
        
        # Delete encrypted file
        file_key = f"{REDIS_FILE_PREFIX}{file_id}"
        if await redis.delete(file_key):
            deleted += 1
        
        # Delete metadata
        metadata_key = f"{REDIS_FILE_METADATA_PREFIX}{file_id}"
        if await redis.delete(metadata_key):
            deleted += 1
        
        # Delete passcode salt
        salt_key = f"drive:passcode_salt:{file_id}"
        await redis.delete(salt_key)
        
        # Delete rate limit counter
        rate_limit_key = f"{REDIS_RATE_LIMIT_UNLOCK_PREFIX}{file_id}"
        await redis.delete(rate_limit_key)
        
        if deleted > 0:
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


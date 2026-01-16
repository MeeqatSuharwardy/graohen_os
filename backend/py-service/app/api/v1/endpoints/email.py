"""Email API endpoints"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, Field, field_validator
import logging

from app.config import settings
from app.services.email_service import (
    get_email_service,
    EmailEncryptionError,
)
from app.api.v1.endpoints.auth import get_current_user
from app.core.redis_client import get_redis
from app.core.security_hardening import (
    get_security_service,
    SecurityEvent,
    RateLimitError,
    ViewOnceError,
    BruteForceError,
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Rate limiting constants
REDIS_RATE_LIMIT_PREFIX = "rate_limit:unlock:"
MAX_UNLOCK_ATTEMPTS = 5
UNLOCK_RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
LOCKOUT_DURATION = 3600  # 1 hour lockout after max attempts

# External link settings
EXTERNAL_HTTPS_BASE_URL = settings.EXTERNAL_HTTPS_BASE_URL


# Pydantic Models
class EmailSendRequest(BaseModel):
    """Email send request"""
    to: List[EmailStr] = Field(..., min_items=1, description="Recipient email addresses")
    subject: Optional[str] = Field(None, max_length=500, description="Email subject (encrypted)")
    body: str = Field(..., min_length=1, description="Email body content")
    passcode: Optional[str] = Field(None, min_length=4, max_length=128, description="Optional passcode for email protection")
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760, description="Expiration time in hours (1-8760)")
    self_destruct: bool = Field(False, description="Delete email after first read")


class EmailSendResponse(BaseModel):
    """Email send response"""
    email_id: str = Field(..., description="Access token for email access")
    email_address: str = Field(..., description="Email address (for sending via SMTP)")
    secure_link: str = Field(..., description="Secure HTTPS link for recipients")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    encryption_mode: str = Field(..., description="authenticated or passcode_protected")


class EmailUnlockRequest(BaseModel):
    """Email unlock request"""
    passcode: str = Field(..., min_length=1, description="Passcode to unlock email")


class EmailUnlockResponse(BaseModel):
    """Email unlock response"""
    email_id: str
    subject: Optional[str] = None
    body: str
    unlocked_at: str


class EmailGetResponse(BaseModel):
    """Email get response (for authenticated users)"""
    email_id: str
    subject: Optional[str] = None
    body: str
    encryption_mode: str
    expires_at: Optional[str] = None
    is_passcode_protected: bool


class EmailDeleteResponse(BaseModel):
    """Email delete response"""
    email_id: str
    deleted: bool
    message: str


async def check_rate_limit(identifier: str, max_attempts: int, window_seconds: int) -> bool:
    """
    Check if identifier has exceeded rate limit.
    
    Returns:
        True if within limits, False if exceeded
    """
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_PREFIX}{identifier}"
    
    # Get current count
    current_count = await redis.get(key)
    
    if current_count is None:
        # First attempt, set counter with TTL
        await redis.setex(key, window_seconds, "1")
        return True
    
    count = int(current_count)
    
    if count >= max_attempts:
        # Check if lockout expired
        ttl = await redis.ttl(key)
        if ttl > 0:
            return False  # Still locked out
        else:
            # Reset counter
            await redis.setex(key, window_seconds, "1")
            return True
    
    # Increment counter
    await redis.incr(key)
    await redis.expire(key, window_seconds)
    return True


async def increment_unlock_attempt(email_id: str) -> int:
    """Increment unlock attempt counter and return current count"""
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_PREFIX}{email_id}"
    
    current_count = await redis.incr(key)
    
    # Set expiration on first attempt
    if current_count == 1:
        await redis.expire(key, UNLOCK_RATE_LIMIT_WINDOW)
    
    # Check if we've exceeded max attempts
    if current_count >= MAX_UNLOCK_ATTEMPTS:
        # Extend lockout period
        await redis.expire(key, LOCKOUT_DURATION)
    
    return current_count


async def get_unlock_attempts_remaining(email_id: str) -> int:
    """Get remaining unlock attempts before lockout"""
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_PREFIX}{email_id}"
    
    current_count = await redis.get(key)
    if current_count is None:
        return MAX_UNLOCK_ATTEMPTS
    
    count = int(current_count)
    remaining = max(0, MAX_UNLOCK_ATTEMPTS - count)
    
    # Check if locked out
    if count >= MAX_UNLOCK_ATTEMPTS:
        ttl = await redis.ttl(key)
        if ttl > 0:
            return 0  # Locked out
    
    return remaining


async def reset_unlock_attempts(email_id: str) -> None:
    """Reset unlock attempt counter (on successful unlock)"""
    redis = await get_redis()
    key = f"{REDIS_RATE_LIMIT_PREFIX}{email_id}"
    await redis.delete(key)


def generate_secure_link(email_id: str, base_url: Optional[str] = None) -> str:
    """Generate secure HTTPS link for email access"""
    if base_url is None:
        base_url = EXTERNAL_HTTPS_BASE_URL
    
    # Remove trailing slash if present
    base_url = base_url.rstrip("/")
    
    # Generate secure link
    secure_link = f"{base_url}/email/{email_id}"
    
    return secure_link


@router.post("/send", response_model=EmailSendResponse, status_code=status.HTTP_201_CREATED)
async def send_email(
    email_data: EmailSendRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Send encrypted email.
    
    Encrypts email content and returns secure link for recipients.
    Gmail/external services never see plaintext - only encrypted payloads.
    """
    try:
        service = get_email_service()
        security = get_security_service()
        client_ip = request.client.host if request.client else "unknown"
        
        # Prepare email body (include subject in body for encryption)
        email_body_content = email_data.body
        if email_data.subject:
            email_body_content = f"Subject: {email_data.subject}\n\n{email_data.body}"
        
        email_body_bytes = email_body_content.encode("utf-8")
        
        # Encrypt email content
        user_email = current_user.get("email")
        result = await service.encrypt_email_content(
            email_body=email_body_bytes,
            user_email=user_email,
            passcode=email_data.passcode,
            expires_in_hours=email_data.expires_in_hours,
        )
        
        access_token = result["access_token"]
        encryption_mode = result["encryption_mode"]
        
        # Generate email address for SMTP
        email_address = service.generate_email_address(access_token)
        
        # Generate secure HTTPS link for recipients
        secure_link = generate_secure_link(access_token)
        
        # Store self-destruct flag if enabled
        if email_data.self_destruct:
            redis = await get_redis()
            self_destruct_key = f"email:self_destruct:{access_token}"
            # Set flag that will be checked on read
            if result.get("expires_at"):
                # Use expiration time
                expires_at = datetime.fromisoformat(result["expires_at"].replace("Z", "+00:00"))
                expires_seconds = int((expires_at - datetime.utcnow()).total_seconds())
                await redis.setex(self_destruct_key, expires_seconds, "1")
            else:
                # Default: 30 days
                await redis.setex(self_destruct_key, 30 * 24 * 3600, "1")
        
        # Schedule auto-wipe if expiration set
        if email_data.expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=email_data.expires_in_hours)
            await security.schedule_auto_wipe(
                content_id=access_token,
                expires_at=expires_at,
                content_type="email",
            )
        
        # Log email sent event
        await security.log_security_event(
            SecurityEvent.EMAIL_SENT,
            identifier=current_user.get("email"),
            user_id=current_user.get("id"),
            ip_address=client_ip,
            action="email_send",
            metadata={
                "email_id": access_token[:8] + "...",
                "recipients_count": len(email_data.to),
                "has_passcode": email_data.passcode is not None,
                "self_destruct": email_data.self_destruct,
                "expires_in_hours": email_data.expires_in_hours,
            },
            success=True,
        )
        
        logger.info(
            f"Email sent: id={access_token[:8]}..., "
            f"to={email_data.to}, mode={encryption_mode}, "
            f"self_destruct={email_data.self_destruct}"
        )
        
        response = EmailSendResponse(
            email_id=access_token,
            email_address=email_address,
            secure_link=secure_link,
            expires_at=result.get("expires_at"),
            encryption_mode=encryption_mode,
        )
        
        return response
        
    except EmailEncryptionError as e:
        logger.error(f"Email encryption failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt email: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Email send failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )


@router.get("/{email_id}", response_model=EmailGetResponse)
async def get_email(
    email_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get encrypted email (for authenticated users).
    
    Only works for emails in authenticated mode (no passcode).
    For passcode-protected emails, use the unlock endpoint.
    """
    try:
        service = get_email_service()
        security = get_security_service()
        client_ip = request.client.host if request.client else "unknown"
        user_email = current_user.get("email")
        
        # Decrypt email for authenticated user
        email_body_bytes = await service.decrypt_email_for_authenticated_user(
            access_token=email_id,
            user_email=user_email,
        )
        
        # Parse email content (subject + body)
        email_content = email_body_bytes.decode("utf-8")
        subject = None
        body = email_content
        
        if email_content.startswith("Subject: "):
            lines = email_content.split("\n", 1)
            if len(lines) == 2:
                subject = lines[0].replace("Subject: ", "")
                body = lines[1].lstrip()
        
        # Get metadata (using internal method)
        # Note: This accesses internal method - in production, add public method
        from app.services.email_service import REDIS_ACCESS_TOKEN_PREFIX
        redis = await get_redis()
        metadata_key = f"{REDIS_ACCESS_TOKEN_PREFIX}{email_id}"
        metadata_json = await redis.get(metadata_key)
        
        metadata = None
        if metadata_json:
            import json
            try:
                metadata = json.loads(metadata_json)
            except json.JSONDecodeError:
                pass
        
        encryption_mode = metadata.get("encryption_mode", "authenticated") if metadata else "authenticated"
        is_passcode_protected = metadata.get("has_passcode", False) if metadata else False
        
        # Check self-destruct flag
        redis = await get_redis()
        self_destruct_key = f"email:self_destruct:{email_id}"
        self_destruct = await redis.get(self_destruct_key) is not None
        
        # Enforce view-once if self-destruct enabled
        if self_destruct:
            try:
                await security.enforce_view_once(
                    content_id=email_id,
                    identifier=user_email,
                )
            except ViewOnceError:
                await security.log_security_event(
                    SecurityEvent.ACCESS_DENIED,
                    identifier=user_email,
                    user_id=current_user.get("id"),
                    ip_address=client_ip,
                    action="email_access",
                    metadata={"email_id": email_id[:8] + "...", "reason": "view_once"},
                    success=False,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email can only be viewed once (self-destruct)"
                )
        
        # Delete email if self-destruct is enabled
        if self_destruct:
            await service.delete_email(email_id)
            await redis.delete(self_destruct_key)
            
            await security.log_security_event(
                SecurityEvent.EMAIL_ACCESSED,
                identifier=user_email,
                user_id=current_user.get("id"),
                ip_address=client_ip,
                action="email_access",
                metadata={"email_id": email_id[:8] + "...", "self_destructed": True},
                success=True,
            )
            logger.info(f"Email self-destructed after read: {email_id[:8]}...")
        else:
            # Log email access
            await security.log_security_event(
                SecurityEvent.EMAIL_ACCESSED,
                identifier=user_email,
                user_id=current_user.get("id"),
                ip_address=client_ip,
                action="email_access",
                metadata={"email_id": email_id[:8] + "..."},
                success=True,
            )
        
        logger.info(f"Email retrieved: id={email_id[:8]}..., user={user_email}")
        
        # Get expiration from metadata
        expires_at = None
        if metadata:
            created_at_str = metadata.get("created_at")
            if created_at_str:
                # Expiration would be calculated from creation time and TTL
                # For now, we'll indicate if email has expiration
                expires_at = metadata.get("expires_at")
        
        return EmailGetResponse(
            email_id=email_id,
            subject=subject,
            body=body,
            encryption_mode=encryption_mode,
            expires_at=expires_at,
            is_passcode_protected=is_passcode_protected,
        )
        
    except EmailEncryptionError as e:
        error_msg = str(e).lower()
        if "passcode" in error_msg or "unlock" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email requires passcode unlock. Use /unlock endpoint."
            )
        elif "not found" in error_msg or "expired" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found or expired"
            )
        elif "access denied" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        else:
            logger.error(f"Email retrieval failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve email: {str(e)}"
            )
    except Exception as e:
        logger.error(f"Email retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email"
        )


@router.post("/{email_id}/unlock", response_model=EmailUnlockResponse)
async def unlock_email(
    email_id: str,
    unlock_data: EmailUnlockRequest,
    request: Request,
    x_forwarded_for: Optional[str] = Header(None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
):
    """
    Unlock passcode-protected email.
    
    Rate-limited: Max 5 attempts per hour per email.
    After max attempts, email is locked for 1 hour.
    """
    try:
        security = get_security_service()
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else (request.client.host if request.client else "unknown")
        identifier = f"{email_id}:{client_ip}"
        
        # Check rate limit (using email_id as identifier)
        attempts_remaining = await get_unlock_attempts_remaining(email_id)
        
        if attempts_remaining == 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many unlock attempts",
                    "message": "Email is temporarily locked. Please try again later.",
                    "lockout_duration_seconds": LOCKOUT_DURATION,
                }
            )
        
        service = get_email_service()
        
        # Attempt to decrypt with passcode
        try:
            email_body_bytes = await service.decrypt_email_with_passcode(
                access_token=email_id,
                passcode=unlock_data.passcode,
            )
        except EmailEncryptionError as e:
            # Record failed attempt
            remaining = await security.record_failed_attempt(
                identifier=identifier,
                action="email_unlock",
            )
            
            await security.log_security_event(
                SecurityEvent.UNLOCK_ATTEMPT,
                ip_address=client_ip,
                action="email_unlock",
                metadata={
                    "email_id": email_id[:8] + "...",
                    "reason": "incorrect_passcode",
                    "attempts_remaining": remaining,
                },
                success=False,
            )
            
            error_msg = str(e).lower()
            if "passcode" in error_msg or "incorrect" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "Incorrect passcode",
                        "attempts_remaining": remaining,
                        "message": f"Incorrect passcode. {attempts_remaining} attempts remaining." if attempts_remaining > 0 else "Email is now locked due to too many failed attempts."
                    }
                )
            else:
                logger.error(f"Email unlock failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to unlock email"
                )
        
        # Success - reset brute force counter
        await security.reset_brute_force_counter(identifier, action="email_unlock")
        
        # Check view-once if self-destruct enabled
        redis = await get_redis()
        self_destruct_key = f"email:self_destruct:{email_id}"
        self_destruct = await redis.get(self_destruct_key) is not None
        
        if self_destruct:
            try:
                await security.enforce_view_once(
                    content_id=email_id,
                    identifier=identifier,
                )
            except ViewOnceError:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email can only be viewed once (self-destruct)"
                )
        
        # Log successful unlock
        await security.log_security_event(
            SecurityEvent.EMAIL_ACCESSED,
            ip_address=client_ip,
            action="email_unlock",
            metadata={"email_id": email_id[:8] + "...", "self_destruct": self_destruct},
            success=True,
        )
        
        # Parse email content
        email_content = email_body_bytes.decode("utf-8")
        subject = None
        body = email_content
        
        if email_content.startswith("Subject: "):
            lines = email_content.split("\n", 1)
            if len(lines) == 2:
                subject = lines[0].replace("Subject: ", "")
                body = lines[1].lstrip()
        
        # Check self-destruct flag
        redis = await get_redis()
        self_destruct_key = f"email:self_destruct:{email_id}"
        self_destruct = await redis.get(self_destruct_key) is not None
        
        # Delete email if self-destruct is enabled
        if self_destruct:
            await service.delete_email(email_id)
            await redis.delete(self_destruct_key)
            logger.info(f"Email self-destructed after unlock: {email_id[:8]}...")
        
        # Log successful unlock
        logger.info(
            f"Email unlocked: id={email_id[:8]}..., "
            f"ip={client_ip}, ua={user_agent[:50] if user_agent else 'unknown'}"
        )
        
        return EmailUnlockResponse(
            email_id=email_id,
            subject=subject,
            body=body,
            unlocked_at=datetime.utcnow().isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email unlock failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock email"
        )


@router.delete("/{email_id}", response_model=EmailDeleteResponse)
async def delete_email(
    email_id: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """
    Delete encrypted email.
    
    Can be called by:
    - Authenticated user who created the email
    - Anyone with the email_id (public delete endpoint for self-destruct)
    """
    try:
        service = get_email_service()
        
        # Verify user owns the email (if authenticated)
        if current_user:
            from app.services.email_service import REDIS_ACCESS_TOKEN_PREFIX
            redis = await get_redis()
            metadata_key = f"{REDIS_ACCESS_TOKEN_PREFIX}{email_id}"
            metadata_json = await redis.get(metadata_key)
            
            metadata = None
            if metadata_json:
                import json
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    pass
            
            if metadata:
                user_email = current_user.get("email")
                email_owner = metadata.get("user_email")
                if email_owner and email_owner != user_email.lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only delete emails you created"
                    )
        
        # Delete email
        deleted = await service.delete_email(email_id)
        
        # Also delete self-destruct flag if exists
        redis = await get_redis()
        self_destruct_key = f"email:self_destruct:{email_id}"
        await redis.delete(self_destruct_key)
        
        # Delete rate limit counter
        rate_limit_key = f"{REDIS_RATE_LIMIT_PREFIX}{email_id}"
        await redis.delete(rate_limit_key)
        
        if deleted:
            logger.info(f"Email deleted: id={email_id[:8]}...")
            return EmailDeleteResponse(
                email_id=email_id,
                deleted=True,
                message="Email deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email deletion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete email"
        )


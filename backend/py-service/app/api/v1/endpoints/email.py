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
from app.services.email_service_mongodb import (
    get_email_service_mongodb,
    EmailEncryptionError as MongoDBEmailEncryptionError,
)
from app.services.email_ingestion import (
    get_email_ingestion_service,
    EmailIngestionError,
)
from app.middleware.email_security import (
    check_email_rate_limit,
    validate_email_token,
    validate_email_recipients,
    EmailSecurityMiddleware,
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


class EmailListItem(BaseModel):
    """Email list item (metadata only, no encrypted content)"""
    email_id: str
    access_token: str
    sender_email: Optional[str] = None
    recipient_emails: Optional[List[str]] = None
    subject: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    has_passcode: bool = False
    is_draft: bool = False
    status: str  # sent, inbox, draft


class EmailListResponse(BaseModel):
    """Email list response"""
    emails: List[EmailListItem]
    total: int
    limit: int
    offset: int


class DraftSaveRequest(BaseModel):
    """Draft save request"""
    to: List[EmailStr] = Field(..., min_items=1, description="Recipient email addresses")
    subject: Optional[str] = Field(None, max_length=500, description="Email subject")
    body: str = Field(..., min_length=1, description="Email body content")
    draft_id: Optional[str] = Field(None, description="Draft ID for updating existing draft")


class DraftSaveResponse(BaseModel):
    """Draft save response"""
    email_id: str
    access_token: str
    email_address: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EmailIngestRequest(BaseModel):
    """Email ingestion request from Postfix"""
    email_bytes: Optional[bytes] = None
    recipient_address: Optional[str] = None


class EmailIngestResponse(BaseModel):
    """Email ingestion response"""
    email_id: str
    status: str
    message: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None


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
    
    Security:
    - Rate limited: 50 emails/hour, 200 emails/day per user
    - Recipient validation: max 50 recipients per email
    - Token entropy validation: minimum 32 characters
    - Abuse pattern detection
    """
    try:
        user_email = current_user.get("email")
        
        # Security checks
        await check_email_rate_limit(user_email)
        validate_email_recipients(email_data.to)
        await EmailSecurityMiddleware.check_abuse_patterns(user_email, email_data.to)
        
        # Use MongoDB email service with strong encryption
        service = get_email_service_mongodb()
        security = get_security_service()
        client_ip = request.client.host if request.client else "unknown"
        
        # Prepare email body (include subject in body for encryption)
        email_body_content = email_data.body
        if email_data.subject:
            email_body_content = f"Subject: {email_data.subject}\n\n{email_data.body}"
        
        email_body_bytes = email_body_content.encode("utf-8")
        
        # Encrypt and store email in MongoDB with multi-layer encryption
        result = await service.encrypt_and_store_email(
            email_body=email_body_bytes,
            sender_email=user_email,
            recipient_emails=email_data.to,
            user_email=user_email,
            passcode=email_data.passcode,
            expires_in_hours=email_data.expires_in_hours,
            subject=email_data.subject,
            self_destruct=email_data.self_destruct,
        )
        
        access_token = result["access_token"]
        encryption_mode = result["encryption_mode"]
        email_address = result["email_address"]
        secure_link = result["secure_link"]
        
        # Self-destruct and expiration are handled in MongoDB service
        
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
        
        # Log email send for monitoring
        await EmailSecurityMiddleware.log_email_send(
            user_email=user_email,
            recipients=email_data.to,
            email_id=access_token,
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


# Inbox/Sent/Drafts Endpoints (MUST be before /{email_id} route to avoid route conflicts)

@router.get("/inbox", response_model=EmailListResponse)
async def get_inbox_emails(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get inbox emails (received emails).
    
    Returns list of emails where the current user is a recipient.
    Only returns metadata (no encrypted content).
    """
    try:
        user_email = current_user.get("email")
        service = get_email_service_mongodb()
        
        emails = await service.get_inbox_emails(
            user_email=user_email,
            limit=limit,
            offset=offset,
        )
        
        # Get total count
        from app.core.mongodb import get_mongodb
        db = get_mongodb()
        email_collection = db.emails
        total_query = {
            "recipient_emails": {"$in": [user_email.lower()]},
            "is_draft": False,
            "$or": [
                {"expires_at": {"$exists": False}},
                {"expires_at": {"$gt": datetime.utcnow()}},
            ],
        }
        total = await email_collection.count_documents(total_query)
        
        # Validate and create EmailListItem objects
        email_items = []
        for email in emails:
            try:
                email_items.append(EmailListItem(**email))
            except Exception as validation_error:
                logger.error(f"Failed to create EmailListItem: {validation_error}, email data: {email}", exc_info=True)
                # Skip invalid email items but log the error
                continue
        
        return EmailListResponse(
            emails=email_items,
            total=total,
            limit=limit,
            offset=offset,
        )
        
    except (EmailEncryptionError, MongoDBEmailEncryptionError) as e:
        logger.error(f"Email encryption error in inbox: {e}", exc_info=True)
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inbox emails: {error_msg}"
        )
    except Exception as e:
        logger.error(f"Failed to get inbox emails: {e}", exc_info=True)
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inbox emails: {error_msg}"
        )


@router.get("/sent", response_model=EmailListResponse)
async def get_sent_emails(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get sent emails.
    
    Returns list of emails sent by the current user.
    Only returns metadata (no encrypted content).
    """
    try:
        user_email = current_user.get("email")
        service = get_email_service_mongodb()
        
        emails = await service.get_sent_emails(
            user_email=user_email,
            limit=limit,
            offset=offset,
        )
        
        # Get total count
        from app.core.mongodb import get_mongodb
        db = get_mongodb()
        email_collection = db.emails
        total_query = {
            "sender_email": user_email.lower(),
            "is_draft": False,
            "$or": [
                {"expires_at": {"$exists": False}},
                {"expires_at": {"$gt": datetime.utcnow()}},
            ],
        }
        total = await email_collection.count_documents(total_query)
        
        return EmailListResponse(
            emails=[EmailListItem(**email) for email in emails],
            total=total,
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Failed to get sent emails: {e}", exc_info=True)
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sent emails: {error_msg}"
        )


@router.get("/drafts", response_model=EmailListResponse)
async def get_draft_emails(
    limit: int = 50,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get draft emails.
    
    Returns list of draft emails created by the current user.
    Only returns metadata (no encrypted content).
    """
    try:
        user_email = current_user.get("email")
        service = get_email_service_mongodb()
        
        emails = await service.get_draft_emails(
            user_email=user_email,
            limit=limit,
            offset=offset,
        )
        
        # Get total count
        from app.core.mongodb import get_mongodb
        db = get_mongodb()
        email_collection = db.emails
        total = await email_collection.count_documents({
            "sender_email": user_email.lower(),
            "is_draft": True,
        })
        
        return EmailListResponse(
            emails=[EmailListItem(**email) for email in emails],
            total=total,
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Failed to get draft emails: {e}", exc_info=True)
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve draft emails: {error_msg}"
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
        # Use MongoDB email service
        service = get_email_service_mongodb()
        security = get_security_service()
        client_ip = request.client.host if request.client else "unknown"
        user_email = current_user.get("email")
        
        # Decrypt email for authenticated user and get metadata in one call
        # This avoids a second MongoDB query
        email_body_bytes, metadata = await service.decrypt_email_for_authenticated_user(
            access_token=email_id,
            user_email=user_email,
            return_metadata=True,
        )
        
        # Parse email content (subject + body)
        email_content = email_body_bytes.decode("utf-8")
        subject = metadata.get("subject")  # Use subject from metadata if available
        body = email_content
        
        # If subject is in email content, extract it
        if not subject and email_content.startswith("Subject: "):
            lines = email_content.split("\n", 1)
            if len(lines) == 2:
                subject = lines[0].replace("Subject: ", "")
                body = lines[1].lstrip()
        
        # Get metadata from decryption result (no second MongoDB query needed)
        encryption_mode = metadata.get("encryption_mode", "authenticated")
        is_passcode_protected = metadata.get("has_passcode", False)
        self_destruct = metadata.get("self_destruct", False)
        
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
            redis = await get_redis()
            self_destruct_key = f"view_once:email:{email_id}:{user_email}"
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
        
        # Get expiration from metadata (already retrieved)
        expires_at = metadata.get("expires_at")
        if expires_at and isinstance(expires_at, datetime):
            expires_at = expires_at.isoformat()
        elif expires_at and isinstance(expires_at, str):
            # Already a string, use as is
            pass
        
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
        
        # Use MongoDB email service
        service = get_email_service_mongodb()
        
        # Attempt to decrypt with passcode
        try:
            email_body_bytes = await service.decrypt_email_with_passcode(
                access_token=email_id,
                passcode=unlock_data.passcode,
            )
        except (EmailEncryptionError, MongoDBEmailEncryptionError) as e:
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
        
        # Self-destruct is handled automatically in MongoDB service
        
        # Log successful unlock
        await security.log_security_event(
            SecurityEvent.EMAIL_ACCESSED,
            ip_address=client_ip,
            action="email_unlock",
            metadata={"email_id": email_id[:8] + "..."},
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
        # Use MongoDB email service
        service = get_email_service_mongodb()
        
        # Verify user owns the email (if authenticated)
        if current_user:
            from app.core.mongodb import get_mongodb
            db = get_mongodb()
            email_collection = db.emails
            # Try both access_token and email_id (they should be the same)
            email_doc = await email_collection.find_one({
                "$or": [
                    {"access_token": email_id},
                    {"email_id": email_id}
                ]
            })
            
            if email_doc:
                user_email = current_user.get("email")
                email_owner = email_doc.get("sender_email", "").lower()
                if email_owner and email_owner != user_email.lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only delete emails you created"
                    )
        
        # Delete email from MongoDB
        deleted = await service.delete_email(email_id)
        
        # Delete rate limit counter from Redis
        redis = await get_redis()
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


@router.post("/ingest", response_model=EmailIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_email(
    request: Request,
):
    """
    Ingest incoming email from Postfix SMTP server.
    
    This endpoint receives emails piped from Postfix and:
    1. Parses email content
    2. Extracts token from recipient address (token@fxmail.ai)
    3. Encrypts email with 3-layer encryption
    4. Stores in MongoDB
    
    Expected flow:
    Postfix → Pipe → FastAPI /email/ingest → MongoDB
    
    Security:
    - Only accepts emails to token@fxmail.ai addresses
    - Validates token entropy (min 32 chars)
    - Prevents duplicate ingestion
    """
    try:
        # Get raw email bytes from request body
        email_bytes = await request.body()
        
        if not email_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email content is required"
            )
        
        # Validate email size
        EmailSecurityMiddleware.validate_email_size(len(email_bytes))
        
        # Get recipient from headers (Postfix sets this)
        recipient_address = request.headers.get("X-Recipient") or request.headers.get("To")
        
        # Ingest email
        ingestion_service = get_email_ingestion_service()
        result = await ingestion_service.ingest_email(
            email_bytes=email_bytes,
            recipient_address=recipient_address,
        )
        
        logger.info(
            f"Email ingested: id={result['email_id'][:16]}..., "
            f"sender={result.get('sender', 'unknown')}, "
            f"status={result['status']}"
        )
        
        return EmailIngestResponse(
            email_id=result["email_id"],
            status=result["status"],
            message=result.get("message"),
            sender=result.get("sender"),
            recipient=result.get("recipient"),
        )
        
    except EmailIngestionError as e:
        logger.warning(f"Email ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email ingestion error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest email"
        )


@router.get("/token/{token}", response_model=EmailGetResponse)
async def get_email_by_token(
    token: str,
    request: Request,
):
    """
    Get encrypted email by token (for web viewer).
    
    This endpoint allows accessing emails via token without authentication.
    Used by the web email viewer at fxmail.ai/email/{token}
    
    Security:
    - Token must be at least 32 characters
    - Returns encrypted payload (client decrypts)
    - Never decrypts on server
    """
    try:
        # Validate token entropy
        validate_email_token(token)
        
        # Use MongoDB email service
        service = get_email_service_mongodb()
        client_ip = request.client.host if request.client else "unknown"
        
        # Get email metadata from MongoDB
        from app.core.mongodb import get_mongodb
        db = get_mongodb()
        email_collection = db.emails
        
        # Find email by email_id (token)
        # Try both email_id and access_token (they should be the same)
        email_doc = await email_collection.find_one({
            "$or": [
                {"email_id": token},
                {"access_token": token}
            ]
        })
        
        if not email_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        # Check expiration
        if email_doc.get("expires_at"):
            expires_at = email_doc["expires_at"]
            if isinstance(expires_at, str):
                from datetime import datetime
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.utcnow() > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Email has expired"
                )
        
        # Return metadata (encrypted content stays encrypted)
        # Client will decrypt using passcode or authentication
        encryption_mode = email_doc.get("encryption_mode", "authenticated")
        is_passcode_protected = email_doc.get("has_passcode", False)
        
        # Log access
        logger.info(f"Email accessed by token: {token[:16]}..., ip={client_ip}")
        
        return EmailGetResponse(
            email_id=token,
            subject=None,  # Subject is encrypted, don't expose
            body="",  # Body is encrypted, don't expose
            encryption_mode=encryption_mode,
            expires_at=email_doc.get("expires_at").isoformat() if email_doc.get("expires_at") else None,
            is_passcode_protected=is_passcode_protected,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email by token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve email"
        )


@router.post("/drafts", response_model=DraftSaveResponse, status_code=status.HTTP_201_CREATED)
async def save_draft_email(
    draft_data: DraftSaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Save or update draft email.
    
    Creates a new draft or updates an existing draft if draft_id is provided.
    Drafts are encrypted and stored but not sent until explicitly sent.
    """
    try:
        user_email = current_user.get("email")
        service = get_email_service_mongodb()
        
        # Prepare email body (include subject in body for encryption)
        email_body_content = draft_data.body
        if draft_data.subject:
            email_body_content = f"Subject: {draft_data.subject}\n\n{draft_data.body}"
        
        email_body_bytes = email_body_content.encode("utf-8")
        
        # Save draft
        result = await service.save_draft_email(
            email_body=email_body_bytes,
            sender_email=user_email,
            recipient_emails=draft_data.to,
            subject=draft_data.subject,
            draft_id=draft_data.draft_id,
        )
        
        logger.info(f"Draft saved: id={result['email_id'][:8]}...")
        
        return DraftSaveResponse(
            email_id=result["email_id"],
            access_token=result["access_token"],
            email_address=result["email_address"],
            status=result["status"],
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )
        
    except Exception as e:
        logger.error(f"Failed to save draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save draft email"
        )


@router.put("/drafts/{draft_id}", response_model=DraftSaveResponse)
async def update_draft_email(
    draft_id: str,
    draft_data: DraftSaveRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update existing draft email.
    
    Updates the draft with new content. The draft_id must match an existing draft owned by the user.
    """
    try:
        user_email = current_user.get("email")
        
        # Verify draft ownership
        from app.core.mongodb import get_mongodb
        db = get_mongodb()
        email_collection = db.emails
        draft = await email_collection.find_one({"email_id": draft_id, "is_draft": True})
        
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
        
        if draft.get("sender_email", "").lower() != user_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own drafts"
            )
        
        service = get_email_service_mongodb()
        
        # Prepare email body
        email_body_content = draft_data.body
        if draft_data.subject:
            email_body_content = f"Subject: {draft_data.subject}\n\n{draft_data.body}"
        
        email_body_bytes = email_body_content.encode("utf-8")
        
        # Update draft
        result = await service.save_draft_email(
            email_body=email_body_bytes,
            sender_email=user_email,
            recipient_emails=draft_data.to,
            subject=draft_data.subject,
            draft_id=draft_id,
        )
        
        logger.info(f"Draft updated: id={draft_id[:8]}...")
        
        return DraftSaveResponse(
            email_id=result["email_id"],
            access_token=result["access_token"],
            email_address=result["email_address"],
            status=result["status"],
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update draft email"
        )


@router.delete("/drafts/{draft_id}", response_model=EmailDeleteResponse)
async def delete_draft_email(
    draft_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Delete draft email.
    
    Only the owner of the draft can delete it.
    """
    try:
        user_email = current_user.get("email")
        
        # Verify draft ownership
        from app.core.mongodb import get_mongodb
        db = get_mongodb()
        email_collection = db.emails
        draft = await email_collection.find_one({"email_id": draft_id, "is_draft": True})
        
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
        
        if draft.get("sender_email", "").lower() != user_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own drafts"
            )
        
        service = get_email_service_mongodb()
        deleted = await service.delete_email(draft_id)
        
        if deleted:
            logger.info(f"Draft deleted: id={draft_id[:8]}...")
            return EmailDeleteResponse(
                email_id=draft_id,
                deleted=True,
                message="Draft deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete draft email"
        )


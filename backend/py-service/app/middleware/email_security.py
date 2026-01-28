"""Email Security Middleware

Rate limiting, abuse protection, and validation for email operations.
"""

import hashlib
import secrets
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import logging

from app.core.redis_client import get_redis
from app.config import settings

logger = logging.getLogger(__name__)

# Rate limiting constants
MAX_EMAILS_PER_HOUR = 50
MAX_EMAILS_PER_DAY = 200
MAX_RECIPIENTS_PER_EMAIL = 50
MAX_EMAIL_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MIN_TOKEN_LENGTH = 32

# Redis key prefixes
REDIS_EMAIL_RATE_LIMIT_PREFIX = "email:rate_limit:"
REDIS_EMAIL_ABUSE_PREFIX = "email:abuse:"


class EmailSecurityMiddleware:
    """Security middleware for email operations"""
    
    @staticmethod
    async def check_email_send_rate_limit(user_email: str) -> bool:
        """
        Check if user has exceeded email send rate limit.
        
        Args:
            user_email: User email address
            
        Returns:
            True if within limits
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        redis = await get_redis()
        user_key = user_email.lower()
        
        # Check hourly limit
        hourly_key = f"{REDIS_EMAIL_RATE_LIMIT_PREFIX}hour:{user_key}"
        hourly_count = await redis.get(hourly_key)
        
        if hourly_count and int(hourly_count) >= MAX_EMAILS_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {MAX_EMAILS_PER_HOUR} emails per hour allowed",
                    "retry_after": 3600,
                }
            )
        
        # Check daily limit
        daily_key = f"{REDIS_EMAIL_RATE_LIMIT_PREFIX}day:{user_key}"
        daily_count = await redis.get(daily_key)
        
        if daily_count and int(daily_count) >= MAX_EMAILS_PER_DAY:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Daily limit exceeded",
                    "message": f"Maximum {MAX_EMAILS_PER_DAY} emails per day allowed",
                    "retry_after": 86400,
                }
            )
        
        # Increment counters
        if hourly_count:
            await redis.incr(hourly_key)
        else:
            await redis.setex(hourly_key, 3600, "1")  # 1 hour TTL
        
        if daily_count:
            await redis.incr(daily_key)
        else:
            await redis.setex(daily_key, 86400, "1")  # 24 hours TTL
        
        return True
    
    @staticmethod
    async def validate_sender_domain(sender_email: str) -> bool:
        """
        Validate sender email domain.
        
        Args:
            sender_email: Sender email address
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If invalid domain
        """
        if not sender_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sender email is required"
            )
        
        sender_email = sender_email.lower().strip()
        
        # For now, allow any domain (can be restricted later)
        # In production, you might want to restrict to @fxmail.ai
        if not "@" in sender_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid sender email format"
            )
        
        return True
    
    @staticmethod
    def validate_token_entropy(token: str) -> bool:
        """
        Validate token has sufficient entropy.
        
        Args:
            token: Token string
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If token entropy insufficient
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is required"
            )
        
        if len(token) < MIN_TOKEN_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token must be at least {MIN_TOKEN_LENGTH} characters"
            )
        
        # Check for sufficient randomness (basic check)
        # Count unique characters
        unique_chars = len(set(token))
        if unique_chars < 16:  # At least 16 unique characters
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token lacks sufficient entropy"
            )
        
        return True
    
    @staticmethod
    def validate_recipients(recipients: list) -> bool:
        """
        Validate recipient list.
        
        Args:
            recipients: List of recipient email addresses
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If invalid recipients
        """
        if not recipients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one recipient is required"
            )
        
        if len(recipients) > MAX_RECIPIENTS_PER_EMAIL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_RECIPIENTS_PER_EMAIL} recipients per email allowed"
            )
        
        # Validate email format
        import re
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
        
        for recipient in recipients:
            if not email_pattern.match(recipient.lower()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid recipient email format: {recipient}"
                )
        
        return True
    
    @staticmethod
    def validate_email_size(email_size_bytes: int) -> bool:
        """
        Validate email size.
        
        Args:
            email_size_bytes: Email size in bytes
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If email too large
        """
        if email_size_bytes > MAX_EMAIL_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Email size exceeds maximum of {MAX_EMAIL_SIZE_BYTES / (1024*1024):.1f} MB"
            )
        
        return True
    
    @staticmethod
    async def check_abuse_patterns(user_email: str, recipients: list) -> bool:
        """
        Check for abuse patterns.
        
        Args:
            user_email: User email address
            recipients: List of recipients
            
        Returns:
            True if no abuse detected
            
        Raises:
            HTTPException: If abuse detected
        """
        redis = await get_redis()
        user_key = user_email.lower()
        
        # Check for rapid-fire sending (same recipients repeatedly)
        abuse_key = f"{REDIS_EMAIL_ABUSE_PREFIX}rapid:{user_key}"
        rapid_count = await redis.get(abuse_key)
        
        if rapid_count and int(rapid_count) > 10:  # More than 10 rapid sends
            logger.warning(f"Abuse pattern detected for {user_email}: rapid sending")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Abuse pattern detected: too many rapid sends"
            )
        
        # Increment rapid send counter (expires in 5 minutes)
        if rapid_count:
            await redis.incr(abuse_key)
        else:
            await redis.setex(abuse_key, 300, "1")  # 5 minutes
        
        return True
    
    @staticmethod
    async def log_email_send(
        user_email: str,
        recipients: list,
        email_id: str,
        success: bool = True,
    ) -> None:
        """
        Log email send event for monitoring.
        
        Args:
            user_email: Sender email
            recipients: Recipient emails
            email_id: Email ID/token
            success: Whether send was successful
        """
        logger.info(
            f"Email send: user={user_email}, recipients={len(recipients)}, "
            f"email_id={email_id[:16]}..., success={success}"
        )


# Convenience functions
async def check_email_rate_limit(user_email: str) -> bool:
    """Check email send rate limit"""
    return await EmailSecurityMiddleware.check_email_send_rate_limit(user_email)


def validate_email_token(token: str) -> bool:
    """Validate email token entropy"""
    return EmailSecurityMiddleware.validate_token_entropy(token)


def validate_email_recipients(recipients: list) -> bool:
    """Validate recipient list"""
    return EmailSecurityMiddleware.validate_recipients(recipients)

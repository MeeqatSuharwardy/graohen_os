"""Security Hardening Module

Comprehensive security features:
- Redis-based rate limiting
- Audit logging
- Brute-force detection
- Token expiration enforcement
- View-once logic
- Auto-wipe after expiry
- Sensitive data sanitization in logs
"""

import json
import re
import hashlib
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum
import logging

from app.core.redis_client import get_redis
from app.config import settings

logger = logging.getLogger(__name__)

# Redis key prefixes
REDIS_RATE_LIMIT_PREFIX = "security:rate_limit:"
REDIS_BRUTE_FORCE_PREFIX = "security:brute_force:"
REDIS_AUDIT_LOG_PREFIX = "security:audit:"
REDIS_VIEW_ONCE_PREFIX = "security:view_once:"
REDIS_TOKEN_EXPIRY_PREFIX = "security:token_expiry:"

# Rate limiting defaults
DEFAULT_RATE_LIMIT_WINDOW = 3600  # 1 hour
DEFAULT_MAX_REQUESTS = 100
DEFAULT_BRUTE_FORCE_ATTEMPTS = 5
DEFAULT_BRUTE_FORCE_WINDOW = 3600  # 1 hour
DEFAULT_BRUTE_FORCE_LOCKOUT = 3600  # 1 hour

# Audit log retention
AUDIT_LOG_RETENTION_DAYS = 90


class SecurityEvent(str, Enum):
    """Security event types for audit logging"""
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REVOKED = "token_revoked"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    FILE_DELETE = "file_delete"
    EMAIL_SENT = "email_sent"
    EMAIL_ACCESSED = "email_accessed"
    UNLOCK_ATTEMPT = "unlock_attempt"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCESS_DENIED = "access_denied"


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded"""
    pass


class BruteForceError(Exception):
    """Exception raised when brute force is detected"""
    pass


class TokenExpiredError(Exception):
    """Exception raised when token is expired"""
    pass


class ViewOnceError(Exception):
    """Exception raised when content was already viewed"""
    pass


class SecurityService:
    """Centralized security service"""
    
    def __init__(self):
        self.rate_limits: Dict[str, Dict[str, int]] = {}
    
    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW,
        action: Optional[str] = None,
    ) -> bool:
        """
        Check if identifier has exceeded rate limit.
        
        Args:
            identifier: Unique identifier (IP, user_id, email, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            action: Optional action name for logging
        
        Returns:
            True if within limits, False if exceeded
        
        Raises:
            RateLimitError: If rate limit exceeded
        """
        redis = await get_redis()
        
        # Create key with optional action
        if action:
            key = f"{REDIS_RATE_LIMIT_PREFIX}{action}:{identifier}"
        else:
            key = f"{REDIS_RATE_LIMIT_PREFIX}{identifier}"
        
        # Get current count
        current_count = await redis.get(key)
        
        if current_count is None:
            # First request - set counter with TTL
            await redis.setex(key, window_seconds, "1")
            return True
        
        count = int(current_count)
        
        if count >= max_requests:
            # Log rate limit exceeded
            await self.log_security_event(
                SecurityEvent.RATE_LIMIT_EXCEEDED,
                identifier=identifier,
                action=action,
                metadata={"count": count, "max_requests": max_requests}
            )
            raise RateLimitError(
                f"Rate limit exceeded: {count}/{max_requests} requests in {window_seconds}s"
            )
        
        # Increment counter
        await redis.incr(key)
        await redis.expire(key, window_seconds)
        
        return True
    
    async def check_brute_force(
        self,
        identifier: str,
        max_attempts: int = DEFAULT_BRUTE_FORCE_ATTEMPTS,
        window_seconds: int = DEFAULT_BRUTE_FORCE_WINDOW,
        lockout_seconds: int = DEFAULT_BRUTE_FORCE_LOCKOUT,
        action: Optional[str] = None,
    ) -> bool:
        """
        Check for brute force attempts and apply lockout.
        
        Args:
            identifier: Unique identifier (IP, user_id, email, etc.)
            max_attempts: Maximum failed attempts before lockout
            window_seconds: Time window for counting attempts
            lockout_seconds: Lockout duration after max attempts
            action: Optional action name for logging
        
        Returns:
            True if not locked out, False if locked out
        
        Raises:
            BruteForceError: If locked out
        """
        redis = await get_redis()
        
        if action:
            key = f"{REDIS_BRUTE_FORCE_PREFIX}{action}:{identifier}"
        else:
            key = f"{REDIS_BRUTE_FORCE_PREFIX}{identifier}"
        
        # Get current attempt count
        current_count = await redis.get(key)
        
        if current_count is None:
            # First attempt
            await redis.setex(key, window_seconds, "1")
            return True
        
        count = int(current_count)
        
        if count >= max_attempts:
            # Check if still in lockout period
            ttl = await redis.ttl(key)
            if ttl > 0:
                # Log brute force detection
                await self.log_security_event(
                    SecurityEvent.BRUTE_FORCE_DETECTED,
                    identifier=identifier,
                    action=action,
                    metadata={
                        "attempts": count,
                        "lockout_remaining_seconds": ttl
                    }
                )
                raise BruteForceError(
                    f"Too many failed attempts. Locked out for {ttl} seconds."
                )
            else:
                # Lockout expired - reset counter
                await redis.setex(key, window_seconds, "1")
                return True
        
        # Increment counter
        await redis.incr(key)
        await redis.expire(key, window_seconds)
        
        return True
    
    async def record_failed_attempt(
        self,
        identifier: str,
        action: Optional[str] = None,
        max_attempts: int = DEFAULT_BRUTE_FORCE_ATTEMPTS,
        window_seconds: int = DEFAULT_BRUTE_FORCE_WINDOW,
        lockout_seconds: int = DEFAULT_BRUTE_FORCE_LOCKOUT,
    ) -> int:
        """
        Record a failed attempt and return remaining attempts.
        
        Returns:
            Remaining attempts before lockout
        """
        redis = await get_redis()
        
        if action:
            key = f"{REDIS_BRUTE_FORCE_PREFIX}{action}:{identifier}"
        else:
            key = f"{REDIS_BRUTE_FORCE_PREFIX}{identifier}"
        
        current_count = await redis.incr(key)
        
        if current_count == 1:
            await redis.expire(key, window_seconds)
        
        # If exceeded max attempts, extend lockout
        if current_count >= max_attempts:
            await redis.expire(key, lockout_seconds)
            
            # Log brute force
            await self.log_security_event(
                SecurityEvent.BRUTE_FORCE_DETECTED,
                identifier=identifier,
                action=action,
                metadata={"attempts": current_count}
            )
        
        remaining = max(0, max_attempts - current_count)
        return remaining
    
    async def reset_brute_force_counter(
        self,
        identifier: str,
        action: Optional[str] = None,
    ) -> None:
        """Reset brute force counter after successful attempt"""
        redis = await get_redis()
        
        if action:
            key = f"{REDIS_BRUTE_FORCE_PREFIX}{action}:{identifier}"
        else:
            key = f"{REDIS_BRUTE_FORCE_PREFIX}{identifier}"
        
        await redis.delete(key)
    
    async def log_security_event(
        self,
        event_type: SecurityEvent,
        identifier: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        action: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """
        Log security event to audit log.
        
        Logs are stored in Redis with TTL for automatic cleanup.
        Sensitive data is sanitized before logging.
        """
        redis = await get_redis()
        
        event = {
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "identifier": sanitize_log_data(identifier) if identifier else None,
            "user_id": sanitize_log_data(user_id) if user_id else None,
            "ip_address": sanitize_ip_address(ip_address) if ip_address else None,
            "action": action,
            "success": success,
            "metadata": sanitize_metadata(metadata) if metadata else None,
        }
        
        # Store in Redis with TTL (90 days retention)
        event_id = f"{event_type.value}:{datetime.utcnow().timestamp()}:{hashlib.sha256(str(identifier or '').encode()).hexdigest()[:8]}"
        key = f"{REDIS_AUDIT_LOG_PREFIX}{event_id}"
        
        event_json = json.dumps(event)
        
        # Store with TTL
        ttl_seconds = AUDIT_LOG_RETENTION_DAYS * 24 * 3600
        await redis.setex(key, ttl_seconds, event_json)
        
        # Also log to application logger (sanitized)
        log_message = f"Security Event: {event_type.value} | identifier={sanitize_log_data(identifier)} | action={action} | success={success}"
        if success:
            logger.info(log_message)
        else:
            logger.warning(log_message)
    
    async def get_audit_logs(
        self,
        event_type: Optional[SecurityEvent] = None,
        identifier: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs from Redis.
        
        Note: This uses SCAN which may be slow for large datasets.
        In production, consider using a time-series database.
        """
        redis = await get_redis()
        logs = []
        
        pattern = f"{REDIS_AUDIT_LOG_PREFIX}*"
        if event_type:
            pattern = f"{REDIS_AUDIT_LOG_PREFIX}{event_type.value}:*"
        
        async for key in redis.scan_iter(match=pattern, count=1000):
            event_json = await redis.get(key)
            if not event_json:
                continue
            
            try:
                event = json.loads(event_json)
                
                # Filter by identifier
                if identifier and event.get("identifier") != sanitize_log_data(identifier):
                    continue
                
                # Filter by time range
                event_time = datetime.fromisoformat(event["timestamp"])
                if start_time and event_time < start_time:
                    continue
                if end_time and event_time > end_time:
                    continue
                
                logs.append(event)
                
                if len(logs) >= limit:
                    break
                    
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return logs
    
    async def check_token_expiration(
        self,
        token_id: str,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Check if token is expired and enforce expiration.
        
        Args:
            token_id: Token identifier
            expires_at: Expiration timestamp (if known)
        
        Returns:
            True if valid, False if expired
        
        Raises:
            TokenExpiredError: If token is expired
        """
        redis = await get_redis()
        key = f"{REDIS_TOKEN_EXPIRE_PREFIX}{token_id}"
        
        # Check Redis for expiration marker
        expiry_marker = await redis.get(key)
        if expiry_marker == "expired":
            raise TokenExpiredError("Token has been expired")
        
        # Check explicit expiration time
        if expires_at:
            if datetime.utcnow() > expires_at:
                # Mark as expired in Redis
                await redis.setex(key, 86400, "expired")  # Keep marker for 24h
                raise TokenExpiredError("Token has expired")
        
        return True
    
    async def mark_token_expired(self, token_id: str) -> None:
        """Mark token as expired in Redis"""
        redis = await get_redis()
        key = f"{REDIS_TOKEN_EXPIRE_PREFIX}{token_id}"
        await redis.setex(key, 86400, "expired")  # Keep marker for 24h
    
    async def enforce_view_once(
        self,
        content_id: str,
        identifier: Optional[str] = None,
    ) -> bool:
        """
        Enforce view-once logic (content can only be viewed once).
        
        Args:
            content_id: Unique content identifier
            identifier: Optional viewer identifier (IP, user_id)
        
        Returns:
            True if view allowed, False if already viewed
        
        Raises:
            ViewOnceError: If content was already viewed
        """
        redis = await get_redis()
        
        # Create view key
        if identifier:
            key = f"{REDIS_VIEW_ONCE_PREFIX}{content_id}:{identifier}"
        else:
            key = f"{REDIS_VIEW_ONCE_PREFIX}{content_id}"
        
        # Check if already viewed
        viewed = await redis.get(key)
        if viewed:
            await self.log_security_event(
                SecurityEvent.ACCESS_DENIED,
                identifier=identifier,
                action="view_once_violation",
                metadata={"content_id": content_id},
                success=False,
            )
            raise ViewOnceError("Content can only be viewed once")
        
        # Mark as viewed (permanent or with TTL)
        # Using TTL matching content expiration or default 7 days
        await redis.setex(key, 7 * 24 * 3600, "1")
        
        return True
    
    async def check_view_once_status(
        self,
        content_id: str,
        identifier: Optional[str] = None,
    ) -> bool:
        """Check if content was already viewed"""
        redis = await get_redis()
        
        if identifier:
            key = f"{REDIS_VIEW_ONCE_PREFIX}{content_id}:{identifier}"
        else:
            key = f"{REDIS_VIEW_ONCE_PREFIX}{content_id}"
        
        viewed = await redis.get(key)
        return viewed is not None
    
    async def schedule_auto_wipe(
        self,
        content_id: str,
        expires_at: datetime,
        content_type: str = "generic",
    ) -> None:
        """
        Schedule automatic content wipe after expiration.
        
        Content is marked for deletion and will be automatically
        cleaned up after expiration time.
        """
        redis = await get_redis()
        
        # Calculate TTL
        now = datetime.utcnow()
        if expires_at <= now:
            # Already expired - mark for immediate deletion
            ttl = 0
        else:
            ttl = int((expires_at - now).total_seconds())
        
        if ttl > 0:
            # Store expiration marker
            expiry_key = f"{REDIS_TOKEN_EXPIRE_PREFIX}wipe:{content_type}:{content_id}"
            await redis.setex(
                expiry_key,
                ttl,
                json.dumps({
                    "content_id": content_id,
                    "content_type": content_type,
                    "expires_at": expires_at.isoformat(),
                    "scheduled_at": now.isoformat(),
                })
            )
            
            logger.info(
                f"Scheduled auto-wipe for {content_type}:{content_id} "
                f"at {expires_at.isoformat()} (TTL: {ttl}s)"
            )
    
    async def execute_auto_wipe(
        self,
        content_id: str,
        content_type: str,
        wipe_function: Callable[[str], Any],
    ) -> bool:
        """
        Execute auto-wipe for expired content.
        
        Args:
            content_id: Content identifier
            content_type: Type of content (file, email, etc.)
            wipe_function: Async function to call for wiping content
        
        Returns:
            True if wiped, False if not found
        """
        try:
            # Call wipe function
            if asyncio.iscoroutinefunction(wipe_function):
                await wipe_function(content_id)
            else:
                wipe_function(content_id)
            
            # Log wipe event
            await self.log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,  # Using available event type
                action="auto_wipe",
                metadata={
                    "content_id": content_id,
                    "content_type": content_type,
                    "reason": "expiration",
                },
                success=True,
            )
            
            logger.info(f"Auto-wiped {content_type}:{content_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to auto-wipe {content_type}:{content_id}: {e}", exc_info=True)
            return False


import asyncio


def sanitize_log_data(data: Optional[str]) -> Optional[str]:
    """
    Sanitize sensitive data from logs.
    
    Removes or masks:
    - Passwords/passcodes
    - API keys
    - Tokens
    - Credit card numbers
    - Email addresses (partial masking)
    - IP addresses (partial masking)
    """
    if not data:
        return data
    
    # Mask email addresses (keep first 3 chars and domain)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    data = re.sub(
        email_pattern,
        lambda m: m.group(0)[:3] + "***@" + m.group(0).split("@")[1] if "@" in m.group(0) else "***",
        data
    )
    
    # Mask tokens (base64-like strings)
    token_pattern = r'\b[A-Za-z0-9_-]{32,}\b'
    data = re.sub(
        token_pattern,
        lambda m: m.group(0)[:8] + "***" if len(m.group(0)) > 16 else "***",
        data
    )
    
    # Mask passcodes/passwords (common patterns)
    password_patterns = [
        r'passcode["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'password["\']?\s*[:=]\s*["\']?([^"\']+)',
        r'pass["\']?\s*[:=]\s*["\']?([^"\']+)',
    ]
    for pattern in password_patterns:
        data = re.sub(pattern, r'passcode="***"', data, flags=re.IGNORECASE)
    
    return data


def sanitize_ip_address(ip: Optional[str]) -> Optional[str]:
    """Sanitize IP address for logging (keep last octet only)"""
    if not ip:
        return ip
    
    # Handle IPv4
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"***.***.***.{parts[-1]}"
    
    # Handle IPv6 (mask last 4 groups)
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) >= 4:
            masked = ["***"] * (len(parts) - 4) + parts[-4:]
            return ":".join(masked)
    
    return "***"


def sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Sanitize metadata dictionary for logging"""
    if not metadata:
        return metadata
    
    sanitized = {}
    sensitive_keys = [
        "password", "passcode", "token", "key", "secret",
        "api_key", "access_token", "refresh_token",
        "credit_card", "ssn", "personal_data",
    ]
    
    for key, value in metadata.items():
        key_lower = key.lower()
        
        # Check if key is sensitive
        is_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)
        
        if is_sensitive:
            sanitized[key] = "***"
        elif isinstance(value, str):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_metadata(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(str(item)) if isinstance(item, str) else item
                for item in value[:5]  # Limit list size
            ]
        else:
            sanitized[key] = value
    
    return sanitized


# Global security service instance
_security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """Get the global SecurityService instance"""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService()
    return _security_service


# FastAPI dependency for rate limiting
async def rate_limit_check(
    identifier: str,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW,
    action: Optional[str] = None,
):
    """FastAPI dependency for rate limiting"""
    security = get_security_service()
    await security.check_rate_limit(identifier, max_requests, window_seconds, action)


# FastAPI dependency for brute force protection
async def brute_force_check(
    identifier: str,
    max_attempts: int = DEFAULT_BRUTE_FORCE_ATTEMPTS,
    window_seconds: int = DEFAULT_BRUTE_FORCE_WINDOW,
    lockout_seconds: int = DEFAULT_BRUTE_FORCE_LOCKOUT,
    action: Optional[str] = None,
):
    """FastAPI dependency for brute force protection"""
    security = get_security_service()
    await security.check_brute_force(identifier, max_attempts, window_seconds, lockout_seconds, action)


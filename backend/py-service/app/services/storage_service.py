"""Storage quota service - 5GB free tier, admin-configurable"""

from typing import Optional
from app.core.redis_client import get_redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Redis key prefixes
REDIS_STORAGE_USED_PREFIX = "storage:used:"
REDIS_STORAGE_QUOTA_PREFIX = "storage:quota:"
REDIS_STORAGE_USERS_PREFIX = "storage:users:"

def _default_quota() -> int:
    return getattr(settings, "DEFAULT_STORAGE_QUOTA_BYTES", 5 * 1024 * 1024 * 1024)


async def get_user_storage_used(user_email: str) -> int:
    """Get bytes used by user"""
    redis = await get_redis()
    key = f"{REDIS_STORAGE_USED_PREFIX}{user_email.lower()}"
    val = await redis.get(key)
    return int(val) if val else 0


async def get_user_storage_quota(user_email: str) -> int:
    """Get storage quota for user (bytes). Default 5GB."""
    redis = await get_redis()
    key = f"{REDIS_STORAGE_QUOTA_PREFIX}{user_email.lower()}"
    val = await redis.get(key)
    return int(val) if val else _default_quota()


async def set_user_storage_quota(user_email: str, quota_bytes: int) -> None:
    """Set storage quota for user (admin only)"""
    redis = await get_redis()
    key = f"{REDIS_STORAGE_QUOTA_PREFIX}{user_email.lower()}"
    await redis.set(key, str(quota_bytes))
    logger.info(f"Storage quota set for {user_email}: {quota_bytes} bytes")


async def check_storage_available(user_email: str, additional_bytes: int) -> bool:
    """Check if user has enough storage for additional_bytes"""
    used = await get_user_storage_used(user_email)
    quota = await get_user_storage_quota(user_email)
    return (used + additional_bytes) <= quota


async def add_storage_used(user_email: str, bytes_added: int) -> None:
    """Add to user's storage usage"""
    redis = await get_redis()
    key = f"{REDIS_STORAGE_USED_PREFIX}{user_email.lower()}"
    await redis.incrby(key, bytes_added)
    # Track user for admin listing
    users_key = f"{REDIS_STORAGE_USERS_PREFIX}all"
    await redis.sadd(users_key, user_email.lower())


async def subtract_storage_used(user_email: str, bytes_removed: int) -> None:
    """Subtract from user's storage usage"""
    redis = await get_redis()
    key = f"{REDIS_STORAGE_USED_PREFIX}{user_email.lower()}"
    current = await redis.get(key)
    if current:
        new_val = max(0, int(current) - bytes_removed)
        await redis.set(key, str(new_val))


async def get_all_users_storage() -> list:
    """Get storage usage for all users (admin)"""
    redis = await get_redis()
    users_raw = await redis.smembers(f"{REDIS_STORAGE_USERS_PREFIX}all")
    users = set(u.decode() if isinstance(u, bytes) else u for u in (users_raw or set()))
    # Also scan metadata for any owners not in set (backward compat)
    async for key in redis.scan_iter(match=f"{REDIS_STORAGE_USED_PREFIX}*"):
        k = key.decode() if isinstance(key, bytes) else key
        email = k.replace(REDIS_STORAGE_USED_PREFIX, "")
        if email:
            users.add(email)
    result = []
    for email_str in users:
        used = await get_user_storage_used(email_str)
        quota = await get_user_storage_quota(email_str)
        result.append({
            "email": email_str,
            "used_bytes": used,
            "quota_bytes": quota,
            "used_mb": round(used / (1024 * 1024), 2),
            "quota_gb": round(quota / (1024 * 1024 * 1024), 2),
        })
    return sorted(result, key=lambda x: x["used_bytes"], reverse=True)


async def get_total_storage_used() -> int:
    """Get total storage used across all users"""
    users = await get_all_users_storage()
    return sum(u["used_bytes"] for u in users)

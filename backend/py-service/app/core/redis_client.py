"""Redis Client Configuration"""

from typing import Optional
import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[Redis] = None


async def init_redis() -> Redis:
    """Initialize Redis connection"""
    global redis_client
    
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection initialized")
    
    return redis_client


async def get_redis() -> Redis:
    """Get Redis client"""
    if redis_client is None:
        return await init_redis()
    return redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


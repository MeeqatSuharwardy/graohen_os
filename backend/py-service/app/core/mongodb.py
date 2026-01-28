"""MongoDB Database Connection

Async MongoDB client using Motor for storing encrypted emails and files.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Global MongoDB client and database
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_db: Optional[AsyncIOMotorDatabase] = None


async def init_mongodb() -> None:
    """Initialize MongoDB connection"""
    global mongodb_client, mongodb_db
    
    if mongodb_client is None:
        try:
            # MongoDB connection string from settings
            connection_string = settings.MONGODB_CONNECTION_STRING
            
            # Create async MongoDB client
            mongodb_client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
            )
            
            # Get database
            mongodb_db = mongodb_client[settings.MONGODB_DATABASE]
            
            # Test connection
            await mongodb_client.admin.command('ping')
            
            logger.info(f"MongoDB connected to database: {settings.MONGODB_DATABASE}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise


async def close_mongodb() -> None:
    """Close MongoDB connection"""
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        logger.info("MongoDB connection closed")


def get_mongodb() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance"""
    if mongodb_db is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongodb() first.")
    return mongodb_db

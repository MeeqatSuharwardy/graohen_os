#!/usr/bin/env python3
"""Setup MongoDB Users Collection

Creates indexes on the users collection for optimal query performance.
Run this script after deploying the updated code.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.mongodb import init_mongodb, get_mongodb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_users_collection():
    """Create indexes on users collection"""
    try:
        logger.info("📋 Setting up MongoDB users collection...")
        
        # Initialize MongoDB connection
        await init_mongodb()
        db = get_mongodb()
        users_collection = db["users"]
        
        # Clean up any documents with null email_hash (old/invalid data)
        logger.info("Cleaning up invalid documents...")
        delete_result = await users_collection.delete_many({"email_hash": None})
        if delete_result.deleted_count > 0:
            logger.info(f"   Deleted {delete_result.deleted_count} invalid document(s)")
        
        # Create indexes
        logger.info("Creating indexes on 'users' collection...")
        
        # Index on email_hash for fast lookups (sparse to allow nulls, but unique for non-nulls)
        # First, drop existing index if it exists
        try:
            await users_collection.drop_index("email_hash_unique")
            logger.info("   Dropped existing email_hash_unique index")
        except Exception:
            pass  # Index doesn't exist, that's fine
        
        # Create sparse unique index (only indexes non-null values)
        await users_collection.create_index(
            "email_hash",
            unique=True,
            sparse=True,
            name="email_hash_unique"
        )
        logger.info("✅ Created index: email_hash (unique, sparse)")
        
        # Index on created_at for sorting
        await users_collection.create_index("created_at", name="created_at_idx")
        logger.info("✅ Created index: created_at")
        
        # Index on is_active for filtering
        await users_collection.create_index("is_active", name="is_active_idx")
        logger.info("✅ Created index: is_active")
        
        # Compound index for common queries
        await users_collection.create_index(
            [("is_active", 1), ("created_at", -1)],
            name="active_created_idx"
        )
        logger.info("✅ Created compound index: is_active + created_at")
        
        # List existing indexes
        indexes = await users_collection.list_indexes().to_list(length=10)
        logger.info("\n📊 Existing indexes on 'users' collection:")
        for idx in indexes:
            logger.info(f"   - {idx.get('name', 'unnamed')}: {idx.get('key', {})}")
        
        logger.info("\n✅ Users collection setup complete!")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup users collection: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_users_collection())

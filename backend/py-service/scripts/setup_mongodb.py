#!/usr/bin/env python3
"""Setup MongoDB Collections and Indexes

Ensures MongoDB is ready to store emails and files.
Creates collections and indexes if they don't exist.
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


async def setup_mongodb():
    """Setup MongoDB collections and indexes"""
    try:
        # Initialize MongoDB connection
        await init_mongodb()
        db = get_mongodb()
        
        logger.info(f"✅ Connected to MongoDB database: {db.name}")
        
        # Get collections
        emails_collection = db.emails
        files_collection = db.files
        
        # Create indexes for emails collection
        logger.info("📧 Setting up emails collection indexes...")
        
        # Index on email_id for fast lookups
        await emails_collection.create_index("email_id", unique=True)
        logger.info("   ✅ Index created: email_id (unique)")
        
        # Index on access_token for public access
        await emails_collection.create_index("access_token", unique=True)
        logger.info("   ✅ Index created: access_token (unique)")
        
        # Index on sender_email for sent emails query
        await emails_collection.create_index("sender_email")
        logger.info("   ✅ Index created: sender_email")
        
        # Index on recipient_emails for inbox query
        await emails_collection.create_index("recipient_emails")
        logger.info("   ✅ Index created: recipient_emails")
        
        # Index on created_at for sorting
        await emails_collection.create_index("created_at")
        logger.info("   ✅ Index created: created_at")
        
        # Index on expires_at for expiration queries
        await emails_collection.create_index("expires_at")
        logger.info("   ✅ Index created: expires_at")
        
        # Compound index for inbox queries (recipient + is_draft + expires_at)
        await emails_collection.create_index([
            ("recipient_emails", 1),
            ("is_draft", 1),
            ("expires_at", 1)
        ])
        logger.info("   ✅ Index created: compound (recipient_emails, is_draft, expires_at)")
        
        # Compound index for sent queries (sender + is_draft)
        await emails_collection.create_index([
            ("sender_email", 1),
            ("is_draft", 1),
            ("created_at", -1)
        ])
        logger.info("   ✅ Index created: compound (sender_email, is_draft, created_at)")
        
        # Create indexes for files collection
        logger.info("📁 Setting up files collection indexes...")
        
        # Index on file_id for fast lookups
        await files_collection.create_index("file_id", unique=True)
        logger.info("   ✅ Index created: file_id (unique)")
        
        # Index on owner_email for user file queries
        await files_collection.create_index("owner_email")
        logger.info("   ✅ Index created: owner_email")
        
        # Index on created_at for sorting
        await files_collection.create_index("created_at")
        logger.info("   ✅ Index created: created_at")
        
        # Index on expires_at for expiration queries
        await files_collection.create_index("expires_at")
        logger.info("   ✅ Index created: expires_at")
        
        # Compound index for file listing (owner + expires_at)
        await files_collection.create_index([
            ("owner_email", 1),
            ("expires_at", 1),
            ("created_at", -1)
        ])
        logger.info("   ✅ Index created: compound (owner_email, expires_at, created_at)")
        
        # Count existing documents
        emails_count = await emails_collection.count_documents({})
        files_count = await files_collection.count_documents({})
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ MongoDB Setup Complete!")
        logger.info("=" * 60)
        logger.info(f"   Database: {db.name}")
        logger.info(f"   Emails collection: {emails_count} documents")
        logger.info(f"   Files collection: {files_count} documents")
        logger.info("")
        logger.info("📋 Indexes Created:")
        logger.info("   Emails: email_id, access_token, sender_email, recipient_emails, created_at, expires_at")
        logger.info("   Files: file_id, owner_email, created_at, expires_at")
        logger.info("")
        logger.info("✅ MongoDB is ready to store data!")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup MongoDB: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_mongodb())

#!/usr/bin/env python3
"""Create User Table Migration Script

Creates the users table in PostgreSQL with encrypted fields.
Run this script after deploying the updated code.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import init_db, engine, Base
from app.models.user import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all database tables"""
    try:
        # Initialize database connection
        await init_db()
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ User table created successfully!")
        logger.info("   Table: users")
        logger.info("   Fields: id, encrypted_email, email_hash, hashed_password, encrypted_full_name, etc.")
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())

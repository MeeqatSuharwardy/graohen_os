#!/usr/bin/env python3
"""Check MongoDB Collections

Verifies if MongoDB collections (emails and files) exist and shows their status.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Credentials
MONGODB_USER = "doadmin"
MONGODB_PASS = "R6j8Oe2r1h749U5C"
MONGODB_HOST = "db-mongodb-nyc3-19012-1834d74a.mongo.ondigitalocean.com"
MONGODB_DB = "admin"

MONGODB_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_HOST}/{MONGODB_DB}?tls=true&authSource=admin"


async def check_mongodb():
    """Check MongoDB collections"""
    try:
        print("=" * 70)
        print("  MongoDB Collection Check")
        print("=" * 70)
        print()
        print(f"Connecting to: {MONGODB_HOST}")
        print(f"Database: {MONGODB_DB}")
        print()
        
        # Connect to MongoDB
        client = AsyncIOMotorClient(
            MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        print()
        
        # Get database
        db = client[MONGODB_DB]
        
        # List all collections (excluding system collections)
        all_collections = await db.list_collection_names()
        user_collections = [c for c in all_collections if not c.startswith('system.')]
        
        print(f"📋 Collections in database '{MONGODB_DB}':")
        if user_collections:
            for coll in sorted(user_collections):
                try:
                    count = await db[coll].count_documents({})
                    print(f"   - {coll}: {count} documents")
                except Exception as e:
                    print(f"   - {coll}: (error counting: {str(e)[:50]})")
        else:
            print("   (No user collections found)")
        print()
        
        # Check emails collection
        print("📧 Checking 'emails' collection:")
        if 'emails' in user_collections:
            emails_count = await db.emails.count_documents({})
            print(f"   ✅ Collection exists")
            print(f"   📊 Documents: {emails_count}")
            
            # Check indexes
            indexes = await db.emails.list_indexes().to_list(length=None)
            print(f"   📑 Indexes: {len(indexes)}")
            for idx in indexes:
                idx_name = idx.get('name', 'unknown')
                idx_keys = idx.get('key', {})
                print(f"      - {idx_name}: {list(idx_keys.keys())}")
        else:
            print("   ⚠️  Collection does not exist (will be created automatically on first insert)")
        print()
        
        # Check files collection
        print("📁 Checking 'files' collection:")
        if 'files' in user_collections:
            files_count = await db.files.count_documents({})
            print(f"   ✅ Collection exists")
            print(f"   📊 Documents: {files_count}")
            
            # Check indexes
            indexes = await db.files.list_indexes().to_list(length=None)
            print(f"   📑 Indexes: {len(indexes)}")
            for idx in indexes:
                idx_name = idx.get('name', 'unknown')
                idx_keys = idx.get('key', {})
                print(f"      - {idx_name}: {list(idx_keys.keys())}")
        else:
            print("   ⚠️  Collection does not exist (will be created automatically on first insert)")
        print()
        
        # Summary
        print("=" * 70)
        print("  Summary")
        print("=" * 70)
        
        emails_exists = 'emails' in user_collections
        files_exists = 'files' in user_collections
        
        if emails_exists and files_exists:
            print("✅ Both collections exist and are ready to store data!")
        elif emails_exists or files_exists:
            print("⚠️  One collection exists, one will be created on first use")
        else:
            print("ℹ️  Collections will be created automatically when data is inserted")
            print("   (This is normal - MongoDB creates collections on first insert)")
        
        print()
        print("💡 Note: Collections are created automatically when you:")
        print("   - Send an email (creates 'emails' collection)")
        print("   - Upload a file (creates 'files' collection)")
        print()
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_mongodb())

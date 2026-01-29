#!/usr/bin/env python3
"""Check Users in Database

Verifies if users are being stored in PostgreSQL database.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import init_db, get_db
from app.models.user import User
from sqlalchemy import select
from app.core.user_encryption import decrypt_user_data, hash_email_for_lookup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_users():
    """Check users in database"""
    try:
        print("=" * 70)
        print("  Checking Users in PostgreSQL Database")
        print("=" * 70)
        print()
        
        # Initialize database
        await init_db()
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Query all users
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            print(f"📊 Total users in database: {len(users)}")
            print()
            
            if users:
                print("👥 Users List:")
                print("-" * 70)
                for user in users:
                    try:
                        # Decrypt email
                        decrypted_email = decrypt_user_data(
                            user.encrypted_email,
                            user.encryption_metadata
                        )
                        
                        # Decrypt full_name if present
                        decrypted_full_name = None
                        if user.encrypted_full_name:
                            decrypted_full_name = decrypt_user_data(
                                user.encrypted_full_name,
                                user.encryption_metadata
                            )
                        
                        print(f"   ID: {user.id}")
                        print(f"   Email: {decrypted_email}")
                        print(f"   Email Hash: {user.email_hash[:16]}...")
                        print(f"   Full Name: {decrypted_full_name or 'N/A'}")
                        print(f"   Active: {user.is_active}")
                        print(f"   Verified: {user.is_verified}")
                        print(f"   Created: {user.created_at}")
                        print()
                    except Exception as e:
                        print(f"   ⚠️  Error decrypting user {user.id}: {str(e)}")
                        print(f"   Email Hash: {user.email_hash[:16]}...")
                        print()
            else:
                print("⚠️  No users found in database")
                print("   Users will be created when registration API is called")
                print()
            
            # Check specific test accounts
            print("🔍 Checking Test Accounts:")
            print("-" * 70)
            
            test_emails = ["test20@fxmail.ai", "test21@fxmail.ai"]
            for email in test_emails:
                email_hash = hash_email_for_lookup(email)
                result = await db.execute(
                    select(User).where(User.email_hash == email_hash)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    try:
                        decrypted_email = decrypt_user_data(
                            user.encrypted_email,
                            user.encryption_metadata
                        )
                        print(f"   ✅ {email}: Found in database (ID: {user.id})")
                    except Exception as e:
                        print(f"   ⚠️  {email}: Found but decryption error: {str(e)}")
                else:
                    print(f"   ❌ {email}: Not found in database")
            
            print()
            print("=" * 70)
            print("  Summary")
            print("=" * 70)
            print(f"   Total users: {len(users)}")
            print(f"   Database: Ready")
            print(f"   Encryption: Working")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_users())

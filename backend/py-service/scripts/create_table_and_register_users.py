#!/usr/bin/env python3
"""Create Users Table and Register Test Accounts

This script:
1. Creates the users table in PostgreSQL
2. Registers test accounts via API
3. Verifies registration success
"""

import asyncio
import sys
import requests
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import init_db, engine, Base
from app.models.user import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://freedomos.vulcantech.co/api/v1"

# Test accounts to register
TEST_ACCOUNTS = [
    {"email": "test20@fxmail.ai", "password": "test20@#", "full_name": "Test User 20"},
    {"email": "test21@fxmail.ai", "password": "test20@#", "full_name": "Test User 21"},
]


async def create_tables():
    """Create all database tables"""
    try:
        logger.info("📋 Step 1: Creating users table...")
        await init_db()
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Users table created successfully!")
        logger.info("   Table: users")
        logger.info("   Fields: id, encrypted_email, email_hash, hashed_password, etc.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


def register_users():
    """Register test accounts via API"""
    logger.info("\n📋 Step 2: Registering test accounts...")
    logger.info("-" * 70)
    
    results = []
    
    for i, account in enumerate(TEST_ACCOUNTS, 1):
        logger.info(f"\n📝 Account {i}: {account['email']}")
        
        try:
            # Try registration
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json=account,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"   ✅ Registration successful!")
                logger.info(f"   Access Token: {data.get('access_token', 'N/A')[:50]}...")
                results.append({"email": account["email"], "status": "registered", "success": True})
                
            elif response.status_code == 400:
                error_msg = response.json().get("detail", response.text)
                logger.info(f"   ⚠️  Registration failed: {error_msg}")
                
                # If user already exists, try login
                if "already" in error_msg.lower():
                    logger.info(f"   ℹ️  User may already exist, testing login...")
                    login_response = requests.post(
                        f"{BASE_URL}/auth/login",
                        json={"email": account["email"], "password": account["password"]},
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    
                    if login_response.status_code == 200:
                        login_data = login_response.json()
                        logger.info(f"   ✅ Login successful! User exists in database.")
                        logger.info(f"   Access Token: {login_data.get('access_token', 'N/A')[:50]}...")
                        results.append({"email": account["email"], "status": "exists", "success": True})
                    else:
                        logger.error(f"   ❌ Login failed: {login_response.text[:200]}")
                        results.append({"email": account["email"], "status": "login_failed", "success": False})
                else:
                    results.append({"email": account["email"], "status": "registration_failed", "success": False})
                    
            else:
                logger.error(f"   ❌ Registration failed ({response.status_code}): {response.text[:200]}")
                results.append({"email": account["email"], "status": "error", "success": False})
                
        except Exception as e:
            logger.error(f"   ❌ Exception: {str(e)}")
            results.append({"email": account["email"], "status": "exception", "success": False})
    
    return results


def main():
    """Main execution"""
    print("=" * 70)
    print("  Create Users Table and Register Test Accounts")
    print("=" * 70)
    print()
    
    # Step 1: Create tables
    success = asyncio.run(create_tables())
    
    if not success:
        print("\n❌ Failed to create tables. Cannot proceed with registration.")
        sys.exit(1)
    
    # Step 2: Register users
    results = register_users()
    
    # Summary
    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"   Total accounts: {total}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {total - successful}")
    print()
    
    for result in results:
        status_icon = "✅" if result["success"] else "❌"
        print(f"   {status_icon} {result['email']}: {result['status']}")
    
    print()
    
    if successful == total:
        print("✅ All accounts registered/verified successfully!")
        sys.exit(0)
    else:
        print("⚠️  Some accounts failed. Check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()

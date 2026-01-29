#!/usr/bin/env python3
"""Test Inbox API with Pydantic Validation Check"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.email_service_mongodb import get_email_service_mongodb
from app.core.mongodb import init_mongodb
from app.core.user_encryption import hash_email_for_lookup
from app.services.user_service_mongodb import get_user_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_inbox_directly():
    """Test inbox emails function directly"""
    print("="*70)
    print("  Testing Inbox Emails Function Directly")
    print("="*70)
    print()
    
    try:
        # Initialize MongoDB
        await init_mongodb()
        
        # Get user service to get user email
        user_service = get_user_service()
        user = await user_service.get_user_by_email("test20@fxmail.ai")
        
        if not user:
            print("❌ User not found")
            return
        
        user_email = user["email"]
        print(f"✅ User found: {user_email}")
        
        # Get email service
        email_service = get_email_service_mongodb()
        
        # Test get_inbox_emails
        print(f"\n📥 Testing get_inbox_emails for {user_email}")
        print("-"*70)
        
        emails = await email_service.get_inbox_emails(
            user_email=user_email,
            limit=10,
            offset=0
        )
        
        print(f"✅ Function returned {len(emails)} emails")
        
        if emails:
            print("\nFirst email data:")
            print("-"*70)
            first_email = emails[0]
            print(f"Keys: {list(first_email.keys())}")
            print(f"Email ID: {first_email.get('email_id', 'MISSING')}")
            print(f"Access Token: {first_email.get('access_token', 'MISSING')}")
            print(f"Sender: {first_email.get('sender_email', 'MISSING')}")
            print(f"Recipients: {first_email.get('recipient_emails', 'MISSING')}")
            print(f"Subject: {first_email.get('subject', 'MISSING')}")
            print(f"Created: {first_email.get('created_at', 'MISSING')}")
            print(f"Status: {first_email.get('status', 'MISSING')}")
            
            # Test EmailListItem validation
            print("\n🧪 Testing EmailListItem validation...")
            print("-"*70)
            try:
                from app.api.v1.endpoints.email import EmailListItem
                item = EmailListItem(**first_email)
                print("✅ EmailListItem validation passed!")
                print(f"   Validated item: {item.email_id[:30]}...")
            except Exception as e:
                print(f"❌ EmailListItem validation failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("ℹ️  No emails in inbox")
        
        print("\n" + "="*70)
        print("  Test Complete")
        print("="*70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_inbox_directly())

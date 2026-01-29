#!/usr/bin/env python3
"""Test Email APIs Locally"""

import asyncio
import sys
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000/api/v1"

# Test account
TEST_EMAIL = "test20@fxmail.ai"
TEST_PASSWORD = "test20@#"

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

def test_local_apis():
    """Test email APIs locally"""
    print("="*70)
    print("  Testing Email APIs Locally")
    print("="*70)
    print()
    
    # Step 1: Register/Login
    print("📝 Step 1: Register/Login")
    print("-"*70)
    
    try:
        # Try login first
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            print_success(f"Login successful")
            print_info(f"Token: {access_token[:50]}...")
        else:
            # Try register
            print_info("Login failed, trying registration...")
            response = requests.post(
                f"{BASE_URL}/auth/register",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "full_name": "Test User"
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                access_token = data.get("access_token")
                print_success(f"Registration successful")
                print_info(f"Token: {access_token[:50]}...")
            else:
                print_error(f"Registration failed: {response.status_code}")
                print_error(f"Response: {response.text[:200]}")
                return None
    except Exception as e:
        print_error(f"Auth failed: {str(e)}")
        return None
    
    if not access_token:
        print_error("No access token obtained")
        return None
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Step 2: Test Inbox
    print("\n📥 Step 2: Testing GET /email/inbox")
    print("-"*70)
    try:
        response = requests.get(f"{BASE_URL}/email/inbox", headers=headers, timeout=10)
        print_info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            print_success(f"Inbox API: {count} emails found")
        else:
            print_error(f"Inbox API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Inbox API exception: {str(e)}")
    
    # Step 3: Test Sent
    print("\n📤 Step 3: Testing GET /email/sent")
    print("-"*70)
    try:
        response = requests.get(f"{BASE_URL}/email/sent", headers=headers, timeout=10)
        print_info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            print_success(f"Sent API: {count} emails found")
        else:
            print_error(f"Sent API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Sent API exception: {str(e)}")
    
    # Step 4: Test Drafts
    print("\n📝 Step 4: Testing GET /email/drafts")
    print("-"*70)
    try:
        response = requests.get(f"{BASE_URL}/email/drafts", headers=headers, timeout=10)
        print_info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            print_success(f"Drafts API: {count} drafts found")
        else:
            print_error(f"Drafts API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Drafts API exception: {str(e)}")
    
    # Step 5: Test Send Email
    print("\n✉️  Step 5: Testing POST /email/send")
    print("-"*70)
    try:
        send_data = {
            "to": [TEST_EMAIL],
            "subject": "Test Email",
            "body": "This is a test email."
        }
        response = requests.post(
            f"{BASE_URL}/email/send",
            json=send_data,
            headers={**headers, "Content-Type": "application/json"},
            timeout=15
        )
        print_info(f"Status: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            print_success(f"Send Email API: Email sent successfully")
            print_info(f"Email ID: {data.get('email_id', 'N/A')[:30]}...")
        else:
            print_error(f"Send Email API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Send Email API exception: {str(e)}")
    
    # Step 6: Test Save Draft
    print("\n💾 Step 6: Testing POST /email/drafts")
    print("-"*70)
    try:
        draft_data = {
            "to": [TEST_EMAIL],
            "subject": "Test Draft",
            "body": "This is a test draft."
        }
        response = requests.post(
            f"{BASE_URL}/email/drafts",
            json=draft_data,
            headers={**headers, "Content-Type": "application/json"},
            timeout=15
        )
        print_info(f"Status: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            print_success(f"Save Draft API: Draft saved successfully")
            print_info(f"Draft ID: {data.get('email_id', 'N/A')[:30]}...")
        else:
            print_error(f"Save Draft API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Save Draft API exception: {str(e)}")
    
    print("\n" + "="*70)
    print("  Testing Complete")
    print("="*70)

if __name__ == "__main__":
    test_local_apis()

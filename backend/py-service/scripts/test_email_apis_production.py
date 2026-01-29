#!/usr/bin/env python3
"""Test Email APIs on Production Server"""

import requests
import json
import sys

BASE_URL = "https://freedomos.vulcantech.co/api/v1"

# Test accounts
ACCOUNTS = [
    {"email": "test20@fxmail.ai", "password": "test20@#"},
    {"email": "test21@fxmail.ai", "password": "test20@#"},
]

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")

def login_user(email: str, password: str) -> str:
    """Login and return access token"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print_error(f"Login failed ({response.status_code}): {response.text[:200]}")
            return None
    except Exception as e:
        print_error(f"Login exception: {str(e)}")
        return None

def test_email_apis(access_token: str, user_email: str, other_email: str):
    """Test all email APIs"""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("\n" + "="*70)
    print(f"  Testing Email APIs for {user_email}")
    print("="*70)
    
    # Test 1: Get Inbox
    print("\n📥 Test 1: GET /email/inbox")
    print("-"*70)
    try:
        response = requests.get(f"{BASE_URL}/email/inbox", headers=headers, timeout=15)
        print_info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            total = data.get("total", 0)
            print_success(f"Inbox API: {count} emails (total: {total})")
            if count > 0:
                print_info(f"   First email: {data['emails'][0].get('subject', 'No subject')[:50]}")
        else:
            print_error(f"Inbox API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Inbox API exception: {str(e)}")
    
    # Test 2: Get Sent
    print("\n📤 Test 2: GET /email/sent")
    print("-"*70)
    try:
        response = requests.get(f"{BASE_URL}/email/sent", headers=headers, timeout=15)
        print_info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            total = data.get("total", 0)
            print_success(f"Sent API: {count} emails (total: {total})")
            if count > 0:
                print_info(f"   First email: {data['emails'][0].get('subject', 'No subject')[:50]}")
        else:
            print_error(f"Sent API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Sent API exception: {str(e)}")
    
    # Test 3: Get Drafts
    print("\n📝 Test 3: GET /email/drafts")
    print("-"*70)
    try:
        response = requests.get(f"{BASE_URL}/email/drafts", headers=headers, timeout=15)
        print_info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            total = data.get("total", 0)
            print_success(f"Drafts API: {count} drafts (total: {total})")
            if count > 0:
                print_info(f"   First draft: {data['emails'][0].get('subject', 'No subject')[:50]}")
        else:
            print_error(f"Drafts API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Drafts API exception: {str(e)}")
    
    # Test 4: Send Email
    print("\n✉️  Test 4: POST /email/send")
    print("-"*70)
    try:
        send_data = {
            "to": [other_email],
            "subject": f"Test Email from {user_email}",
            "body": f"This is a test email sent from {user_email} to {other_email}."
        }
        response = requests.post(
            f"{BASE_URL}/email/send",
            json=send_data,
            headers={**headers, "Content-Type": "application/json"},
            timeout=20
        )
        print_info(f"Status: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            print_success(f"Send Email API: Email sent successfully")
            print_info(f"   Email ID: {data.get('email_id', 'N/A')[:30]}...")
            print_info(f"   Email Address: {data.get('email_address', 'N/A')}")
        else:
            print_error(f"Send Email API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Send Email API exception: {str(e)}")
    
    # Test 5: Save Draft
    print("\n💾 Test 5: POST /email/drafts")
    print("-"*70)
    try:
        draft_data = {
            "to": [other_email],
            "subject": f"Test Draft from {user_email}",
            "body": f"This is a test draft from {user_email}."
        }
        response = requests.post(
            f"{BASE_URL}/email/drafts",
            json=draft_data,
            headers={**headers, "Content-Type": "application/json"},
            timeout=20
        )
        print_info(f"Status: {response.status_code}")
        if response.status_code in [200, 201]:
            data = response.json()
            draft_id = data.get("email_id", "N/A")
            print_success(f"Save Draft API: Draft saved successfully")
            print_info(f"   Draft ID: {draft_id[:30]}...")
            return draft_id
        else:
            print_error(f"Save Draft API failed: {response.text[:300]}")
    except Exception as e:
        print_error(f"Save Draft API exception: {str(e)}")
    
    return None

def main():
    print("="*70)
    print("  Testing Email APIs on Production Server")
    print("="*70)
    print()
    
    # Login both accounts
    tokens = {}
    for account in ACCOUNTS:
        print(f"🔐 Logging in: {account['email']}")
        token = login_user(account["email"], account["password"])
        if token:
            tokens[account["email"]] = token
            print_success(f"Login successful")
        else:
            print_error(f"Failed to login {account['email']}")
            return
    
    # Test email APIs for both accounts
    for i, account in enumerate(ACCOUNTS):
        email = account["email"]
        other_email = ACCOUNTS[1-i]["email"]
        token = tokens[email]
        
        test_email_apis(token, email, other_email)
    
    print("\n" + "="*70)
    print("  Testing Complete")
    print("="*70)
    print_success("All email API tests completed!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Comprehensive API Testing Script

Tests registration, login, email APIs, and drive APIs.
"""

import requests
import json
import sys
from typing import Dict, Optional

BASE_URL = "https://freedomos.vulcantech.co/api/v1"

# Test accounts
ACCOUNTS = [
    {"email": "test20@fxmail.ai", "password": "test20@#", "full_name": "Test User 20"},
    {"email": "test21@fxmail.ai", "password": "test20@#", "full_name": "Test User 21"},
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

def register_user(email: str, password: str, full_name: str) -> Optional[Dict]:
    """Register a user"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            return response.json()
        elif response.status_code == 400:
            error = response.json().get("detail", "")
            if "already" in error.lower():
                print_warning(f"User {email} already exists, trying login...")
                return login_user(email, password)
            else:
                print_error(f"Registration failed: {error}")
                return None
        else:
            print_error(f"Registration failed ({response.status_code}): {response.text[:200]}")
            return None
    except Exception as e:
        print_error(f"Registration exception: {str(e)}")
        return None

def login_user(email: str, password: str) -> Optional[Dict]:
    """Login a user"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print_error(f"Login failed ({response.status_code}): {response.text[:200]}")
            return None
    except Exception as e:
        print_error(f"Login exception: {str(e)}")
        return None

def test_email_apis(access_token: str, user_email: str):
    """Test email APIs"""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("\n" + "="*70)
    print("  Testing Email APIs")
    print("="*70)
    
    # Test Inbox
    print("\n📥 Testing GET /email/inbox")
    try:
        response = requests.get(f"{BASE_URL}/email/inbox", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            print_success(f"Inbox API: {count} emails found")
        else:
            print_error(f"Inbox API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Inbox API exception: {str(e)}")
    
    # Test Sent
    print("\n📤 Testing GET /email/sent")
    try:
        response = requests.get(f"{BASE_URL}/email/sent", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("emails", []))
            print_success(f"Sent API: {count} emails found")
        else:
            print_error(f"Sent API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Sent API exception: {str(e)}")
    
    # Test Drafts
    print("\n📝 Testing GET /email/drafts")
    try:
        response = requests.get(f"{BASE_URL}/email/drafts", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("drafts", []))
            print_success(f"Drafts API: {count} drafts found")
        else:
            print_error(f"Drafts API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Drafts API exception: {str(e)}")
    
    # Test Send Email
    print("\n✉️  Testing POST /email/send (Send Email)")
    try:
        send_data = {
            "to": [ACCOUNTS[1]["email"] if user_email == ACCOUNTS[0]["email"] else ACCOUNTS[0]["email"]],
            "subject": "Test Email from API",
            "body": "This is a test email sent via the send API."
        }
        response = requests.post(
            f"{BASE_URL}/email/send",
            json=send_data,
            headers=headers,
            timeout=15
        )
        if response.status_code in [200, 201]:
            data = response.json()
            print_success(f"Send Email API: Email sent successfully")
            print_info(f"Email ID: {data.get('email_id', 'N/A')}")
            print_info(f"Email Address: {data.get('email_address', 'N/A')}")
        else:
            print_error(f"Send Email API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Send Email API exception: {str(e)}")
    
    # Test Save Draft
    print("\n💾 Testing POST /email/drafts (Save Draft)")
    try:
        draft_data = {
            "to": [ACCOUNTS[1]["email"] if user_email == ACCOUNTS[0]["email"] else ACCOUNTS[0]["email"]],
            "subject": "Test Draft",
            "body": "This is a test draft."
        }
        response = requests.post(
            f"{BASE_URL}/email/drafts",
            json=draft_data,
            headers=headers,
            timeout=15
        )
        if response.status_code in [200, 201]:
            data = response.json()
            draft_id = data.get("email_id", "N/A")
            print_success(f"Save Draft API: Draft saved successfully")
            print_info(f"Draft ID: {draft_id}")
            return draft_id
        else:
            print_error(f"Save Draft API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Save Draft API exception: {str(e)}")
    
    return None

def test_drive_apis(access_token: str):
    """Test drive APIs"""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("\n" + "="*70)
    print("  Testing Drive APIs")
    print("="*70)
    
    # Test Storage Quota
    print("\n💾 Testing GET /drive/storage/quota")
    try:
        response = requests.get(f"{BASE_URL}/drive/storage/quota", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            print_success(f"Quota API: {data.get('used_gb', 0):.2f} GB / {data.get('quota_gb', 5):.2f} GB")
        else:
            print_error(f"Quota API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Quota API exception: {str(e)}")
    
    # Test List Files
    print("\n📁 Testing GET /drive/files")
    try:
        response = requests.get(f"{BASE_URL}/drive/files", headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("files", []))
            print_success(f"List Files API: {count} files found")
        else:
            print_error(f"List Files API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"List Files API exception: {str(e)}")
    
    # Test Upload File
    print("\n⬆️  Testing POST /drive/upload")
    try:
        # Create a test file
        test_content = b"This is a test file content for drive upload."
        files = {
            "file": ("test_file.txt", test_content, "text/plain")
        }
        data = {
            "filename": "test_file.txt"
        }
        response = requests.post(
            f"{BASE_URL}/drive/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30
        )
        if response.status_code in [200, 201]:
            result = response.json()
            file_id = result.get("file_id", "N/A")
            print_success(f"Upload API: File uploaded successfully")
            print_info(f"File ID: {file_id}")
            return file_id
        else:
            print_error(f"Upload API failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print_error(f"Upload API exception: {str(e)}")
    
    return None

def main():
    print("="*70)
    print("  Comprehensive API Testing")
    print("="*70)
    print()
    
    tokens = {}
    
    # Step 1: Register/Login accounts
    print("="*70)
    print("  Step 1: Register/Login Accounts")
    print("="*70)
    
    for account in ACCOUNTS:
        print(f"\n📝 Processing: {account['email']}")
        result = register_user(account["email"], account["password"], account["full_name"])
        if result and "access_token" in result:
            tokens[account["email"]] = result["access_token"]
            print_success(f"Account {account['email']} ready (Token: {result['access_token'][:30]}...)")
        else:
            print_error(f"Failed to register/login {account['email']}")
            return
    
    # Step 2: Test Email APIs for both accounts
    for account in ACCOUNTS:
        email = account["email"]
        token = tokens[email]
        print(f"\n{'='*70}")
        print(f"  Testing Email APIs for {email}")
        print("="*70)
        test_email_apis(token, email)
    
    # Step 3: Test Drive APIs
    for account in ACCOUNTS:
        email = account["email"]
        token = tokens[email]
        print(f"\n{'='*70}")
        print(f"  Testing Drive APIs for {email}")
        print("="*70)
        test_drive_apis(token)
    
    print("\n" + "="*70)
    print("  Testing Complete")
    print("="*70)
    print_success("All API tests completed!")

if __name__ == "__main__":
    main()

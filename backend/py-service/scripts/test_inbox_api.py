#!/usr/bin/env python3
"""Test Inbox API on Production Server"""

import requests
import json
import sys

BASE_URL = "https://freedomos.vulcantech.co/api/v1"

# Test account
TEST_EMAIL = "test20@fxmail.ai"
TEST_PASSWORD = "test20@#"

def print_success(msg):
    print(f"✅ {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def print_info(msg):
    print(f"ℹ️  {msg}")

def test_inbox_api():
    """Test inbox API"""
    print("="*70)
    print("  Testing GET /email/inbox API")
    print("="*70)
    print()
    
    # Step 1: Login
    print("🔐 Step 1: Logging in...")
    print("-"*70)
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            print_success(f"Login successful")
            print_info(f"Token: {access_token[:50]}...")
        else:
            print_error(f"Login failed ({response.status_code}): {response.text[:200]}")
            return
    except Exception as e:
        print_error(f"Login exception: {str(e)}")
        return
    
    # Step 2: Test Inbox API
    print("\n📥 Step 2: Testing GET /email/inbox")
    print("-"*70)
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(
            f"{BASE_URL}/email/inbox",
            headers=headers,
            timeout=15
        )
        
        print_info(f"Status Code: {response.status_code}")
        print_info(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Inbox API: SUCCESS!")
            print()
            print("Response Data:")
            print("-"*70)
            print(f"Total emails: {data.get('total', 0)}")
            print(f"Limit: {data.get('limit', 0)}")
            print(f"Offset: {data.get('offset', 0)}")
            print(f"Emails returned: {len(data.get('emails', []))}")
            print()
            
            if data.get('emails'):
                print("First Email Details:")
                print("-"*70)
                first_email = data['emails'][0]
                print(f"  Email ID: {first_email.get('email_id', 'N/A')[:50]}...")
                print(f"  Access Token: {first_email.get('access_token', 'N/A')[:50]}...")
                print(f"  Sender: {first_email.get('sender_email', 'N/A')}")
                print(f"  Recipients: {first_email.get('recipient_emails', [])}")
                print(f"  Subject: {first_email.get('subject', 'No subject')}")
                print(f"  Created: {first_email.get('created_at', 'N/A')}")
                print(f"  Expires: {first_email.get('expires_at', 'Never')}")
                print(f"  Has Passcode: {first_email.get('has_passcode', False)}")
                print(f"  Is Draft: {first_email.get('is_draft', False)}")
                print(f"  Status: {first_email.get('status', 'N/A')}")
                print()
                
                # Check if all required fields are present
                required_fields = ['email_id', 'access_token', 'sender_email', 'recipient_emails', 
                                  'created_at', 'expires_at', 'has_passcode', 'is_draft', 'status']
                missing_fields = [field for field in required_fields if field not in first_email]
                
                if missing_fields:
                    print_warning(f"⚠️  Missing fields: {missing_fields}")
                else:
                    print_success("✅ All required fields present!")
            else:
                print_info("No emails in inbox (empty list)")
            
            print()
            print("Full Response JSON:")
            print("-"*70)
            print(json.dumps(data, indent=2))
            
        elif response.status_code == 500:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_msg = error_data.get('detail', response.text)
            print_error(f"Inbox API failed with 500 error")
            print_error(f"Error detail: {error_msg}")
            print()
            print("This indicates the fixes need to be deployed to the server.")
        else:
            print_error(f"Inbox API failed ({response.status_code})")
            print_error(f"Response: {response.text[:500]}")
            
    except requests.exceptions.Timeout:
        print_error("Request timed out (server may be slow or unresponsive)")
    except Exception as e:
        print_error(f"Inbox API exception: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()
    print("="*70)
    print("  Test Complete")
    print("="*70)

if __name__ == "__main__":
    test_inbox_api()

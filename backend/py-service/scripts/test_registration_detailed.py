#!/usr/bin/env python3
"""Test Registration with Detailed Error Reporting"""

import requests
import json
import sys

BASE_URL = "https://freedomos.vulcantech.co/api/v1"

# Test accounts
accounts = [
    {"email": "test20@fxmail.ai", "password": "test20@#", "full_name": "Test User 20"},
    {"email": "test21@fxmail.ai", "password": "test20@#", "full_name": "Test User 21"},
]

print("=" * 70)
print("  Testing User Registration with Detailed Error Reporting")
print("=" * 70)
print()

for i, account in enumerate(accounts, 1):
    print(f"📝 Testing Account {i}: {account['email']}")
    print("-" * 70)
    
    # Try registration
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=account,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"   Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"   Response Text: {response.text[:500]}")
        
        if response.status_code in [200, 201]:
            print(f"   ✅ Registration successful!")
            if "access_token" in response_data:
                print(f"   Access Token: {response_data.get('access_token', 'N/A')[:50]}...")
        elif response.status_code == 400:
            error_msg = response_data.get("detail", response.text)
            print(f"   ⚠️  Registration failed: {error_msg}")
            
            # If user already exists, try login
            if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                print(f"   ℹ️  User may already exist, testing login...")
                login_response = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": account["email"], "password": account["password"]},
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                print(f"   Login Status: {login_response.status_code}")
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    print(f"   ✅ Login successful!")
                    print(f"   Access Token: {login_data.get('access_token', 'N/A')[:50]}...")
                else:
                    try:
                        login_error = login_response.json()
                        print(f"   ❌ Login failed: {json.dumps(login_error, indent=2)}")
                    except:
                        print(f"   ❌ Login failed: {login_response.text[:200]}")
        else:
            print(f"   ❌ Registration failed with status {response.status_code}")
            print(f"   Full response: {response.text[:500]}")
        
        print()
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Network Error: {str(e)}")
        print()
    except Exception as e:
        print(f"   ❌ Unexpected Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print()

print("=" * 70)
print("  Test Complete")
print("=" * 70)

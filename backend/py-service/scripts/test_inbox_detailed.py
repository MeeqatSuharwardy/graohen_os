#!/usr/bin/env python3
"""Test Inbox API with Detailed Error Checking"""

import requests
import json

BASE_URL = "https://freedomos.vulcantech.co/api/v1"
TEST_EMAIL = "test20@fxmail.ai"
TEST_PASSWORD = "test20@#"

print("="*70)
print("  Detailed Inbox API Test")
print("="*70)
print()

# Login
print("🔐 Logging in...")
try:
    login_resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=15
    )
    if login_resp.status_code != 200:
        print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
        exit(1)
    access_token = login_resp.json().get("access_token")
    print(f"✅ Login successful")
except Exception as e:
    print(f"❌ Login error: {e}")
    exit(1)

# Test inbox with different parameters
print("\n📥 Testing GET /email/inbox")
print("-"*70)

headers = {"Authorization": f"Bearer {access_token}"}

# Test 1: Basic request
print("\n1. Basic request (no params):")
try:
    resp = requests.get(f"{BASE_URL}/email/inbox", headers=headers, timeout=15)
    print(f"   Status: {resp.status_code}")
    print(f"   Content-Type: {resp.headers.get('content-type')}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ SUCCESS!")
        print(f"   Total: {data.get('total', 0)}")
        print(f"   Emails: {len(data.get('emails', []))}")
        if data.get('emails'):
            email = data['emails'][0]
            print(f"   First email fields: {list(email.keys())}")
    else:
        print(f"   ❌ Error: {resp.text[:300]}")
        try:
            error_json = resp.json()
            print(f"   Error detail: {json.dumps(error_json, indent=2)}")
        except:
            pass
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Test 2: With limit
print("\n2. With limit=10:")
try:
    resp = requests.get(f"{BASE_URL}/email/inbox?limit=10", headers=headers, timeout=15)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ SUCCESS! Emails: {len(data.get('emails', []))}")
    else:
        print(f"   ❌ Error: {resp.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

# Test 3: With offset
print("\n3. With offset=0&limit=5:")
try:
    resp = requests.get(f"{BASE_URL}/email/inbox?offset=0&limit=5", headers=headers, timeout=15)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ SUCCESS! Emails: {len(data.get('emails', []))}")
    else:
        print(f"   ❌ Error: {resp.text[:200]}")
except Exception as e:
    print(f"   ❌ Exception: {e}")

print("\n" + "="*70)
print("  Test Complete")
print("="*70)

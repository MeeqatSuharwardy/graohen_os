#!/bin/bash
# Setup Users Table and Test Registration
# Run this on the deployed server

set -e

echo "============================================================"
echo "  Setting up Users Table and Testing Registration"
echo "============================================================"
echo

cd /root/graohen_os/backend/py-service

# Activate virtual environment
source venv/bin/activate

echo "📋 Step 1: Creating Users Table"
echo "--------------------------------"
python3 scripts/create_user_table.py

echo
echo "📋 Step 2: Testing Registration"
echo "--------------------------------"

# Test accounts
python3 << 'EOF'
import requests
import json

BASE_URL = "https://freedomos.vulcantech.co/api/v1"

accounts = [
    {"email": "test20@fxmail.ai", "password": "test20@#", "full_name": "Test User 20"},
    {"email": "test21@fxmail.ai", "password": "test20@#", "full_name": "Test User 21"},
]

for account in accounts:
    print(f"\n📝 Registering: {account['email']}")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=account,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"   ✅ Success! Token: {data.get('access_token', 'N/A')[:30]}...")
        elif response.status_code == 400:
            error = response.json().get("detail", "")
            if "already" in error.lower():
                print(f"   ℹ️  User already exists")
                # Try login
                login_resp = requests.post(
                    f"{BASE_URL}/auth/login",
                    json={"email": account["email"], "password": account["password"]},
                    timeout=15
                )
                if login_resp.status_code == 200:
                    print(f"   ✅ Login successful!")
                else:
                    print(f"   ❌ Login failed: {login_resp.text[:100]}")
            else:
                print(f"   ⚠️  Error: {error}")
        else:
            print(f"   ❌ Failed ({response.status_code}): {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")

print("\n✅ Registration test complete!")
EOF

echo
echo "============================================================"
echo "  Setup Complete"
echo "============================================================"

#!/usr/bin/env python3
"""
Test register + login (including second login) against VPS.

Email: meeqatt@fxmail.ai
Password: admin@123

Usage:
  API_BASE=https://freedomos.vulcantech.co/api/v1 python scripts/test_register_login.py
"""
import json
import os
import sys
import base64
import hmac
import hashlib

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.device_key_service import decrypt_seed_from_device
from app.core.device_key import create_device_proof
from app.core.secure_derivation import derive_device_time_key, get_current_time_slot

API_BASE = os.environ.get("API_BASE", "https://freedomos.vulcantech.co/api/v1")
EMAIL = "meeqatt@fxmail.ai"
PASSWORD = "admin@123"
DEVICE_ID = "meeqatt-test-device-001"


def req(method: str, path: str, data: dict = None, token: str = None) -> dict:
    import urllib.request
    import urllib.error
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def do_device_login(device_key_blob: dict) -> dict:
    """Perform device-bound login: challenge -> derive proof -> login/secure."""
    # 1. Get challenge
    ch = req("POST", "/auth/login/challenge", {"email": EMAIL, "device_id": DEVICE_ID})
    challenge = ch["challenge"]
    time_slot = ch.get("time_slot") or get_current_time_slot()

    # 2. Decrypt device seed from blob
    seed = decrypt_seed_from_device(device_key_blob, PASSWORD)

    # 3. Derive time-slot key and create proof
    time_key = derive_device_time_key(seed, DEVICE_ID, time_slot)
    proof = create_device_proof(time_key, challenge)

    # 4. Login secure
    return req("POST", "/auth/login/secure", {
        "email": EMAIL,
        "password": PASSWORD,
        "device_id": DEVICE_ID,
        "challenge": challenge,
        "proof": proof,
        "time_slot": time_slot,
    })


def main():
    print(f"API_BASE={API_BASE}")
    print(f"Email: {EMAIL}")
    print("")

    device_key_blob = None

    # 1. Register (or get device key if user exists)
    print("1. Registering...")
    try:
        reg = req("POST", "/auth/register", {
            "email": EMAIL,
            "password": PASSWORD,
            "device_id": DEVICE_ID,
        })
        device_key_blob = reg.get("device_key_download")
        if device_key_blob:
            print("   OK: User registered, device_key_download received")
        else:
            print("   OK: User registered (no device_key?)")
    except RuntimeError as e:
        if "409" in str(e) or "400" in str(e):
            print("   User exists, downloading device key...")
            try:
                dk = req("POST", "/auth/device-key/download", {
                    "email": EMAIL,
                    "password": PASSWORD,
                    "device_id": DEVICE_ID,
                })
                device_key_blob = dk.get("device_key_download")
                if device_key_blob:
                    print("   OK: device_key_download received")
                else:
                    print("   FAIL: No device_key_download in response")
                    sys.exit(1)
            except RuntimeError as e2:
                print(f"   FAIL: {e2}")
                sys.exit(1)
        else:
            print(f"   FAIL: {e}")
            sys.exit(1)

    if not device_key_blob:
        print("   FAIL: No device_key_blob - cannot test device login")
        sys.exit(1)

    print("")

    # 2. First login (device-bound)
    print("2. First login (device-bound)...")
    try:
        login1 = do_device_login(device_key_blob)
        tok1 = login1.get("access_token")
        if tok1:
            print("   OK: First login successful, got access_token")
        else:
            print("   FAIL: No access_token in response")
            sys.exit(1)
    except RuntimeError as e:
        print(f"   FAIL: {e}")
        sys.exit(1)

    print("")

    # 3. Second login (device-bound) - same flow
    print("3. Second login (device-bound)...")
    try:
        login2 = do_device_login(device_key_blob)
        tok2 = login2.get("access_token")
        if tok2:
            print("   OK: Second login successful, got access_token")
        else:
            print("   FAIL: No access_token in response")
            sys.exit(1)
    except RuntimeError as e:
        print(f"   FAIL: {e}")
        sys.exit(1)

    print("")
    print("=== All tests passed ===")


if __name__ == "__main__":
    main()

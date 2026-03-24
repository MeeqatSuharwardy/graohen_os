#!/usr/bin/env python3
"""
Test all APIs: auth (register, login), email, drive.
Run with backend server: uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
import json
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"
TEST_EMAIL = f"test_{int(time.time())}@example.com"
TEST_PASS = "TestPass123!"
DEVICE_ID = f"device-{int(time.time())}"


def req(method, url, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = Request(url, data=body, headers=headers, method=method)
    with urlopen(r, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main():
    print("=== API Tests ===\n")
    ok, fail = 0, 0

    # 1. Health
    try:
        with urlopen(f"{BASE}/health", timeout=5) as r:
            print("1. Health: OK")
            ok += 1
    except Exception as e:
        print(f"1. Health: FAIL - {e}")
        fail += 1
        return

    # 2. API root
    try:
        d = req("GET", f"{API}/")
        print(f"2. API root: OK - {d.get('message', d)}")
        ok += 1
    except Exception as e:
        print(f"2. API root: FAIL - {e}")
        fail += 1

    # 3. Register
    try:
        d = req("POST", f"{API}/auth/register", {
            "email": TEST_EMAIL,
            "password": TEST_PASS,
            "device_id": DEVICE_ID,
        })
        token = d.get("access_token")
        print(f"3. Register: OK - token received")
        ok += 1
    except HTTPError as e:
        print(f"3. Register: FAIL - {e.code} {e.reason}")
        fail += 1
        token = None
    except Exception as e:
        print(f"3. Register: FAIL - {e}")
        fail += 1
        token = None

    # 4. Login
    try:
        d = req("POST", f"{API}/auth/login", {
            "email": TEST_EMAIL,
            "password": TEST_PASS,
        })
        token = d.get("access_token", token)
        print(f"4. Login: OK")
        ok += 1
    except HTTPError as e:
        print(f"4. Login: FAIL - {e.code} {e.reason}")
        fail += 1
    except Exception as e:
        print(f"4. Login: FAIL - {e}")
        fail += 1

    if not token:
        print("\nNo token - skipping auth-required tests")
        print(f"Results: {ok} OK, {fail} FAIL")
        return

    # 5. Drive storage
    try:
        r = Request(f"{API}/drive/storage", headers={"Authorization": f"Bearer {token}"})
        with urlopen(r, timeout=5) as resp:
            d = json.loads(resp.read().decode())
        print(f"5. Drive storage: OK - {d.get('used_bytes', 0)} bytes used")
        ok += 1
    except Exception as e:
        print(f"5. Drive storage: FAIL - {e}")
        fail += 1

    # 6. Email send (authenticated mode - no passcode)
    email_id = None
    try:
        d = req("POST", f"{API}/email/send", {
            "to": [TEST_EMAIL],
            "subject": "Test",
            "body": "Hello",
        }, token=token)
        email_id = d.get("email_id")
        print(f"6. Email send: OK - email_id={email_id[:12] if email_id else '?'}...")
        ok += 1
    except HTTPError as e:
        print(f"6. Email send: FAIL - {e.code} {e.reason}")
        fail += 1
    except Exception as e:
        print(f"6. Email send: FAIL - {e}")
        fail += 1

    # 6b. View email (decrypt for authenticated user)
    if email_id:
        try:
            r = Request(f"{API}/email/{email_id}", headers={"Authorization": f"Bearer {token}"})
            with urlopen(r, timeout=5) as resp:
                view_d = json.loads(resp.read().decode())
            body = view_d.get("body", "")
            print(f"6b. View email: OK - body={body[:30]}...")
            ok += 1
        except HTTPError as e:
            print(f"6b. View email: FAIL - {e.code} {e.reason}")
            fail += 1
        except Exception as e:
            print(f"6b. View email: FAIL - {e}")
            fail += 1

        # 6c. Reply to email
        try:
            reply_d = req("POST", f"{API}/email/{email_id}/reply", {
                "body": "Reply body",
            }, token=token)
            print(f"6c. Reply: OK - reply_id={reply_d.get('email_id', '?')[:12]}...")
            ok += 1
        except HTTPError as e:
            print(f"6c. Reply: FAIL - {e.code} {e.reason}")
            fail += 1
        except Exception as e:
            print(f"6c. Reply: FAIL - {e}")
            fail += 1

    # 6d. Send passcode-protected email + unlock
    passcode_email_id = None
    try:
        passcode_d = req("POST", f"{API}/email/send", {
            "to": [TEST_EMAIL],
            "subject": "Passcode test",
            "body": "Secret content",
            "passcode": "test1234",
        }, token=token)
        passcode_email_id = passcode_d.get("email_id")
        print(f"6d. Send passcode email: OK")
        ok += 1
    except HTTPError as e:
        print(f"6d. Send passcode email: FAIL - {e.code} {e.reason}")
        fail += 1
    except Exception as e:
        print(f"6d. Send passcode email: FAIL - {e}")
        fail += 1

    if passcode_email_id:
        try:
            unlock_d = req("POST", f"{API}/email/{passcode_email_id}/unlock", {
                "passcode": "test1234",
            })
            body = unlock_d.get("body", "")
            print(f"6e. Unlock passcode email: OK - body={body[:30]}...")
            ok += 1
        except HTTPError as e:
            print(f"6e. Unlock passcode email: FAIL - {e.code} {e.reason}")
            fail += 1
        except Exception as e:
            print(f"6e. Unlock passcode email: FAIL - {e}")
            fail += 1

    # 7. Login challenge
    try:
        d = req("POST", f"{API}/auth/login/challenge", {
            "email": TEST_EMAIL,
            "device_id": DEVICE_ID,
        })
        print(f"7. Login challenge: OK - challenge received")
        ok += 1
    except Exception as e:
        print(f"7. Login challenge: FAIL - {e}")
        fail += 1

    print(f"\n=== Results: {ok} OK, {fail} FAIL ===")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()

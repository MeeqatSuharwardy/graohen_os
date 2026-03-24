#!/usr/bin/env python3
"""
Test auth, email, and drive APIs locally.
Run with backend: uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
import json
import sys
import time
import io
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
    with urlopen(r, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    print("=== API Tests: Auth, Email, Drive ===\n")
    ok, fail = 0, 0

    # --- Health ---
    try:
        with urlopen(f"{BASE}/health", timeout=5) as r:
            h = json.loads(r.read().decode())
            print("1. Health: OK -", h.get("status", h))
            ok += 1
    except Exception as e:
        print(f"1. Health: FAIL - {e}")
        fail += 1
        return

    # --- Auth: Register ---
    token = None
    refresh_token = None
    try:
        d = req("POST", f"{API}/auth/register", {
            "email": TEST_EMAIL,
            "password": TEST_PASS,
            "device_id": DEVICE_ID,
        })
        token = d.get("access_token")
        refresh_token = d.get("refresh_token")
        print(f"2. Auth register: OK - token received")
        ok += 1
    except HTTPError as e:
        print(f"2. Auth register: FAIL - {e.code} {e.reason}")
        fail += 1
    except Exception as e:
        print(f"2. Auth register: FAIL - {e}")
        fail += 1

    # --- Auth: Login (may fail - device-bound required after register) ---
    try:
        d = req("POST", f"{API}/auth/login", {
            "email": TEST_EMAIL,
            "password": TEST_PASS,
            "device_id": DEVICE_ID,
        })
        token = d.get("access_token", token)
        print(f"3. Auth login: OK")
        ok += 1
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            err = json.loads(body)
            detail = err.get("detail", body)
        except Exception:
            detail = body[:80]
        if "device-bound" in str(detail).lower() or "device_id" in str(detail).lower():
            print(f"3. Auth login: SKIP (device-bound required, use register token)")
        else:
            print(f"3. Auth login: FAIL - {e.code} {detail}")
            fail += 1
    except Exception as e:
        print(f"3. Auth login: FAIL - {e}")
        fail += 1

    if not token:
        print("\nNo token - skipping auth-required tests")
        print(f"Results: {ok} OK, {fail} FAIL")
        return

    # --- Auth: Refresh ---
    if refresh_token:
        try:
            d = req("POST", f"{API}/auth/refresh", {"refresh_token": refresh_token})
            new_token = d.get("access_token")
            if new_token:
                token = new_token  # use refreshed token for rest of tests
            print(f"4. Auth refresh: OK")
            ok += 1
        except HTTPError as e:
            err = e.read().decode() if e.fp else ""
            print(f"4. Auth refresh: FAIL - {e.code} {err[:60]}")
            fail += 1
        except Exception as e:
            print(f"4. Auth refresh: FAIL - {e}")
            fail += 1
    else:
        print(f"4. Auth refresh: SKIP (no refresh token)")

    # --- Drive: Storage ---
    try:
        d = req("GET", f"{API}/drive/storage", token=token)
        print(f"5. Drive storage: OK - {d.get('used_bytes', 0)} bytes, quota {d.get('quota_gb', 0)}GB")
        ok += 1
    except Exception as e:
        print(f"5. Drive storage: FAIL - {e}")
        fail += 1

    # --- Drive: Upload (multipart via requests if available) ---
    file_id = None
    try:
        try:
            import requests
            r = requests.post(
                f"{API}/drive/upload",
                files={"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")},
                data={"never_expire": "true"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            if r.status_code == 201:
                d = r.json()
                file_id = d.get("file_id")
                print(f"6. Drive upload: OK - file_id={file_id[:12] if file_id else '?'}...")
                ok += 1
            else:
                print(f"6. Drive upload: FAIL - {r.status_code} {r.text[:80]}")
                fail += 1
        except ImportError:
            print(f"6. Drive upload: SKIP (install requests for multipart)")
    except Exception as e:
        print(f"6. Drive upload: FAIL - {e}")
        fail += 1

    # --- Drive: Files list ---
    try:
        d = req("GET", f"{API}/drive/files", token=token)
        files = d.get("files", [])
        print(f"7. Drive files list: OK - {len(files)} file(s)")
        ok += 1
    except Exception as e:
        print(f"7. Drive files list: FAIL - {e}")
        fail += 1

    # --- Drive: File info ---
    if file_id:
        try:
            d = req("GET", f"{API}/drive/file/{file_id}", token=token)
            print(f"8. Drive file info: OK - {d.get('filename', '?')}")
            ok += 1
        except Exception as e:
            print(f"8. Drive file info: FAIL - {e}")
            fail += 1

    # --- Email: Send ---
    email_id = None
    try:
        d = req("POST", f"{API}/email/send", {
            "to": [TEST_EMAIL],
            "subject": "Test",
            "body": "Hello",
        }, token=token)
        email_id = d.get("email_id")
        print(f"9. Email send: OK - email_id={email_id[:12] if email_id else '?'}...")
        ok += 1
    except HTTPError as e:
        print(f"9. Email send: FAIL - {e.code} {e.reason}")
        fail += 1
    except Exception as e:
        print(f"9. Email send: FAIL - {e}")
        fail += 1

    # --- Email: View ---
    if email_id:
        try:
            d = req("GET", f"{API}/email/{email_id}", token=token)
            print(f"10. Email view: OK - body={d.get('body', '')[:30]}...")
            ok += 1
        except Exception as e:
            print(f"10. Email view: FAIL - {e}")
            fail += 1

        # --- Email: Reply ---
        try:
            d = req("POST", f"{API}/email/{email_id}/reply", {"body": "Reply"}, token=token)
            print(f"11. Email reply: OK")
            ok += 1
        except Exception as e:
            print(f"11. Email reply: FAIL - {e}")
            fail += 1

    # --- Email: Inbox ---
    try:
        d = req("GET", f"{API}/email/inbox", token=token)
        total = d.get("total", 0)
        print(f"12. Email inbox: OK - {total} email(s)")
        ok += 1
    except Exception as e:
        print(f"12. Email inbox: FAIL - {e}")
        fail += 1

    # --- Email: Sent ---
    try:
        d = req("GET", f"{API}/email/sent", token=token)
        total = d.get("total", 0)
        print(f"13. Email sent: OK - {total} email(s)")
        ok += 1
    except Exception as e:
        print(f"13. Email sent: FAIL - {e}")
        fail += 1

    # --- Email: Drafts ---
    try:
        d = req("GET", f"{API}/email/drafts", token=token)
        total = d.get("total", 0)
        print(f"13b. Email drafts: OK - {total} draft(s)")
        ok += 1
    except Exception as e:
        print(f"13b. Email drafts: FAIL - {e}")
        fail += 1

    # --- Email: Passcode send + unlock ---
    passcode_email_id = None
    try:
        d = req("POST", f"{API}/email/send", {
            "to": [TEST_EMAIL],
            "subject": "Secret",
            "body": "Secret content",
            "passcode": "test1234",
        }, token=token)
        passcode_email_id = d.get("email_id")
        print(f"14. Email send (passcode): OK")
        ok += 1
    except Exception as e:
        print(f"14. Email send (passcode): FAIL - {e}")
        fail += 1

    if passcode_email_id:
        try:
            d = req("POST", f"{API}/email/{passcode_email_id}/unlock", {"passcode": "test1234"})
            print(f"15. Email unlock: OK - body={d.get('body', '')[:25]}...")
            ok += 1
        except Exception as e:
            print(f"15. Email unlock: FAIL - {e}")
            fail += 1

    # --- Drive: Delete ---
    if file_id:
        try:
            d = req("DELETE", f"{API}/drive/file/{file_id}", token=token)
            print(f"16. Drive delete: OK")
            ok += 1
        except Exception as e:
            print(f"16. Drive delete: FAIL - {e}")
            fail += 1

    print(f"\n=== Results: {ok} OK, {fail} FAIL ===")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()

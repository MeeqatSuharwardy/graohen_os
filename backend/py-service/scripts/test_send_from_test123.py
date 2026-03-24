#!/usr/bin/env python3
"""
Test: Create user test123@fxmail.ai, send to Gmail and Yahoo, record logs.

Usage:
  API_BASE=https://freedomos.vulcantech.co/api/v1 python scripts/test_send_from_test123.py
  # Or locally: API_BASE=http://127.0.0.1:8000/api/v1 python scripts/test_send_from_test123.py

Writes log to: scripts/test_send_from_test123.log
"""
import json
import os
import sys
from datetime import datetime
from typing import Optional

API_BASE = os.environ.get("API_BASE", "https://freedomos.vulcantech.co/api/v1")
LOG_FILE = os.path.join(os.path.dirname(__file__), "test_send_from_test123.log")
USER_EMAIL = "test123@fxmail.ai"
USER_PASS = "TestPass123!"
RECIPIENTS = ["meeqatsuharward@gmail.com", "meeqatsuherward@yahoo.com"]


def log(msg: str, also_print: bool = True):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line)


def req(method: str, path: str, data: Optional[dict] = None, token: Optional[str] = None) -> dict:
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


def main():
    # Clear/init log
    with open(LOG_FILE, "w") as f:
        f.write(f"=== Test run {datetime.utcnow().isoformat()} ===\n")
        f.write(f"API_BASE={API_BASE}\n")
        f.write(f"User={USER_EMAIL}\n")
        f.write(f"Recipients={RECIPIENTS}\n\n")

    log("1. Registering user test123@fxmail.ai...")
    try:
        reg = req("POST", "/auth/register", {
            "email": USER_EMAIL,
            "password": USER_PASS,
            "device_id": "test123-device",
        })
        token = reg.get("access_token")
        if not token:
            log("FAIL: No access_token in register response", also_print=True)
            sys.exit(1)
        log(f"   OK: User created, token received (len={len(token)})")
    except Exception as e:
        if "409" in str(e) or "already" in str(e).lower():
            log("   User exists, attempting login...")
            try:
                login = req("POST", "/auth/login", {
                    "email": USER_EMAIL,
                    "password": USER_PASS,
                    "device_id": "test123-device",
                })
                token = login.get("access_token")
                if token:
                    log("   OK: Logged in (device-bound may require /login/secure)")
                else:
                    log("   FAIL: Could not get token from login")
                    sys.exit(1)
            except Exception as e2:
                log(f"   FAIL: {e2}")
                sys.exit(1)
        else:
            log(f"   FAIL: {e}")
            sys.exit(1)

    log("")
    log("2. Sending email to both recipients (link_only)...")
    try:
        send_resp = req("POST", "/email/send", {
            "to": RECIPIENTS,
            "subject": "Test from test123@fxmail.ai",
            "body": "This is a secure message from test123@fxmail.ai. Open the link to read.",
            "notification_delivery": "link_only",
        }, token=token)

        email_id = send_resp.get("email_id", "")
        secure_link = send_resp.get("secure_link", "")
        notifications = send_resp.get("notifications_sent") or []

        log(f"   email_id: {email_id[:20]}...")
        log(f"   secure_link: {secure_link}")
        log("")
        log("   Notification delivery status:")
        for n in notifications:
            status = "SENT" if n.get("sent") else "FAILED"
            log(f"     {n.get('to', '?')}: {status}")
        if not notifications:
            log("     (No notifications - SMTP may not be configured or delivery=none)")
    except Exception as e:
        log(f"   FAIL: {e}")
        sys.exit(1)

    log("")
    log("3. Sending passcode-protected email (link_and_passcode)...")
    try:
        send2 = req("POST", "/email/send", {
            "to": RECIPIENTS,
            "subject": "Passcode-protected from test123@fxmail.ai",
            "body": "Use passcode: secure5678 to unlock this message.",
            "passcode": "secure5678",
            "notification_delivery": "link_and_passcode",
        }, token=token)

        notifications2 = send2.get("notifications_sent") or []
        log(f"   email_id: {send2.get('email_id', '')[:20]}...")
        log("   Notification delivery status:")
        for n in notifications2:
            status = "SENT" if n.get("sent") else "FAILED"
            log(f"     {n.get('to', '?')}: {status}")
        log("   Passcode: secure5678")
    except Exception as e:
        log(f"   FAIL: {e}")
        sys.exit(1)

    log("")
    log("=== Done. Log saved to " + LOG_FILE)


if __name__ == "__main__":
    main()

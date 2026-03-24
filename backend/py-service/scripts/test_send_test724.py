#!/usr/bin/env python3
"""
Test: Create user, send to Gmail and Yahoo, record logs.

Usage:
  # Option A: Use test-smtp endpoint (no auth, requires SMTP_TEST_SECRET in .env)
  API_BASE=https://freedomos.vulcantech.co/api/v1 SMTP_TEST_SECRET=your-secret python scripts/test_send_test724.py

  # Option B: Full auth flow (register + send) - works for NEW users
  API_BASE=https://freedomos.vulcantech.co/api/v1 python scripts/test_send_test724.py

  # With custom sender:
  SENDER_EMAIL=test727@fxmail.ai API_BASE=... python scripts/test_send_test724.py

Log: scripts/test_send_test724.log
"""
import json
import os
import sys
from datetime import datetime
from typing import Optional

API_BASE = os.environ.get("API_BASE", "https://freedomos.vulcantech.co/api/v1")
SMTP_TEST_SECRET = os.environ.get("SMTP_TEST_SECRET", "")
SENDER = os.environ.get("SENDER_EMAIL", "test727@fxmail.ai")
LOG_FILE = os.path.join(os.path.dirname(__file__), "test_send_test724.log")
USER_PASS = "TestPass123!"
RECEIVERS = ["meeqatsuharward@gmail.com", "meeqatsuherward@yahoo.com"]


def log(msg: str, also_print: bool = True):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line)


def req(method: str, path: str, data: Optional[dict] = None, token: Optional[str] = None, extra_headers: Optional[dict] = None) -> dict:
    import urllib.request
    import urllib.error
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def run_test_smtp() -> bool:
    """Use /email/test-smtp endpoint (no auth). Returns True if all sent."""
    log("Using /email/test-smtp (no auth)")
    log("")
    log(f"Sending test email from {SENDER} to both receivers...")
    log(f"   Sender: {SENDER}")
    log(f"   Receivers: {', '.join(RECEIVERS)}")
    try:
        resp = req(
            "POST",
            "/email/test-smtp",
            {
                "from_email": SENDER,
                "to": RECEIVERS,
                "subject": f"Test from {SENDER}",
                "body": f"This is a test email from {SENDER}. Receivers: meeqatsuharward@gmail.com and meeqatsuherward@yahoo.com.",
            },
            extra_headers={"X-SMTP-Test-Secret": SMTP_TEST_SECRET},
        )
        notifications = resp.get("notifications_sent") or []
        log("")
        log("   Notification delivery status (SENT or FAILED):")
        all_ok = True
        for n in notifications:
            status = "SENT" if n.get("sent") else "FAILED"
            if not n.get("sent"):
                all_ok = False
            log(f"     {n.get('to', '?')}: {status}")
        return all_ok
    except Exception as e:
        log(f"   FAIL: {e}")
        return False


def run_full_auth_flow() -> bool:
    """Register/login + send via /email/send."""
    device_id = SENDER.replace("@", "-") + "-device"
    log(f"1. Registering user {SENDER}...")
    try:
        reg = req("POST", "/auth/register", {
            "email": SENDER,
            "password": USER_PASS,
            "device_id": device_id,
        })
        token = reg.get("access_token")
        if not token:
            log("   FAIL: No access_token in register response")
            return False
        log(f"   OK: User created, token received")
    except Exception as e:
        if "409" in str(e) or "400" in str(e):
            log("   User may exist, trying login...")
            try:
                login = req("POST", "/auth/login", {
                    "email": SENDER,
                    "password": USER_PASS,
                    "device_id": device_id,
                })
                token = login.get("access_token")
                if token:
                    log("   OK: Logged in")
                else:
                    log(f"   FAIL: Could not get token - {login}")
                    return False
            except Exception as e2:
                log(f"   FAIL: {e2}")
                return False
        else:
            log(f"   FAIL: {e}")
            return False

    log("")
    log(f"2. Sending email from {SENDER} to both receivers (link_only)...")
    log(f"   Sender: {SENDER}")
    log(f"   Receivers: {', '.join(RECEIVERS)}")
    try:
        send_resp = req("POST", "/email/send", {
            "to": RECEIVERS,
            "subject": f"Secure message from {SENDER}",
            "body": f"This is a secure message from {SENDER}. Open the link to read.",
            "notification_delivery": "link_only",
        }, token=token)

        email_id = send_resp.get("email_id", "")
        secure_link = send_resp.get("secure_link", "")
        notifications = send_resp.get("notifications_sent") or []

        log(f"   email_id: {email_id[:24]}...")
        log(f"   secure_link: {secure_link}")
        log("")
        log("   Notification delivery status (SENT or FAILED):")
        all_ok = True
        for n in notifications:
            status = "SENT" if n.get("sent") else "FAILED"
            if not n.get("sent"):
                all_ok = False
            log(f"     {n.get('to', '?')}: {status}")
        if not notifications:
            log("     (notifications_sent not in response - SMTP may not be configured)")
        return all_ok
    except Exception as e:
        log(f"   FAIL: {e}")
        return False


def main():
    with open(LOG_FILE, "w") as f:
        f.write(f"=== Test run {datetime.utcnow().isoformat()} ===\n")
        f.write(f"API_BASE={API_BASE}\n")
        f.write(f"Sender: {SENDER}\n")
        f.write(f"Receivers: {RECEIVERS}\n\n")

    if SMTP_TEST_SECRET:
        success = run_test_smtp()
    else:
        log("SMTP_TEST_SECRET not set. Use auth flow (register/login + send).")
        log("Note: If user exists with device-binding, login will fail. Set SMTP_TEST_SECRET in .env for direct SMTP test.")
        log("")
        success = run_full_auth_flow()

    log("")
    log("=== Done. Log saved to " + LOG_FILE)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

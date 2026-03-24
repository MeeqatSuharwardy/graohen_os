#!/usr/bin/env python3
"""
Test sending notification emails to Gmail and Yahoo.
Requires: Backend running, valid SMTP config in .env, registered user token.

Usage:
  1. Register: POST /api/v1/auth/register
  2. Set ACCESS_TOKEN and run: python scripts/test_send_to_gmail_yahoo.py
"""
import json
import os
import sys

API = os.environ.get("API_BASE", "http://127.0.0.1:8000/api/v1")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")

GMAIL = "meeqatsuharward@gmail.com"
YAHOO = "meeqatsuherward@yahoo.com"


def req(method, path, data=None):
    headers = {"Content-Type": "application/json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    url = f"{API}{path}"
    import urllib.request
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.loads(resp.read().decode())


def main():
    if not ACCESS_TOKEN:
        print("Set ACCESS_TOKEN env (from /auth/register or /auth/login)")
        print("Example: ACCESS_TOKEN=xxx python scripts/test_send_to_gmail_yahoo.py")
        sys.exit(1)

    print("Sending to Gmail (link_only)...")
    try:
        d = req("POST", "/email/send", {
            "to": [GMAIL],
            "subject": "Secure message test - Gmail",
            "body": "This is the secret content. Only you can read it via the link.",
            "notification_delivery": "link_only",
        })
        print(f"  OK: email_id={d.get('email_id', '')[:16]}..., secure_link={d.get('secure_link', '')[:50]}...")
    except Exception as e:
        print(f"  FAIL: {e}")
        sys.exit(1)

    print("Sending to Yahoo (link_and_passcode)...")
    try:
        d = req("POST", "/email/send", {
            "to": [YAHOO],
            "subject": "Secure message test - Yahoo",
            "body": "Protected content. Use the passcode I will share.",
            "passcode": "test1234",
            "notification_delivery": "link_and_passcode",
        })
        print(f"  OK: email_id={d.get('email_id', '')[:16]}...")
        print(f"  Passcode (share separately): test1234")
    except Exception as e:
        print(f"  FAIL: {e}")
        sys.exit(1)

    print("\nCheck Gmail and Yahoo inboxes for notification emails.")
    print("Gmail: link_only (just the secure link)")
    print("Yahoo: link_and_passcode (link + note to get passcode separately)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check all API endpoints on server."""
import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = os.environ.get("API_BASE", "https://freedomos.vulcantech.co/api/v1")


def req(method, path, data=None, token=None):
    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)


def main():
    print(f"=== Checking endpoints on {API_BASE.replace('/api/v1','')} ===\n")

    # Register for token
    token = ""
    try:
        email = f"epcheck_{os.getpid()}@example.com"
        r = urllib.request.Request(
            f"{API_BASE}/auth/register",
            data=json.dumps({"email": email, "password": "TestPass123!", "device_id": "ep-1"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(r, timeout=10) as resp:
            token = json.loads(resp.read().decode()).get("access_token", "")
    except Exception as e:
        print(f"Register failed: {e}")

    if token:
        print(f"Token: {token[:30]}... (len={len(token)})\n")
    else:
        print("No token - auth endpoints will show 401/403\n")

    tests = [
        # Auth
        ("POST", "/auth/register", {"email": "x@y.com", "password": "TestPass123!", "device_id": "d1"}, None),
        ("POST", "/auth/login", {"email": "x@y.com", "password": "TestPass123!"}, None),
        ("POST", "/auth/login/challenge", {"email": "x@y.com", "device_id": "d1"}, None),
        ("POST", "/auth/refresh", {"refresh_token": "x"}, None),
        ("POST", "/auth/logout", {}, token),
        ("POST", "/auth/device-key/download", {"email": "x@y.com", "password": "x", "device_id": "d1"}, None),
        ("GET", "/auth/device/key-info/d1", None, None),
        ("POST", "/auth/device/register-key", {"device_id": "d1", "key_blob": "x"}, token),
        # Email
        ("POST", "/email/send", {"to": ["a@b.com"], "subject": "T", "body": "B", "notification_delivery": "link_only"}, token),
        ("GET", "/email/inbox", None, token),
        ("GET", "/email/sent", None, token),
        ("GET", "/email/drafts", None, token),
        ("GET", "/email/token/abc123xyz", None, None),
        ("POST", "/email/ingest", None, None),  # No JSON, raw body
        ("POST", "/email/drafts", {"to": ["a@b.com"], "body": "B"}, token),
        # Drive
        ("GET", "/drive/storage", None, token),
        ("GET", "/drive/files", None, token),
        ("GET", "/drive/storage/quota", None, token),
        ("GET", "/drive/file/nonexistent-id", None, token),
        ("DELETE", "/drive/file/nonexistent-id", None, token),
        # Public
        ("GET", "/public/view/testtoken", None, None),
        ("POST", "/public/unlock/testtoken", {"passcode": "1234"}, None),
        ("GET", "/public/data/testtoken", None, None),
        ("GET", "/public/session/testtoken", None, None),
        # Example
        ("GET", "/example", None, None),
        # GrapheneOS
        ("GET", "/grapheneos/check/cheetah", None, None),
        ("POST", "/grapheneos/start", {"codename": "cheetah"}, None),
        ("GET", "/grapheneos/status/nonexistent", None, None),
        # Admin
        ("GET", "/admin/stats", None, token),
        ("GET", "/admin/storage", None, token),
        ("GET", "/admin/drive", None, token),
    ]

    # Special case: ingest expects raw body, not JSON
    ingest_status = "skip"
    if token:
        try:
            r = urllib.request.Request(
                f"{API_BASE}/email/ingest",
                data=b"",
                headers={"Content-Type": "application/octet-stream"},
                method="POST",
            )
            urllib.request.urlopen(r, timeout=5)
            ingest_status = 201
        except urllib.error.HTTPError as e:
            ingest_status = e.code
        except Exception as e:
            ingest_status = str(e)

    print("--- Auth ---")
    for method, path, data, tok in tests[:8]:
        s = req(method, path, data, tok)
        print(f"{method:6} {path:45} {s}")

    print("\n--- Email ---")
    for method, path, data, tok in tests[8:15]:
        if path == "/email/ingest":
            print(f"POST   /email/ingest{' ':38} {ingest_status}")
        else:
            s = req(method, path, data, tok)
            print(f"{method:6} {path:45} {s}")

    print("\n--- Drive ---")
    for method, path, data, tok in tests[15:20]:
        s = req(method, path, data, tok)
        print(f"{method:6} {path:45} {s}")

    print("\n--- Public ---")
    for method, path, data, tok in tests[20:24]:
        s = req(method, path, data, tok)
        print(f"{method:6} {path:45} {s}")

    print("\n--- Example ---")
    s = req("GET", "/example", None, None)
    print(f"GET    /example{' ':42} {s}")

    print("\n--- GrapheneOS ---")
    for method, path, data, tok in tests[25:28]:
        s = req(method, path, data, tok)
        print(f"{method:6} {path:45} {s}")

    print("\n--- Admin ---")
    for method, path, data, tok in tests[28:]:
        s = req(method, path, data, tok)
        print(f"{method:6} {path:45} {s}")

    print("\n=== Done ===")
    print("201/200=OK, 401/403=Auth, 404=Not found, 422=Validation, 400=Bad request")


if __name__ == "__main__":
    main()

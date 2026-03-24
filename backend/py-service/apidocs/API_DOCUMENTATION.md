# FxMail API Documentation

**Base URL:** `https://freedomos.vulcantech.co`  
**API Prefix:** `/api/v1`  
**Full API Base:** `https://freedomos.vulcantech.co/api/v1`

This API powers the FxMail secure email platform. Use it to build web mail clients and mobile apps with end-to-end encryption, device binding, and ProtonMail-style security.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Auth Endpoints](#auth-endpoints)
4. [Email Endpoints](#email-endpoints)
5. [Drive (File Storage) Endpoints](#drive-endpoints)
6. [Public Endpoints](#public-endpoints)
7. [Error Handling](#error-handling)
8. [Rate Limits](#rate-limits)

---

## Overview

### Key Concepts

- **Device-bound auth:** After registration, users receive a `device_key_download` blob. Store it securely on the device. Future logins require a challenge-response proof derived from this key.
- **E2E encryption:** Email content and file content are encrypted. The server never stores plaintext. Subject and body are encrypted together.
- **Encryption modes:** `authenticated` (only sender/recipient with device key) or `passcode_protected` (anyone with passcode).
- **Email addresses:** User emails use the format `token@fxmail.ai` (e.g. `alice@fxmail.ai`).

### Request Format

- **Content-Type:** `application/json` for all JSON bodies
- **Authorization:** `Bearer <access_token>` for protected endpoints

---

## Authentication

### Header

```
Authorization: Bearer <access_token>
```

### Token Lifetime

- **Access token:** 30 minutes
- **Refresh token:** 7 days
- Use `/auth/refresh` to get a new access token before expiry

### Device-Bound Login Flow

1. `POST /auth/login/challenge` — Get challenge
2. Derive proof: `HMAC(device_key, challenge)` using current time slot
3. `POST /auth/login/secure` — Submit proof

---

## Auth Endpoints

### Register

Create a new account.

```
POST /api/v1/auth/register
```

**Request body:**

```json
{
  "email": "user@fxmail.ai",
  "password": "SecurePass123!",
  "full_name": "Alice",
  "device_id": "my-device-uuid"
}
```

| Field       | Type   | Required | Description                                |
|------------|--------|----------|--------------------------------------------|
| email          | string | Yes      | Valid email (e.g. user@fxmail.ai)          |
| password       | string | Yes      | Min 8 characters                           |
| full_name      | string | No       | Display name                               |
| device_id      | string | No       | Device identifier for mobile (min 8 chars if provided) |
| ssh_public_key | string | No       | SSH public key for browser login (OpenSSH format)      |

**Response (201):**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "my-device-uuid",
  "device_key_download": {
    "ciphertext": "base64...",
    "nonce": "base64...",
    "tag": "base64...",
    "salt": "base64..."
  }
}
```

**Important:** Save `device_key_download` on the device. It is required for future logins. It is encrypted with the user's password.

---

### Login (Device-bound)

```
POST /api/v1/auth/login/challenge
```

**Request body:**

```json
{
  "email": "user@fxmail.ai",
  "device_id": "my-device-uuid"
}
```

**Response (200):**

```json
{
  "challenge": "random-base64-string",
  "time_slot": 12345678,
  "expires_in_seconds": 120
}
```

---

```
POST /api/v1/auth/login/secure
```

**Request body:**

```json
{
  "email": "user@fxmail.ai",
  "password": "SecurePass123!",
  "device_id": "my-device-uuid",
  "challenge": "challenge-from-previous-step",
  "proof": "hmac-base64-derived-from-device-key",
  "time_slot": 12345678
}
```

**Response (200):** Same as register (tokens + optionally device_key_download).

---

### Device Key Download

For existing users who need a device key for a new device.

```
POST /api/v1/auth/device-key/download
```

**Request body:**

```json
{
  "email": "user@fxmail.ai",
  "password": "SecurePass123!",
  "device_id": "new-device-uuid"
}
```

**Response (200):**

```json
{
  "device_key_download": { "ciphertext": "...", "nonce": "...", "tag": "...", "salt": "..." },
  "device_id": "new-device-uuid"
}
```

---

### SSH Key Login (Browser Only)

For browser-based login without device_id. User registers an SSH public key and signs a challenge with their private key.

**Add SSH Key (authenticated):**

```
POST /api/v1/auth/ssh-key/add
```

**Headers:** `Authorization: Bearer <access_token>`

**Request body:**

```json
{
  "ssh_public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@example.com"
}
```

**Response (200):**

```json
{
  "fingerprint": "sha256-hex-of-public-key",
  "message": "SSH key added successfully"
}
```

---

**Get SSH Login Challenge:**

```
POST /api/v1/auth/login/ssh/challenge
```

**Request body:**

```json
{
  "email": "user@fxmail.ai"
}
```

**Response (200):**

```json
{
  "challenge": "random-base64-string",
  "expires_in_seconds": 120
}
```

**Errors:** 404 if no SSH key registered for email.

---

**SSH Login:**

```
POST /api/v1/auth/login/ssh
```

**Request body:**

```json
{
  "email": "user@fxmail.ai",
  "signature": "base64-encoded-signature-of-challenge"
}
```

Sign the `challenge` string (UTF-8) with the user's private key. Encode raw signature as base64. Ed25519 recommended; RSA also supported.

**Response (200):** Same as register (tokens).

---

### Refresh Token

```
POST /api/v1/auth/refresh
```

**Request body:**

```json
{
  "refresh_token": "eyJ...",
  "device_id": "my-device-uuid"
}
```

**Response (200):** New `access_token` and `refresh_token`. Old refresh token is revoked.

---

### Logout

```
POST /api/v1/auth/logout
```

**Request body:**

```json
{
  "refresh_token": "eyJ...",
  "all_devices": false
}
```

| Field         | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| refresh_token | string  | Optional; if not provided, uses Bearer token     |
| all_devices   | boolean | If true, logout from all devices for this user  |

---

## Email Endpoints

All email endpoints (except public viewer) require `Authorization: Bearer <access_token>`.

### Send Email

```
POST /api/v1/email/send
```

**Request body:**

```json
{
  "to": ["recipient@gmail.com", "other@yahoo.com"],
  "subject": "Hello",
  "body": "This is the email body.",
  "passcode": null,
  "expires_in_hours": null,
  "self_destruct": false,
  "notification_delivery": "link_only"
}
```

| Field                 | Type   | Required | Description                                                                 |
|-----------------------|--------|----------|-----------------------------------------------------------------------------|
| to                    | array  | Yes      | Recipient emails (1–50)                                                     |
| subject               | string | No       | Subject (encrypted with body)                                               |
| body                  | string | Yes      | Body, max 500KB                                                             |
| passcode              | string | No       | 4–128 chars; if set, email is passcode-protected                            |
| expires_in_hours      | int    | No       | 1–8760                                                                      |
| self_destruct         | bool   | No       | Delete after first read                                                     |
| notification_delivery | string | No       | `"none"` \| `"link_only"` \| `"link_and_passcode"`; default `"none"`        |

**Response (201):**

```json
{
  "email_id": "9aT8x1tQT1vBoKltZp3YJrW_Na8mQFxSHJRIqVaKwdo",
  "email_address": "sender@fxmail.ai",
  "secure_link": "https://fxmail.ai/email/9aT8x1tQT1vBoKltZp3YJrW_Na8mQFxSHJRIqVaKwdo",
  "expires_at": "2026-04-20T12:00:00",
  "encryption_mode": "authenticated",
  "notifications_sent": [
    { "to": "recipient@gmail.com", "sent": true },
    { "to": "other@yahoo.com", "sent": false }
  ]
}
```

---

### Get Inbox

```
GET /api/v1/email/inbox?limit=50&offset=0
```

**Query params:** `limit` (default 50), `offset` (default 0)

**Response (200):**

```json
{
  "emails": [
    {
      "email_id": "abc123...",
      "access_token": "abc123...",
      "sender_email": "bob@fxmail.ai",
      "recipient_emails": ["alice@fxmail.ai"],
      "subject": null,
      "created_at": "2026-03-20T12:00:00",
      "expires_at": null,
      "has_passcode": false,
      "is_draft": false,
      "status": "inbox"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

---

### Get Sent

```
GET /api/v1/email/sent?limit=50&offset=0
```

Same response shape as inbox, with `status: "sent"`.

---

### Get Drafts

```
GET /api/v1/email/drafts?limit=50&offset=0
```

Same response shape, with `status: "draft"`.

---

### Get Single Email (Authenticated)

```
GET /api/v1/email/{email_id}
```

Returns decrypted content for emails in `authenticated` mode. For passcode-protected emails, use the unlock endpoint.

**Response (200):**

```json
{
  "email_id": "abc123...",
  "subject": "Hello",
  "body": "Decrypted body content.",
  "encryption_mode": "authenticated",
  "expires_at": null,
  "is_passcode_protected": false
}
```

**Errors:**
- 403: Email requires passcode unlock
- 404: Email not found or expired

---

### Unlock Passcode-Protected Email

```
POST /api/v1/email/{email_id}/unlock
```

**Request body:**

```json
{
  "passcode": "user-provided-passcode"
}
```

**Response (200):**

```json
{
  "email_id": "abc123...",
  "subject": "Hello",
  "body": "Decrypted body content.",
  "unlocked_at": "2026-03-20T12:00:00"
}
```

**Errors:**
- 401: Incorrect passcode (includes `attempts_remaining`)
- 429: Too many attempts, email locked

**Rate limit:** 5 attempts per hour per email. After 5, locked for 1 hour.

---

### Reply to Email

```
POST /api/v1/email/{email_id}/reply
```

**Request body:**

```json
{
  "body": "Reply content",
  "subject": null,
  "passcode": null,
  "expires_in_hours": null,
  "self_destruct": false,
  "notification_delivery": "link_only"
}
```

**Response (201):** Same as send email.

---

### Delete Email

```
DELETE /api/v1/email/{email_id}
```

Requires authentication or ownership. Used for self-destruct flow as well.

**Response (200):**

```json
{
  "email_id": "abc123...",
  "deleted": true,
  "message": "Email deleted"
}
```

---

### Get Email by Token (Public Web Viewer)

Used by the web viewer at `https://fxmail.ai/email/{token}`. No auth required.

```
GET /api/v1/email/token/{token}
```

**Response (200):**

```json
{
  "email_id": "abc123...",
  "subject": null,
  "body": "",
  "encryption_mode": "passcode_protected",
  "expires_at": null,
  "is_passcode_protected": true
}
```

Returns metadata only. If `is_passcode_protected` is true, the client should show a passcode form and call `POST /api/v1/email/{email_id}/unlock` with the token as `email_id`.

---

### Save Draft

```
POST /api/v1/email/drafts
```

**Request body:**

```json
{
  "to": ["recipient@example.com"],
  "subject": "Draft subject",
  "body": "Draft body",
  "draft_id": null
}
```

Use `draft_id` to update an existing draft.

**Response (201):**

```json
{
  "email_id": "draft-id...",
  "access_token": "draft-id...",
  "email_address": "sender@fxmail.ai",
  "status": "draft",
  "created_at": "2026-03-20T12:00:00",
  "updated_at": "2026-03-20T12:00:00"
}
```

---

### Update Draft

```
PUT /api/v1/email/drafts/{draft_id}
```

**Request body:** Same as save draft (without `draft_id`).

---

### Delete Draft

```
DELETE /api/v1/email/drafts/{draft_id}
```

---

## Drive Endpoints

All drive endpoints require `Authorization: Bearer <access_token>`.

### Get Storage Info

```
GET /api/v1/drive/storage
```

**Response (200):**

```json
{
  "used_bytes": 1048576,
  "quota_bytes": 5368709120,
  "used_mb": 1.0,
  "quota_gb": 5.0,
  "percent_used": 0.02
}
```

---

### Get Storage Quota

```
GET /api/v1/drive/storage/quota
```

**Response (200):**

```json
{
  "used_bytes": 1048576,
  "quota_bytes": 5368709120,
  "used_gb": 0.001,
  "quota_gb": 5.0,
  "available_bytes": 5367658240,
  "available_gb": 4.999,
  "percentage_used": 0.02
}
```

---

### Upload File (Plain)

```
POST /api/v1/drive/upload
```

**Content-Type:** `multipart/form-data`

| Field      | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| file      | file   | Yes      | File binary              |
| passcode  | string | No       | Optional passcode        |
| expires_in_hours | int | No | Expiration in hours      |

**Response (201):**

```json
{
  "file_id": "abc123...",
  "filename": "document.pdf",
  "size": 102400,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": null,
  "created_at": "2026-03-20T12:00:00"
}
```

---

### Upload Encrypted File (Client-Side Encryption)

```
POST /api/v1/drive/upload-encrypted
```

**Request body:**

```json
{
  "filename": "document.pdf",
  "encrypted_content": {
    "ciphertext": "base64...",
    "nonce": "base64...",
    "tag": "base64..."
  },
  "encrypted_content_key": {
    "ciphertext": "base64...",
    "nonce": "base64...",
    "tag": "base64..."
  },
  "content_type": "application/pdf",
  "size": 102400,
  "passcode": null,
  "never_expire": false,
  "expires_in_hours": 24,
  "expires_in_days": null
}
```

---

### List Files

```
GET /api/v1/drive/files?limit=50&offset=0
```

**Response (200):**

```json
{
  "files": [
    {
      "file_id": "abc123...",
      "filename": "document.pdf",
      "size": 102400,
      "content_type": "application/pdf",
      "passcode_protected": false,
      "created_at": "2026-03-20T12:00:00",
      "expires_at": null
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

---

### Get File Info

```
GET /api/v1/drive/file/{file_id}
```

**Response (200):**

```json
{
  "file_id": "abc123...",
  "filename": "document.pdf",
  "size": 102400,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "owner_email": "user@fxmail.ai",
  "expires_at": null,
  "created_at": "2026-03-20T12:00:00",
  "signed_url": null,
  "signed_url_expires_at": null
}
```

---

### Download File

```
GET /api/v1/drive/file/{file_id}/download
```

**Query params:** `passcode` (if passcode-protected)

Returns the file binary with appropriate `Content-Disposition` header. For encrypted uploads, use the encrypted download endpoint.

---

### Download Encrypted File

```
GET /api/v1/drive/file/{file_id}/download-encrypted
```

**Response (200):**

```json
{
  "file_id": "abc123...",
  "filename": "document.pdf",
  "size": 102400,
  "content_type": "application/pdf",
  "encrypted_content": { "ciphertext": "...", "nonce": "...", "tag": "..." },
  "encrypted_content_key": { "ciphertext": "...", "nonce": "...", "tag": "..." },
  "passcode_protected": false,
  "created_at": "2026-03-20T12:00:00",
  "expires_at": null,
  "message": "File downloaded. Decrypt encrypted_content_key using your device key, then decrypt encrypted_content using the decrypted content key."
}
```

---

### Unlock File (Passcode-Protected)

```
POST /api/v1/drive/file/{file_id}/unlock
```

**Request body:**

```json
{
  "passcode": "user-provided-passcode"
}
```

**Response (200):**

```json
{
  "file_id": "abc123...",
  "signed_url": "https://freedomos.vulcantech.co/api/v1/drive/file/abc123/download?token=...",
  "signed_url_expires_at": "2026-03-20T13:00:00",
  "unlocked_at": "2026-03-20T12:00:00"
}
```

---

### Delete File

```
DELETE /api/v1/drive/file/{file_id}
```

**Response (200):**

```json
{
  "file_id": "abc123...",
  "deleted": true,
  "message": "File deleted"
}
```

---

## Public Endpoints

### View Encrypted Content (Web Viewer)

```
GET /api/v1/public/view/{token}
```

Returns an HTML page for viewing encrypted content (email). Used by the fxmail.ai web viewer.

---

### Unlock Public Content

```
POST /api/v1/public/unlock/{token}
```

**Request body:**

```json
{
  "passcode": "user-passcode"
}
```

**Response (200):** Decrypted content (structure depends on content type).

---

### Get Encrypted Data (JSON)

```
GET /api/v1/public/data/{token}
```

Returns encrypted payload for client-side decryption.

---

## Error Handling

### HTTP Status Codes

| Code | Meaning                    |
|------|----------------------------|
| 200  | Success                    |
| 201  | Created                    |
| 400  | Bad request                |
| 401  | Unauthorized               |
| 403  | Forbidden                  |
| 404  | Not found                  |
| 429  | Rate limit exceeded        |
| 500  | Server error               |

### Error Response Format

```json
{
  "detail": "Error message string"
}
```

Or for structured errors (e.g. unlock):

```json
{
  "detail": {
    "error": "Incorrect passcode",
    "attempts_remaining": 4,
    "message": "Incorrect passcode. 4 attempts remaining."
  }
}
```

---

## Rate Limits

| Action            | Limit                    |
|-------------------|--------------------------|
| Register          | 20 per hour per IP       |
| Email send        | 30 per hour per user     |
| Email unlock      | 5 attempts per hour per email |
| Public unlock     | 5 attempts per hour per token  |

---

## Email Web Flow for Recipients

When a recipient receives an email with `secure_link` (e.g. from Gmail):

1. Open `https://fxmail.ai/email/{token}` (or equivalent).
2. Frontend calls `GET /api/v1/email/token/{token}` to get metadata.
3. If `is_passcode_protected` is true, show passcode form.
4. Call `POST /api/v1/email/{token}/unlock` with `{ "passcode": "..." }`.
5. Display decrypted subject and body.

---

## Mobile App Considerations

- **Secure storage:** Store `device_key_download` in keychain/keystore.
- **Biometrics:** Use device biometrics to unlock the stored key before deriving login proof.
- **Token refresh:** Refresh access token before expiry; handle 401 by refreshing or re-login.
- **Offline:** Consider caching inbox/sent metadata; sync when online.

---

*Last updated: March 2026*

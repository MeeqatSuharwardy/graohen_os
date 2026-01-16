# Complete API Documentation

This document provides comprehensive documentation for all API endpoints in the GrapheneOS Installer backend.

## Base URLs

- **Local Development**: `http://127.0.0.1:17890`
- **API v1 Prefix**: `/api/v1`
- **Legacy Routes**: Direct paths (no prefix)

---

## Authentication Endpoints

All authentication endpoints are under `/api/v1/auth/`.

### POST `/api/v1/auth/register`

Register a new user account.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "full_name": "John Doe",
  "device_id": "optional-device-id"
}
```

**Response** (201 Created):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 1800,
  "device_id": "device-123"
}
```

**Features**:
- Rate limited (5 registrations/hour per IP)
- Password hashed with Argon2
- Automatic token generation
- Audit logged

---

### POST `/api/v1/auth/login`

Login with email and password.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "device_id": "optional-device-id"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 1800,
  "device_id": "device-123"
}
```

**Features**:
- Brute-force protection (5 attempts, 1hr lockout)
- Device binding support
- Token rotation on refresh
- Audit logged

---

### POST `/api/v1/auth/refresh`

Refresh access token using refresh token.

**Request Body**:
```json
{
  "refresh_token": "eyJ..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 1800,
  "device_id": "device-123"
}
```

**Features**:
- Token rotation (new refresh token issued)
- Old refresh token revoked
- Expiration checking
- Audit logged

---

### POST `/api/v1/auth/logout`

Logout and revoke tokens.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (204 No Content)

**Features**:
- Access and refresh tokens revoked
- Redis-based revocation
- Audit logged

---

## Email Service Endpoints

All email endpoints are under `/api/v1/email/`.

### POST `/api/v1/email/send`

Send encrypted email.

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Form Data**:
- `body` (string, required): Email body content
- `subject` (string, optional): Email subject
- `to` (array, required): List of recipient email addresses
- `passcode` (string, optional): Passcode for encryption (if provided, email is passcode-protected)
- `expires_in_hours` (integer, optional): Hours until email expires
- `self_destruct` (boolean, optional): If true, email is deleted after first view

**Response** (201 Created):
```json
{
  "email_id": "token-123",
  "email_address": "token-123@fxmail.ai",
  "secure_link": "https://fxmail.ai/email/token-123",
  "expires_at": "2024-12-31T23:59:59Z",
  "encryption_mode": "authenticated" | "passcode"
}
```

**Features**:
- End-to-end encryption (AES-256-GCM)
- Two-layer encryption (content key + user/passcode key)
- Rate limited (50 emails/hour per user)
- Auto-wipe scheduling if expiration set
- Audit logged
- Gmail/external services never see plaintext

---

### GET `/api/v1/email/{email_id}`

Get encrypted email (for authenticated users).

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "email_id": "token-123",
  "subject": "Subject",
  "body": "Decrypted email body",
  "encryption_mode": "authenticated",
  "is_passcode_protected": false,
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Features**:
- Auto-decryption for authenticated users (if no passcode)
- View-once enforcement for self-destruct emails
- Ownership validation
- Auto-deletion after view if self-destruct enabled
- Audit logged

---

### POST `/api/v1/email/{email_id}/unlock`

Unlock passcode-protected email.

**Request Body**:
```json
{
  "passcode": "user-passcode"
}
```

**Response** (200 OK):
```json
{
  "email_id": "token-123",
  "subject": "Subject",
  "body": "Decrypted email body",
  "self_destruct": true
}
```

**Features**:
- Rate limited (5 attempts/hour per email)
- Brute-force protection
- Passcode verification
- View-once enforcement for self-destruct
- Audit logged

---

### DELETE `/api/v1/email/{email_id}`

Delete email.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (204 No Content)

**Features**:
- Ownership validation
- Complete data deletion (Redis keys)
- Audit logged

---

## Drive Service Endpoints

All drive endpoints are under `/api/v1/drive/`.

### POST `/api/v1/drive/upload`

Upload encrypted file.

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Form Data**:
- `file` (file, required): File to upload (max 100MB)
- `passcode` (string, optional): Passcode for encryption
- `expires_in_hours` (integer, optional): Hours until file expires (1-8760)

**Response** (201 Created):
```json
{
  "file_id": "file-123",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Features**:
- End-to-end encryption (AES-256-GCM)
- Streaming support for large files
- Session key generation for device access
- Auto-wipe scheduling if expiration set
- Rate limited
- Audit logged

---

### GET `/api/v1/drive/file/{file_id}`

Get file metadata and signed download URL.

**Headers** (optional):
```
Authorization: Bearer <access_token>
```

**Query Parameters**:
- `signed_url_expires_minutes` (integer, optional): Minutes until signed URL expires (default: 60)

**Response** (200 OK):
```json
{
  "file_id": "file-123",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "owner_email": "user@example.com",
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-01-01T00:00:00Z",
  "signed_url": "/api/v1/drive/file/file-123/download?token=...",
  "signed_url_expires_at": "2024-01-01T01:00:00Z"
}
```

**Features**:
- Ownership validation
- Time-limited signed URLs
- Access control

---

### GET `/api/v1/drive/file/{file_id}/download`

Download file (requires signed URL token or authentication).

**Query Parameters**:
- `token` (string, optional): Signed URL token

**Headers** (optional, if no token):
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
- Content-Type: File's original content type
- Content-Disposition: attachment; filename="..."
- Body: Decrypted file content (streaming)

**Features**:
- Signed URL verification
- Authentication fallback
- Streaming download for large files
- Client-side decryption option
- Audit logged

---

### POST `/api/v1/drive/file/{file_id}/unlock`

Unlock passcode-protected file.

**Request Body**:
```json
{
  "passcode": "user-passcode"
}
```

**Query Parameters**:
- `signed_url_expires_minutes` (integer, optional): Minutes until signed URL expires

**Response** (200 OK):
```json
{
  "file_id": "file-123",
  "signed_url": "/api/v1/drive/file/file-123/download?token=...",
  "signed_url_expires_at": "2024-01-01T01:00:00Z",
  "session_key": "base64-encoded-session-key"
}
```

**Features**:
- Rate limited (5 attempts/hour per file)
- Brute-force protection
- Session key generation for device access
- Passcode verification
- Audit logged

---

### DELETE `/api/v1/drive/file/{file_id}`

Delete file.

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (204 No Content)

**Features**:
- Ownership validation
- Complete data deletion
- Audit logged

---

## Public Viewer Endpoints

Public endpoints for viewing encrypted content without authentication.

### GET `/api/v1/public/view/{token}`

Get HTML viewer page for encrypted content.

**Response** (200 OK):
- Content-Type: text/html
- Body: HTML page with JavaScript for client-side decryption

**Features**:
- Client-side decryption using WebCrypto API
- Passcode prompt UI
- Biometric authentication support (WebAuthn)
- No server-side plaintext rendering
- Rate limiting

---

### POST `/api/v1/public/unlock/{token}`

Unlock content with passcode (returns encrypted data for client-side decryption).

**Request Body**:
```json
{
  "passcode": "user-passcode"
}
```

**Response** (200 OK):
```json
{
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
  "session_key": "base64-encoded-session-key"
}
```

**Features**:
- Rate limited (5 attempts/hour)
- Returns encrypted payload only (no plaintext)
- Session key for device storage
- Client-side decryption required

---

### GET `/api/v1/public/data/{token}`

Get encrypted data for client-side decryption.

**Response** (200 OK):
```json
{
  "encrypted_content": {...},
  "encrypted_content_key": {...}
}
```

**Features**:
- No authentication required
- Returns encrypted payload only

---

### GET `/api/v1/public/session/{token}`

Get stored session key (for biometric access).

**Response** (200 OK):
```json
{
  "session_key": "base64-encoded-session-key"
}
```

**Features**:
- Enables biometric authentication on devices
- Key stored securely in Redis

---

## GrapheneOS Download Endpoints

Build download endpoints under `/api/v1/download/`.

### GET `/api/v1/download/check/{codename}`

Check if build is available for download.

**Response** (200 OK):
```json
{
  "available": true,
  "has_bundle": false,
  "latest_version": "2025122500",
  "bundle_path": null,
  "message": "Latest version 2025122500 available for download"
}
```

**Use Case**: Called when frontend app loads to show/hide download button.

---

### POST `/api/v1/download/start`

Start downloading a GrapheneOS build.

**Request Body**:
```json
{
  "codename": "panther",
  "version": null  // null = auto-find latest
}
```

**Response** (200 OK):
```json
{
  "download_id": "panther-2025122500",
  "status": "started",
  "message": "Download started for panther 2025122500",
  "codename": "panther",
  "version": "2025122500"
}
```

**Features**:
- Background download with progress tracking
- SHA256 verification
- Automatic extraction
- Progress polling via status endpoint

---

### GET `/api/v1/download/status/{download_id}`

Get download progress.

**Response** (200 OK):
```json
{
  "status": "downloading",
  "progress": 45.5,
  "downloaded": 45678901,
  "total": 100000000,
  "error": null,
  "bundle_path": null
}
```

**Status Values**:
- `downloading`: Download in progress
- `completed`: Download finished successfully
- `error`: Download failed

---

## GrapheneOS Device Management (Legacy Routes)

### GET `/devices/`

List all connected devices.

**Response** (200 OK):
```json
[
  {
    "serial": "35201FDH2000G6",
    "state": "fastboot",
    "codename": "panther",
    "model": "Pixel 7"
  }
]
```

---

### GET `/devices/{device_id}/identify`

Identify device codename.

**Response** (200 OK):
```json
{
  "codename": "panther",
  "model": "Pixel 7",
  "manufacturer": "Google"
}
```

---

### POST `/devices/{device_id}/reboot/bootloader`

Reboot device to bootloader mode.

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Device rebooting to bootloader"
}
```

---

## GrapheneOS Bundle Management (Legacy Routes)

### GET `/bundles/for/{codename}`

Get latest bundle for device codename.

**Response** (200 OK):
```json
{
  "codename": "panther",
  "version": "2025122500",
  "deviceName": "Pixel 7",
  "path": "/path/to/bundle"
}
```

---

### POST `/bundles/index`

Index all available bundles.

**Response** (200 OK):
```json
{
  "panther": [
    {
      "codename": "panther",
      "version": "2025122500",
      "path": "/path/to/bundle"
    }
  ]
}
```

---

### POST `/bundles/download`

Start bundle download (legacy endpoint).

**Request Body**:
```json
{
  "codename": "panther",
  "version": "2025122500"
}
```

**Response** (200 OK):
```json
{
  "download_id": "panther-2025122500",
  "status": "started"
}
```

---

### GET `/bundles/download/{download_id}/status`

Get download status (legacy endpoint).

**Response**: Same as `/api/v1/download/status/{download_id}`

---

## GrapheneOS Flash Endpoints (Legacy Routes)

### POST `/flash/unlock-and-flash`

Unlock bootloader and flash GrapheneOS.

**Request Body**:
```json
{
  "device_serial": "35201FDH2000G6",
  "bundle_path": null,  // null = auto-detect
  "skip_unlock": false  // true = skip unlock (bootloader already unlocked)
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "job_id": "job-123",
  "message": "Unlock and flash process started"
}
```

**Features**:
- Uses `flasher.py` script
- Real-time log streaming via SSE
- Progress tracking
- Job management

---

### GET `/flash/jobs/{job_id}`

Get flash job status and logs.

**Response** (200 OK):
```json
{
  "id": "job-123",
  "status": "running",
  "logs": ["log line 1", "log line 2"],
  "device_serial": "35201FDH2000G6",
  "bundle_path": "/path/to/bundle"
}
```

---

### GET `/flash/jobs/{job_id}/stream`

Stream flash job logs (Server-Sent Events).

**Response**: SSE stream with log events

---

### POST `/flash/jobs/{job_id}/cancel`

Cancel flash job.

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Job cancelled"
}
```

---

## Health & Tools

### GET `/health`

Health check endpoint.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "GrapheneOS Installer API"
}
```

---

### GET `/tools/check`

Check ADB and Fastboot availability.

**Response** (200 OK):
```json
{
  "adb": {
    "available": true,
    "path": "/usr/local/bin/adb"
  },
  "fastboot": {
    "available": true,
    "path": "/usr/local/bin/fastboot"
  }
}
```

---

## Authentication

Most endpoints require authentication via JWT Bearer token:

```
Authorization: Bearer <access_token>
```

**Getting an Access Token**:
1. Register: `POST /api/v1/auth/register`
2. Login: `POST /api/v1/auth/login`
3. Use the `access_token` from response

**Token Refresh**:
- Access tokens expire (default: 30 minutes)
- Use `refresh_token` to get new access token: `POST /api/v1/auth/refresh`

---

## Rate Limiting

- **Global**: 100 requests/hour per IP
- **Registration**: 5 requests/hour per IP
- **Login**: 5 failed attempts → 1 hour lockout
- **Email Send**: 50 emails/hour per user
- **Unlock**: 5 attempts/hour per content
- **Drive Upload**: Rate limited per user

Rate limit headers in responses:
- `X-RateLimit-Limit`: Maximum requests
- `X-RateLimit-Window`: Time window in seconds
- `Retry-After`: Seconds until retry (when exceeded)

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "message": "Additional details"
}
```

**Common Status Codes**:
- `200 OK`: Success
- `201 Created`: Resource created
- `204 No Content`: Success (no body)
- `400 Bad Request`: Invalid request
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Security Features

1. **Encryption**: All sensitive data encrypted (AES-256-GCM)
2. **Rate Limiting**: Redis-based per IP/user
3. **Brute-Force Protection**: Automatic lockout after failed attempts
4. **Audit Logging**: All security events logged (90-day retention)
5. **Token Expiration**: Automatic token invalidation
6. **View-Once**: One-time viewing for sensitive content
7. **Auto-Wipe**: Automatic deletion after expiration
8. **Sensitive Data Sanitization**: Logs never contain passwords/tokens

---

## Testing APIs

### Using cURL

```bash
# Register user
curl -X POST http://127.0.0.1:17890/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Login
curl -X POST http://127.0.0.1:17890/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Send email (with token)
curl -X POST http://127.0.0.1:17890/api/v1/email/send \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"body":"Hello","to":["recipient@example.com"]}'
```

### Using Swagger UI

Visit `http://127.0.0.1:17890/docs` for interactive API documentation.

---

## Complete Endpoint List

### Authentication (`/api/v1/auth/`)
- `POST /register` - Register user
- `POST /login` - Login
- `POST /refresh` - Refresh token
- `POST /logout` - Logout

### Email (`/api/v1/email/`)
- `POST /send` - Send encrypted email
- `GET /{email_id}` - Get email (authenticated)
- `POST /{email_id}/unlock` - Unlock passcode-protected email
- `DELETE /{email_id}` - Delete email

### Drive (`/api/v1/drive/`)
- `POST /upload` - Upload file
- `GET /file/{file_id}` - Get file info
- `GET /file/{file_id}/download` - Download file
- `POST /file/{file_id}/unlock` - Unlock passcode-protected file
- `DELETE /file/{file_id}` - Delete file

### Public Viewer (`/api/v1/public/`)
- `GET /view/{token}` - HTML viewer
- `POST /unlock/{token}` - Unlock with passcode
- `GET /data/{token}` - Get encrypted data
- `GET /session/{token}` - Get session key

### Download (`/api/v1/download/`)
- `GET /check/{codename}` - Check build availability
- `POST /start` - Start download
- `GET /status/{download_id}` - Get download progress

### Devices (`/devices/`)
- `GET /` - List devices
- `GET /{device_id}/identify` - Identify device
- `POST /{device_id}/reboot/bootloader` - Reboot to bootloader

### Bundles (`/bundles/`)
- `POST /index` - Index bundles
- `GET /for/{codename}` - Get bundle for codename
- `POST /verify` - Verify bundle
- `GET /releases/{codename}` - Get releases
- `GET /find-latest/{codename}` - Find latest version
- `POST /download` - Download bundle
- `GET /download/{download_id}/status` - Get download status

### Flash (`/flash/`)
- `POST /execute` - Execute flash
- `POST /unlock-and-flash` - Unlock and flash
- `GET /jobs` - List jobs
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs/{job_id}/stream` - Stream job logs
- `POST /jobs/{job_id}/cancel` - Cancel job

### Health & Tools
- `GET /health` - Health check
- `GET /tools/check` - Check tools
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc UI

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- File sizes are in bytes
- Time durations are in seconds unless specified
- All sensitive data is encrypted at rest (Redis) and in transit (HTTPS)
- Rate limits are per identifier (IP or user email)
- Audit logs retained for 90 days



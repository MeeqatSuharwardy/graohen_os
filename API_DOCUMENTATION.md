# FlashDash API Documentation

Complete API reference for FlashDash platform including GrapheneOS flashing, encrypted email, and secure drive services.

## Base URLs

- **Development**: `http://localhost:8000`
- **Production Backend**: `https://backend.fxmail.ai`
- **Production Email**: `https://fxmail.ai`
- **Production Drive**: `https://drive.fxmail.ai`

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Getting an Access Token

1. **Register** a new user account
2. **Login** to get access and refresh tokens
3. **Use** the access token for authenticated requests
4. **Refresh** the token when it expires

---

## Authentication Endpoints

### Register User

Create a new user account with email and password.

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "howie@fxmail.ai",
  "password": "secure-password-123",
  "full_name": "Howie User",
  "device_id": "optional-device-id"
}
```

**Response** (201 Created):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-id-here"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid email format or weak password
- `409 Conflict`: Email already registered

---

### Login

Authenticate and get access tokens.

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "email": "howie@fxmail.ai",
  "password": "secure-password-123",
  "device_id": "optional-device-id"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "device_id": "device-id-here"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid credentials

---

### Refresh Token

Get a new access token using refresh token.

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "device_id": "optional-device-id"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### Logout

Revoke tokens and logout.

**Endpoint**: `POST /api/v1/auth/logout`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "refresh_token": "optional-refresh-token",
  "all_devices": false
}
```

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

## Email Service Endpoints

### Send Encrypted Email

Create and send an encrypted email. Returns a secure link for recipients.

**Endpoint**: `POST /api/v1/email/send`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "to": ["recipient@example.com"],
  "subject": "Encrypted Message",
  "body": "This is the encrypted email content.",
  "passcode": "optional-passcode",
  "expires_in_hours": 168,
  "self_destruct": false
}
```

**Response** (201 Created):
```json
{
  "email_id": "abc123xyz",
  "email_address": "abc123xyz@fxmail.ai",
  "secure_link": "https://fxmail.ai/email/abc123xyz",
  "expires_at": "2025-01-23T12:00:00Z",
  "encryption_mode": "authenticated"
}
```

**Field Descriptions**:
- `to`: List of recipient email addresses (required)
- `subject`: Email subject (optional, max 500 chars)
- `body`: Email body content (required)
- `passcode`: Optional passcode for additional protection (4-128 chars)
- `expires_in_hours`: Expiration time in hours (1-8760, optional)
- `self_destruct`: Delete email after first read (default: false)

**Encryption Modes**:
- `authenticated`: Auto-decrypt for authenticated users
- `passcode_protected`: Requires passcode to unlock

---

### Get Email (Authenticated)

Retrieve email content for authenticated users.

**Endpoint**: `GET /api/v1/email/{email_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "email_id": "abc123xyz",
  "subject": "Encrypted Message",
  "body": "This is the decrypted email content.",
  "encryption_mode": "authenticated",
  "expires_at": "2025-01-23T12:00:00Z",
  "is_passcode_protected": false
}
```

**Error Responses**:
- `404 Not Found`: Email not found or expired
- `401 Unauthorized`: Invalid or missing token

---

### Unlock Email (Passcode Protected)

Unlock a passcode-protected email.

**Endpoint**: `POST /api/v1/email/{email_id}/unlock`

**Request Body**:
```json
{
  "passcode": "your-passcode"
}
```

**Response** (200 OK):
```json
{
  "email_id": "abc123xyz",
  "subject": "Encrypted Message",
  "body": "This is the decrypted email content.",
  "unlocked_at": "2025-01-16T12:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid passcode
- `404 Not Found`: Email not found or expired
- `429 Too Many Requests`: Too many unlock attempts (rate limited)

**Rate Limiting**: Maximum 5 unlock attempts per hour. After 5 failed attempts, account is locked for 1 hour.

---

### Delete Email

Delete an email (owner only).

**Endpoint**: `DELETE /api/v1/email/{email_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "email_id": "abc123xyz",
  "deleted": true,
  "message": "Email deleted successfully"
}
```

---

## Drive Service Endpoints

### Upload File

Upload and encrypt a file.

**Endpoint**: `POST /api/v1/drive/upload`

**Headers**: `Authorization: Bearer <access_token>`

**Request**: `multipart/form-data`
- `file`: File to upload (required)
- `passcode`: Optional passcode for protection (optional)
- `expires_in_hours`: Expiration time in hours (1-8760, optional)

**Response** (201 Created):
```json
{
  "file_id": "xyz789abc",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "expires_at": "2025-01-23T12:00:00Z",
  "created_at": "2025-01-16T12:00:00Z"
}
```

**File Size Limit**: Maximum 500MB per file

---

### Get File Info

Get file information and signed download URL.

**Endpoint**: `GET /api/v1/drive/file/{file_id}`

**Headers**: `Authorization: Bearer <access_token>` (optional for public files)

**Query Parameters**:
- `signed_url_expires_minutes`: Expiration time for signed URL (default: 60)

**Response** (200 OK):
```json
{
  "file_id": "xyz789abc",
  "filename": "document.pdf",
  "size": 1048576,
  "content_type": "application/pdf",
  "passcode_protected": false,
  "owner_email": "howie@fxmail.ai",
  "expires_at": "2025-01-23T12:00:00Z",
  "created_at": "2025-01-16T12:00:00Z",
  "signed_url": "https://drive.fxmail.ai/api/v1/drive/download/xyz789abc?token=...",
  "signed_url_expires_at": "2025-01-16T13:00:00Z"
}
```

---

### Download File

Download a file using signed URL or authentication.

**Endpoint**: `GET /api/v1/drive/download/{file_id}`

**Query Parameters**:
- `token`: Signed URL token (for public access)

**Headers**: `Authorization: Bearer <access_token>` (for authenticated access)

**Response** (200 OK):
- File stream with appropriate `Content-Type` header

**Error Responses**:
- `404 Not Found`: File not found or expired
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Invalid token or insufficient permissions

---

### Unlock File (Passcode Protected)

Unlock a passcode-protected file and get signed download URL.

**Endpoint**: `POST /api/v1/drive/file/{file_id}/unlock`

**Request Body**:
```json
{
  "passcode": "your-passcode"
}
```

**Response** (200 OK):
```json
{
  "file_id": "xyz789abc",
  "signed_url": "https://drive.fxmail.ai/api/v1/drive/download/xyz789abc?token=...",
  "signed_url_expires_at": "2025-01-16T13:00:00Z",
  "unlocked_at": "2025-01-16T12:00:00Z"
}
```

**Rate Limiting**: Maximum 5 unlock attempts per hour.

---

### Delete File

Delete a file (owner only).

**Endpoint**: `DELETE /api/v1/drive/file/{file_id}`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "file_id": "xyz789abc",
  "deleted": true,
  "message": "File deleted successfully"
}
```

---

## GrapheneOS Flashing Endpoints

### Health Check

Check API health status.

**Endpoint**: `GET /health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "GrapheneOS Installer API"
}
```

---

### Check Tools

Check if ADB and Fastboot are available.

**Endpoint**: `GET /tools/check`

**Response** (200 OK):
```json
{
  "adb": {
    "available": true,
    "path": "/usr/bin/adb"
  },
  "fastboot": {
    "available": true,
    "path": "/usr/bin/fastboot"
  }
}
```

---

### List Devices

List all connected devices (ADB and Fastboot).

**Endpoint**: `GET /devices`

**Response** (200 OK):
```json
[
  {
    "serial": "ABC123XYZ",
    "state": "device",
    "codename": "panther",
    "device_name": "Pixel 7"
  }
]
```

---

### Get Device Info

Identify a device's codename and name.

**Endpoint**: `GET /devices/{device_id}/identify`

**Response** (200 OK):
```json
{
  "codename": "panther",
  "device_name": "Pixel 7"
}
```

---

### Reboot to Bootloader

Reboot device to bootloader mode.

**Endpoint**: `POST /devices/{device_id}/reboot/bootloader`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Device rebooting to bootloader"
}
```

---

### List Bundles

Get available bundles for a device codename.

**Endpoint**: `GET /bundles/for/{codename}`

**Response** (200 OK):
```json
{
  "codename": "panther",
  "version": "2025122500",
  "path": "/app/bundles/panther/2025122500"
}
```

---

### Execute Flash

Start a flash operation.

**Endpoint**: `POST /flash/execute`

**Request Body**:
```json
{
  "device_serial": "ABC123XYZ",
  "bundle_path": "/app/bundles/panther/2025122500",
  "dry_run": false,
  "confirmation_token": "optional-token"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "job_id": "uuid-here",
  "message": "Flash job started"
}
```

---

### Get Flash Job Status

Get flash job status and logs.

**Endpoint**: `GET /flash/jobs/{job_id}`

**Response** (200 OK):
```json
{
  "id": "job-id",
  "device_serial": "ABC123XYZ",
  "status": "running",
  "dry_run": false,
  "log_count": 150,
  "logs": [
    "[INIT] Starting flash process...",
    "[ADB] Device detected",
    "[FASTBOOT] Flashing bootloader..."
  ]
}
```

---

### Stream Flash Job Logs

Stream flash job logs via Server-Sent Events (SSE).

**Endpoint**: `GET /flash/jobs/{job_id}/stream`

**Response**: SSE stream with events:
- `log`: New log line
- `status`: Status update
- `heartbeat`: Keep-alive
- `close`: Stream ended

**Example**:
```javascript
const eventSource = new EventSource('/flash/jobs/job-id/stream');

eventSource.addEventListener('log', (event) => {
  const data = JSON.parse(event.data);
  console.log(data.line);
});

eventSource.addEventListener('status', (event) => {
  const data = JSON.parse(event.data);
  console.log('Status:', data.status);
});
```

---

### Cancel Flash Job

Cancel a running flash job.

**Endpoint**: `POST /flash/jobs/{job_id}/cancel`

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Job cancelled"
}
```

---

## APK Management Endpoints

### List APKs

List all uploaded APK files.

**Endpoint**: `GET /apks/list`

**Response** (200 OK):
```json
[
  {
    "filename": "app.apk",
    "size": 1048576,
    "upload_time": "2025-01-16T12:00:00Z"
  }
]
```

---

### Upload APK

Upload an APK file (HTTP Basic Auth required).

**Endpoint**: `POST /apks/upload`

**Authentication**: HTTP Basic
- Username: `admin`
- Password: `AllHailToEagle`

**Request**: `multipart/form-data`
- `file`: APK file

**Response**: HTML page with success message

---

### Install APK

Install APK on connected device.

**Endpoint**: `POST /apks/install`

**Request Body**:
```json
{
  "device_serial": "ABC123XYZ",
  "apk_filename": "app.apk"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "APK app.apk installed successfully",
  "device_serial": "ABC123XYZ"
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message here"
}
```

### Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or invalid
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `413 Payload Too Large`: File too large
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Some endpoints have rate limiting:

- **Email Unlock**: 5 attempts per hour
- **Drive Unlock**: 5 attempts per hour
- **Authentication**: Configurable per endpoint

Rate limit headers:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1642248000
```

---

## CORS

CORS is configured to allow requests from:
- `https://frontend.fxmail.ai`
- `https://backend.fxmail.ai`
- `https://fxmail.ai`
- `https://drive.fxmail.ai`
- `http://localhost:*` (development)

---

## WebSocket / SSE

Some endpoints use Server-Sent Events (SSE) for real-time updates:

- `/flash/jobs/{job_id}/stream`: Flash job logs
- `/build/jobs/{build_job_id}/stream`: Build job logs

---

## Examples

### Complete Email Flow

```bash
# 1. Register user
curl -X POST https://backend.fxmail.ai/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "howie@fxmail.ai",
    "password": "secure123456"
  }'

# 2. Login
curl -X POST https://backend.fxmail.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "howie@fxmail.ai",
    "password": "secure123456"
  }'

# 3. Send encrypted email
curl -X POST https://fxmail.ai/api/v1/email/send \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Hello",
    "body": "This is encrypted!",
    "passcode": "secret123"
  }'

# 4. Unlock email (recipient)
curl -X POST https://fxmail.ai/api/v1/email/{email_id}/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "secret123"
  }'
```

### Complete Drive Flow

```bash
# 1. Upload file
curl -X POST https://drive.fxmail.ai/api/v1/drive/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf" \
  -F "passcode=secret123" \
  -F "expires_in_hours=168"

# 2. Get file info
curl -X GET https://drive.fxmail.ai/api/v1/drive/file/{file_id} \
  -H "Authorization: Bearer <access_token>"

# 3. Unlock file (if passcode protected)
curl -X POST https://drive.fxmail.ai/api/v1/drive/file/{file_id}/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "secret123"
  }'

# 4. Download file
curl -X GET "https://drive.fxmail.ai/api/v1/drive/download/{file_id}?token=<signed_token>" \
  -o downloaded_file.pdf
```

---

## Version

Current API version: `1.0.0`

For the latest API documentation, visit `/docs` (Swagger UI) when `DEBUG=true`.

---

**Last Updated**: January 2025
**Version**: 1.0.0

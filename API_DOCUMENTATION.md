# FlashDash API Documentation

Complete API reference for FlashDash platform including GrapheneOS flashing, encrypted email, and secure drive services.

## Base URLs

- **Development**: `http://localhost:8000`
- **Production Backend**: `https://freedomos.vulcantech.co`
- **Production Email**: `https://vulcantech.tech`
- **Production Drive**: `https://freedomos.vulcantech.co`

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
  "email": "howie@vulcantech.tech",
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
  "email": "howie@vulcantech.tech",
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
  "email_address": "abc123xyz@vulcantech.tech",
  "secure_link": "https://vulcantech.tech/email/abc123xyz",
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
  "owner_email": "howie@vulcantech.tech",
  "expires_at": "2025-01-23T12:00:00Z",
  "created_at": "2025-01-16T12:00:00Z",
  "signed_url": "https://freedomos.vulcantech.co/api/v1/drive/download/xyz789abc?token=...",
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
  "signed_url": "https://freedomos.vulcantech.co/api/v1/drive/download/xyz789abc?token=...",
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

List all connected devices (ADB and Fastboot). Can also register devices from frontend.

**Endpoint**: `GET /devices` or `POST /devices`

**GET Request**: List devices detected by backend

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

**POST Request**: Register devices detected by frontend (WebADB)

**Request Body**:
```json
{
  "devices": [
    {
      "serial": "ABC123XYZ",
      "state": "device",
      "codename": "panther",
      "device_name": "Pixel 7",
      "manufacturer": "Google",
      "model": "Pixel 7",
      "bootloader_unlocked": false
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Registered 1 device(s)",
  "devices": [
    {
      "serial": "ABC123XYZ",
      "state": "device",
      "codename": "panther",
      "device_name": "Pixel 7",
      "manufacturer": "Google",
      "model": "Pixel 7",
      "bootloader_unlocked": false
    }
  ]
}
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
  "path": "/root/graohen_os/bundles/panther/2025122500",
  "deviceName": "Pixel 7",
  "downloadUrl": "https://releases.grapheneos.org/panther-factory-2025122500.zip",
  "metadata": {
    "codename": "panther",
    "version": "2025122500",
    "files": {
      "imageZip": "image.zip",
      "sha256": "image.zip.sha256",
      "sig": "image.zip.sig",
      "flashSh": "flash-all.sh",
      "flashBat": "flash-all.bat"
    }
  }
}
```

---

### Index All Bundles

Get all available bundles indexed by codename.

**Endpoint**: `POST /bundles/index`

**Response** (200 OK):
```json
{
  "panther": [
    {
      "codename": "panther",
      "version": "2025122500",
      "path": "/root/graohen_os/bundles/panther/2025122500",
      ...
    }
  ]
}
```

---

### Download Bundle ZIP

Download the complete bundle ZIP file from the bundles folder.

**Endpoint**: `GET /bundles/releases/{codename}/{version}/download`

**Parameters**:
- `codename` (path): Device codename (e.g., `panther`)
- `version` (path): Bundle version (e.g., `2025122500`)

**Response**: 
- Returns the ZIP file as a download
- Content-Type: `application/zip`
- Filename: `{codename}-factory-{version}.zip`

**Example**:
```bash
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download
```

**File Lookup Order**:
1. `bundles/{codename}/{version}/image.zip`
2. `bundles/{codename}/{version}/{codename}-factory-{version}.zip`
3. Bundle path itself if it's a ZIP file

---

### Download Specific File from Bundle

Download a specific file from a bundle (e.g., `boot.img`, `system.img`, `flash-all.sh`).

**Endpoint**: `GET /bundles/releases/{codename}/{version}/file/{filename}`

**Parameters**:
- `codename` (path): Device codename
- `version` (path): Bundle version
- `filename` (path): Name of the file to download

**Response**:
- Returns the file as a download
- Content-Type determined by file extension

**Example**:
```bash
# Download boot.img
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/panther-install-2025122500/boot.img

# Download flash-all.sh
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/flash-all.sh
```

**Security**:
- Prevents directory traversal (`..`, `/`, `\` are blocked)
- Ensures file is within bundle directory

---

### List Files in Bundle

List all files available in a bundle directory.

**Endpoint**: `GET /bundles/releases/{codename}/{version}/list`

**Parameters**:
- `codename` (path): Device codename
- `version` (path): Bundle version

**Response** (200 OK):
```json
{
  "codename": "panther",
  "version": "2025122500",
  "bundle_path": "/root/graohen_os/bundles/panther/2025122500",
  "files": [
    {
      "name": "image.zip",
      "size": 2147483648,
      "path": "/bundles/releases/panther/2025122500/file/image.zip"
    },
    {
      "name": "flash-all.sh",
      "size": 2048,
      "path": "/bundles/releases/panther/2025122500/file/flash-all.sh"
    },
    {
      "name": "panther-install-2025122500/boot.img",
      "size": 67108864,
      "path": "/bundles/releases/panther/2025122500/file/panther-install-2025122500/boot.img"
    }
  ],
  "total_files": 30
}
```

**Features**:
- Lists all files in bundle directory (recursive)
- Includes subdirectories
- Provides download paths for each file
- Shows file sizes

---

### Download Bundle from GrapheneOS (External)

Download a bundle from GrapheneOS releases (external download).

**Endpoint**: `POST /bundles/download`

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
  "status": "started",
  "message": "Download started"
}
```

**Status Check**: `GET /bundles/download/{download_id}/status`

**Response** (200 OK):
```json
{
  "status": "downloading",
  "progress": 45.5,
  "downloaded": 977272832,
  "total": 2147483648,
  "error": null
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
  "bundle_path": "/root/graohen_os/bundles/panther/2025122500",
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

### Device Flash (Frontend-Initiated)

Start flash process from frontend-detected device. Frontend sends device info (detected via WebADB) and backend starts flashing automatically.

**Endpoint**: `POST /flash/device-flash`

**Request Body**:
```json
{
  "serial": "ABC123XYZ",
  "codename": "panther",
  "state": "fastboot",
  "bootloader_unlocked": false,
  "version": "2025122500",
  "skip_unlock": null
}
```

**Field Descriptions**:
- `serial` (required): Device serial number
- `codename` (required): Device codename (e.g., `panther`)
- `state` (required): Device state (`device` or `fastboot`)
- `bootloader_unlocked` (optional): Bootloader unlock status (auto-determines `skip_unlock`)
- `version` (optional): Bundle version (defaults to latest)
- `skip_unlock` (optional): Skip bootloader unlock (auto-determined from `bootloader_unlocked` if not provided)

**Response** (200 OK):
```json
{
  "success": true,
  "job_id": "uuid-here",
  "message": "Unlock and flash process started"
}
```

**Process**:
1. Finds bundle for codename (and version if provided)
2. Determines `skip_unlock` from `bootloader_unlocked` flag
3. Starts flash job in background
4. Returns `job_id` for status tracking

---

### Unlock and Flash

Unlock bootloader and flash GrapheneOS in one operation. Enhanced to accept device info from frontend.

**Endpoint**: `POST /flash/unlock-and-flash`

**Request Body**:
```json
{
  "device_serial": "ABC123XYZ",
  "bundle_path": "/root/graohen_os/bundles/panther/2025122500",
  "skip_unlock": false,
  "codename": "panther",
  "bootloader_unlocked": false
}
```

**Field Descriptions**:
- `device_serial` (required): Device serial number
- `bundle_path` (optional): Path to bundle (auto-detected if not provided)
- `skip_unlock` (optional): Skip bootloader unlock (auto-determined from `bootloader_unlocked` if not provided)
- `codename` (optional): Device codename from frontend (skips device identification if provided)
- `bootloader_unlocked` (optional): Bootloader state from frontend (auto-determines `skip_unlock`)

**Response** (200 OK):
```json
{
  "success": true,
  "job_id": "uuid-here",
  "message": "Unlock and flash process started"
}
```

**Process**:
1. Uses codename from request if provided (skips device identification)
2. Uses bootloader_unlocked flag to determine skip_unlock
3. Finds bundle for codename
4. Starts flash job in background
5. Returns `job_id` for status tracking

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

### Download APK

Download an APK file from the server.

**Endpoint**: `GET /apks/download/{filename}`

**Path Parameters**:
- `filename`: Name of the APK file to download (must end with `.apk`)

**Example**:
```
GET /apks/download/my-app.apk
```

**Response** (200 OK):
- Content-Type: `application/vnd.android.package-archive`
- File download with the APK file

**Error Responses**:
- `400 Bad Request`: Invalid filename (contains `..`, `/`, `\`, or doesn't end with `.apk`)
- `404 Not Found`: APK file not found
- `500 Internal Server Error`: Server error during download

**Security**:
- Filename validation prevents directory traversal attacks
- Only files with `.apk` extension can be downloaded
- File must exist in the APK storage directory

**Example Usage**:
```bash
# Using cURL
curl -O https://freedomos.vulcantech.co/apks/download/my-app.apk

# Using wget
wget https://freedomos.vulcantech.co/apks/download/my-app.apk

# Using browser
# Navigate to: https://freedomos.vulcantech.co/apks/download/my-app.apk
```

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

**Note**: This endpoint requires the device to be connected to the backend server. For Electron app, use local ADB installation instead.

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

CORS is configured to allow requests from all origins (`*`):
- `https://freedomos.vulcantech.co`
- `https://vulcantech.tech`
- `http://localhost:*` (development)
- All other origins (for web flasher compatibility)

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
curl -X POST https://freedomos.vulcantech.co/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "howie@vulcantech.tech",
    "password": "secure123456"
  }'

# 2. Login
curl -X POST https://freedomos.vulcantech.co/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "howie@vulcantech.tech",
    "password": "secure123456"
  }'

# 3. Send encrypted email
curl -X POST https://vulcantech.tech/api/v1/email/send \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Hello",
    "body": "This is encrypted!",
    "passcode": "secret123"
  }'

# 4. Unlock email (recipient)
curl -X POST https://vulcantech.tech/api/v1/email/{email_id}/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "secret123"
  }'
```

### Complete Drive Flow

```bash
# 1. Upload file
curl -X POST https://freedomos.vulcantech.co/api/v1/drive/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf" \
  -F "passcode=secret123" \
  -F "expires_in_hours=168"

# 2. Get file info
curl -X GET https://freedomos.vulcantech.co/api/v1/drive/file/{file_id} \
  -H "Authorization: Bearer <access_token>"

# 3. Unlock file (if passcode protected)
curl -X POST https://freedomos.vulcantech.co/api/v1/drive/file/{file_id}/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "secret123"
  }'

# 4. Download file
curl -X GET "https://freedomos.vulcantech.co/api/v1/drive/download/{file_id}?token=<signed_token>" \
  -o downloaded_file.pdf
```

### Complete Flashing Flow (Frontend-Initiated)

```bash
# 1. Register device from frontend (WebADB detection)
curl -X POST https://freedomos.vulcantech.co/devices \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [{
      "serial": "ABC123XYZ",
      "state": "fastboot",
      "codename": "panther",
      "bootloader_unlocked": false
    }]
  }'

# 2. Start flash from frontend device
curl -X POST https://freedomos.vulcantech.co/flash/device-flash \
  -H "Content-Type: application/json" \
  -d '{
    "serial": "ABC123XYZ",
    "codename": "panther",
    "state": "fastboot",
    "bootloader_unlocked": false,
    "version": "2025122500"
  }'

# 3. Poll flash job status
curl -X GET https://freedomos.vulcantech.co/flash/jobs/{job_id}

# 4. Stream flash logs (SSE)
curl -N https://freedomos.vulcantech.co/flash/jobs/{job_id}/stream
```

### Bundle Download Flow

```bash
# 1. Get bundle info
curl -X GET https://freedomos.vulcantech.co/bundles/for/panther

# 2. List files in bundle
curl -X GET https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/list

# 3. Download complete bundle ZIP
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/download

# 4. Download specific file
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2025122500/file/panther-install-2025122500/boot.img
```

---

## Version

Current API version: `1.0.0`

For the latest API documentation, visit `/docs` (Swagger UI) when `DEBUG=true`.

---

## API Endpoints Summary

### Device Management
- `GET /devices` - List devices (backend detection)
- `POST /devices` - Register devices from frontend (WebADB)
- `GET /devices/{device_id}/identify` - Identify device codename
- `POST /devices/{device_id}/reboot/bootloader` - Reboot to bootloader

### Bundle Management
- `POST /bundles/index` - Index all available bundles
- `GET /bundles/for/{codename}` - Get bundle for codename
- `GET /bundles/releases/{codename}/{version}/download` - Download bundle ZIP
- `GET /bundles/releases/{codename}/{version}/file/{filename}` - Download specific file
- `GET /bundles/releases/{codename}/{version}/list` - List all files in bundle
- `POST /bundles/download` - Download bundle from GrapheneOS (external)
- `GET /bundles/download/{download_id}/status` - Check download status

### Flashing Operations
- `POST /flash/execute` - Execute flash directly
- `POST /flash/device-flash` - Start flash from frontend device (NEW)
- `POST /flash/unlock-and-flash` - Unlock and flash (enhanced with frontend info)
- `GET /flash/jobs/{job_id}` - Get flash job status
- `GET /flash/jobs/{job_id}/stream` - Stream flash logs (SSE)
- `POST /flash/jobs/{job_id}/cancel` - Cancel flash job

### Authentication & Services
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/email/send` - Send encrypted email
- `GET /api/v1/email/{email_id}` - Get email
- `POST /api/v1/email/{email_id}/unlock` - Unlock email
- `POST /api/v1/drive/upload` - Upload file
- `GET /api/v1/drive/file/{file_id}` - Get file info
- `GET /api/v1/drive/download/{file_id}` - Download file

---

**Last Updated**: January 2025
**Version**: 1.0.0

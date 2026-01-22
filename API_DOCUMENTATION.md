# FlashDash API Documentation

Complete API reference for the FlashDash GrapheneOS Installer backend.

## Base URL

- Development: `http://localhost:8000`
- Production: `https://api.flashdash.dev` (or your configured domain)

## Authentication

Most endpoints do not require authentication. Some endpoints (like APK upload) use HTTP Basic Authentication.

## Endpoints

### Health & Status

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "GrapheneOS Installer API"
}
```

#### `GET /tools/check`
Check if ADB and Fastboot tools are available.

**Response:**
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

## Flash

### `POST /flash/execute`
Execute a flash operation directly.

**Request Body:**
```json
{
  "device_serial": "ABC123XYZ",
  "bundle_path": "/path/to/bundle",  // Optional, auto-detected if not provided
  "dry_run": false,
  "confirmation_token": "optional-token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Flash completed successfully"
}
```

### `POST /flash/unlock-and-flash`
Unlock bootloader and flash GrapheneOS in one operation.

**Request Body:**
```json
{
  "device_serial": "ABC123XYZ",
  "bundle_path": "/path/to/bundle",  // Optional
  "skip_unlock": false
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "uuid-here",
  "message": "Unlock and flash process started"
}
```

### `GET /flash/jobs`
List all flash jobs.

**Response:**
```json
{
  "jobs": [
    {
      "id": "job-id",
      "device_serial": "ABC123XYZ",
      "status": "running",
      "dry_run": false
    }
  ]
}
```

### `GET /flash/jobs/{job_id}`
Get flash job status and logs.

**Response:**
```json
{
  "id": "job-id",
  "device_serial": "ABC123XYZ",
  "status": "completed",
  "dry_run": false,
  "log_count": 150,
  "logs": [
    "[INIT] Starting flash process...",
    "[ADB] Device detected",
    "[FASTBOOT] Flashing bootloader..."
  ]
}
```

### `GET /flash/jobs/{job_id}/stream`
Stream flash job logs via Server-Sent Events (SSE).

**Response:** SSE stream with events:
- `log`: New log line
- `status`: Status update
- `heartbeat`: Keep-alive
- `close`: Stream ended

### `POST /flash/jobs/{job_id}/cancel`
Cancel a flash job.

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled"
}
```

---

## Devices

### `GET /devices/`
List all connected devices (ADB and Fastboot).

**Response:**
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

### `GET /devices/{device_id}/identify`
Identify a device's codename and name.

**Response:**
```json
{
  "codename": "panther",
  "device_name": "Pixel 7"
}
```

### `POST /devices/{device_id}/reboot/bootloader`
Reboot device to bootloader mode.

**Response:**
```json
{
  "success": true,
  "message": "Device rebooting to bootloader"
}
```

### `GET /devices/debug/fastboot`
Debug endpoint to check fastboot device detection.

**Response:**
```json
{
  "returncode": 0,
  "stdout": "ABC123XYZ    fastboot",
  "stderr": "",
  "detected_devices": [...]
}
```

---

## Bundles

### `POST /bundles/index`
Index all available bundles.

**Response:**
```json
{
  "panther": {
    "codename": "panther",
    "version": "2025122500",
    "path": "/path/to/bundle"
  }
}
```

### `GET /bundles/for/{codename}`
Get the newest bundle for a codename.

**Response:**
```json
{
  "codename": "panther",
  "version": "2025122500",
  "path": "/path/to/bundle"
}
```

### `POST /bundles/verify`
Verify bundle integrity.

**Request Body:**
```json
{
  "bundle_path": "/path/to/bundle"
}
```

**Response:**
```json
{
  "valid": true,
  "message": "Bundle is valid"
}
```

### `GET /bundles/releases/{codename}`
Get available GrapheneOS releases for a codename.

**Response:**
```json
{
  "codename": "panther",
  "releases": [
    "2025122500",
    "2025122400",
    "2025122300"
  ]
}
```

### `GET /bundles/find-latest/{codename}`
Find the latest available version for a codename.

**Response:**
```json
{
  "codename": "panther",
  "version": "2025122500"
}
```

### `POST /bundles/download`
Download a GrapheneOS factory image bundle.

**Request Body:**
```json
{
  "codename": "panther",
  "version": "2025122500"
}
```

**Response:**
```json
{
  "download_id": "panther-2025122500",
  "status": "started",
  "message": "Download started"
}
```

### `GET /bundles/download/{download_id}/status`
Get download status and progress.

**Response:**
```json
{
  "status": "downloading",
  "progress": 45.5,
  "downloaded": 455000000,
  "total": 1000000000,
  "error": null
}
```

---

## APKs

### `GET /apks/list`
List all uploaded APKs.

**Response:**
```json
[
  {
    "filename": "app.apk",
    "size": 1048576,
    "upload_time": "2025-01-16T12:00:00"
  }
]
```

### `GET /apks/upload`
Get password-protected APK upload form (HTTP Basic Auth required).

**Authentication:** HTTP Basic
- Username: `admin`
- Password: `AllHailToEagle`

### `POST /apks/upload`
Upload an APK file.

**Request:** Multipart form data
- `file`: APK file
- `username`: `admin`
- `password`: `AllHailToEagle`

**Response:** HTML page with success message

### `POST /apks/install`
Install APK on connected device.

**Request Body:**
```json
{
  "device_serial": "ABC123XYZ",
  "apk_filename": "app.apk"
}
```

**Response:**
```json
{
  "success": true,
  "message": "APK app.apk installed successfully",
  "device_serial": "ABC123XYZ"
}
```

### `POST /apks/devices/detect`
API endpoint for electron app to send detected device information.

**Request Body:**
```json
{
  "serial": "ABC123XYZ",
  "state": "device",
  "codename": "panther",
  "device_name": "Pixel 7"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device detection received",
  "device": {
    "serial": "ABC123XYZ",
    "state": "device",
    "codename": "panther",
    "device_name": "Pixel 7"
  }
}
```

---

## Source

### `GET /source/status`
Check GrapheneOS source status.

**Response:**
```json
{
  "exists": true,
  "repo_initialized": true,
  "path": "/path/to/source",
  "manifest_revision": "refs/heads/main"
}
```

### `POST /source/validate`
Validate GrapheneOS source.

**Response:**
```json
{
  "valid": true,
  "message": "Source appears to be valid"
}
```

---

## Build

### `POST /build/start`
Start a build job (Linux only).

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "started",
  "message": "Build feature placeholder"
}
```

### `GET /build/jobs/{build_job_id}/stream`
Stream build job logs via SSE.

**Response:** SSE stream with events:
- `log`: New log line
- `status`: Status update
- `close`: Stream ended

### `POST /build/jobs/{build_job_id}/cancel`
Cancel a build job.

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled"
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

Common HTTP status codes:
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `500`: Internal Server Error

---

## WebSocket / SSE

Some endpoints use Server-Sent Events (SSE) for real-time updates:

- `/flash/jobs/{job_id}/stream`: Flash job logs
- `/build/jobs/{build_job_id}/stream`: Build job logs

**Usage Example:**
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

eventSource.addEventListener('close', () => {
  eventSource.close();
});
```

---

## Rate Limiting

Currently, rate limiting is disabled for development. In production, you may want to enable it via the `RateLimitMiddleware`.

---

## CORS

CORS is configured to allow all origins. In production, you may want to restrict this to specific domains.

---

## Version

Current API version: `1.0.0`

For the latest API documentation, visit `/docs` (Swagger UI) when `DEBUG=true`.

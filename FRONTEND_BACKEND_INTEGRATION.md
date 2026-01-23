# 🔄 Frontend-Backend Integration - Device Detection & Flashing

## Overview

The backend now supports receiving device information from the frontend (detected via WebADB) and automatically starting the flash process.

## Architecture

### Flow

```
Frontend (Browser)
  ↓ WebADB
Detects Device Locally
  ↓
POST /devices (register device)
  ↓
POST /flash/device-flash (start flash)
  ↓
Backend starts flash process
  ↓
Frontend polls /flash/jobs/{job_id} for status
```

## API Endpoints

### 1. `POST /devices` - Register Devices from Frontend

**Purpose**: Frontend sends device information detected via WebADB to backend.

**Request Body**:
```json
{
  "devices": [
    {
      "serial": "35201FDH2000G6",
      "state": "device",  // "device" | "fastboot" | "unauthorized" | "offline"
      "codename": "panther",  // Optional - from frontend detection
      "device_name": "Pixel 7",  // Optional
      "manufacturer": "Google",  // Optional
      "model": "Pixel 7",  // Optional
      "bootloader_unlocked": false  // Optional - from frontend check
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "message": "Registered 1 device(s)",
  "devices": [
    {
      "serial": "35201FDH2000G6",
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

**Code Location**: `backend/py-service/app/routes/devices.py:register_devices()`

---

### 2. `POST /flash/device-flash` - Start Flash from Frontend Device

**Purpose**: Frontend sends device info and backend automatically starts flash process.

**Request Body**:
```json
{
  "serial": "35201FDH2000G6",
  "codename": "panther",
  "state": "fastboot",  // "device" or "fastboot"
  "bootloader_unlocked": false,  // Optional - auto-determines skip_unlock
  "version": "2025122500"  // Optional - defaults to latest
}
```

**Response**:
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

**Code Location**: `backend/py-service/app/routes/flash.py:device_flash()`

---

### 3. `POST /flash/unlock-and-flash` - Enhanced with Frontend Info

**Purpose**: Unlock and flash endpoint, now accepts device info from frontend.

**Request Body**:
```json
{
  "device_serial": "35201FDH2000G6",
  "codename": "panther",  // NEW: From frontend
  "bootloader_unlocked": false,  // NEW: From frontend
  "bundle_path": "/path/to/bundle",  // Optional
  "skip_unlock": false  // Optional - auto-determined from bootloader_unlocked
}
```

**Changes**:
- Accepts `codename` from frontend (skips device identification if provided)
- Accepts `bootloader_unlocked` flag (auto-determines `skip_unlock`)
- Uses frontend-provided info to speed up process

**Code Location**: `backend/py-service/app/routes/flash.py:unlock_and_flash()`

---

## Frontend Integration Example

### Step 1: Detect Device (WebADB)

```typescript
// Frontend detects device via WebADB
const device = await deviceManager.connectDevice(serial);
const bootloaderUnlocked = await checkBootloaderState(device);

const deviceInfo = {
  serial: device.serial,
  state: device.state,
  codename: device.codename,
  bootloader_unlocked: bootloaderUnlocked,
};
```

### Step 2: Register Device with Backend

```typescript
// POST /devices
const response = await apiClient.post('/devices', {
  devices: [deviceInfo]
});

console.log('Device registered:', response.data);
```

### Step 3: Start Flash Process

```typescript
// POST /flash/device-flash
const flashResponse = await apiClient.post('/flash/device-flash', {
  serial: deviceInfo.serial,
  codename: deviceInfo.codename,
  state: deviceInfo.state,
  bootloader_unlocked: deviceInfo.bootloader_unlocked,
  version: '2025122500'  // Optional
});

const jobId = flashResponse.data.job_id;
```

### Step 4: Poll Job Status

```typescript
// Poll /flash/jobs/{job_id}
const pollJob = async () => {
  const jobResponse = await apiClient.get(`/flash/jobs/${jobId}`);
  const job = jobResponse.data;
  
  // Display logs
  job.logs.forEach(log => console.log(log));
  
  if (job.status === 'completed') {
    console.log('Flash completed!');
  } else if (job.status === 'failed') {
    console.error('Flash failed');
  } else {
    // Continue polling
    setTimeout(pollJob, 1000);
  }
};

pollJob();
```

---

## Benefits

### 1. **Faster Flash Start**
- Frontend provides codename (no backend identification needed)
- Frontend provides bootloader state (no backend check needed)
- Backend can start flash immediately

### 2. **Better Accuracy**
- Frontend detects device locally (more reliable)
- Frontend checks bootloader state via WebADB
- Backend uses accurate device info

### 3. **Simplified Flow**
- Frontend handles device detection
- Backend handles flashing
- Clear separation of concerns

---

## Backend Device Detection (GET)

The `GET /devices` endpoint still works for backend-based device detection:

```bash
# Backend detects devices on server
curl https://freedomos.vulcantech.co/devices
```

**Use Cases**:
- Admin/debugging tools
- Server-side device management
- Fallback if frontend detection fails

---

## Error Handling

### Device Not Found
```json
{
  "status_code": 404,
  "detail": "No bundle found for device codename: panther"
}
```

### Bundle Not Available
```json
{
  "status_code": 404,
  "detail": "Device codename panther but no bundle found. Please download a bundle first."
}
```

### Invalid Device State
```json
{
  "status_code": 400,
  "detail": "Device must be in fastboot mode for flashing"
}
```

---

## Code References

- **Device Registration**: `backend/py-service/app/routes/devices.py:register_devices()`
- **Device Flash Endpoint**: `backend/py-service/app/routes/flash.py:device_flash()`
- **Unlock and Flash**: `backend/py-service/app/routes/flash.py:unlock_and_flash()`
- **Bundle Management**: `backend/py-service/app/utils/bundles.py:get_bundle_for_codename()`

---

**Last Updated**: 2025-01-22
**Backend Version**: 1.0.0

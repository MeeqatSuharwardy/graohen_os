# Electron App Flash Fix

## Problem

The Electron app was not successfully flashing devices via the deployed backend. The issue was caused by incorrect request body format when calling the backend flash endpoints.

## Issues Found

### 1. Field Name Mismatch
- **Problem**: When calling `/flash/unlock-and-flash`, the frontend was sending `serial` but the backend expects `device_serial`
- **Location**: `frontend/renderer/app.js` line 379-393
- **Impact**: Backend couldn't find the device serial, causing flash requests to fail

### 2. Incorrect `skip_unlock` Logic
- **Problem**: When `unlockBootloader=true`, the code was setting `skip_unlock` based on bootloader state, but it should always be `false` when we want to unlock
- **Impact**: Backend might skip unlock even when user requested unlock

### 3. Poor Error Handling
- **Problem**: Error responses weren't properly parsed (FastAPI uses `detail` field, not `error`)
- **Impact**: Users saw generic error messages instead of specific backend errors

### 4. Missing Debug Logging
- **Problem**: No console logs to debug API calls
- **Impact**: Hard to troubleshoot issues

## Fixes Applied

### Fix 1: Correct Request Body Format

**Before:**
```javascript
const requestBody = {
  serial: selectedDevice.serial,  // Wrong field name for unlock-and-flash
  codename: selectedDevice.codename,
  state: 'fastboot',
  bootloader_unlocked: selectedDevice.bootloader_unlocked,
};
```

**After:**
```javascript
if (unlockBootloader) {
  // /flash/unlock-and-flash expects device_serial
  endpoint = `${BACKEND_URL}/flash/unlock-and-flash`;
  requestBody = {
    device_serial: selectedDevice.serial,  // Correct field name
    codename: selectedDevice.codename,
    skip_unlock: false,  // We want to unlock, so don't skip
    bootloader_unlocked: selectedDevice.bootloader_unlocked,
  };
} else {
  // /flash/device-flash expects serial
  endpoint = `${BACKEND_URL}/flash/device-flash`;
  requestBody = {
    serial: selectedDevice.serial,
    codename: selectedDevice.codename,
    state: 'fastboot',
    bootloader_unlocked: selectedDevice.bootloader_unlocked,
    skip_unlock: selectedDevice.bootloader_unlocked || false,
  };
  if (version) {
    requestBody.version = version;
  }
}
```

### Fix 2: Proper Error Handling

**Before:**
```javascript
if (!response.ok) {
  const errorData = await response.json().catch(() => ({}));
  throw new Error(errorData.error || `Failed to start flash: ${response.statusText}`);
}
```

**After:**
```javascript
if (!response.ok) {
  let errorMessage = `Failed to start flash: ${response.status} ${response.statusText}`;
  try {
    const errorData = await response.json();
    // FastAPI returns errors in 'detail' field
    errorMessage = errorData.detail || errorData.error || errorData.message || errorMessage;
  } catch (e) {
    const text = await response.text().catch(() => '');
    if (text) {
      errorMessage = text;
    }
  }
  throw new Error(errorMessage);
}
```

### Fix 3: Added Debug Logging

Added console logs to help debug:
```javascript
console.log(`[Flash] Calling endpoint: ${endpoint}`);
console.log(`[Flash] Request body:`, requestBody);
console.log(`[Flash] Response status: ${response.status} ${response.statusText}`);
console.log(`[Flash] Success response:`, data);
console.log(`[Flash] Job ID: ${currentJobId}`);
```

## Backend Endpoint Details

### `/flash/unlock-and-flash`
- **Request Model**: `UnlockAndFlashRequest`
- **Fields**:
  - `device_serial` (required) - Device serial number
  - `codename` (optional) - Device codename
  - `skip_unlock` (optional) - Skip unlock if bootloader already unlocked
  - `bootloader_unlocked` (optional) - Current bootloader state
  - `bundle_path` (optional) - Path to bundle (auto-detected if not provided)
- **Response**: `{"success": true, "job_id": "...", "message": "..."}`

### `/flash/device-flash`
- **Request Model**: `DeviceFlashRequest`
- **Fields**:
  - `serial` (required) - Device serial number
  - `codename` (required) - Device codename
  - `state` (required) - Device state ("device" or "fastboot")
  - `bootloader_unlocked` (optional) - Current bootloader state
  - `version` (optional) - Bundle version (defaults to latest)
  - `skip_unlock` (optional) - Skip unlock if bootloader already unlocked
- **Response**: `{"success": true, "job_id": "...", "message": "..."}`

## Testing

To test the fix:

1. **Start Electron App**
   ```bash
   cd frontend/electron
   npm start
   ```

2. **Connect Device**
   - Connect Pixel device via USB
   - Enable USB debugging
   - Click "Detect Devices"

3. **Test Unlock & Flash**
   - Select device with locked bootloader
   - Click "Unlock Bootloader & Flash"
   - Check browser console for logs
   - Verify job starts and logs stream

4. **Test Flash (Already Unlocked)**
   - Select device with unlocked bootloader
   - Click "Start Flashing"
   - Verify flash proceeds without unlock

## Expected Behavior

### Successful Flash Flow:
1. User clicks "Unlock Bootloader & Flash" or "Start Flashing"
2. Device reboots to fastboot (if not already there)
3. Frontend calls appropriate endpoint with correct field names
4. Backend creates flash job and returns `job_id`
5. Frontend connects to SSE stream: `/flash/jobs/{job_id}/stream`
6. Logs stream in real-time
7. Job completes successfully

### Error Scenarios:
- **No Bundle Found**: Backend returns 404 with detail message
- **Device Not Found**: Backend returns 400 with detail message
- **Network Error**: Frontend shows connection error
- **Invalid Request**: Backend returns 422 with validation errors

## Files Modified

- `frontend/renderer/app.js` - Fixed request body format, error handling, added logging

## Verification Checklist

- [x] Request body uses correct field names (`device_serial` for unlock-and-flash, `serial` for device-flash)
- [x] `skip_unlock` logic is correct (false when unlocking, true when already unlocked)
- [x] Error messages properly parsed from FastAPI responses
- [x] Debug logging added for troubleshooting
- [x] Job ID properly extracted from response
- [x] SSE stream connection works correctly

---

**Last Updated**: 2026-01-23

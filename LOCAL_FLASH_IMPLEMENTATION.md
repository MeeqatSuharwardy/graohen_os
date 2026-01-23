# Local Flash Implementation

## Overview

The Electron app now downloads bundles locally, extracts them, and executes flash commands directly from the local bundle folder. This solves the issue where the remote backend on VPS cannot access locally connected USB devices.

## Changes Made

### 1. Bundle Download & Extraction (`frontend/electron/main.js`)

- **Automatic Extraction**: After downloading the bundle ZIP, it's automatically extracted to maintain the same directory structure as the server's bundles folder
- **Directory Structure**: Bundles are stored at `{LOCAL_BUNDLES_DIR}/{codename}/{version}/` with the same structure as server bundles
- **Extraction Method**: Uses `adm-zip` library (with fallback to system `unzip` command)
- **Progress Tracking**: Shows extraction progress (50-100%) after download completes

### 2. Local Flash Execution (`frontend/electron/main.js`)

- **New Function**: `executeLocalFlash()` - Executes `flash-all.sh` (or `flash-all.bat` on Windows) from the extracted bundle folder
- **Device Serial**: Sets `ANDROID_SERIAL` environment variable to target specific device
- **Script Execution**: Makes script executable and runs it from the bundle directory
- **Output Streaming**: Streams stdout/stderr line-by-line to the frontend via IPC

### 3. IPC Handlers (`frontend/electron/main.js`)

- **`execute-local-flash`**: New IPC handler that:
  - Verifies bundle is extracted (checks for `flash-all.sh` or `flash-all.bat`)
  - Executes flash locally
  - Sends progress updates via `flash-progress` events

### 4. Preload API (`frontend/electron/preload.js`)

- **`executeLocalFlash()`**: Exposed to renderer process
- **`onFlashProgress()`**: Allows renderer to subscribe to flash progress updates

### 5. Frontend Flash Flow (`frontend/renderer/app.js`)

- **Step 1**: Download and extract bundle locally (REQUIRED)
- **Step 2**: Reboot device to fastboot if needed
- **Step 3**: Execute flash locally from extracted bundle (NEW)
  - No longer calls backend `/flash/device-flash` endpoint
  - Executes `flash-all.sh` directly from local bundle folder
  - Shows real-time progress in logs

## Bundle Location

Bundles are stored locally at:
- **macOS**: `~/Library/Application Support/FlashDash/bundles/{codename}/{version}/`
- **Windows**: `%APPDATA%/FlashDash/bundles/{codename}/{version}/`
- **Linux**: `~/.config/FlashDash/bundles/{codename}/{version}/`

After extraction, the folder contains:
```
bundles/
  └── panther/
      └── 2026011300/
          ├── flash-all.sh
          ├── flash-all.bat
          ├── image.zip
          ├── metadata.json
          └── [other bundle files]
```

## How It Works

1. **User selects device and version**
2. **App downloads bundle ZIP** from GrapheneOS releases or backend
3. **App extracts ZIP** to local bundles directory
4. **App reboots device** to fastboot mode (if needed)
5. **App executes `flash-all.sh`** from extracted bundle folder:
   ```bash
   ANDROID_SERIAL={device_serial} bash "{bundle_path}/flash-all.sh"
   ```
6. **Flash script runs locally** with direct USB device access
7. **Progress is streamed** to frontend UI in real-time

## Benefits

- ✅ **Solves USB Access Issue**: Flash executes locally where device is connected
- ✅ **No Network Dependency**: Flash doesn't require backend to access local USB
- ✅ **Faster**: No network latency for flash commands
- ✅ **Same Structure**: Local bundles match server structure for consistency
- ✅ **Offline Capable**: Once downloaded, flash can run without internet

## Dependencies

- **adm-zip**: Added to `frontend/electron/package.json` for ZIP extraction
- **System Requirements**: 
  - Unix: `unzip` command (fallback if adm-zip unavailable)
  - Windows: PowerShell `Expand-Archive` (fallback)

## Testing

To test the implementation:

1. Select a device and version
2. Click "Flash" button
3. Watch download progress (0-50%)
4. Watch extraction progress (50-100%)
5. Verify bundle is extracted to local bundles directory
6. Watch flash execution logs in real-time
7. Verify device is flashed successfully

## Notes

- Bundle download is now **required** before flashing (no longer optional)
- Flash execution happens **entirely locally** - no backend API calls for flash
- Backend is still used for:
  - Device registration
  - Bundle metadata/listing
  - Bundle download URLs
- Local flash bypasses all backend flash endpoints (`/flash/device-flash`, `/flash/unlock-and-flash`)

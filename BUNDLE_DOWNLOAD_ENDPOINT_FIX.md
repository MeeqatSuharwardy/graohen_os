# Bundle Download Endpoint Fix

## Problem

The bundle download endpoint was returning 404 because it was looking for `image.zip` file, but the bundle folder exists with extracted files instead.

## Solution

Updated `/bundles/releases/{codename}/{version}/download` endpoint to:
1. First check for `image.zip` or factory zip file
2. If not found, create a ZIP archive on-the-fly from the bundle folder
3. Return the ZIP file for download

## Changes Made

**File**: `backend/py-service/app/routes/bundles.py`

### Added Imports
```python
import tempfile
import shutil
```

### Updated Download Endpoint

The endpoint now:
1. Checks for existing zip files (`image.zip`, `{codename}-factory-{version}.zip`)
2. If bundle folder exists but no zip file, creates one dynamically
3. Creates a temporary zip file containing all files in the bundle directory
4. Returns the zip file for download

## How It Works

1. **Check for existing zip**:
   - `image.zip` in bundle directory
   - `{codename}-factory-{version}.zip` in bundle directory
   - Bundle path itself if it's a zip file

2. **Create archive if needed**:
   - Creates temporary zip file
   - Walks through bundle directory
   - Adds all files (excluding hidden files)
   - Returns the zip file

3. **Cleanup**:
   - Temporary files are cleaned up by the OS
   - FileResponse handles file serving

## Testing

### Test 1: Bundle with image.zip
```bash
curl -I https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download
# Should return 200 OK with image.zip
```

### Test 2: Bundle without image.zip (extracted)
```bash
curl -I https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download
# Should return 200 OK with dynamically created zip
```

### Test 3: Download the bundle
```bash
curl -O https://freedomos.vulcantech.co/bundles/releases/panther/2026011300/download
# Should download panther-factory-2026011300.zip
```

## Architecture Note

**Important**: The current setup has the Electron app running locally (with device connected) but backend on VPS. This means:

- ✅ **Bundle download works**: Electron can download bundle from VPS backend
- ❌ **Flash from VPS won't work**: VPS backend can't access local device via USB

### Solutions

**Option 1: Local Flash Execution (Recommended)**
- Electron app downloads bundle from backend
- Electron app executes flash locally using local fastboot/adb
- Backend only serves bundles and provides flash scripts

**Option 2: Network ADB/Fastboot**
- Set up network ADB/Fastboot on local machine
- Forward USB device to network
- Backend connects via network ADB/Fastboot

**Option 3: Hybrid Approach**
- Backend provides flash commands/scripts
- Electron app executes commands locally
- Backend tracks progress via API

---

**Last Updated**: 2026-01-23

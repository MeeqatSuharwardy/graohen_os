# ✅ Backend API Updates - Frontend Device Detection Integration

## Summary

The backend API has been updated to accept device information from the frontend (detected via WebADB) and automatically start the flash process.

## Changes Made

### 1. **`/devices` Endpoint - POST Support Added**

**File**: `backend/py-service/app/routes/devices.py`

**New Endpoint**: `POST /devices`

**Purpose**: Frontend sends device information detected via WebADB to backend.

**Request Model**:
```python
class DeviceInfo(BaseModel):
    serial: str
    state: str  # 'device', 'fastboot', 'unauthorized', 'offline'
    codename: Optional[str] = None
    device_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    bootloader_unlocked: Optional[bool] = None

class DeviceListRequest(BaseModel):
    devices: List[DeviceInfo]
```

**Response**:
```json
{
  "success": true,
  "message": "Registered 1 device(s)",
  "devices": [...]
}
```

**Features**:
- Accepts multiple devices in one request
- Tries to identify device if codename not provided
- Returns registered device info with identification results

---

### 2. **`/flash/device-flash` Endpoint - New**

**File**: `backend/py-service/app/routes/flash.py`

**New Endpoint**: `POST /flash/device-flash`

**Purpose**: Main endpoint for web flasher - frontend sends device info and backend starts flash automatically.

**Request Model**:
```python
class DeviceFlashRequest(BaseModel):
    serial: str
    codename: str
    state: str  # 'device' or 'fastboot'
    bootloader_unlocked: Optional[bool] = None
    version: Optional[str] = None  # Bundle version, defaults to latest
    skip_unlock: Optional[bool] = None  # Auto-determined from bootloader_unlocked
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
1. Determines `skip_unlock` from `bootloader_unlocked` flag
2. Finds bundle for codename (and version if provided)
3. Calls `unlock_and_flash` with device info
4. Returns `job_id` for status tracking

---

### 3. **`/flash/unlock-and-flash` Endpoint - Enhanced**

**File**: `backend/py-service/app/routes/flash.py`

**Updated Request Model**:
```python
class UnlockAndFlashRequest(BaseModel):
    device_serial: str
    bundle_path: Optional[str] = None
    skip_unlock: bool = False
    codename: Optional[str] = None  # NEW: From frontend
    bootloader_unlocked: Optional[bool] = None  # NEW: From frontend
```

**New Features**:
- Accepts `codename` from frontend (skips device identification if provided)
- Accepts `bootloader_unlocked` flag (auto-determines `skip_unlock`)
- Uses frontend-provided info to speed up process

**Logic**:
```python
# Use codename from request if provided (from frontend), otherwise try to identify
codename = request.codename

if not codename:
    device_info = identify_device(request.device_serial)
    if device_info:
        codename = device_info["codename"]

# Use skip_unlock from request, or determine from bootloader_unlocked flag
skip_unlock = request.skip_unlock
if request.bootloader_unlocked is True:
    skip_unlock = True
```

---

### 4. **`get_bundle_for_codename` Function - Version Support Added**

**File**: `backend/py-service/app/utils/bundles.py`

**Updated Signature**:
```python
def get_bundle_for_codename(codename: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
```

**New Features**:
- Accepts optional `version` parameter
- If version provided, returns specific version bundle
- If version not provided, returns latest bundle (existing behavior)

**Logic**:
```python
if codename_bundles:
    if version:
        # Find specific version
        for bundle in codename_bundles:
            if bundle.get("version") == version:
                return bundle
        return None
    # Return the newest bundle (first in sorted list)
    return codename_bundles[0]
```

---

## API Flow

### Complete Flow

```
1. Frontend detects device via WebADB
   ↓
2. Frontend POSTs device info to /devices
   POST /devices
   {
     "devices": [{
       "serial": "35201FDH2000G6",
       "state": "fastboot",
       "codename": "panther",
       "bootloader_unlocked": false
     }]
   }
   ↓
3. Frontend calls /flash/device-flash with device info
   POST /flash/device-flash
   {
     "serial": "35201FDH2000G6",
     "codename": "panther",
     "state": "fastboot",
     "bootloader_unlocked": false,
     "version": "2025122500"  // Optional
   }
   ↓
4. Backend finds bundle and starts flash process
   ↓
5. Backend returns job_id
   {
     "success": true,
     "job_id": "uuid-here"
   }
   ↓
6. Frontend polls /flash/jobs/{job_id} for status
   GET /flash/jobs/{job_id}
   ↓
7. Frontend streams logs via SSE (optional)
   GET /flash/jobs/{job_id}/stream
```

---

## Benefits

### 1. **Faster Flash Start**
- ✅ Frontend provides codename (no backend identification needed)
- ✅ Frontend provides bootloader state (no backend check needed)
- ✅ Backend can start flash immediately

### 2. **Better Accuracy**
- ✅ Frontend detects device locally (more reliable)
- ✅ Frontend checks bootloader state via WebADB
- ✅ Backend uses accurate device info

### 3. **Simplified Flow**
- ✅ Frontend handles device detection
- ✅ Backend handles flashing
- ✅ Clear separation of concerns

### 4. **Version Support**
- ✅ Frontend can specify bundle version
- ✅ Backend finds specific version or latest
- ✅ Flexible bundle selection

---

## Backward Compatibility

### Existing Endpoints Still Work

1. **`GET /devices`** - Backend device detection (unchanged)
2. **`POST /flash/unlock-and-flash`** - Works with or without frontend info
3. **`POST /flash/execute`** - Direct flash execution (unchanged)

### New Endpoints

1. **`POST /devices`** - Register devices from frontend (new)
2. **`POST /flash/device-flash`** - Start flash from frontend device (new)

---

## Testing

### Test POST /devices

```bash
curl -X POST https://freedomos.vulcantech.co/devices \
  -H "Content-Type: application/json" \
  -d '{
    "devices": [{
      "serial": "35201FDH2000G6",
      "state": "fastboot",
      "codename": "panther",
      "bootloader_unlocked": false
    }]
  }'
```

### Test POST /flash/device-flash

```bash
curl -X POST https://freedomos.vulcantech.co/flash/device-flash \
  -H "Content-Type: application/json" \
  -d '{
    "serial": "35201FDH2000G6",
    "codename": "panther",
    "state": "fastboot",
    "bootloader_unlocked": false,
    "version": "2025122500"
  }'
```

### Test GET /flash/jobs/{job_id}

```bash
curl https://freedomos.vulcantech.co/flash/jobs/{job_id}
```

---

## Code Files Modified

1. ✅ `backend/py-service/app/routes/devices.py`
   - Added `DeviceInfo` and `DeviceListRequest` models
   - Added `POST /devices` endpoint (`register_devices` function)

2. ✅ `backend/py-service/app/routes/flash.py`
   - Added `DeviceFlashRequest` model
   - Added `POST /flash/device-flash` endpoint (`device_flash` function)
   - Updated `UnlockAndFlashRequest` model (added `codename` and `bootloader_unlocked`)
   - Updated `unlock_and_flash` function to use frontend-provided info

3. ✅ `backend/py-service/app/utils/bundles.py`
   - Updated `get_bundle_for_codename` signature (added `version` parameter)
   - Added version filtering logic

---

## Documentation

- ✅ `FRONTEND_BACKEND_INTEGRATION.md` - Complete integration guide
- ✅ `BACKEND_FLASHING_PROCESS.md` - Backend flashing process documentation
- ✅ `BACKEND_API_UPDATES.md` - This file (summary of changes)

---

## Status

✅ **All changes complete and tested**

- ✅ POST /devices endpoint implemented
- ✅ POST /flash/device-flash endpoint implemented
- ✅ POST /flash/unlock-and-flash enhanced
- ✅ get_bundle_for_codename supports version parameter
- ✅ All endpoints backward compatible
- ✅ Documentation created

---

**Last Updated**: 2025-01-22
**Backend Version**: 1.0.0

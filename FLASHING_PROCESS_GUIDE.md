# Complete Flashing Process: Frontend-Backend Communication Guide

## Overview

This document explains the complete flashing workflow, including how the frontend (web flasher) and backend communicate to flash GrapheneOS on Pixel devices.

---

## Architecture Overview

```
┌─────────────────┐         HTTP/REST API         ┌─────────────────┐
│                 │◄──────────────────────────────►│                 │
│  Frontend       │         SSE Streaming          │  Backend        │
│  (Web Flasher)  │◄──────────────────────────────►│  (FastAPI)      │
│                 │                                │                 │
│  - WebADB       │                                │  - Flash Jobs   │
│  - Device UI    │                                │  - flasher.py   │
│  - Progress     │                                │  - ADB/Fastboot │
└─────────────────┘                                └─────────────────┘
                                                           │
                                                           ▼
                                                    ┌──────────────┐
                                                    │   Device     │
                                                    │  (Pixel)     │
                                                    └──────────────┘
```

---

## Complete Flashing Flow

### Phase 1: Device Detection & Connection

#### Frontend (Web Flasher)
1. **User clicks "Connect Device"**
   - Uses WebADB API (`navigator.usb.requestDevice()`)
   - Browser prompts user to select USB device
   - Device is connected via WebADB

2. **Device Information Retrieved**
   ```typescript
   // Frontend detects device via WebADB
   const device = await adb.getDevice(serial);
   const deviceInfo = {
     serial: device.serial,
     codename: device.codename,  // e.g., "panther"
     manufacturer: device.manufacturer,
     model: device.model,
     state: device.state,  // "device" or "fastboot"
     bootloaderUnlocked: device.bootloaderUnlocked
   };
   ```

#### Backend (No API call needed)
- Frontend handles device detection locally via WebADB
- Backend doesn't need to detect device at this stage

---

### Phase 2: Build Selection & Download

#### Frontend → Backend: Fetch Available Builds

**API Call:**
```typescript
GET /bundles/releases/{codename}
// Example: GET /bundles/releases/panther
```

**Request:**
```http
GET /bundles/releases/panther HTTP/1.1
Host: freedomos.vulcantech.co
```

**Backend Response:**
```json
{
  "codename": "panther",
  "releases": [
    {
      "codename": "panther",
      "version": "2026011300",
      "path": "/root/graohen_os/bundles/panther/2026011300",
      "downloadUrl": "https://releases.grapheneos.org/panther-factory-2026011300.zip"
    }
  ]
}
```

**Backend Implementation:**
- `GET /bundles/releases/{codename}` endpoint in `backend/py-service/app/routes/bundles.py`
- Calls `get_available_releases(codename)` from `utils/bundles.py`
- Returns list of available bundles for the device codename

#### Frontend: User Selects Build

```typescript
// User selects build from dropdown
const selectedBuild = {
  codename: "panther",
  version: "2026011300"
};
```

#### Frontend → Backend: Download Build (Optional)

**Option A: Download via Backend API**
```typescript
GET /bundles/releases/{codename}/{version}/download
// Downloads image.zip from server
```

**Option B: Download Directly (Current Implementation)**
- Frontend downloads build ZIP directly from GrapheneOS releases
- Or uses backend's bundle if already downloaded

---

### Phase 3: Bootloader Check & Reboot

#### Frontend: Check Bootloader State

**Local Check (WebADB):**
```typescript
// Frontend checks bootloader state via WebADB
const bootloaderUnlocked = device.bootloaderUnlocked;
// Shows UI: "Bootloader: ✓ Unlocked" or "🔒 Locked"
```

#### Frontend → Backend: Reboot to Bootloader (if needed)

**API Call:**
```typescript
POST /devices/{serial}/reboot/bootloader
```

**Request:**
```json
POST /devices/ABC123/reboot/bootloader
```

**Backend Response:**
```json
{
  "success": true,
  "message": "Device rebooting to bootloader"
}
```

**Backend Implementation:**
- `POST /devices/{serial}/reboot/bootloader` in `backend/py-service/app/routes/devices.py`
- Executes: `adb -s {serial} reboot bootloader`
- Device reboots to fastboot mode

**Frontend:**
- Waits 5 seconds for device to reboot
- Checks if device is now in fastboot mode
- Updates UI: "✓ Device is now in fastboot mode"

---

### Phase 4: Start Flash Process

#### Frontend → Backend: Start Unlock & Flash

**API Call:**
```typescript
POST /flash/unlock-and-flash
```

**Request:**
```json
{
  "device_serial": "ABC123",
  "codename": "panther",
  "skip_unlock": false,  // or true if bootloader already unlocked
  "bootloader_unlocked": false,
  "version": "2026011300"  // optional, defaults to latest
}
```

**Backend Response:**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Unlock and flash process started"
}
```

**Backend Implementation:**

1. **Find Bundle** (`backend/py-service/app/routes/flash.py:245`)
   ```python
   bundle = get_bundle_for_codename(codename, version=version)
   bundle_path = bundle["path"]  # e.g., "/root/graohen_os/bundles/panther/2026011300"
   ```

2. **Create Flash Job**
   ```python
   job_id = str(uuid.uuid4())
   job = {
       "id": job_id,
       "device_serial": request.device_serial,
       "bundle_path": str(extracted_dir),
       "status": "starting",
       "logs": [],
       "process": None,
   }
   flash_jobs[job_id] = job
   ```

3. **Start Background Process**
   ```python
   # Runs flasher.py script in background thread
   thread = threading.Thread(
       target=_run_unlock_and_flash,
       args=(job, flasher_script, extracted_dir, device_serial, skip_unlock)
   )
   thread.start()
   ```

4. **Execute Flasher Script**
   ```python
   # Command executed:
   python -u backend/flasher.py \
       --fastboot-path /usr/local/bin/fastboot \
       --adb-path /usr/local/bin/adb \
       --bundle-path /root/graohen_os/bundles/panther/2026011300 \
       --device-serial ABC123 \
       --confirm \
       [--skip-unlock]  # if bootloader already unlocked
   ```

---

### Phase 5: Flash Execution (Backend)

#### Backend: Execute flasher.py Script

**Script Location:** `backend/flasher.py`

**Process Flow:**

1. **Preflight Checks**
   - Verify device is in fastboot mode
   - Check OEM unlock capability
   - Verify bundle files exist

2. **Bootloader Unlock** (if `skip_unlock=False`)
   ```
   fastboot -s ABC123 oem unlock
   # Device shows confirmation screen
   # User must confirm on device
   ```

3. **Flash Partitions**
   ```
   fastboot -s ABC123 flash boot boot.img
   fastboot -s ABC123 flash dtbo dtbo.img
   fastboot -s ABC123 flash vendor_boot vendor_boot.img
   fastboot -s ABC123 flash super super.img
   # ... more partitions
   ```

4. **Reboot Device**
   ```
   fastboot -s ABC123 reboot
   ```

**Output Streaming:**
- `flasher.py` outputs JSON logs line-by-line
- Backend captures output in real-time
- Logs stored in `job["logs"]` array

---

### Phase 6: Progress Monitoring

#### Frontend → Backend: Stream Flash Logs

**Two Methods:**

**Method 1: Server-Sent Events (SSE) - Preferred**

**API Call:**
```typescript
GET /flash/jobs/{job_id}/stream
```

**Connection:**
```typescript
const eventSource = new EventSource(
  `${apiBase}/flash/jobs/${jobId}/stream`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data = { "line": "Flashing boot partition..." }
  updateLogs(data.line);
};

eventSource.addEventListener('status', (event) => {
  const data = JSON.parse(event.data);
  // data = { "status": "completed" }
  if (data.status === 'completed') {
    eventSource.close();
  }
});
```

**Backend Implementation:**
```python
@router.get("/jobs/{job_id}/stream")
async def stream_flash_job(job_id: str):
    async def event_generator():
        last_log_count = 0
        while True:
            job = get_flash_job(job_id)
            
            # Send new logs
            if len(job["logs"]) > last_log_count:
                for log_line in job["logs"][last_log_count:]:
                    yield {"event": "log", "data": json.dumps({"line": log_line})}
                last_log_count = len(job["logs"])
            
            # Send status updates
            if job["status"] in ["completed", "failed", "cancelled"]:
                yield {"event": "status", "data": json.dumps({"status": job["status"]})}
                yield {"event": "close", "data": json.dumps({})}
                break
            
            await asyncio.sleep(0.5)  # Poll every 500ms
    
    return EventSourceResponse(event_generator())
```

**Method 2: Polling (Fallback)**

**API Call:**
```typescript
GET /flash/jobs/{job_id}
```

**Polling:**
```typescript
const pollInterval = setInterval(async () => {
  const response = await apiClient.get(`/flash/jobs/${jobId}`);
  const job = response.data;
  
  // Update logs
  job.logs.forEach(log => updateLogs(log));
  
  // Check status
  if (job.status === 'completed' || job.status === 'failed') {
    clearInterval(pollInterval);
  }
}, 1000);  // Poll every second
```

**Backend Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "device_serial": "ABC123",
  "status": "running",
  "logs": [
    "Starting unlock and flash process...",
    "Device identified: panther",
    "Checking bootloader state...",
    "Flashing boot partition...",
    "Flashing super partition...",
    "✓ Flash completed successfully!"
  ],
  "log_count": 6
}
```

---

### Phase 7: Completion

#### Backend: Flash Completes

**Job Status Updates:**
```python
job["status"] = "completed"
job["logs"].append("✓ Unlock and flash completed successfully!")
```

#### Frontend: Receive Completion

**Via SSE:**
```typescript
eventSource.addEventListener('status', (event) => {
  const data = JSON.parse(event.data);
  if (data.status === 'completed') {
    setStatus('completed');
    showSuccessMessage('Flash completed successfully!');
  } else if (data.status === 'failed') {
    setStatus('failed');
    showErrorMessage('Flash failed');
  }
});
```

**Via Polling:**
```typescript
if (job.status === 'completed') {
  setIsFlashing(false);
  setProgress({ message: 'Flash completed successfully!', progress: 100 });
}
```

---

## API Endpoints Reference

### Device Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices` | GET | List all connected devices |
| `/devices/{serial}/identify` | GET | Identify device codename |
| `/devices/{serial}/reboot/bootloader` | POST | Reboot device to bootloader |

### Bundle Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/bundles/index` | POST | Index all available bundles |
| `/bundles/for/{codename}` | GET | Get newest bundle for codename |
| `/bundles/releases/{codename}` | GET | Get available releases for codename |
| `/bundles/releases/{codename}/{version}/download` | GET | Download bundle ZIP |
| `/bundles/releases/{codename}/{version}/list` | GET | List files in bundle |

### Flash Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/flash/unlock-and-flash` | POST | Start unlock and flash process |
| `/flash/device-flash` | POST | Start flash from frontend-detected device |
| `/flash/execute` | POST | Execute flash directly |
| `/flash/jobs` | GET | List all flash jobs |
| `/flash/jobs/{job_id}` | GET | Get flash job status and logs |
| `/flash/jobs/{job_id}/stream` | GET | Stream flash job logs (SSE) |
| `/flash/jobs/{job_id}/cancel` | POST | Cancel flash job |

---

## Request/Response Examples

### Example 1: Start Flash Process

**Request:**
```http
POST /flash/unlock-and-flash HTTP/1.1
Host: freedomos.vulcantech.co
Content-Type: application/json

{
  "device_serial": "ABC123",
  "codename": "panther",
  "skip_unlock": false,
  "bootloader_unlocked": false,
  "version": "2026011300"
}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Unlock and flash process started"
}
```

### Example 2: Stream Flash Logs (SSE)

**Request:**
```http
GET /flash/jobs/550e8400-e29b-41d4-a716-446655440000/stream HTTP/1.1
Host: freedomos.vulcantech.co
Accept: text/event-stream
```

**Response (Streaming):**
```
event: log
data: {"line": "Starting unlock and flash process..."}

event: log
data: {"line": "Device identified: panther"}

event: log
data: {"line": "Checking bootloader state..."}

event: log
data: {"line": "Flashing boot partition..."}

event: status
data: {"status": "completed"}

event: close
data: {}
```

### Example 3: Get Job Status (Polling)

**Request:**
```http
GET /flash/jobs/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: freedomos.vulcantech.co
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "device_serial": "ABC123",
  "status": "running",
  "dry_run": false,
  "log_count": 15,
  "logs": [
    "Starting unlock and flash process...",
    "Device identified: panther",
    "Checking bootloader state...",
    "Bootloader is locked, will unlock...",
    "Rebooting to bootloader...",
    "Waiting for device in fastboot mode...",
    "Device is in fastboot mode",
    "Unlocking bootloader...",
    "Please confirm unlock on device...",
    "Bootloader unlocked successfully",
    "Flashing boot partition...",
    "Flashing dtbo partition...",
    "Flashing vendor_boot partition...",
    "Flashing super partition...",
    "Flash completed successfully!"
  ]
}
```

---

## Frontend Implementation Details

### useBackendFlasher Hook

**Location:** `frontend/apps/web-flasher/src/hooks/useBackendFlasher.ts`

**Key Functions:**

1. **startFlash(options)**
   - Identifies device codename
   - Checks device state (reboots to bootloader if needed)
   - Calls `/flash/unlock-and-flash` endpoint
   - Sets up SSE or polling for logs

2. **Progress Monitoring**
   - Uses SSE (`EventSource`) for real-time logs
   - Falls back to polling if SSE fails
   - Updates UI with progress and logs

3. **cancelFlash()**
   - Calls `/flash/jobs/{job_id}/cancel`
   - Stops monitoring
   - Updates UI

**Usage:**
```typescript
const { 
  isFlashing, 
  progress, 
  error, 
  startFlash, 
  cancelFlash 
} = useBackendFlasher();

await startFlash({
  deviceSerial: "ABC123",
  codename: "panther",
  version: "2026011300",
  skipUnlock: false,
  onProgress: (prog) => console.log(prog.message),
  onLog: (msg, level) => console.log(msg, level)
});
```

---

## Backend Implementation Details

### Flash Job Management

**Location:** `backend/py-service/app/utils/flash.py`

**Job Structure:**
```python
flash_jobs = {
    "job_id": {
        "id": "job_id",
        "device_serial": "ABC123",
        "bundle_path": "/path/to/bundle",
        "status": "running",  # starting, running, completed, failed, cancelled
        "logs": ["log line 1", "log line 2", ...],
        "process": subprocess.Popen object
    }
}
```

### Flash Execution

**Location:** `backend/py-service/app/routes/flash.py:_run_unlock_and_flash()`

**Process:**
1. Creates subprocess for `flasher.py`
2. Reads output line-by-line in real-time
3. Parses JSON logs from flasher.py
4. Updates job logs array
5. Updates job status on completion/failure

**Output Parsing:**
```python
def _process_flasher_output(job: dict, line: str, job_id: str):
    try:
        log_data = json.loads(line)  # Parse JSON log
        if "message" in log_data:
            job["logs"].append(log_data["message"])
        elif "status" in log_data:
            job["status"] = log_data["status"]
    except json.JSONDecodeError:
        # Plain text output
        job["logs"].append(line)
```

---

## Error Handling

### Frontend Error Handling

```typescript
try {
  await startFlash(options);
} catch (err: any) {
  if (err.response?.data?.detail) {
    // Backend error
    setError(err.response.data.detail);
  } else if (err.code === 'ECONNABORTED') {
    // Timeout
    setError('Request timed out. Backend may be busy.');
  } else {
    // Network error
    setError('Failed to connect to backend.');
  }
}
```

### Backend Error Handling

```python
try:
    # Start flash process
    result = await unlock_and_flash(request)
    return result
except HTTPException:
    raise  # Re-raise HTTP exceptions
except Exception as e:
    logger.error(f"Error in unlock_and_flash: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail=f"Failed to start unlock and flash: {str(e)}"
    )
```

---

## State Machine

### Flash States

```
idle
  ↓
device_connected (WebADB detects device)
  ↓
bootloader_checked (Check bootloader state)
  ↓
build_selected (User selects build)
  ↓
downloading (Download build ZIP)
  ↓
download_complete (Build downloaded)
  ↓
rebooting_to_bootloader (Reboot device)
  ↓
fastboot_mode (Device in fastboot)
  ↓
unlocking_bootloader (Unlock bootloader - if needed)
  ↓
flashing (Flash partitions)
  ↓
flash_complete (All partitions flashed)
  ↓
rebooting (Reboot device)
  ↓
complete (Flash completed successfully)
```

---

## Security Considerations

1. **Device Serial Validation**
   - Backend validates device serial exists
   - Prevents flashing wrong device

2. **Bundle Verification**
   - SHA256 checksums verified
   - Bundle integrity checked before flashing

3. **Confirmation Tokens**
   - Optional typed confirmation required
   - Prevents accidental flashes

4. **Job Isolation**
   - Each flash job runs in separate process
   - Jobs can be cancelled independently

---

## Troubleshooting

### Frontend Can't Connect to Backend

**Problem:** `ECONNREFUSED` error

**Solutions:**
1. Check backend is running: `curl http://localhost:8000/docs`
2. Verify `VITE_API_BASE_URL` in frontend `.env`
3. Check CORS configuration in backend

### Flash Job Stuck

**Problem:** Job status stays "running" but no progress

**Solutions:**
1. Check backend logs: `docker logs flashdash`
2. Check flasher.py output: `ps aux | grep flasher.py`
3. Cancel and restart: `POST /flash/jobs/{job_id}/cancel`

### Device Not Detected

**Problem:** Frontend can't detect device via WebADB

**Solutions:**
1. Ensure Chrome/Edge browser (WebADB support)
2. Check USB debugging enabled on device
3. Grant USB permission in browser

---

## Summary

**Complete Flow:**
1. Frontend detects device via WebADB (local)
2. Frontend fetches available builds from backend
3. User selects build and downloads (optional)
4. Frontend reboots device to bootloader (via backend API)
5. Frontend calls `/flash/unlock-and-flash` endpoint
6. Backend creates flash job and starts `flasher.py` script
7. Frontend streams logs via SSE or polling
8. Backend executes flash commands (fastboot)
9. Frontend receives completion status
10. Device reboots with GrapheneOS installed

**Key Communication Points:**
- **Device Detection:** Frontend (WebADB) - no backend call
- **Build Selection:** `GET /bundles/releases/{codename}`
- **Reboot:** `POST /devices/{serial}/reboot/bootloader`
- **Start Flash:** `POST /flash/unlock-and-flash`
- **Progress:** `GET /flash/jobs/{job_id}/stream` (SSE) or polling
- **Status:** `GET /flash/jobs/{job_id}`

---

**Last Updated:** 2026-01-23

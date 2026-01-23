# 🔧 Backend OS Flashing Process

## Overview

The backend uses a **finite state machine (FSM)** approach to flash GrapheneOS to Pixel devices. The flashing process is handled by the `flasher.py` script, which is executed via the `/flash/unlock-and-flash` API endpoint.

## Architecture

### Components

1. **API Endpoint**: `POST /flash/unlock-and-flash`
   - Located in: `backend/py-service/app/routes/flash.py`
   - Accepts device serial and bundle path
   - Creates a background job and returns `job_id`

2. **Flasher Script**: `backend/flasher.py`
   - Main flashing logic
   - Executes ADB and Fastboot commands
   - Outputs structured JSON logs

3. **Flash Engine**: `backend/py-service/app/utils/grapheneos/flash_engine.py`
   - FSM implementation for flashing workflow
   - Manages state transitions and partition flashing

## Flashing Process Flow

### State Machine States

```
INIT → ADB → FASTBOOT → FASTBOOT_FLASH → FASTBOOTD → FASTBOOTD_FLASH → FINAL → DONE
```

### Detailed Steps

#### 1. **INIT State** - Initialization
- **Purpose**: Prepare for flashing
- **Actions**:
  - Validate bundle path exists
  - Extract bundle if needed (ZIP file)
  - Scan for partition files
  - Identify device codename

**Code Location**: `flash_engine.py:execute_flash()`

```python
# Ensure bundle is available
bundle_path = self.build_manager.ensure_bundle_available(codename, version)

# Find partition files
self.partition_files = self.build_manager.find_partition_files(bundle_path)
```

---

#### 2. **ADB State** - Bootloader Unlock
- **Purpose**: Unlock bootloader if locked
- **Requirements**: Device must be in ADB mode
- **User Action Required**: Physical confirmation on device (Volume Up + Power)

**Process**:
1. Check unlock status via `adb shell getprop ro.boot.flash.locked`
2. If locked (`1`), execute `fastboot flashing unlock`
3. Wait for user confirmation on device screen
4. Device reboots automatically after unlock

**Code Location**: `flash_engine.py:_unlock_bootloader()`

```python
# Check if already unlocked
result = self.transport.adb_command(["shell", "getprop", "ro.boot.flash.locked"])

if "0" in result.get("stdout", ""):
    # Already unlocked
    return True

# Request unlock
result = self.transport.fastboot_command(["flashing", "unlock"], timeout=60)
```

**⚠️ Security Note**: Bootloader unlock **FACTORY RESETS** the device. All data is permanently erased.

---

#### 3. **FASTBOOT State** - Enter Bootloader Mode
- **Purpose**: Reboot device to bootloader fastboot mode
- **Actions**:
  - Execute `adb reboot bootloader`
  - Wait for device to appear in fastboot mode
  - Verify with `fastboot getvar product`

**Code Location**: `flash_engine.py:_enter_fastboot()`

```python
# Reboot to bootloader
result = self.transport.adb_command(["reboot", "bootloader"], timeout=60)

# Wait for fastboot mode
if not self.transport.wait_for_fastboot(timeout=90):
    return False
```

---

#### 4. **FASTBOOT_FLASH State** - Flash Firmware Partitions
- **Purpose**: Flash bootloader, radio, and core partitions in bootloader fastboot mode
- **Sequence** (CRITICAL ORDER):

##### Step 4.1: Flash Bootloader
```bash
fastboot flash bootloader bootloader.img
fastboot reboot-bootloader  # REQUIRED: Reboot bootloader ONCE
# Wait 5 seconds
```

##### Step 4.2: Flash Radio
```bash
fastboot flash radio radio.img
fastboot reboot-bootloader  # REQUIRED: Reboot bootloader ONCE (LAST reboot before fastbootd)
# Wait 5 seconds
```

##### Step 4.3: Flash Core Partitions (NO REBOOT between these)
```bash
fastboot flash boot boot.img
fastboot flash init_boot init_boot.img
fastboot flash dtbo dtbo.img
fastboot flash vendor_kernel_boot vendor_kernel_boot.img
fastboot flash pvmfw pvmfw.img
fastboot flash vendor_boot vendor_boot.img
fastboot flash vbmeta vbmeta.img
```

**Code Location**: `flash_engine.py:_flash_in_bootloader_fastboot()`

**⚠️ Critical Rules**:
- Bootloader flash → **reboot bootloader** → Radio flash → **reboot bootloader** → Core partitions (no reboot)
- Only **2 reboots** total in this state (after bootloader and radio)
- USB disconnect/reconnect is **normal** during reboots

---

#### 5. **FASTBOOTD State** - Transition to Userspace Fastboot
- **Purpose**: Reboot to fastbootd (userspace fastboot) for super partition flashing
- **Actions**:
  - Execute `fastboot reboot fastboot`
  - Wait until `fastboot getvar is-userspace` returns `yes`
  - Verify device is in fastbootd mode

**Code Location**: `flash_engine.py:_enter_fastbootd()`

```python
# Reboot to fastbootd
result = self.transport.fastboot_command(["reboot", "fastboot"], timeout=60)

# Wait for is-userspace=yes
while timeout:
    test_result = self.transport.fastbootd_command(["getvar", "is-userspace"])
    if "is-userspace: yes" in output:
        return True
```

**Why Fastbootd?**: Super partition images **MUST** be flashed in fastbootd mode, not bootloader fastboot.

---

#### 6. **FASTBOOTD_FLASH State** - Flash Super Partition
- **Purpose**: Flash super partition images (system, vendor, product, etc.)
- **Actions**:
  - Find all `super_*.img` files in bundle
  - Flash each super image sequentially: `fastboot flash super super_1.img`, `super_2.img`, etc.
  - **NO REBOOT** between super images

**Code Location**: `flash_engine.py:_flash_super_in_fastbootd()`

```python
# Find super images
super_images = sorted(bundle_path.glob("super_*.img"))

# Flash each sequentially
for super_img in super_images:
    result = self.transport.fastbootd_command(["flash", "super", str(super_img)], timeout=300)
```

**Super Partition**: Contains system, vendor, product, and other dynamic partitions. Typically 2-4 images.

---

#### 7. **FINAL State** - Complete and Reboot
- **Purpose**: Finalize flash and reboot device
- **Actions**:
  - Optional: Lock bootloader (if `lock_bootloader=True`)
  - Reboot device: `fastboot reboot`
  - Device boots into GrapheneOS

**Code Location**: `flash_engine.py:execute_flash()`

```python
# Reboot device
reboot_result = self.transport.fastbootd_command(["reboot"], timeout=30)
```

---

## API Endpoint Details

### `POST /flash/unlock-and-flash`

**Request Body**:
```json
{
  "device_serial": "35201FDH2000G6",
  "skip_unlock": false,
  "bundle_path": "/path/to/bundle"  // Optional - auto-detected if not provided
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
1. Identifies device codename from serial
2. Finds bundle for codename (or uses provided path)
3. Extracts bundle if ZIP file
4. Creates background job
5. Executes `flasher.py` script in separate thread
6. Returns `job_id` for status tracking

**Code Location**: `backend/py-service/app/routes/flash.py:_run_unlock_and_flash()`

```python
cmd = [
    python_cmd,
    "-u",  # Unbuffered output
    str(flasher_script),
    "--fastboot-path", settings.FASTBOOT_PATH,
    "--adb-path", settings.ADB_PATH,
    "--bundle-path", str(bundle_path),
    "--device-serial", device_serial,
    "--confirm",
]
if skip_unlock:
    cmd.append("--skip-unlock")
```

---

## Job Status Tracking

### `GET /flash/jobs/{job_id}`

Returns job status and logs:
```json
{
  "id": "job-id",
  "device_serial": "35201FDH2000G6",
  "status": "running",  // "starting" | "running" | "completed" | "failed" | "cancelled"
  "logs": [
    "[preflight] Starting unlock and flash process...",
    "[unlock] Checking bootloader unlock status...",
    "[flash] Flashing bootloader..."
  ]
}
```

### `GET /flash/jobs/{job_id}/stream`

Server-Sent Events (SSE) stream for real-time logs:
```
event: log
data: {"line": "[preflight] Starting process..."}

event: status
data: {"status": "completed"}
```

---

## Tools Used

### ADB (Android Debug Bridge)
- **Path**: `/usr/local/bin/adb` (configurable)
- **Used for**:
  - Device detection
  - Bootloader unlock commands
  - Rebooting to bootloader
  - Checking device properties

### Fastboot
- **Path**: `/usr/local/bin/fastboot` (configurable)
- **Used for**:
  - Flashing partitions
  - Rebooting device
  - Checking device state (`getvar`)
  - Bootloader unlock/lock

---

## Bundle Structure

Bundles are extracted ZIP files containing:

```
bundle/
├── bootloader.img
├── radio.img
├── boot.img
├── init_boot.img
├── dtbo.img
├── vendor_kernel_boot.img
├── pvmfw.img
├── vendor_boot.img
├── vbmeta.img
├── super_1.img
├── super_2.img
├── super_3.img
└── ... (other partitions)
```

**Bundle Location**: `bundles/{codename}/{version}/` (e.g., `bundles/panther/2025122500/`)

---

## Error Handling

### Common Errors

1. **Device Not Found**
   - Error: `No devices found in fastboot`
   - Solution: Ensure device is connected and in correct mode

2. **Bootloader Locked**
   - Error: `OEM unlocking is disabled`
   - Solution: Enable OEM unlocking in Developer Options

3. **Bundle Not Found**
   - Error: `No bundle found for codename: {codename}`
   - Solution: Download bundle first via `/bundles/download`

4. **Flash Timeout**
   - Error: `Fastboot command timed out`
   - Solution: Check USB connection, try different cable/port

### Log Format

All logs are JSON-formatted:
```json
{
  "step": "flash",
  "partition": "bootloader",
  "status": "info",
  "message": "Flashing bootloader: bootloader.img"
}
```

---

## Security Considerations

1. **Bootloader Unlock**
   - Requires **physical confirmation** on device
   - User must press Volume Up + Power on device screen
   - **FACTORY RESETS** device (all data erased)
   - Never attempted silently or unattended

2. **Bundle Verification**
   - SHA256 checksums verified (if available)
   - Bundle structure validated before flashing

3. **Device Validation**
   - Codename verified before flashing
   - Prevents flashing wrong device

---

## Performance

- **Typical Flash Time**: 5-10 minutes
- **Bootloader Unlock**: 30-60 seconds (includes user confirmation)
- **Partition Flashing**: 2-5 minutes
- **Super Partition**: 2-4 minutes (largest partition)

---

## Example Complete Flow

```
1. User calls: POST /flash/unlock-and-flash
   → {"device_serial": "35201FDH2000G6", "skip_unlock": false}

2. Backend:
   - Identifies device: panther
   - Finds bundle: bundles/panther/2025122500/
   - Creates job: job-12345
   - Starts flasher.py in background

3. Flasher Process:
   [INIT] Extracting bundle...
   [ADB] Checking bootloader status...
   [ADB] Bootloader locked, requesting unlock...
   [ADB] ⚠️ ACTION REQUIRED: Confirm unlock on device
   [FASTBOOT] Rebooting to bootloader...
   [FASTBOOT_FLASH] Flashing bootloader...
   [FASTBOOT_FLASH] Rebooting bootloader...
   [FASTBOOT_FLASH] Flashing radio...
   [FASTBOOT_FLASH] Rebooting bootloader...
   [FASTBOOT_FLASH] Flashing boot, init_boot, dtbo...
   [FASTBOOTD] Rebooting to fastbootd...
   [FASTBOOTD_FLASH] Flashing super_1.img...
   [FASTBOOTD_FLASH] Flashing super_2.img...
   [FINAL] Rebooting device...
   [DONE] ✓ Flash completed successfully!

4. User polls: GET /flash/jobs/job-12345
   → {"status": "completed", "logs": [...]}
```

---

## Code References

- **API Route**: `backend/py-service/app/routes/flash.py`
- **Flash Engine**: `backend/py-service/app/utils/grapheneos/flash_engine.py`
- **Flasher Script**: `backend/flasher.py`
- **Transport Layer**: `backend/py-service/app/utils/tools.py`
- **Bundle Management**: `backend/py-service/app/utils/bundles.py`

---

**Last Updated**: 2025-01-22
**Backend Version**: 1.0.0

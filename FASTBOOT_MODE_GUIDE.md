# Fastboot Mode Guide

Complete guide on how devices enter fastboot mode and which APIs are used in the FlashDash platform.

## Overview

Fastboot mode is a special boot mode on Android devices that allows low-level operations like flashing firmware, unlocking bootloaders, and modifying system partitions. In FlashDash, devices can enter fastboot mode through multiple methods depending on the context (frontend WebADB detection vs backend ADB commands).

---

## Fastboot Mode Entry Methods

### 1. **Backend API-Driven Reboot** (Most Common)

When the backend needs to flash a device, it uses ADB commands to reboot the device into fastboot mode.

#### API Endpoint

**`POST /devices/{device_id}/reboot/bootloader`**

**Request**:
```bash
curl -X POST https://freedomos.vulcantech.co/devices/ABC123XYZ/reboot/bootloader
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Device rebooting to bootloader"
}
```

#### Implementation Flow

1. **Backend receives request** at `backend/py-service/app/routes/devices.py`
2. **Executes ADB command**: `adb -s {serial} reboot bootloader`
3. **Waits for device** to disconnect from ADB (expected behavior)
4. **Returns success** even if connection is lost (normal during reboot)

**Code Location**: `backend/py-service/app/routes/devices.py` (lines 134-165)

```python
@router.post("/{device_id}/reboot/bootloader")
async def reboot_to_bootloader(device_id: str):
    """
    Reboot device to bootloader mode.
    """
    try:
        logger.info(f"Rebooting device {device_id} to bootloader...")
        
        # Execute ADB reboot bootloader command
        result = run_adb_command(["reboot", "bootloader"], serial=device_id, timeout=60)
        
        # Device will disconnect during reboot - this is expected
        if result is None or result.returncode != 0:
            # Check if it's a timeout/connection loss (expected during reboot)
            if result and result.returncode == -1:
                # Timeout is expected - device is rebooting
                logger.info(f"Device {device_id} rebooting (connection lost - expected)")
                return {"success": True, "message": "Device rebooting to bootloader"}
        
        return {"success": True, "message": "Device rebooting to bootloader"}
    except Exception as e:
        logger.error(f"Error rebooting device {device_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

#### ADB Command Used

```bash
adb -s {device_serial} reboot bootloader
```

**What happens**:
- ADB sends reboot command to device
- Device immediately reboots
- ADB connection is lost (expected)
- Device boots into fastboot mode
- Device appears in `fastboot devices` output

---

### 2. **Frontend WebADB Reboot** (Web Flasher)

When using the web flasher, devices are detected via WebADB in the browser. The frontend can reboot devices directly using WebADB APIs.

#### Frontend Implementation

**Hook**: `frontend/apps/web-flasher/src/hooks/useWebADBDevice.ts`

**Function**: `rebootToBootloader(serial: string)`

```typescript
const rebootToBootloader = useCallback(async (serial: string) => {
  try {
    const adb = await deviceManager.connectDevice(serial);
    await adb.reboot('bootloader');
    
    // Update device state locally
    setDevices(prev => prev.map(d => 
      d.serial === serial 
        ? { ...d, state: 'fastboot' as const, inFastbootMode: true }
        : d
    ));
  } catch (err: any) {
    setError(err.message || 'Failed to reboot to bootloader');
  }
}, [deviceManager]);
```

#### WebADB Library Used

**Library**: `@yume-chan/adb` with `@yume-chan/adb-backend-webusb`

**Method**: `adb.reboot('bootloader')`

**What happens**:
- Browser requests USB device access (WebUSB API)
- WebADB connects to device via USB
- Sends reboot command through WebUSB
- Device reboots into fastboot mode
- Browser loses WebADB connection (expected)
- Device can be detected in fastboot mode via WebUSB Fastboot

---

### 3. **Automatic Reboot During Flash** (Backend Flash Engine)

During the flashing process, the backend automatically reboots devices to fastboot mode if they're not already in it.

#### Flash Engine Flow

**Code Location**: `backend/py-service/app/utils/grapheneos/flash_engine.py`

**Method**: `_enter_fastboot()`

```python
def _enter_fastboot(self) -> bool:
    """
    Enter fastboot mode (reboot to bootloader).
    
    This is the FIRST transition to fastboot mode.
    After this, device will remain in fastboot until we transition to fastbootd.
    
    Returns:
        True if device enters fastboot successfully
    """
    # If device is already in fastboot, skip reboot
    test_result = self.transport.fastboot_command(["getvar", "product"], timeout=5)
    if test_result.get("success"):
        self._log("Device is already in fastboot mode", "info")
        return True
    
    # Reboot to bootloader
    self._log("Rebooting device to bootloader fastboot mode...", "info")
    result = self.transport.adb_command(["reboot", "bootloader"], timeout=60)
    
    if not result.get("success"):
        self._log("Failed to reboot to bootloader via ADB, device may already be in fastboot", "warning")
    
    # Wait for fastboot
    self._log("Waiting for device to enter fastboot mode (this may take up to 60 seconds)...", "info")
    if not self.transport.wait_for_fastboot(timeout=90):
        return False
    
    self._log("Device successfully entered fastboot mode", "info")
    return True
```

**Process**:
1. Check if device is already in fastboot mode
2. If not, execute `adb reboot bootloader`
3. Wait up to 90 seconds for device to appear in `fastboot devices`
4. Verify device is accessible via fastboot commands

---

## Device State Detection

### Backend Detection

**API**: `GET /devices`

**Implementation**: `backend/py-service/app/utils/tools.py`

The backend checks both ADB and Fastboot devices:

```python
def get_devices() -> List[Dict[str, str]]:
    """Get list of connected devices"""
    devices = []
    
    # Get ADB devices
    result = run_adb_command(["devices"], timeout=10)
    # Parse ADB output: "SERIAL\tdevice"
    
    # Get Fastboot devices
    result = run_fastboot_command(["devices"], timeout=15)
    # Parse Fastboot output: "SERIAL\tfastboot"
    
    return devices
```

**Device States**:
- `device` - Device is in ADB mode (normal Android)
- `fastboot` - Device is in fastboot mode
- `unauthorized` - Device needs USB debugging authorization
- `offline` - Device is disconnected or rebooting

### Frontend Detection (WebADB)

**Hook**: `frontend/apps/web-flasher/src/hooks/useWebADBDevice.ts`

**Library**: `@flashdash/device-manager`

The frontend detects devices using WebADB:

```typescript
const { devices, requestDeviceAccess } = useWebADBDevice();

// Devices detected via WebADB have:
// - serial: Device serial number
// - state: 'device' | 'fastboot' | 'unauthorized'
// - bootloaderUnlocked: boolean
// - inFastbootMode: boolean
```

**WebADB Detection**:
- Uses WebUSB API to access USB devices
- Connects via `@yume-chan/adb-backend-webusb`
- Detects device state (ADB or Fastboot)
- Checks bootloader unlock status via ADB properties

---

## Fastboot Mode Verification

### Backend Verification

After rebooting, the backend verifies the device is in fastboot mode:

```python
# Check if device responds to fastboot commands
result = run_fastboot_command(["getvar", "product"], serial=device_serial, timeout=10)

if result and result.returncode == 0:
    # Device is in fastboot mode
    return True
```

**Fastboot Command**: `fastboot -s {serial} getvar product`

**Expected Output**: `product: {codename}` (e.g., `product: panther`)

### Frontend Verification

The frontend checks device state after reboot:

```typescript
// After reboot, check if device is in fastboot mode
const updatedDevices = await deviceManager.getDevices();
const device = updatedDevices.find(d => d.serial === serial);

if (device?.state === 'fastboot' || device?.inFastbootMode) {
    // Device is in fastboot mode
    setCurrentStep('fastboot_mode');
}
```

---

## Complete Flow Examples

### Example 1: Manual Reboot via API

```bash
# 1. List devices
curl https://freedomos.vulcantech.co/devices
# Response: [{"serial": "ABC123XYZ", "state": "device", ...}]

# 2. Reboot to bootloader
curl -X POST https://freedomos.vulcantech.co/devices/ABC123XYZ/reboot/bootloader
# Response: {"success": true, "message": "Device rebooting to bootloader"}

# 3. Wait 10-30 seconds for device to reboot

# 4. Check devices again
curl https://freedomos.vulcantech.co/devices
# Response: [{"serial": "ABC123XYZ", "state": "fastboot", ...}]
```

### Example 2: Web Flasher Flow

```typescript
// 1. Detect device via WebADB
const { devices, requestDeviceAccess } = useWebADBDevice();
await requestDeviceAccess();
// Device detected: { serial: "ABC123XYZ", state: "device" }

// 2. Check bootloader state
const device = devices[0];
if (device.bootloaderState === 'locked') {
    // Bootloader is locked, will be unlocked during flash
}

// 3. Reboot to bootloader
const { rebootToBootloader } = useWebADBDevice();
await rebootToBootloader(device.serial);
// Device rebooting...

// 4. Wait and verify
setTimeout(async () => {
    const updatedDevices = await deviceManager.getDevices();
    const updatedDevice = updatedDevices.find(d => d.serial === device.serial);
    if (updatedDevice?.inFastbootMode) {
        // Device is now in fastboot mode
        // Ready to flash
    }
}, 10000);
```

### Example 3: Automatic Reboot During Flash

```bash
# 1. Start flash process
curl -X POST https://freedomos.vulcantech.co/flash/device-flash \
  -H "Content-Type: application/json" \
  -d '{
    "serial": "ABC123XYZ",
    "codename": "panther",
    "state": "device",
    "bootloader_unlocked": false
  }'

# Response: {"success": true, "job_id": "uuid-here"}

# 2. Backend automatically:
#    - Checks if device is in fastboot (it's not, state="device")
#    - Executes: adb -s ABC123XYZ reboot bootloader
#    - Waits for device to enter fastboot mode
#    - Verifies fastboot connection
#    - Continues with flashing process

# 3. Monitor flash progress
curl https://freedomos.vulcantech.co/flash/jobs/{job_id}/stream
```

---

## API Endpoints Summary

### Device Reboot

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices/{device_id}/reboot/bootloader` | POST | Reboot device to bootloader mode |

### Device Detection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices` | GET | List all devices (ADB and Fastboot) |
| `/devices` | POST | Register devices from frontend (WebADB) |
| `/devices/{device_id}/identify` | GET | Identify device codename |

### Flash Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/flash/device-flash` | POST | Start flash from frontend device (auto-reboots if needed) |
| `/flash/unlock-and-flash` | POST | Unlock and flash (auto-reboots if needed) |
| `/flash/jobs/{job_id}` | GET | Get flash job status |
| `/flash/jobs/{job_id}/stream` | GET | Stream flash logs (SSE) |

---

## Technical Details

### ADB Reboot Command

**Command**: `adb -s {serial} reboot bootloader`

**What it does**:
- Sends reboot command to Android device via ADB
- Device immediately reboots
- ADB connection is terminated (expected)
- Device boots into fastboot mode instead of normal Android

**Timeout**: 60 seconds (device may take time to reboot)

**Expected Behavior**:
- ADB command may timeout or lose connection (normal)
- Device will appear in `fastboot devices` after reboot
- Fastboot commands become available

### Fastboot Detection

**Command**: `fastboot -s {serial} getvar product`

**What it does**:
- Tests if device responds to fastboot commands
- Returns device codename if successful
- Confirms device is in fastboot mode

**Timeout**: 5-10 seconds (quick check)

**Expected Output**:
```
product: panther
Finished. Total time: 0.001s
```

### WebADB Reboot

**Library**: `@yume-chan/adb`

**Method**: `adb.reboot('bootloader')`

**What it does**:
- Uses WebUSB API to communicate with device
- Sends reboot command via USB
- Device reboots into fastboot mode
- Browser loses WebADB connection (expected)

**Browser Requirements**:
- Chrome/Edge (WebUSB support)
- HTTPS connection (required for WebUSB)
- User permission granted for USB device access

---

## Troubleshooting

### Device Not Entering Fastboot Mode

**Symptoms**:
- Reboot command succeeds but device doesn't appear in fastboot
- Device reboots normally instead of fastboot

**Solutions**:
1. **Check USB connection**: Ensure USB cable is connected and working
2. **Check USB debugging**: Device must have USB debugging enabled
3. **Manual reboot**: Try manually rebooting device to fastboot (Power + Volume Down)
4. **Check device compatibility**: Ensure device supports fastboot mode
5. **Wait longer**: Some devices take 30-60 seconds to enter fastboot

### Connection Lost During Reboot

**Symptoms**:
- API returns success but connection is lost
- Error: "device offline" or timeout

**This is Normal**:
- ADB connection is lost during reboot (expected)
- Device will reconnect in fastboot mode
- Wait 10-30 seconds and check devices again

### WebADB Reboot Fails

**Symptoms**:
- Browser shows error: "Failed to reboot to bootloader"
- Device doesn't reboot

**Solutions**:
1. **Check browser**: Use Chrome or Edge (WebUSB support)
2. **Check HTTPS**: Must be on HTTPS (not HTTP)
3. **Grant permissions**: Ensure USB device access is granted
4. **Check device**: Device must be in ADB mode (not fastboot already)
5. **Try backend API**: Use `POST /devices/{serial}/reboot/bootloader` instead

---

## Summary

**Fastboot mode entry** in FlashDash works through:

1. **Backend API**: `POST /devices/{device_id}/reboot/bootloader`
   - Uses ADB command: `adb reboot bootloader`
   - Waits for device to enter fastboot
   - Verifies with fastboot commands

2. **Frontend WebADB**: `deviceManager.rebootToBootloader(serial)`
   - Uses WebUSB API
   - Sends reboot via WebADB
   - Updates device state locally

3. **Automatic during flash**: Flash engine auto-reboots if needed
   - Checks current device state
   - Reboots if not in fastboot
   - Waits and verifies fastboot mode

**Device detection**:
- Backend: `GET /devices` (checks ADB and Fastboot)
- Frontend: WebADB via `@flashdash/device-manager`

**Verification**:
- Backend: `fastboot getvar product`
- Frontend: Check `device.state === 'fastboot'` or `device.inFastbootMode`

---

**Last Updated**: January 2025
**Version**: 1.0.0

# Complete Local Flash Implementation

## Overview

The Electron app now contains **all** the flashing logic from the Python backend, ported to Node.js. The app no longer needs backend APIs for flashing - it executes everything locally using the extracted bundle folder.

## Architecture

### Components

1. **`flasher.js`** - Complete GrapheneOS flasher implementation
   - Ported from `backend/flasher.py`
   - Implements official GrapheneOS flashing sequence
   - Handles all partition flashing, reboots, and error handling

2. **`main.js`** - Electron main process
   - Finds fastboot/ADB executables automatically
   - Downloads and extracts bundles locally
   - Executes flash using `GrapheneFlasher` class
   - Streams progress to renderer via IPC

3. **`app.js`** (renderer) - Frontend UI
   - Downloads bundle (required)
   - Extracts bundle automatically
   - Executes local flash
   - Shows real-time progress

## Flash Sequence (Matches Python Backend)

The flash sequence follows the **exact** order from the Python backend:

1. **Pre-flight Checks**
   - Verify device product
   - Verify slot-count (must be 2)

2. **Bootloader Flash** (2 passes to other slot)
   - Flash bootloader to other slot (first pass)
   - Set active slot to other
   - Reboot bootloader
   - Wait 5 seconds + USB re-enumeration
   - Flash bootloader to other slot (second pass)
   - Set active slot to other
   - Reboot bootloader
   - Wait 5 seconds + USB re-enumeration
   - Set active slot to A

3. **Radio Flash**
   - Flash radio
   - Reboot bootloader (LAST reboot before core partitions)
   - Wait 5 seconds + USB re-enumeration

4. **AVB Custom Key Operations**
   - Erase avb_custom_key (may fail if doesn't exist - normal)
   - Flash avb_pkmd.bin (if present)

5. **OEM Operations**
   - Disable UART

6. **Erase Operations**
   - Erase fips, dpm_a, dpm_b

7. **Android-info Validation**
   - Validate android-info.zip (non-blocking)

8. **Snapshot Update Cancel**
   - Cancel any pending snapshot updates

9. **Core Partitions** (NO MORE REBOOTS)
   - Flash: boot, init_boot, dtbo, vendor_kernel_boot, pvmfw, vendor_boot, vbmeta
   - All in one continuous session

10. **Erase User Data**
    - Erase userdata
    - Erase metadata

11. **Super Partition** (in bootloader fastboot, NOT fastbootd)
    - Flash all super_*.img files sequentially
    - Sorted for correct order

12. **Final Reboot**
    - Reboot device

## Key Features

### Automatic Tool Detection

The app automatically finds `fastboot` and `adb` executables:
- Checks common installation paths
- Uses `which`/`where` command as fallback
- Supports Windows, macOS, and Linux

### USB Re-enumeration Handling

Tensor Pixels (Pixel 6-8) reset USB on bootloader reboot. The flasher:
- Waits for device to reconnect after reboots
- Handles USB disconnect/reconnect gracefully
- Uses `_waitForFastboot()` with proper timeouts

### Error Handling

- Hard fails on critical errors (bootloader, radio, core partitions)
- Warns on non-critical errors (erase operations, validation)
- Provides detailed error messages with partition context

### Progress Streaming

- Real-time log streaming via IPC
- Shows step, partition, and status for each operation
- Frontend displays progress in UI

## Bundle Structure

Bundles are stored locally at:
- **macOS**: `~/Library/Application Support/FlashDash/bundles/{codename}/{version}/`
- **Windows**: `%APPDATA%/FlashDash/bundles/{codename}/{version}/`
- **Linux**: `~/.config/FlashDash/bundles/{codename}/{version}/`

After extraction, contains:
```
bundles/
  └── panther/
      └── 2026011300/
          ├── flash-all.sh
          ├── flash-all.bat
          ├── bootloader-panther-*.img
          ├── radio-panther-*.img
          ├── boot.img
          ├── init_boot.img
          ├── dtbo.img
          ├── vendor_kernel_boot.img
          ├── pvmfw.img
          ├── vendor_boot.img
          ├── vbmeta.img
          ├── super_*.img (multiple split images)
          ├── avb_pkmd.bin (optional)
          ├── android-info.zip
          └── metadata.json
```

## Usage Flow

1. User selects device and version
2. App downloads bundle ZIP (if not cached)
3. App extracts bundle automatically
4. App reboots device to fastboot (if needed)
5. App executes flash using `GrapheneFlasher`
6. Progress streams to UI in real-time
7. Flash completes, device reboots

## No Backend Dependencies

The Electron app is now **completely independent** for flashing:
- ✅ No backend API calls for flash execution
- ✅ All logic runs locally
- ✅ Uses local bundle folder directly
- ✅ Direct USB device access

Backend is still used for:
- Device registration (optional)
- Bundle metadata/listing (optional)
- Bundle download URLs (if downloading from server)

## Testing

To test:
1. Ensure `fastboot` and `adb` are in PATH or common locations
2. Connect device via USB
3. Select device and version in app
4. Click "Flash"
5. Watch progress logs
6. Verify device flashes successfully

## Differences from Python Backend

1. **Language**: Node.js instead of Python
2. **Execution**: Electron main process instead of subprocess
3. **Progress**: IPC events instead of JSON stdout
4. **Tool Detection**: Automatic path finding instead of explicit paths
5. **Error Handling**: JavaScript exceptions instead of sys.exit()

## Benefits

- ✅ **Faster**: No network latency for flash commands
- ✅ **Reliable**: Direct USB access, no network issues
- ✅ **Offline**: Works without internet after bundle download
- ✅ **Secure**: All operations run locally
- ✅ **Complete**: All Python backend logic ported

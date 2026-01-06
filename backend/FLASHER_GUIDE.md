# GrapheneOS Flasher - Complete Workflow Guide

## Overview

This document explains the complete flashing workflow for Google Pixel 7 (panther) with bootloader unlock support. The `flasher.py` script implements a production-grade, safety-first approach to flashing GrapheneOS.

## Table of Contents

1. [Workflow Overview](#workflow-overview)
2. [Fastboot Command Reference](#fastboot-command-reference)
3. [Safety Requirements](#safety-requirements)
4. [Why Manual Unlock is Required](#why-manual-unlock-is-required)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)

---

## Workflow Overview

The flasher implements a 6-step process:

### STEP 1: Preflight Checks (ADB Mode)

**Purpose**: Validate environment and device state before attempting unlock/flash

**Actions**:
1. Verify `fastboot` and `adb` binaries exist and are executable
2. Check for connected devices via `adb devices`
3. **CRITICAL**: Verify OEM unlocking is enabled via `adb shell getprop sys.oem_unlock_allowed`
   - Must return `1` (enabled)
   - If disabled, script aborts with instructions
4. Reboot device to bootloader: `adb reboot bootloader`
5. Wait up to 30 seconds for device to enter fastboot mode

**Why this matters**: 
- OEM unlock check prevents wasted time and potential bricking
- Ensures device is in correct state before proceeding
- Validates tool availability before starting irreversible operations

---

### STEP 2: Validate Fastboot State

**Purpose**: Confirm device identity and bootloader lock status

**Actions**:
1. Verify device appears in `fastboot devices`
2. Get device codename: `fastboot getvar product`
   - Must return `panther` (Pixel 7)
   - Script aborts if mismatch
3. Get unlock status: `fastboot getvar unlocked`
   - Returns `yes` or `no`

**Why this matters**:
- Prevents flashing wrong device (could brick device)
- Determines if unlock step is needed
- Ensures device is responding in fastboot mode

---

### STEP 3: Bootloader Unlock (If Locked)

**Purpose**: Unlock bootloader to allow custom firmware installation

**Actions**:
1. Check if already unlocked (skip if `unlocked == "yes"`)
2. Display data wipe warning to user
3. Execute: `fastboot flashing unlock`
4. **PAUSE**: Script waits for user to confirm on device screen
   - User must press Volume Up/Down + Power on device
   - This is a PHYSICAL confirmation requirement
5. Poll `fastboot getvar unlocked` up to 60 times (2 second intervals)
   - Device may reboot during unlock
   - Script waits for device to return to fastboot mode
6. Verify unlock succeeded (`unlocked == "yes"`)

**Critical Safety Features**:
- ❌ NEVER attempts silent unlock
- ❌ NEVER bypasses device confirmation
- ❌ NEVER auto-proceeds if unlock fails
- ✅ Requires user to physically confirm on device
- ✅ Verifies unlock succeeded before continuing

**Why manual confirmation is required**: See [Why Manual Unlock is Required](#why-manual-unlock-is-required)

---

### STEP 4: Reboot Back to Fastboot

**Purpose**: Ensure device is in clean fastboot state before flashing

**Actions**:
1. Execute: `fastboot reboot bootloader`
2. Wait up to 30 seconds for device to return to fastboot mode
3. Verify device is responsive

**Why this matters**:
- After unlock, device may be in inconsistent state
- Fresh bootloader session ensures clean state
- Validates device survived unlock process

---

### STEP 5: Flash GrapheneOS

**Purpose**: Flash all required partitions from local bundle

**Flash Order** (critical - must follow this sequence):

1. **Bootloader** (`bootloader-panther-*.img`)
   ```bash
   fastboot flash bootloader bootloader-panther-*.img
   fastboot reboot bootloader  # Required after bootloader flash
   ```
   - Wait for device to return to fastboot mode

2. **Radio** (`radio-panther-*.img`)
   ```bash
   fastboot flash radio radio-panther-*.img
   fastboot reboot bootloader  # Required after radio flash
   ```
   - Wait for device to return to fastboot mode

3. **Core Partitions** (no reboot needed between these)
   ```bash
   fastboot flash boot boot.img
   fastboot flash vendor_boot vendor_boot.img
   fastboot flash dtbo dtbo.img
   ```

4. **System Partitions** (choose one method)

   **Method A: Super Partition (Preferred - Split Images)**
   ```bash
   fastboot flash super super_1.img
   fastboot flash super super_2.img
   # ... repeat for all super_*.img files in order
   ```

   **Method B: Individual Partitions (Fallback)**
   ```bash
   fastboot flash system system.img
   fastboot flash product product.img
   fastboot flash vendor vendor.img
   ```

5. **Verified Boot Metadata**
   ```bash
   fastboot flash vbmeta vbmeta.img --disable-verity --disable-verification
   ```
   - `--disable-verity`: Disables dm-verity (required for custom ROMs)
   - `--disable-verification`: Disables AVB verification

**Error Handling**:
- Script aborts immediately on ANY fastboot error
- No automatic retries (prevents double-flashing)
- All errors include full fastboot output for debugging

---

### STEP 6: Final Reboot

**Purpose**: Boot device into newly flashed GrapheneOS

**Actions**:
1. Execute: `fastboot reboot`
2. Device boots normally into GrapheneOS
3. Script completes

---

## Fastboot Command Reference

### Device Detection & Status

```bash
# List devices in fastboot mode
fastboot devices

# Get device information (outputs to stderr)
fastboot getvar product          # Device codename (e.g., "panther")
fastboot getvar unlocked         # Bootloader lock status ("yes" or "no")
fastboot getvar version-bootloader
fastboot getvar version-baseband
```

### Bootloader Operations

```bash
# Unlock bootloader (requires device confirmation)
fastboot flashing unlock

# Lock bootloader (not used in this workflow)
fastboot flashing lock

# Reboot to bootloader
fastboot reboot bootloader

# Reboot normally
fastboot reboot

# Reboot to recovery (not used in this workflow)
fastboot reboot recovery
```

### Partition Flashing

```bash
# Flash a partition
fastboot flash <partition_name> <image_file.img>

# Flash with verification disabled (vbmeta only)
fastboot flash vbmeta <vbmeta.img> --disable-verity --disable-verification

# Flash super partition (split images)
fastboot flash super <super_1.img>
fastboot flash super <super_2.img>
# ... (must flash all split images)
```

### Pixel 7 (panther) Partition List

| Partition | Image File | Reboot After? | Notes |
|-----------|------------|---------------|-------|
| `bootloader` | `bootloader-panther-*.img` | ✅ Yes | Firmware version specific |
| `radio` | `radio-panther-*.img` | ✅ Yes | Baseband version specific |
| `boot` | `boot.img` | ❌ No | Kernel/initramfs |
| `vendor_boot` | `vendor_boot.img` | ❌ No | Vendor-specific boot components |
| `dtbo` | `dtbo.img` | ❌ No | Device Tree Blob Overlay |
| `super` | `super_*.img` (split) | ❌ No | Dynamic partition (system/product/vendor) |
| `vbmeta` | `vbmeta.img` | ❌ No | Verified Boot metadata |

**Note**: `super` partition contains `system`, `product`, and `vendor` as logical partitions. Individual flashing of these is only needed if super partition is not available.

---

## Safety Requirements

### Hard Requirements (Script Enforces)

1. **OEM Unlocking Must Be Enabled**
   - Checked before any operations
   - Script aborts with instructions if disabled

2. **Device Codename Must Match**
   - Must be `panther` (Pixel 7)
   - Prevents flashing wrong device

3. **Bootloader Unlock Requires Physical Confirmation**
   - User must press buttons on device
   - Script waits for confirmation
   - Never attempts silent unlock

4. **All Flashing Operations Hard Fail on Error**
   - No automatic retries
   - Immediate abort on any fastboot error
   - Full error output preserved

5. **Reboot Validation**
   - After bootloader/radio flash, device must return to fastboot
   - Aborts if device doesn't respond within timeout

### Safety Guarantees

✅ **Never** auto-enables OEM unlocking  
✅ **Never** bypasses user confirmation  
✅ **Never** flashes if device mismatch  
✅ **Never** unlocks bootloader silently  
✅ **Never** proceeds after unlock without re-validation  
✅ **Never** retries flashing automatically  

---

## Why Manual Unlock is Required

### Technical Reason

Android bootloader unlock is a **destructive operation** that:
1. Wipes all user data (factory reset)
2. Changes device security state permanently
3. Voids device warranty
4. Cannot be easily reversed (requires re-locking, which may brick device)

### Security Reasons

1. **Prevents Accidental Data Loss**
   - User must be physically present
   - Confirmation prompt on device screen requires button presses
   - Prevents remote/unattended unlocks

2. **Legal/Compliance**
   - Warranty implications
   - Corporate device management policies
   - Regulatory requirements in some regions

3. **Prevents Malicious Unlocks**
   - Remote attack prevention
   - Requires physical access
   - Device owner awareness

### Why Not Automate?

❌ **Automated unlock would be dangerous because**:
- Could wipe data without user knowledge
- Could be exploited remotely
- Violates Android security model
- Could void warranties unintentionally

✅ **Manual unlock ensures**:
- User is physically present
- User understands consequences
- User explicitly consents to data wipe
- Compliance with Android security standards

### Implementation Note

The script uses `fastboot flashing unlock` which:
- Sends unlock command to device
- Device displays confirmation screen
- User must use Volume keys + Power to confirm
- Device completes unlock and may reboot
- Script polls to verify unlock succeeded

**Script behavior during unlock**:
- Executes unlock command
- Waits (up to 5 minutes) for user interaction
- Polls device status (handles reboots)
- Verifies unlock completed successfully
- Aborts if verification fails

---

## Usage Examples

### Basic Usage (Unlock + Flash)

```bash
python3 flasher.py \
  --fastboot-path /usr/local/bin/fastboot \
  --adb-path /usr/local/bin/adb \
  --bundle-path ~/.graphene-installer/bundles/panther/2025122500 \
  --confirm
```

### With Device Serial (Multiple Devices)

```bash
python3 flasher.py \
  --fastboot-path /usr/local/bin/fastboot \
  --adb-path /usr/local/bin/adb \
  --bundle-path /path/to/bundle/panther/2025122500 \
  --device-serial ABC123XYZ \
  --confirm
```

### Skip Unlock (Already Unlocked)

```bash
python3 flasher.py \
  --fastboot-path /usr/local/bin/fastboot \
  --adb-path /usr/local/bin/adb \
  --bundle-path /path/to/bundle/panther/2025122500 \
  --skip-unlock \
  --confirm
```

### Using Environment Variables

```bash
export FASTBOOT_PATH=/usr/local/bin/fastboot
export ADB_PATH=/usr/local/bin/adb
export GRAPHENE_BUNDLE_PATH=~/.graphene-installer/bundles/panther/2025122500

python3 flasher.py \
  --fastboot-path "$FASTBOOT_PATH" \
  --adb-path "$ADB_PATH" \
  --bundle-path "$GRAPHENE_BUNDLE_PATH" \
  --confirm
```

---

## Troubleshooting

### "No devices found in ADB mode"

**Causes**:
- USB debugging not enabled
- Device not authorized for USB debugging
- USB cable issue
- Device not connected

**Solutions**:
1. Enable Developer options: Settings > About phone > Tap "Build number" 7 times
2. Enable USB debugging: Settings > Developer options > USB debugging
3. Connect device and accept authorization prompt on device screen
4. Try different USB cable/port

### "OEM unlocking is disabled"

**Solution**:
1. Settings > About phone > Tap "Build number" 7 times
2. Settings > Developer options > Enable "OEM unlocking"
3. Reconnect device and try again

**Note**: Some carrier-locked devices cannot enable OEM unlocking.

### "Device mismatch: expected 'panther', got 'cheetah'"

**Cause**: Wrong device model (cheetah = Pixel 7 Pro)

**Solution**: Use correct bundle for your device model.

### "Bootloader unlock verification failed"

**Causes**:
- User didn't confirm on device screen
- Device rebooted during unlock
- Unlock command failed

**Solutions**:
1. Ensure device is still connected
2. Check device screen for unlock status
3. Manually verify: `fastboot getvar unlocked`
4. If already unlocked, use `--skip-unlock` flag

### "Failed to flash bootloader"

**Causes**:
- Corrupted image file
- Wrong bootloader version
- Device communication issue

**Solutions**:
1. Verify bundle integrity (SHA256 checksums)
2. Ensure bundle matches device model
3. Try different USB cable/port
4. Check device is still in fastboot mode

### "Device did not return to bootloader"

**Causes**:
- Device rebooted to system instead
- Fastboot communication issue
- Device crashed during flash

**Solutions**:
1. Manually reboot to bootloader: `fastboot reboot bootloader`
2. Check device screen
3. Try reconnecting USB cable
4. Verify device serial: `fastboot devices`

### Device Bootloops After Flash

**Causes**:
- Incomplete flash (interrupted)
- Wrong vbmeta flags
- Corrupted system partition

**Solutions**:
1. Boot to fastboot: Power + Volume Down
2. Re-flash entire bundle
3. Ensure `--disable-verity --disable-verification` was used for vbmeta
4. Try flashing factory image first, then GrapheneOS

---

## JSON Log Format

All output is structured JSON for easy parsing by Electron frontend:

```json
{
  "step": "flash",
  "partition": "bootloader",
  "status": "success",
  "message": "✓ Bootloader flashed"
}
```

**Status types**: `info`, `success`, `warning`, `error`, `command`, `output`

**Steps**: `preflight`, `validate`, `unlock`, `reboot_fastboot`, `flash`, `reboot`, `complete`

---

## Additional Notes

### Bundle Structure

Bundles must be extracted before flashing:

```
bundle-path/
  panther-install-YYYYMMDDHH/
    bootloader-panther-*.img
    radio-panther-*.img
    boot.img
    vendor_boot.img
    dtbo.img
    super_1.img
    super_2.img
    ...
    vbmeta.img
```

### Platform Compatibility

- ✅ macOS (tested)
- ✅ Linux (tested)
- ✅ Windows (paths must use backslashes or forward slashes)

### Timeouts

- ADB commands: 30 seconds default
- Fastboot commands: 60-300 seconds (partition-dependent)
- Bootloader unlock: 300 seconds (5 minutes for user interaction)
- Device reboot wait: 30 seconds

### Error Recovery

If script fails mid-flash:
1. Boot device to fastboot mode manually
2. Verify device serial: `fastboot devices`
3. Re-run script (it will resume from current step)
4. **Never** interrupt fastboot commands manually (may brick device)

---

## Security Checklist

Before running flasher, verify:

- [ ] Device is Google Pixel 7 (panther) - check `fastboot getvar product`
- [ ] OEM unlocking is enabled in Developer options
- [ ] USB debugging is enabled and authorized
- [ ] Bundle integrity verified (SHA256 checksums)
- [ ] Device is fully charged (>50% recommended)
- [ ] All data is backed up (unlock wipes device)
- [ ] USB cable is reliable (data-capable, not charge-only)
- [ ] Only one device connected (or serial specified)
- [ ] Bundle path is correct and accessible
- [ ] fastboot/adb paths are correct for your platform

---

## License & Disclaimer

⚠️ **WARNING**: Flashing custom firmware can:
- Permanently damage your device
- Void warranties
- Result in complete data loss
- Brick your device if interrupted

Use this tool at your own risk. Always backup data before proceeding.


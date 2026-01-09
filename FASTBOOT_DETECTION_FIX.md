# Fastboot Device Detection Fix

## Issue
Device in fastboot mode not being detected by the backend API.

## Changes Made

### 1. Improved Fastboot Command Execution (`tools.py`)

**Enhanced error handling:**
- Added specific handling for `FileNotFoundError` (fastboot not installed)
- Added specific handling for `PermissionError` (USB permissions)
- Better logging for debugging command execution
- Logs stdout/stderr in debug mode

### 2. Improved Fastboot Device Parsing (`tools.py`)

**Key improvements:**
- **Better output handling**: Properly combines stdout and stderr (fastboot often outputs to stderr)
- **Flexible parsing**: Handles multiple output formats:
  - Tab-separated: `SERIAL\tfastboot`
  - Space-separated: `SERIAL fastboot`
  - Serial only: `SERIAL`
- **Better validation**: Validates serial numbers (6+ characters, alphanumeric with hyphens/underscores)
- **Filtering**: Filters out status messages, warnings, and error messages
- **More robust**: Doesn't require `returncode == 0` (fastboot can return non-zero on warnings)

### 3. Enhanced Logging (`devices.py`)

- Added info-level logging for device detection
- Logs when devices are found
- Logs device identification attempts
- Better error messages with context

### 4. Debug Endpoint (`devices.py`)

Added `/devices/debug/fastboot` endpoint to help troubleshoot:
- Shows raw fastboot command output
- Shows stdout and stderr separately
- Shows detected devices
- Shows fastboot path being used

## Testing

### 1. Check Fastboot Installation

```bash
which fastboot
fastboot --version
```

### 2. Test Fastboot Detection Manually

```bash
# Run fastboot devices command
fastboot devices

# Should output something like:
# SERIAL123456789	fastboot
```

### 3. Test via API

```bash
# Check devices endpoint
curl http://localhost:17890/devices/

# Check debug endpoint
curl http://localhost:17890/devices/debug/fastboot
```

### 4. Check Logs

```bash
# Check backend logs for device detection
# Look for messages like:
# "Listing devices - checking ADB and Fastboot..."
# "Found X device(s): [...]"
# "Found fastboot device: SERIAL"
```

## Common Issues and Solutions

### Issue 1: Fastboot Not Found

**Symptoms:**
- Debug endpoint shows `"error": "Fastboot command returned None"`
- Logs show `"Fastboot not found at path: ..."`

**Solutions:**
```bash
# Check if fastboot is installed
which fastboot

# If not installed, install platform-tools
# macOS:
brew install android-platform-tools

# Linux:
sudo apt install android-tools-fastboot
# OR download from: https://developer.android.com/tools/releases/platform-tools

# Verify installation
fastboot --version
```

### Issue 2: Permission Denied

**Symptoms:**
- Debug endpoint shows permission errors
- Logs show `"Permission denied running fastboot"`

**Solutions:**
```bash
# Check USB permissions
lsusb  # Should show your device

# Add udev rules (Linux)
sudo cat > /etc/udev/rules.d/51-android.rules << 'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

# Or run with sudo (not recommended for production)
sudo fastboot devices
```

### Issue 3: Device Not Showing in Output

**Symptoms:**
- `fastboot devices` shows device manually
- But API doesn't detect it
- Debug endpoint shows empty output

**Solutions:**

1. **Check if device is actually in fastboot mode:**
   ```bash
   fastboot devices
   # Should show: SERIAL	fastboot
   ```

2. **Check output format:**
   ```bash
   # Test raw output
   fastboot devices 2>&1
   # Check both stdout and stderr
   ```

3. **Enable debug logging:**
   ```python
   # In app/main.py, change logging level:
   logging.basicConfig(
       level=logging.DEBUG,  # Change from INFO
       ...
   )
   ```

4. **Use debug endpoint:**
   ```bash
   curl http://localhost:17890/devices/debug/fastboot
   # Check stdout_raw and stderr_raw fields
   ```

### Issue 4: USB Cable/Connection Issues

**Symptoms:**
- Device appears and disappears
- Intermittent detection
- Timeout errors

**Solutions:**
```bash
# Use a high-quality USB cable (preferably the one that came with device)
# Connect directly to computer (not through USB hub)

# Check USB connection
lsusb | grep -i google

# Restart fastboot server
fastboot kill-server
fastboot start-server
fastboot devices
```

### Issue 5: Device in Wrong Mode

**Symptoms:**
- Device shows in ADB but not fastboot
- Device booted to Android instead of fastboot mode

**Solutions:**
```bash
# Reboot to fastboot
adb reboot bootloader
# OR
# Hold Volume Down + Power during boot

# Wait for device to enter fastboot (screen should show "Fastboot Mode")
fastboot devices
```

## Debugging Steps

1. **Check Backend Logs:**
   ```bash
   # View logs in real-time
   journalctl -u graphene-flasher -f
   # OR if running manually
   tail -f /path/to/logs/backend.log
   ```

2. **Test Fastboot Manually:**
   ```bash
   # Basic test
   fastboot devices
   
   # With verbose output
   fastboot devices -l
   
   # Test specific device
   fastboot -s SERIAL devices
   ```

3. **Use Debug Endpoint:**
   ```bash
   # Get detailed output
   curl http://localhost:17890/devices/debug/fastboot | jq
   
   # Check what the API sees
   curl http://localhost:17890/devices/ | jq
   ```

4. **Check Configuration:**
   ```bash
   # Verify fastboot path in config
   grep FASTBOOT_PATH /path/to/.env
   
   # Or check settings
   curl http://localhost:17890/tools/check
   ```

## Code Changes Summary

### `tools.py` - `get_devices()` function:
- Improved fastboot output parsing
- Better handling of stdout vs stderr
- More flexible serial number validation
- Better filtering of status messages

### `tools.py` - `run_fastboot_command()` function:
- Added debug logging
- Better error handling for FileNotFoundError and PermissionError
- Improved timeout handling

### `devices.py` - `list_devices()` endpoint:
- Added info-level logging
- Better error messages
- More context in logs

### `devices.py` - New `debug_fastboot_devices()` endpoint:
- Debug endpoint for troubleshooting
- Shows raw fastboot output
- Shows detected devices

## Verification

After applying fixes, verify:

1. ✅ Device detected when in fastboot mode
2. ✅ Serial number correctly extracted
3. ✅ Device state correctly set to "fastboot"
4. ✅ No false positives (invalid devices)
5. ✅ Works with different fastboot versions
6. ✅ Handles timeout scenarios gracefully

## Next Steps

If device still not detected:

1. Check debug endpoint output: `/devices/debug/fastboot`
2. Enable DEBUG logging in backend
3. Test fastboot command manually
4. Check USB permissions and udev rules
5. Verify fastboot version compatibility
6. Check device is actually in fastboot mode (check device screen)


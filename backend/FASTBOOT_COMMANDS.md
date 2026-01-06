# Fastboot Commands Reference - Pixel 7 (panther)

Quick reference for all fastboot commands used in the GrapheneOS flashing workflow.

## Device Detection

```bash
# List all devices in fastboot mode
fastboot devices

# Get device codename (should return "panther" for Pixel 7)
fastboot getvar product

# Get bootloader unlock status ("yes" or "no")
fastboot getvar unlocked

# Get bootloader version
fastboot getvar version-bootloader

# Get baseband/radio version
fastboot getvar version-baseband
```
uvicorn app.main:app --reload --host 127.0.0.1 --port 17890
 pnpm dev
## Bootloader Operations

```bash
# Unlock bootloader (REQUIRES PHYSICAL CONFIRMATION ON DEVICE)
fastboot flashing unlock

# Lock bootloader (NOT USED in this workflow - dangerous)
# fastboot flashing lock

# Reboot to bootloader
fastboot reboot bootloader

# Reboot normally (after flashing)
fastboot reboot

# Reboot to recovery (NOT USED in this workflow)
# fastboot reboot recovery
```

## Complete Flash Sequence for Pixel 7

**⚠️ IMPORTANT**: Execute commands in this exact order. Do NOT skip reboots after bootloader/radio.

### 1. Bootloader Flash

```bash
fastboot flash bootloader bootloader-panther-cloudripper-16.4-14097579.img
fastboot reboot bootloader
# Wait for device to return to fastboot mode (check with: fastboot devices)
```

### 2. Radio Flash

```bash
fastboot flash radio radio-panther-g5300q-250909-251024-b-14326967.img
fastboot reboot bootloader
# Wait for device to return to fastboot mode
```

### 3. Core Partitions

```bash
fastboot flash boot boot.img
fastboot flash vendor_boot vendor_boot.img
fastboot flash dtbo dtbo.img
```

### 4. System Partitions (Super - Preferred)

```bash
# Flash all super partition split images in order
fastboot flash super super_1.img
fastboot flash super super_2.img
fastboot flash super super_3.img
fastboot flash super super_4.img
fastboot flash super super_5.img
fastboot flash super super_6.img
fastboot flash super super_7.img
fastboot flash super super_8.img
fastboot flash super super_9.img
fastboot flash super super_10.img
fastboot flash super super_11.img
fastboot flash super super_12.img
fastboot flash super super_13.img
fastboot flash super super_14.img
```

**Alternative - Individual Partitions** (if super not available):

```bash
fastboot flash system system.img
fastboot flash product product.img
fastboot flash vendor vendor.img
```

### 5. Verified Boot Metadata

```bash
# CRITICAL: Must disable verity and verification for custom ROMs
fastboot flash vbmeta vbmeta.img --disable-verity --disable-verification
```

### 6. Final Reboot

```bash
fastboot reboot
```

## Pixel 7 Partition List

| Partition | Description | Reboot After? | Typical Size |
|-----------|-------------|---------------|--------------|
| `bootloader` | Bootloader firmware | ✅ Yes | ~50 MB |
| `radio` | Baseband/Modem firmware | ✅ Yes | ~100 MB |
| `boot` | Kernel + initramfs | ❌ No | ~100 MB |
| `vendor_boot` | Vendor-specific boot components | ❌ No | ~50 MB |
| `dtbo` | Device Tree Blob Overlay | ❌ No | ~1 MB |
| `super` | Dynamic partition container | ❌ No | ~12 GB (split) |
| `vbmeta` | Verified Boot metadata | ❌ No | ~4 KB |

## Important Notes

### Reboot Requirements

- **MUST reboot bootloader** after flashing `bootloader` partition
- **MUST reboot bootloader** after flashing `radio` partition
- **DO NOT reboot** between core partitions or system partitions
- **DO NOT reboot** before flashing vbmeta with proper flags

### VBMeta Flags

For custom ROMs (GrapheneOS), you **MUST** use:
- `--disable-verity`: Disables dm-verity (required)
- `--disable-verification`: Disables AVB verification (required)

Without these flags, device may bootloop or fail to boot.

### Super Partition

The `super` partition is a dynamic partition that contains:
- `system` (logical partition)
- `product` (logical partition)
- `vendor` (logical partition)

When flashing split images (`super_1.img`, `super_2.img`, etc.), flash ALL of them in numerical order. Do not skip any.

### Error Handling

- If any command fails (non-zero exit), **STOP** and investigate
- Do not continue flashing if previous command failed
- Verify device is still in fastboot: `fastboot devices`
- Check device screen for error messages

## Verification Commands

After flashing, verify device state:

```bash
# Check device is still connected
fastboot devices

# Verify unlock status (should be "yes")
fastboot getvar unlocked

# Check product (should be "panther")
fastboot getvar product
```

## Common Issues

### Device Disappears After Flash

**Symptom**: `fastboot devices` shows nothing after flashing bootloader/radio

**Solution**: 
1. Wait 10-30 seconds (device is rebooting)
2. Try: `fastboot devices` again
3. If still nothing, manually boot to fastboot (Power + Volume Down)

### Flash Fails with "sparse image too large"

**Cause**: Image file is corrupted or wrong for device

**Solution**: 
1. Verify image file integrity (SHA256)
2. Ensure correct device model (panther = Pixel 7)
3. Re-download bundle if needed

### Device Bootloops After Flash

**Cause**: Missing or incorrect vbmeta flags

**Solution**:
1. Boot to fastboot: Power + Volume Down
2. Re-flash vbmeta with correct flags:
   ```bash
   fastboot flash vbmeta vbmeta.img --disable-verity --disable-verification
   ```
3. Reboot: `fastboot reboot`

## Manual Flash Example (Without Script)

If you need to flash manually without the Python script:

```bash
# 1. Enter fastboot mode
adb reboot bootloader

# 2. Verify device
fastboot devices
fastboot getvar product  # Should be "panther"

# 3. Unlock (if needed - requires device confirmation)
fastboot flashing unlock

# 4. Flash bootloader
fastboot flash bootloader bootloader-panther-*.img
fastboot reboot bootloader

# 5. Flash radio
fastboot flash radio radio-panther-*.img
fastboot reboot bootloader

# 6. Flash core partitions
fastboot flash boot boot.img
fastboot flash vendor_boot vendor_boot.img
fastboot flash dtbo dtbo.img

# 7. Flash super partition (all split images)
for img in super_*.img; do
  fastboot flash super "$img"
done

# 8. Flash vbmeta
fastboot flash vbmeta vbmeta.img --disable-verity --disable-verification

# 9. Reboot
fastboot reboot
```

## Platform-Specific Notes

### macOS/Linux

- Commands work as-is
- Use forward slashes in paths
- May need `sudo` for some fastboot operations (try without first)

### Windows

- Use `fastboot.exe` instead of `fastboot`
- Paths can use forward slashes or backslashes
- Device drivers must be installed

### Paths with Spaces

If bundle path contains spaces, quote it:

```bash
fastboot flash boot "/path/with spaces/boot.img"
```

## Timeout Values

Recommended timeouts for different operations:

- `fastboot devices`: 5-10 seconds
- `fastboot getvar`: 10 seconds
- `fastboot flash bootloader`: 120 seconds
- `fastboot flash radio`: 120 seconds
- `fastboot flash boot/vendor_boot/dtbo`: 120 seconds
- `fastboot flash super`: 300 seconds (large partitions)
- `fastboot flash vbmeta`: 120 seconds
- `fastboot reboot bootloader`: 60 seconds

These are the timeouts used by the Python flasher script.


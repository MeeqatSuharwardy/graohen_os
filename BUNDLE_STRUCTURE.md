# GrapheneOS Bundle Structure Guide

Complete guide for organizing GrapheneOS factory images in the `bundles/` directory.

## Directory Structure

The bundle structure follows this pattern:

```
bundles/
├── {codename}/                    # Device codename (e.g., panther, raven, oriole)
│   └── {version}/                 # Build version (e.g., 2025122500)
│       ├── image.zip              # Factory image ZIP file
│       ├── image.zip.sha256       # SHA256 checksum
│       ├── image.zip.sig          # Signature file
│       ├── flash-all.sh           # Flash script (Linux/Mac)
│       ├── flash-all.bat          # Flash script (Windows)
│       ├── metadata.json          # Build metadata (optional)
│       └── {codename}-install-{version}/  # Extracted install directory
│           ├── boot.img
│           ├── vendor_boot.img
│           ├── init_boot.img
│           ├── dtbo.img
│           ├── vbmeta.img
│           ├── vendor_kernel_boot.img
│           ├── pvmfw.img
│           ├── bootloader-{codename}-*.img
│           ├── radio-{codename}-*.img
│           ├── super_1.img
│           ├── super_2.img
│           ├── ...
│           └── super_14.img
```

## Example Structure

### Pixel 7 (panther)

```
bundles/
└── panther/
    └── 2025122500/
        ├── image.zip
        ├── image.zip.sha256
        ├── image.zip.sig
        ├── flash-all.sh
        ├── flash-all.bat
        ├── metadata.json
        └── panther-install-2025122500/
            ├── android-info.txt
            ├── android-info.zip
            ├── avb_pkmd.bin
            ├── boot.img
            ├── bootloader-panther-cloudripper-16.4-14097579.img
            ├── d3m2.ec.bin
            ├── dtbo.img
            ├── evt.ec.bin
            ├── init_boot.img
            ├── proto11.ec.bin
            ├── pvmfw.img
            ├── radio-panther-g5300q-250909-251024-b-14326967.img
            ├── script.txt
            ├── super_1.img
            ├── super_2.img
            ├── super_3.img
            ├── super_4.img
            ├── super_5.img
            ├── super_6.img
            ├── super_7.img
            ├── super_8.img
            ├── super_9.img
            ├── super_10.img
            ├── super_11.img
            ├── super_12.img
            ├── super_13.img
            ├── super_14.img
            ├── vbmeta.img
            ├── vendor_boot.img
            └── vendor_kernel_boot.img
```

## Required Files

### Version Directory Files

These files should be in the version directory (`bundles/{codename}/{version}/`):

- **image.zip** - Factory image ZIP file (required)
- **image.zip.sha256** - SHA256 checksum (optional but recommended)
- **image.zip.sig** - Signature file (optional but recommended)
- **flash-all.sh** - Flash script for Linux/Mac (optional)
- **flash-all.bat** - Flash script for Windows (optional)
- **metadata.json** - Build metadata (optional)

### Install Directory Files

These files should be in the install directory (`bundles/{codename}/{version}/{codename}-install-{version}/`):

#### Required Core Partitions

- **boot.img** - Boot partition
- **vendor_boot.img** - Vendor boot partition
- **init_boot.img** - Initial boot partition
- **dtbo.img** - Device tree overlay
- **vbmeta.img** - Verified boot metadata
- **vendor_kernel_boot.img** - Vendor kernel boot

#### Required Firmware

- **bootloader-{codename}-*.img** - Bootloader image (e.g., `bootloader-panther-cloudripper-16.4-14097579.img`)
- **radio-{codename}-*.img** - Radio/modem firmware (e.g., `radio-panther-g5300q-250909-251024-b-14326967.img`)

#### Required System Partitions

- **super_1.img** through **super_14.img** - Super partition split images (usually 14 files)

#### Optional Files

- **pvmfw.img** - Protected VM firmware
- **android-info.txt** - Android build information
- **android-info.zip** - Android info ZIP
- **avb_pkmd.bin** - AVB public key metadata
- **script.txt** - Flash script content
- ***.ec.bin** - EC firmware files (device-specific)

## How to Add a GrapheneOS Build

### Method 1: Download and Extract Manually

1. **Download the factory image** from [GrapheneOS Releases](https://grapheneos.org/releases)

   ```bash
   # Example for Pixel 7 (panther)
   wget https://releases.grapheneos.org/panther-factory-2025122500.zip
   ```

2. **Create the directory structure**

   ```bash
   mkdir -p bundles/panther/2025122500
   ```

3. **Extract the factory image**

   ```bash
   cd bundles/panther/2025122500
   unzip panther-factory-2025122500.zip
   ```

4. **Extract the inner image.zip**

   ```bash
   unzip image.zip
   ```

5. **Verify structure**

   ```bash
   ls -la panther-install-2025122500/
   # Should show all partition files
   ```

### Method 2: Using the API Download Endpoint

The backend provides an API endpoint to download bundles automatically:

```bash
# Download bundle via API
curl -X POST https://backend.fxmail.ai/api/v1/grapheneos/download \
  -H "Content-Type: application/json" \
  -d '{
    "codename": "panther",
    "version": "2025122500"
  }'
```

### Method 3: Copy from Existing Location

If you already have extracted builds:

```bash
# Copy entire version directory
cp -r /path/to/panther/2025122500 bundles/panther/

# Or copy just the install directory
mkdir -p bundles/panther/2025122500
cp -r /path/to/panther-install-2025122500 bundles/panther/2025122500/
```

## Supported Device Codenames

The following device codenames are supported:

- **panther** - Pixel 7
- **cheetah** - Pixel 7 Pro
- **raven** - Pixel 6 Pro
- **oriole** - Pixel 6
- **husky** - Pixel 8 Pro
- **shiba** - Pixel 8
- **akita** - Pixel 7a
- **felix** - Pixel Fold
- **tangorpro** - Pixel Tablet
- **lynx** - Pixel 7 Pro (5G)
- **bluejay** - Pixel 6a
- **barbet** - Pixel 5a
- **redfin** - Pixel 5

## Version Format

Version format: `YYYYMMDDXX`

- **YYYY** - Year (e.g., 2025)
- **MM** - Month (e.g., 12)
- **DD** - Day (e.g., 25)
- **XX** - Build number (e.g., 00)

Example: `2025122500` = December 25, 2025, build 00

## Verification

### Check Bundle Structure

```bash
# Verify bundle exists
ls -la bundles/panther/2025122500/

# Verify install directory exists
ls -la bundles/panther/2025122500/panther-install-2025122500/

# Check required files
ls -la bundles/panther/2025122500/panther-install-2025122500/*.img
```

### Verify via API

```bash
# List all bundles
curl https://backend.fxmail.ai/bundles

# Get bundle for specific device
curl https://backend.fxmail.ai/bundles/for/panther

# Verify bundle integrity
curl -X POST https://backend.fxmail.ai/bundles/verify \
  -H "Content-Type: application/json" \
  -d '{
    "bundle_path": "/app/bundles/panther/2025122500"
  }'
```

## Common Issues

### Issue: Install Directory Not Found

**Problem**: The flashing process can't find the install directory.

**Solution**: Ensure the install directory follows the pattern `{codename}-install-{version}`:

```bash
# Correct structure
bundles/panther/2025122500/panther-install-2025122500/

# Wrong structure
bundles/panther/2025122500/install/  # Wrong name
bundles/panther/2025122500/           # Files directly in version dir (may work but not recommended)
```

### Issue: Missing Partition Files

**Problem**: Some partition files are missing.

**Solution**: Ensure all required files are present:

```bash
# Check for required files
cd bundles/panther/2025122500/panther-install-2025122500/

# Core partitions
ls boot.img vendor_boot.img init_boot.img dtbo.img vbmeta.img vendor_kernel_boot.img

# Firmware
ls bootloader-*.img radio-*.img

# Super partitions
ls super_*.img | wc -l  # Should show 14 files
```

### Issue: Wrong Codename

**Problem**: Bundle is in wrong codename directory.

**Solution**: Ensure the codename matches the device:

```bash
# Check device codename
# Pixel 7 = panther
# Pixel 7 Pro = cheetah
# Pixel 6 = oriole
# etc.

# Move to correct directory
mv bundles/wrong-codename bundles/correct-codename
```

## Quick Reference

### Directory Paths

- **Local Development**: `bundles/{codename}/{version}/`
- **Docker Container**: `/app/bundles/{codename}/{version}/`
- **Install Directory**: `bundles/{codename}/{version}/{codename}-install-{version}/`

### File Patterns

- **Bootloader**: `bootloader-{codename}-*.img`
- **Radio**: `radio-{codename}-*.img`
- **Super Partitions**: `super_{1..14}.img`
- **Core Partitions**: `{boot,vendor_boot,init_boot,dtbo,vbmeta,vendor_kernel_boot}.img`

### Example Commands

```bash
# Create directory structure
mkdir -p bundles/panther/2025122500

# Extract factory image
cd bundles/panther/2025122500
unzip panther-factory-2025122500.zip
unzip image.zip

# Verify files
ls -la panther-install-2025122500/*.img

# Check super partitions
ls -1 panther-install-2025122500/super_*.img | wc -l  # Should be 14
```

---

**Last Updated**: January 2025
**Version**: 1.0.0

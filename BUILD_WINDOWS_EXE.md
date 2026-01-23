# Building Windows EXE for Production

## Current Step

You are at: `cd /root/graohen_os/frontend/packages/desktop`

## Quick Build Command

```bash
# Make sure you're in the right directory
cd /root/graohen_os/frontend/packages/desktop

# Build Windows EXE (requires Wine on Linux)
pnpm build:win
```

## Prerequisites

### Install Wine (if not already installed)

```bash
sudo apt update
sudo apt install -y wine64 wine32

# Configure Wine (first time only)
winecfg
# Accept defaults and close the configuration window
```

## Build Process

### Step 1: Ensure Dependencies are Built

```bash
cd /root/graohen_os/frontend

# Build workspace dependencies first
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build
```

### Step 2: Build Desktop App

```bash
cd /root/graohen_os/frontend/packages/desktop

# Set environment variables for Wine
export WINEPREFIX=~/.wine
export DISPLAY=:0

# Build Windows EXE
pnpm build:win
```

### Step 3: Locate Built EXE

The EXE will be in: `/root/graohen_os/frontend/packages/desktop/dist/`

Find it:
```bash
find /root/graohen_os/frontend/packages/desktop/dist -name "*.exe"
```

Common names:
- `FlashDash Setup 1.0.0.exe`
- `flashdash-desktop Setup 1.0.0.exe`

### Step 4: Copy to Downloads Directory

```bash
# Find the EXE
EXE_FILE=$(find /root/graohen_os/frontend/packages/desktop/dist -name "*.exe" | head -1)

# Copy to downloads directory
sudo cp "$EXE_FILE" /var/www/flashdash/downloads/FlashDash-Setup-1.0.0.exe
sudo chown www-data:www-data /var/www/flashdash/downloads/FlashDash-Setup-1.0.0.exe

# Verify
ls -lh /var/www/flashdash/downloads/
```

## Alternative: Build on Windows Machine

If Wine doesn't work on Linux:

1. **On Windows machine:**
   ```powershell
   cd C:\graohen_os\frontend\packages\desktop
   pnpm install
   pnpm build:win
   ```

2. **Upload EXE to server:**
   ```bash
   # On your local machine (with EXE file)
   scp "FlashDash Setup 1.0.0.exe" root@your-server:/tmp/
   
   # On server
   sudo mv /tmp/FlashDash-Setup-1.0.0.exe /var/www/flashdash/downloads/
   sudo chown www-data:www-data /var/www/flashdash/downloads/FlashDash-Setup-1.0.0.exe
   ```

## Verify Download Works

```bash
# Test download URL
curl -I https://freedomos.vulcantech.co/downloads/FlashDash-Setup-1.0.0.exe

# Should return HTTP 200 OK
```

## Troubleshooting

### Wine Build Fails

- **Error**: "wine: cannot find ..."
  - Solution: Install Wine properly: `sudo apt install --install-recommends wine64 wine32`

- **Error**: "DISPLAY not set"
  - Solution: `export DISPLAY=:0` or use `xvfb` for headless builds

### EXE Not Found After Build

- Check build output for errors
- Look in `dist/` directory: `ls -la dist/`
- Check for build logs: `cat dist/*.log` (if any)

### Build Takes Too Long

- Normal build time: 5-15 minutes
- If stuck, check system resources: `htop`
- Consider building on Windows machine instead

## Next Steps

After building EXE:

1. Copy EXE to `/var/www/flashdash/downloads/`
2. Set proper permissions
3. Test download URL
4. Users can download from: `https://freedomos.vulcantech.co/downloads/FlashDash-Setup-1.0.0.exe`

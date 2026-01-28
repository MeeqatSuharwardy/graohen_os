#!/bin/bash
# Script to create USB-ready package for FlashDash

set -e

echo "=========================================="
echo "FlashDash USB Package Creator"
echo "=========================================="
echo ""

# Configuration
USB_DIR="usb-package"
BUILD_DIR="../build/win-unpacked"
TOOLS_DIR="$USB_DIR/tools"
FLASHDASH_DIR="$USB_DIR/FlashDash"
BUNDLES_DIR="$USB_DIR/bundles"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Creating directory structure...${NC}"
mkdir -p "$USB_DIR"
mkdir -p "$TOOLS_DIR"
mkdir -p "$FLASHDASH_DIR"
mkdir -p "$BUNDLES_DIR"

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Check if build exists
if [ ! -d "$BUILD_DIR" ]; then
    echo -e "${RED}Error: Build directory not found: $BUILD_DIR${NC}"
    echo "Please run 'npm run build:win' first"
    exit 1
fi

echo -e "${YELLOW}Step 2: Copying FlashDash application...${NC}"
cp -r "$BUILD_DIR"/* "$FLASHDASH_DIR/"
echo -e "${GREEN}✓ Application copied${NC}"
echo ""

echo -e "${YELLOW}Step 3: Copying auto-flash configuration...${NC}"
if [ -f "auto-flash-config.json" ]; then
    cp "auto-flash-config.json" "$FLASHDASH_DIR/"
    echo -e "${GREEN}✓ Configuration copied${NC}"
else
    echo -e "${YELLOW}⚠ Configuration file not found, creating default...${NC}"
    cat > "$FLASHDASH_DIR/auto-flash-config.json" << EOF
{
  "autoDetect": true,
  "autoFlash": false,
  "autoFlashDelay": 5000,
  "targetCodename": null,
  "targetVersion": null,
  "skipUnlock": true,
  "bundlesPath": "../bundles",
  "showWindow": true,
  "minimizeToTray": false
}
EOF
    echo -e "${GREEN}✓ Default configuration created${NC}"
fi
echo ""

echo -e "${YELLOW}Step 4: Creating launcher script...${NC}"
cat > "$USB_DIR/START_FLASHDASH.bat" << 'BAT'
@echo off
echo ==========================================
echo FlashDash Portable - USB Launcher
echo ==========================================
echo.

REM Get USB drive letter
set USB_DRIVE=%~d0
echo USB Drive: %USB_DRIVE%
echo.

REM Add tools to PATH
set PATH=%USB_DRIVE%\tools;%PATH%
echo Added tools to PATH: %USB_DRIVE%\tools
echo.

REM Navigate to FlashDash directory
cd /d "%~dp0FlashDash"
echo Current directory: %CD%
echo.

REM Check if executable exists
if exist "FlashDash.exe" (
    echo Found FlashDash.exe
    echo Starting FlashDash...
    echo.
    start "" "FlashDash.exe"
) else if exist "resources\app\FlashDash.exe" (
    echo Found FlashDash in resources
    cd resources\app
    start "" "FlashDash.exe"
) else (
    echo ERROR: FlashDash executable not found!
    echo.
    echo Expected locations:
    echo   - FlashDash\FlashDash.exe
    echo   - FlashDash\resources\app\FlashDash.exe
    echo.
    pause
    exit /b 1
)

echo.
echo FlashDash started successfully!
echo Check the window for device detection.
echo.
echo Press any key to close this window...
pause >nul
BAT
echo -e "${GREEN}✓ Launcher script created${NC}"
echo ""

echo -e "${YELLOW}Step 5: Creating README...${NC}"
cat > "$USB_DIR/README.txt" << 'EOF'
==========================================
FlashDash Portable - USB Setup
==========================================

QUICK START:
1. Copy this entire folder to your USB drive
2. Download ADB/Fastboot tools (see below)
3. Run START_FLASHDASH.bat

ADB/FASTBOOT TOOLS:
Download from: https://developer.android.com/tools/releases/platform-tools

Extract these files to the 'tools' folder:
- adb.exe
- fastboot.exe
- AdbWinApi.dll
- AdbWinUsbApi.dll

CONFIGURATION:
Edit FlashDash/auto-flash-config.json to configure:
- Auto-detection
- Auto-flash
- Target device/version
- Bundle paths

BUNDLES:
Place GrapheneOS bundles in the 'bundles' folder:
bundles/{codename}/{version}/{codename}-install-{version}/

Example:
bundles/panther/2026011300/panther-install-2026011300/

For detailed instructions, see USB_FLASHING_SETUP.md
EOF
echo -e "${GREEN}✓ README created${NC}"
echo ""

echo -e "${YELLOW}Step 6: Checking for ADB/Fastboot tools...${NC}"
if [ -f "$TOOLS_DIR/adb.exe" ] && [ -f "$TOOLS_DIR/fastboot.exe" ]; then
    echo -e "${GREEN}✓ ADB/Fastboot tools found${NC}"
else
    echo -e "${YELLOW}⚠ ADB/Fastboot tools not found${NC}"
    echo "  Please download from:"
    echo "  https://developer.android.com/tools/releases/platform-tools"
    echo "  And extract to: $TOOLS_DIR"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}USB Package Created Successfully!${NC}"
echo "=========================================="
echo ""
echo "Package location: $USB_DIR"
echo ""
echo "Next steps:"
echo "1. Copy entire '$USB_DIR' folder to USB drive"
echo "2. Add ADB/Fastboot tools to 'tools' folder (if not already present)"
echo "3. Add GrapheneOS bundles to 'bundles' folder (optional)"
echo "4. Run START_FLASHDASH.bat from USB drive"
echo ""
echo "For detailed instructions, see: USB_FLASHING_SETUP.md"
echo ""

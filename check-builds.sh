#!/bin/bash

# FlashDash Build Files Checker
# Checks if Windows, macOS, and Linux build files exist

echo "=========================================="
echo "FlashDash Build Files Checker"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check directories
DOWNLOADS_DIR="./downloads"
WINDOWS_DIR="$DOWNLOADS_DIR/windows"
MAC_DIR="$DOWNLOADS_DIR/mac"
LINUX_DIR="$DOWNLOADS_DIR/linux"

# Expected files
WINDOWS_FILE="@flashdashdesktop Setup 1.0.0.exe"
MAC_FILE="FlashDash-1.0.0.dmg"
LINUX_APPIMAGE="flashdash-1.0.0.AppImage"
LINUX_DEB="flashdash_1.0.0_amd64.deb"

# Check Windows
echo "Checking Windows build..."
if [ -f "$WINDOWS_DIR/$WINDOWS_FILE" ]; then
    SIZE=$(du -h "$WINDOWS_DIR/$WINDOWS_FILE" | cut -f1)
    echo -e "${GREEN}✓${NC} Windows build found: $WINDOWS_FILE ($SIZE)"
else
    echo -e "${RED}✗${NC} Windows build NOT found: $WINDOWS_FILE"
    echo -e "   Expected location: $WINDOWS_DIR/$WINDOWS_FILE"
fi

# Check macOS
echo ""
echo "Checking macOS build..."
if [ -f "$MAC_DIR/$MAC_FILE" ]; then
    SIZE=$(du -h "$MAC_DIR/$MAC_FILE" | cut -f1)
    echo -e "${GREEN}✓${NC} macOS build found: $MAC_FILE ($SIZE)"
else
    echo -e "${RED}✗${NC} macOS build NOT found: $MAC_FILE"
    echo -e "   Expected location: $MAC_DIR/$MAC_FILE"
fi

# Check Linux AppImage
echo ""
echo "Checking Linux builds..."
if [ -f "$LINUX_DIR/$LINUX_APPIMAGE" ]; then
    SIZE=$(du -h "$LINUX_DIR/$LINUX_APPIMAGE" | cut -f1)
    echo -e "${GREEN}✓${NC} Linux AppImage found: $LINUX_APPIMAGE ($SIZE)"
else
    echo -e "${RED}✗${NC} Linux AppImage NOT found: $LINUX_APPIMAGE"
    echo -e "   Expected location: $LINUX_DIR/$LINUX_APPIMAGE"
fi

# Check Linux DEB
if [ -f "$LINUX_DIR/$LINUX_DEB" ]; then
    SIZE=$(du -h "$LINUX_DIR/$LINUX_DEB" | cut -f1)
    echo -e "${GREEN}✓${NC} Linux DEB found: $LINUX_DEB ($SIZE)"
else
    echo -e "${YELLOW}⚠${NC} Linux DEB not found: $LINUX_DEB (optional)"
    echo -e "   Expected location: $LINUX_DIR/$LINUX_DEB"
fi

# Check dist folder
echo ""
echo "Checking desktop package dist folder..."
DIST_DIR="frontend/packages/desktop/dist"
if [ -d "$DIST_DIR" ]; then
    echo "Files in dist folder:"
    find "$DIST_DIR" -type f \( -name "*.exe" -o -name "*.dmg" -o -name "*.AppImage" -o -name "*.deb" \) 2>/dev/null | while read file; do
        SIZE=$(du -h "$file" | cut -f1)
        echo -e "  ${YELLOW}→${NC} $(basename "$file") ($SIZE)"
    done
else
    echo -e "${YELLOW}⚠${NC} Dist folder not found: $DIST_DIR"
fi

# Summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="

MISSING=0

[ ! -f "$WINDOWS_DIR/$WINDOWS_FILE" ] && MISSING=$((MISSING+1))
[ ! -f "$MAC_DIR/$MAC_FILE" ] && MISSING=$((MISSING+1))
[ ! -f "$LINUX_DIR/$LINUX_APPIMAGE" ] && MISSING=$((MISSING+1))

if [ $MISSING -eq 0 ]; then
    echo -e "${GREEN}✓ All required build files are present!${NC}"
    exit 0
else
    echo -e "${RED}✗ Missing $MISSING required build file(s)${NC}"
    echo ""
    echo "To build the desktop apps:"
    echo "  1. cd frontend/packages/desktop"
    echo "  2. pnpm build:win    # Windows (works on any OS)"
    echo "  3. pnpm build:mac    # macOS (macOS only)"
    echo "  4. pnpm build:linux  # Linux (Linux only)"
    echo ""
    echo "Then copy builds to downloads directory:"
    echo "  cp dist/@flashdashdesktop*.exe ../../../downloads/windows/"
    echo "  cp dist/FlashDash-*.dmg ../../../downloads/mac/"
    echo "  cp dist/flashdash-*.AppImage ../../../downloads/linux/"
    exit 1
fi

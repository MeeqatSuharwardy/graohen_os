#!/bin/bash

# Copy Desktop Builds to Downloads Directory
# Run this from the project root after building

set -e

DESKTOP_DIR="frontend/packages/desktop/dist"
DOWNLOADS_DIR="downloads"

echo "Copying builds to downloads directory..."

# Windows - check for actual build name
if [ -f "$DESKTOP_DIR/flashdash-desktop Setup 1.0.0.exe" ]; then
    cp "$DESKTOP_DIR/flashdash-desktop Setup 1.0.0.exe" "$DOWNLOADS_DIR/windows/@flashdashdesktop Setup 1.0.0.exe"
    echo "✓ Windows build copied"
elif [ -f "$DESKTOP_DIR/@flashdashdesktop Setup 1.0.0.exe" ]; then
    cp "$DESKTOP_DIR/@flashdashdesktop Setup 1.0.0.exe" "$DOWNLOADS_DIR/windows/"
    echo "✓ Windows build copied"
else
    echo "⚠ Windows build not found in $DESKTOP_DIR"
fi

# macOS - check for actual build name
if [ -f "$DESKTOP_DIR/flashdash-desktop-1.0.0.dmg" ]; then
    cp "$DESKTOP_DIR/flashdash-desktop-1.0.0.dmg" "$DOWNLOADS_DIR/mac/FlashDash-1.0.0.dmg"
    echo "✓ macOS build copied"
elif [ -f "$DESKTOP_DIR/FlashDash-1.0.0.dmg" ]; then
    cp "$DESKTOP_DIR/FlashDash-1.0.0.dmg" "$DOWNLOADS_DIR/mac/"
    echo "✓ macOS build copied"
else
    echo "⚠ macOS build not found in $DESKTOP_DIR"
fi

# Linux AppImage - check for actual build name
if [ -f "$DESKTOP_DIR/flashdash-desktop-1.0.0.AppImage" ]; then
    cp "$DESKTOP_DIR/flashdash-desktop-1.0.0.AppImage" "$DOWNLOADS_DIR/linux/flashdash-1.0.0.AppImage"
    echo "✓ Linux AppImage copied"
elif [ -f "$DESKTOP_DIR/flashdash-1.0.0.AppImage" ]; then
    cp "$DESKTOP_DIR/flashdash-1.0.0.AppImage" "$DOWNLOADS_DIR/linux/"
    echo "✓ Linux AppImage copied"
else
    echo "⚠ Linux AppImage not found in $DESKTOP_DIR"
fi

# Linux DEB - check for actual build name
if [ -f "$DESKTOP_DIR/flashdash-desktop_1.0.0_amd64.deb" ]; then
    cp "$DESKTOP_DIR/flashdash-desktop_1.0.0_amd64.deb" "$DOWNLOADS_DIR/linux/flashdash_1.0.0_amd64.deb"
    echo "✓ Linux DEB copied"
elif [ -f "$DESKTOP_DIR/flashdash_1.0.0_amd64.deb" ]; then
    cp "$DESKTOP_DIR/flashdash_1.0.0_amd64.deb" "$DOWNLOADS_DIR/linux/"
    echo "✓ Linux DEB copied"
else
    echo "⚠ Linux DEB not found in $DESKTOP_DIR (optional)"
fi

echo ""
echo "Done! Run ./check-builds.sh to verify."

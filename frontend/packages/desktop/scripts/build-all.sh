#!/bin/bash
# Build Electron app for all platforms

set -e

echo "Building FlashDash Desktop for all platforms..."

# Build Windows
echo "Building for Windows..."
pnpm build:win
echo "Windows build complete!"

# Build macOS (only on macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "Building for macOS..."
  pnpm build:mac
  echo "macOS build complete!"
else
  echo "Skipping macOS build (not on macOS)"
fi

# Build Linux
echo "Building for Linux..."
pnpm build:linux
echo "Linux build complete!"

echo "All builds complete!"
echo "Builds are in: dist/"

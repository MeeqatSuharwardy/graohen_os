#!/bin/bash

# Build FlashDash for Windows
# Usage: ./build-windows.sh [--sign]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔨 Building FlashDash for Windows..."
echo ""

# Check if signing is requested
SIGN=false
if [[ "$1" == "--sign" ]]; then
    SIGN=true
fi

cd frontend/electron

# Check if certificate is set
if [ "$SIGN" = true ]; then
    if [ -z "$CSC_LINK" ]; then
        echo "❌ Error: --sign flag used but CSC_LINK not set"
        echo ""
        echo "Set certificate path:"
        echo "  export CSC_LINK=\"/path/to/certificate.pfx\""
        echo "  export CSC_KEY_PASSWORD=\"your-password\""
        exit 1
    fi
    
    if [ ! -f "$CSC_LINK" ]; then
        echo "❌ Error: Certificate file not found: $CSC_LINK"
        exit 1
    fi
    
    echo "🔐 Code signing enabled"
    echo "   Certificate: $CSC_LINK"
else
    if [ -z "$CSC_LINK" ]; then
        echo "⚠️  Warning: No code signing certificate set (CSC_LINK)"
        echo "   Building unsigned executable (SmartScreen warning will appear)"
        echo ""
        echo "To sign the executable, set:"
        echo "  export CSC_LINK=\"/path/to/certificate.pfx\""
        echo "  export CSC_KEY_PASSWORD=\"your-password\""
        echo "  ./build-windows.sh --sign"
        echo ""
    else
        echo "🔐 Code signing certificate found, will sign automatically"
    fi
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build for Windows
echo ""
echo "🏗️  Building Windows EXE..."
echo ""

if npm run build:win; then
    echo ""
    echo "✅ Build complete!"
    echo ""
    
    # Find the output file
    OUTPUT_DIR="../build"
    if [ -d "$OUTPUT_DIR" ]; then
        EXE_FILE=$(find "$OUTPUT_DIR" -name "FlashDash Setup *.exe" -type f | head -1)
        if [ -n "$EXE_FILE" ]; then
            echo "📦 Output: $EXE_FILE"
            
            # Check if signed
            if command -v signtool &> /dev/null && [ -n "$CSC_LINK" ]; then
                echo ""
                echo "🔍 Verifying signature..."
                if signtool verify /pa "$EXE_FILE" &> /dev/null; then
                    echo "✓ Executable is signed"
                else
                    echo "⚠️  Executable signature verification failed (may be normal for self-signed)"
                fi
            fi
        fi
    fi
    
    echo ""
    echo "📋 Next steps:"
    echo "   1. Test the installer on a Windows machine"
    echo "   2. Check SmartScreen behavior"
    echo "   3. Distribute through trusted channels (GitHub, website)"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi

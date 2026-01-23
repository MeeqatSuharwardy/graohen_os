#!/bin/bash
# Build FlashDash Frontend for Shared Hosting Deployment
# This script builds everything locally - you just upload the files

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "FlashDash Shared Hosting Build"
echo "=========================================="
echo ""

# Configuration
BACKEND_URL="${VITE_API_BASE_URL:-https://freedomos.vulcantech.co}"
DOWNLOAD_BASE_URL="${VITE_DOWNLOAD_BASE_URL:-}"

if [ -z "$DOWNLOAD_BASE_URL" ]; then
    echo -e "${YELLOW}Enter your shared hosting domain (e.g., https://yourdomain.com):${NC}"
    read -p "Domain: " DOWNLOAD_BASE_URL
    DOWNLOAD_BASE_URL="${DOWNLOAD_BASE_URL%/}/downloads"
fi

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Backend API: $BACKEND_URL"
echo "  Downloads: $DOWNLOAD_BASE_URL"
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")/frontend" || exit 1

# Step 1: Install dependencies
echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
pnpm install
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 2: Build workspace packages
echo -e "${YELLOW}Step 2: Building workspace packages...${NC}"
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build
echo -e "${GREEN}✓ Workspace packages built${NC}"
echo ""

# Step 3: Create .env files
echo -e "${YELLOW}Step 3: Creating production .env files...${NC}"
echo "VITE_API_BASE_URL=$BACKEND_URL" > packages/web/.env
echo "VITE_DOWNLOAD_BASE_URL=$DOWNLOAD_BASE_URL" >> packages/web/.env
echo "VITE_API_BASE_URL=$BACKEND_URL" > apps/web-flasher/.env
echo "VITE_DOWNLOAD_BASE_URL=$DOWNLOAD_BASE_URL" >> apps/web-flasher/.env
echo "VITE_API_BASE_URL=$BACKEND_URL" > packages/desktop/.env
echo -e "${GREEN}✓ .env files created${NC}"
echo ""

# Step 4: Build web frontend
echo -e "${YELLOW}Step 4: Building web frontend...${NC}"
VITE_API_BASE_URL="$BACKEND_URL" VITE_DOWNLOAD_BASE_URL="$DOWNLOAD_BASE_URL" pnpm --filter @flashdash/web-flasher build
echo -e "${GREEN}✓ Web frontend built${NC}"
echo ""

# Step 5: Build desktop apps
echo -e "${YELLOW}Step 5: Building desktop apps...${NC}"

cd packages/desktop

# Windows EXE
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]] || command -v wine &> /dev/null; then
    echo "  Building Windows EXE..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        VITE_API_BASE_URL="$BACKEND_URL" pnpm build:win && echo "    ✓ Windows EXE built" || echo "    ⚠ Windows build failed"
    else
        export WINEPREFIX=~/.wine
        export DISPLAY=:0
        VITE_API_BASE_URL="$BACKEND_URL" pnpm build:win && echo "    ✓ Windows EXE built" || echo "    ⚠ Windows build failed (Wine may not be configured)"
    fi
else
    echo "  ⚠ Skipping Windows EXE (requires Windows or Wine)"
fi

# Mac DMG
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  Building Mac DMG..."
    VITE_API_BASE_URL="$BACKEND_URL" pnpm build:mac && echo "    ✓ Mac DMG built" || echo "    ⚠ Mac build failed"
else
    echo "  ⚠ Skipping Mac DMG (requires macOS)"
fi

# Linux AppImage
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "  Building Linux AppImage..."
    VITE_API_BASE_URL="$BACKEND_URL" pnpm build:linux && echo "    ✓ Linux AppImage built" || echo "    ⚠ Linux build failed"
else
    echo "  ⚠ Skipping Linux AppImage (requires Linux)"
fi

cd ../..

echo -e "${GREEN}✓ Desktop apps build complete${NC}"
echo ""

# Step 6: Create deployment package
echo -e "${YELLOW}Step 6: Creating deployment package...${NC}"
cd ..

# Remove old deployment directory
rm -rf shared-hosting-upload
mkdir -p shared-hosting-upload/downloads

# Copy web build
cp -r frontend/apps/web-flasher/dist/* shared-hosting-upload/

# Copy desktop apps
if [ -f "frontend/packages/desktop/dist/"*.exe ]; then
    EXE_FILE=$(ls frontend/packages/desktop/dist/*.exe | head -1)
    cp "$EXE_FILE" shared-hosting-upload/downloads/FlashDash-Setup-1.0.0.exe
    echo "  ✓ Windows EXE copied"
fi

if [ -f "frontend/packages/desktop/dist/"*.dmg ]; then
    DMG_FILE=$(ls frontend/packages/desktop/dist/*.dmg | head -1)
    cp "$DMG_FILE" shared-hosting-upload/downloads/FlashDash-1.0.0.dmg
    echo "  ✓ Mac DMG copied"
fi

if [ -f "frontend/packages/desktop/dist/"*.AppImage ]; then
    APPIMAGE_FILE=$(ls frontend/packages/desktop/dist/*.AppImage | head -1)
    cp "$APPIMAGE_FILE" shared-hosting-upload/downloads/flashdash-1.0.0.AppImage
    echo "  ✓ Linux AppImage copied"
fi

# Create .htaccess for Apache
cat > shared-hosting-upload/.htaccess << 'EOF'
# Enable HTTPS redirect
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# SPA Routing - redirect all requests to index.html
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_URI} !^/downloads/
RewriteRule ^ index.html [L]

# Cache static assets
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/gif "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType image/svg+xml "access plus 1 year"
    ExpiresByType text/css "access plus 1 year"
    ExpiresByType application/javascript "access plus 1 year"
    ExpiresByType application/x-javascript "access plus 1 year"
</IfModule>

# Set proper MIME types for downloads
<IfModule mod_mime.c>
    AddType application/octet-stream .exe
    AddType application/x-apple-diskimage .dmg
    AddType application/x-executable .AppImage
</IfModule>

# Force download for desktop app files
<FilesMatch "\.(exe|dmg|AppImage)$">
    Header set Content-Disposition "attachment"
    Header set Content-Type "application/octet-stream"
</FilesMatch>

# Security headers
<IfModule mod_headers.c>
    Header set X-Content-Type-Options "nosniff"
    Header set X-Frame-Options "SAMEORIGIN"
    Header set X-XSS-Protection "1; mode=block"
</IfModule>
EOF

echo -e "${GREEN}✓ Deployment package created${NC}"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Build Complete!${NC}"
echo "=========================================="
echo ""
echo "📦 Files ready in: shared-hosting-upload/"
echo ""
echo "📁 Directory structure:"
echo "   shared-hosting-upload/"
echo "   ├── index.html"
echo "   ├── assets/"
echo "   ├── downloads/"
ls -lh shared-hosting-upload/downloads/ 2>/dev/null | tail -n +2 | awk '{print "   │   └── " $9 " (" $5 ")"}' || echo "   │   └── (no downloads yet)"
echo ""
echo "📤 Next steps:"
echo "   1. Upload everything in 'shared-hosting-upload/' to your shared hosting"
echo "   2. Upload to: public_html/ or www/ directory"
echo "   3. Set file permissions: 644 for files, 755 for directories"
echo "   4. Visit: https://your-domain.com"
echo ""
echo "🔗 Backend API: $BACKEND_URL"
echo "📥 Downloads: $DOWNLOAD_BASE_URL"
echo ""

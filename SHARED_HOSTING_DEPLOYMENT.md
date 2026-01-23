# 🌐 Shared Hosting Frontend Deployment Guide

Deploy FlashDash frontend to shared hosting with downloadable Windows EXE, Mac DMG, and Linux files.

## 📋 Overview

This guide helps you:
1. **Build frontend locally** (on your computer)
2. **Build Windows EXE, Mac DMG, Linux files** locally
3. **Upload everything** to shared hosting
4. **Configure downloads** for desktop apps

**Backend**: Already live at `https://freedomos.vulcantech.co`

## 🏗️ Step 1: Build Frontend Locally

### Prerequisites

- Node.js 20+ installed
- pnpm installed (`npm install -g pnpm`)
- Your local codebase ready

### Build Process

```bash
# Navigate to frontend directory
cd frontend

# Install all dependencies
pnpm install

# Build workspace dependencies first
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build

# Create production .env files
echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > packages/web/.env
echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > apps/web-flasher/.env

# Build web frontend
pnpm --filter @flashdash/web-flasher build

# The built files will be in: frontend/apps/web-flasher/dist/
```

## 💻 Step 2: Build Desktop Apps Locally

### Build Windows EXE

**On Windows Machine:**
```powershell
cd frontend\packages\desktop

# Create .env
"VITE_API_BASE_URL=https://freedomos.vulcantech.co" | Out-File -FilePath ".env" -Encoding utf8

# Build Windows EXE
pnpm build:win

# EXE will be in: frontend/packages/desktop/dist/
# Look for: FlashDash Setup 1.0.0.exe
```

**On Mac/Linux (using Wine):**
```bash
cd frontend/packages/desktop

# Create .env
echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > .env

# Install Wine (if needed)
# macOS: brew install wine-stable
# Linux: sudo apt install wine64 wine32

# Build Windows EXE
export WINEPREFIX=~/.wine
pnpm build:win

# EXE will be in: frontend/packages/desktop/dist/
```

### Build Mac DMG

**On Mac Machine:**
```bash
cd frontend/packages/desktop

# Create .env
echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > .env

# Build Mac DMG
pnpm build:mac

# DMG will be in: frontend/packages/desktop/dist/
# Look for: FlashDash-1.0.0.dmg
```

### Build Linux AppImage

**On Linux Machine:**
```bash
cd frontend/packages/desktop

# Create .env
echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > .env

# Build Linux AppImage
pnpm build:linux

# AppImage will be in: frontend/packages/desktop/dist/
# Look for: flashdash-desktop-1.0.0.AppImage
```

## 📦 Step 3: Prepare Files for Upload

### Create Upload Directory Structure

```bash
# Create a deployment directory
mkdir -p shared-hosting-upload
cd shared-hosting-upload

# Copy frontend build
cp -r ../frontend/apps/web-flasher/dist/* .

# Create downloads directory
mkdir -p downloads

# Copy desktop app files
cp ../frontend/packages/desktop/dist/*.exe downloads/FlashDash-Setup-1.0.0.exe 2>/dev/null || echo "Windows EXE not found"
cp ../frontend/packages/desktop/dist/*.dmg downloads/FlashDash-1.0.0.dmg 2>/dev/null || echo "Mac DMG not found"
cp ../frontend/packages/desktop/dist/*.AppImage downloads/flashdash-1.0.0.AppImage 2>/dev/null || echo "Linux AppImage not found"

# Verify files
ls -lh downloads/
```

### File Structure

```
shared-hosting-upload/
├── index.html
├── assets/
│   ├── *.js
│   ├── *.css
│   └── *.png, *.svg, etc.
└── downloads/
    ├── FlashDash-Setup-1.0.0.exe  (Windows)
    ├── FlashDash-1.0.0.dmg       (Mac)
    └── flashdash-1.0.0.AppImage  (Linux)
```

## 📤 Step 4: Upload to Shared Hosting

### Via FTP/SFTP

**Using FileZilla or similar:**

1. **Connect to your shared hosting**
   - Host: `your-domain.com` or FTP IP
   - Username: Your FTP username
   - Password: Your FTP password
   - Port: 21 (FTP) or 22 (SFTP)

2. **Navigate to public_html or www directory**
   - Usually: `/public_html/` or `/www/` or `/htdocs/`

3. **Upload all files from `shared-hosting-upload/`**
   - Upload `index.html` and all files in `assets/`
   - Upload entire `downloads/` folder

4. **Set proper permissions**
   - Files: `644` (rw-r--r--)
   - Directories: `755` (rwxr-xr-x)

### Via cPanel File Manager

1. **Login to cPanel**
2. **Open File Manager**
3. **Navigate to `public_html`**
4. **Upload files:**
   - Upload all files from `shared-hosting-upload/`
   - Make sure `downloads/` folder is uploaded

### Via SSH (if available)

```bash
# On your local machine
cd shared-hosting-upload

# Upload via SCP
scp -r * user@your-domain.com:/home/user/public_html/

# Or use rsync
rsync -avz --exclude='node_modules' . user@your-domain.com:/home/user/public_html/
```

## ⚙️ Step 5: Configure Shared Hosting

### Create .htaccess File (for Apache)

Create `.htaccess` in your `public_html` directory:

```apache
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
```

### Configure Downloads Directory

Make sure `downloads/` directory is accessible and files are downloadable.

**Check file permissions:**
- Files should be readable: `644`
- Directory should be executable: `755`

## ✅ Step 6: Verify Deployment

### Test Frontend

1. **Visit your domain**: `https://your-domain.com`
2. **Should see**: FlashDash interface
3. **Check browser console** (F12) for errors
4. **Verify API calls** work (should connect to `https://freedomos.vulcantech.co`)

### Test Downloads

1. **Windows EXE**: `https://your-domain.com/downloads/FlashDash-Setup-1.0.0.exe`
2. **Mac DMG**: `https://your-domain.com/downloads/FlashDash-1.0.0.dmg`
3. **Linux AppImage**: `https://your-domain.com/downloads/flashdash-1.0.0.AppImage`

All should download properly.

## 🔧 Step 7: Update Frontend Code (One-Time Setup)

### Update Download URLs

The frontend code needs to know where downloads are hosted. Update these files:

**File**: `frontend/packages/web/src/pages/Dashboard.tsx`
**File**: `frontend/packages/web/src/pages/Landing.tsx`
**File**: `frontend/packages/web/src/pages/Downloads.tsx`

Change the download base URL to your shared hosting domain:

```typescript
const getDownloadBaseUrl = () => {
  return import.meta.env.VITE_DOWNLOAD_BASE_URL || 'https://your-domain.com/downloads';
};
```

Then rebuild and upload again.

**Or** set environment variable during build:

```bash
VITE_DOWNLOAD_BASE_URL=https://your-domain.com/downloads pnpm --filter @flashdash/web-flasher build
```

## 📋 Complete Build Script

Create `build-for-shared-hosting.sh`:

```bash
#!/bin/bash
# Build everything for shared hosting deployment

set -e

echo "Building FlashDash for Shared Hosting..."

cd frontend

# Install dependencies
echo "Installing dependencies..."
pnpm install

# Build workspace packages
echo "Building workspace packages..."
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build

# Set API URL
export VITE_API_BASE_URL=https://freedomos.vulcantech.co
export VITE_DOWNLOAD_BASE_URL=https://your-domain.com/downloads

# Build web frontend
echo "Building web frontend..."
pnpm --filter @flashdash/web-flasher build

# Build desktop apps
echo "Building desktop apps..."
cd packages/desktop

# Windows EXE (if on Windows or Wine available)
if command -v wine &> /dev/null || [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "Building Windows EXE..."
    export VITE_API_BASE_URL=https://freedomos.vulcantech.co
    pnpm build:win || echo "Windows build skipped"
fi

# Mac DMG (if on Mac)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Building Mac DMG..."
    export VITE_API_BASE_URL=https://freedomos.vulcantech.co
    pnpm build:mac || echo "Mac build skipped"
fi

# Linux AppImage (if on Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Building Linux AppImage..."
    export VITE_API_BASE_URL=https://freedomos.vulcantech.co
    pnpm build:linux || echo "Linux build skipped"
fi

cd ../..

# Create deployment package
echo "Creating deployment package..."
rm -rf shared-hosting-upload
mkdir -p shared-hosting-upload/downloads

# Copy web build
cp -r apps/web-flasher/dist/* shared-hosting-upload/

# Copy desktop apps
cp packages/desktop/dist/*.exe shared-hosting-upload/downloads/FlashDash-Setup-1.0.0.exe 2>/dev/null || true
cp packages/desktop/dist/*.dmg shared-hosting-upload/downloads/FlashDash-1.0.0.dmg 2>/dev/null || true
cp packages/desktop/dist/*.AppImage shared-hosting-upload/downloads/flashdash-1.0.0.AppImage 2>/dev/null || true

# Create .htaccess
cat > shared-hosting-upload/.htaccess << 'EOF'
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteCond %{REQUEST_URI} !^/downloads/
RewriteRule ^ index.html [L]

<FilesMatch "\.(exe|dmg|AppImage)$">
    Header set Content-Disposition "attachment"
    Header set Content-Type "application/octet-stream"
</FilesMatch>
EOF

echo ""
echo "✅ Build complete!"
echo ""
echo "Files ready in: shared-hosting-upload/"
echo "Upload everything in that folder to your shared hosting public_html directory"
echo ""
ls -lh shared-hosting-upload/downloads/
```

## 🚀 Quick Deployment Checklist

- [ ] Frontend built locally
- [ ] Windows EXE built (or uploaded separately)
- [ ] Mac DMG built (or uploaded separately)
- [ ] Linux AppImage built (or uploaded separately)
- [ ] All files in `shared-hosting-upload/` directory
- [ ] Files uploaded to shared hosting `public_html/`
- [ ] `.htaccess` file uploaded
- [ ] File permissions set correctly (644 for files, 755 for directories)
- [ ] Frontend accessible: `https://your-domain.com`
- [ ] Downloads working: `https://your-domain.com/downloads/*.exe`
- [ ] API calls connecting to: `https://freedomos.vulcantech.co`

## 🔄 Updating Frontend

When you need to update:

1. **Rebuild locally** using the build script
2. **Upload new files** to shared hosting (replace old files)
3. **Clear browser cache** or wait for CDN cache to expire

## 📝 Notes

- **No backend code** needs to be on shared hosting - backend is already live
- **All builds done locally** - you just upload the built files
- **Downloads directory** contains the desktop app installers
- **Frontend connects** to `https://freedomos.vulcantech.co` for API calls

---

**Your frontend is now ready for shared hosting deployment!** 🎉

Upload the `shared-hosting-upload/` folder contents to your shared hosting and you're done!

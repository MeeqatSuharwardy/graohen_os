# 🚀 Quick Shared Hosting Build Guide

Build and deploy FlashDash frontend to shared hosting in 3 simple steps.

## ⚡ Quick Start

### Step 1: Run Build Script

```bash
# From project root
./build-for-shared-hosting.sh
```

The script will:
- Ask for your shared hosting domain
- Build all frontend dependencies
- Build web frontend
- Build desktop apps (Windows/Mac/Linux if available)
- Create deployment package in `shared-hosting-upload/`

### Step 2: Upload Files

Upload everything in `shared-hosting-upload/` to your shared hosting:
- **Via FTP**: Upload to `public_html/` or `www/`
- **Via cPanel**: Use File Manager, upload to `public_html/`

### Step 3: Set Permissions

Set file permissions:
- **Files**: `644` (rw-r--r--)
- **Directories**: `755` (rwxr-xr-x)

## 📁 What Gets Built

```
shared-hosting-upload/
├── index.html              # Main frontend file
├── assets/                 # JS, CSS, images
│   ├── *.js
│   ├── *.css
│   └── *.png, *.svg, etc.
├── downloads/              # Desktop app installers
│   ├── FlashDash-Setup-1.0.0.exe    # Windows
│   ├── FlashDash-1.0.0.dmg           # Mac
│   └── flashdash-1.0.0.AppImage      # Linux
└── .htaccess              # Apache configuration
```

## 🔗 Configuration

**Backend API**: `https://freedomos.vulcantech.co` (already configured)

**Downloads**: Set during build script (your shared hosting domain)

## ✅ Verification

After uploading:

1. **Visit**: `https://your-domain.com`
2. **Should see**: FlashDash interface
3. **Test downloads**:
   - Windows: `https://your-domain.com/downloads/FlashDash-Setup-1.0.0.exe`
   - Mac: `https://your-domain.com/downloads/FlashDash-1.0.0.dmg`
   - Linux: `https://your-domain.com/downloads/flashdash-1.0.0.AppImage`

## 🔄 Updating

When you need to update:

1. Run build script again: `./build-for-shared-hosting.sh`
2. Upload new files (replace old ones)
3. Done!

## 📝 Notes

- **No code changes needed** - everything uses environment variables
- **Builds done locally** - you just upload files
- **Backend already live** - frontend connects automatically
- **Desktop apps** built based on your OS (Windows/Mac/Linux)

---

**That's it!** Run the script, upload files, and you're live! 🎉

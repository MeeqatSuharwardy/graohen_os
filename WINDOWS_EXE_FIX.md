# 🔧 Windows EXE "Can't Run" Error - Fix Guide

## Problem

Windows shows error: **"This app can't run on your PC"** when trying to run the EXE.

**Root Cause**: The Windows EXE is **not code-signed**, so Windows SmartScreen blocks it as potentially unsafe.

## ✅ Solutions

### Solution 1: User Instructions (Immediate Fix)

**For end users**, provide these instructions to bypass SmartScreen:

1. **Download the EXE** from your website
2. **Right-click** the downloaded file → **Properties**
3. If you see **"Unblock"** checkbox at the bottom, **check it** → Click **OK**
4. **Double-click** the EXE to run
5. When Windows shows the warning:
   - Click **"More info"**
   - Click **"Run anyway"**
6. The app will launch successfully

**Note**: After the first successful run, Windows may remember your choice.

### Solution 2: Code Sign the EXE (Production Solution)

To properly sign the Windows EXE, you need:

1. **Code Signing Certificate** from a trusted Certificate Authority:
   - DigiCert (~$200-400/year)
   - Sectigo (~$200-300/year)
   - GlobalSign (~$200-400/year)

2. **Update electron-builder config**:

```javascript
// electron-builder.config.js
win: {
  sign: 'scripts/sign.js', // Custom signing script
  certificateFile: 'path/to/certificate.pfx',
  certificatePassword: process.env.CERTIFICATE_PASSWORD,
  signingHashAlgorithms: ['sha256'],
}
```

3. **Create signing script** (`scripts/sign.js`):

```javascript
const { sign } = require('electron-builder');
const path = require('path');

exports.default = async function(configuration) {
  const { path: appPath } = configuration;
  
  // Sign the executable
  await sign({
    path: appPath,
    certificateFile: process.env.CERTIFICATE_FILE,
    certificatePassword: process.env.CERTIFICATE_PASSWORD,
  });
};
```

### Solution 3: Improved Installer (Current Build)

The current build uses NSIS installer which is better than a standalone EXE:

**Current Configuration**:
- ✅ NSIS installer (not one-click)
- ✅ Allows choosing installation directory
- ✅ Creates desktop shortcut
- ✅ Creates Start Menu shortcut

**The installer should work better** than running the EXE directly.

### Solution 4: Add Manifest File

Add a manifest to request admin privileges if needed:

Create `assets/app.manifest`:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:com.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="1.0.0.0"
    processorArchitecture="*"
    name="FlashDash"
    type="win32"
  />
  <description>FlashDash Desktop Application</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false" />
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
```

## 📋 Current Status

**Current Build**:
- ✅ NSIS Installer created
- ✅ 64-bit Windows executable
- ❌ Not code-signed (causes SmartScreen warning)
- ✅ Proper installer with options

## 🔄 Rebuild with Better Config

I've updated the electron-builder config. To rebuild:

```bash
cd frontend/packages/desktop
VITE_API_BASE_URL=https://freedomos.vulcantech.co pnpm build:win
cp "dist/flashdash-desktop Setup 1.0.0.exe" ../../shared-hosting-upload/downloads/FlashDash-Setup-1.0.0.exe
```

## 📝 For Your Website

**Add a note on your download page**:

> **Windows SmartScreen Warning**: Windows may show a security warning when downloading. This is normal for unsigned applications. Click "More info" → "Run anyway" to proceed. The application is safe to use.

## 🎯 Recommended Approach

1. **Short-term**: Provide user instructions to bypass SmartScreen
2. **Long-term**: Purchase a code signing certificate and sign the EXE
3. **Alternative**: Use the NSIS installer instead of standalone EXE (better user experience)

---

**Status**: The EXE works, but Windows blocks unsigned executables. Users need to bypass SmartScreen or you need to code-sign the EXE.

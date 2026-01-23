# 🔧 Windows EXE Signing Issue Fix

## Problem

Windows shows error: **"This app can't run on your PC"** when trying to run the EXE.

**Cause**: The Windows EXE is **not code-signed**, so Windows SmartScreen blocks it as potentially unsafe.

## ✅ Solutions

### Option 1: Code Sign the EXE (Recommended for Production)

To properly sign the Windows EXE, you need:

1. **Code Signing Certificate** (from a Certificate Authority like DigiCert, Sectigo, etc.)
   - Cost: ~$200-400/year
   - Required for trusted distribution

2. **Update electron-builder config** in `package.json`:

```json
{
  "build": {
    "win": {
      "sign": "scripts/sign.js",
      "signingHashAlgorithms": ["sha256"],
      "certificateFile": "path/to/certificate.pfx",
      "certificatePassword": "your-certificate-password"
    }
  }
}
```

### Option 2: Disable SmartScreen Warning (User Workaround)

**For end users** who want to run the unsigned EXE:

1. **Right-click** the EXE file
2. Select **"Properties"**
3. Check **"Unblock"** at the bottom (if available)
4. Click **"Run anyway"** when Windows shows the warning
5. Or: **Right-click → Run as administrator**

### Option 3: Build Without Signing (Development/Testing)

Update `package.json` to skip signing:

```json
{
  "build": {
    "win": {
      "sign": null,
      "verifyUpdateCodeSignature": false
    }
  }
}
```

Then rebuild:
```bash
cd frontend/packages/desktop
VITE_API_BASE_URL=https://freedomos.vulcantech.co pnpm build:win
```

### Option 4: Use Windows Installer Instead

Create an installer (NSIS) which is less likely to be blocked:

The current build already creates an installer, but you can configure it better:

```json
{
  "build": {
    "win": {
      "target": [
        {
          "target": "nsis",
          "arch": ["x64"]
        }
      ],
      "nsis": {
        "oneClick": false,
        "allowToChangeInstallationDirectory": true,
        "createDesktopShortcut": true,
        "createStartMenuShortcut": true
      }
    }
  }
}
```

## 🔍 Current Build Configuration

The EXE was built with:
- **Platform**: win32 x64
- **Installer**: NSIS (one-click installer)
- **Signing**: None (not signed)

## 📝 Quick Fix: Rebuild with Better Config

1. **Update `package.json`** to add Windows-specific config:

```json
{
  "build": {
    "win": {
      "target": "nsis",
      "sign": null,
      "publisherName": "Your Company Name"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "installerIcon": "build/icon.ico",
      "uninstallerIcon": "build/icon.ico",
      "installerHeaderIcon": "build/icon.ico",
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "FlashDash"
    }
  }
}
```

2. **Rebuild**:
```bash
cd frontend/packages/desktop
VITE_API_BASE_URL=https://freedomos.vulcantech.co pnpm build:win
```

3. **Copy new EXE**:
```bash
cp "frontend/packages/desktop/dist/flashdash-desktop Setup 1.0.0.exe" shared-hosting-upload/downloads/FlashDash-Setup-1.0.0.exe
```

## 🚨 Important Notes

1. **Unsigned executables** will always trigger Windows SmartScreen warnings
2. **Code signing** is required for trusted distribution
3. **Users can bypass** the warning by clicking "More info" → "Run anyway"
4. **After first run**, Windows may remember the choice

## 📋 For End Users

**Instructions to run unsigned EXE:**

1. Download the EXE
2. Right-click → **Properties**
3. If you see **"Unblock"** checkbox, check it
4. Click **OK**
5. Double-click the EXE
6. When Windows shows warning: Click **"More info"** → **"Run anyway"**

---

**Status**: The EXE works, but Windows blocks unsigned executables by default. Users need to bypass SmartScreen or you need to code-sign the EXE.

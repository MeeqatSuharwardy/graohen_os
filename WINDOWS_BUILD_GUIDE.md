# Windows EXE Build Guide - Bypassing SmartScreen

Complete guide to build FlashDash as a Windows EXE and bypass Windows SmartScreen warnings.

## Prerequisites

1. **Node.js** installed (v18+)
2. **electron-builder** installed
3. **Code Signing Certificate** (for bypassing SmartScreen)

## Quick Build (Without Code Signing)

```bash
cd frontend/electron
npm install
npm run build:win
```

**Or use the build script:**
```bash
./build-windows.sh
```

**Output**: `frontend/build/FlashDash Setup x.x.x.exe`

⚠️ **Note**: Without code signing, Windows SmartScreen will show a warning. Users can click "More info" → "Run anyway".

## Building with Code Signing (Bypass SmartScreen)

### Option 1: Using a Code Signing Certificate (Recommended)

#### Step 1: Obtain a Code Signing Certificate

**Options:**
- **EV (Extended Validation) Certificate**: Best for SmartScreen bypass (~$300-500/year)
  - Providers: DigiCert, Sectigo, GlobalSign
  - Requires hardware token (USB key)
- **Standard Code Signing Certificate**: Good option (~$200-400/year)
  - Providers: Sectigo, DigiCert, SSL.com
  - Can use software-based certificate

#### Step 2: Export Certificate

If you have a `.pfx` file:
```bash
# Certificate is ready to use
```

If you have a certificate in Windows Certificate Store:
```powershell
# Export certificate
certutil -exportPFX -p "your-password" My "C:\path\to\certificate.pfx"
```

#### Step 3: Configure electron-builder

Create `.env` file in `frontend/electron/`:
```env
CSC_LINK=path/to/certificate.pfx
CSC_KEY_PASSWORD=your-certificate-password
```

Or set environment variables:
```bash
export CSC_LINK="/path/to/certificate.pfx"
export CSC_KEY_PASSWORD="your-password"
```

#### Step 4: Build

```bash
cd frontend/electron
npm run build:win
```

The executable will be automatically signed.

### Option 2: Self-Signed Certificate (Development/Testing)

⚠️ **Note**: Self-signed certificates won't fully bypass SmartScreen, but they help reduce warnings.

#### Step 1: Create Self-Signed Certificate

**On Windows (PowerShell as Administrator):**
```powershell
# Create self-signed certificate
New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=FlashDash" -KeyUsage DigitalSignature -FriendlyName "FlashDash Code Signing" -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(10)

# Export certificate
$cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object {$_.Subject -like "*FlashDash*"}
$password = ConvertTo-SecureString -String "YourPassword123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "flashdash-cert.pfx" -Password $password
```

**On macOS/Linux:**
```bash
# Create certificate
openssl req -x509 -newkey rsa:4096 -keyout flashdash-key.pem -out flashdash-cert.pem -days 3650 -nodes -subj "/CN=FlashDash"

# Convert to PFX
openssl pkcs12 -export -out flashdash-cert.pfx -inkey flashdash-key.pem -in flashdash-cert.pem -password pass:YourPassword123!
```

#### Step 2: Configure and Build

```bash
export CSC_LINK="./flashdash-cert.pfx"
export CSC_KEY_PASSWORD="YourPassword123!"
cd frontend/electron
npm run build:win
```

### Option 3: Using SignTool (Windows)

If you have a certificate installed in Windows Certificate Store:

```bash
# Build unsigned
npm run build:win

# Sign manually with signtool
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com /d "FlashDash" /du "https://freedomos.vulcantech.co" "frontend/build/FlashDash Setup x.x.x.exe"
```

## Build Configuration

The build configuration is in `frontend/electron/package.json`:

```json
{
  "build": {
    "appId": "co.vulcantech.flashdash",
    "productName": "FlashDash",
    "win": {
      "target": "nsis",
      "sign": "sign.js",  // Custom signing script (optional)
      "signingHashAlgorithms": ["sha256"],
      "certificateFile": "path/to/certificate.pfx",
      "certificatePassword": "${env.CSC_KEY_PASSWORD}"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "installerIcon": "../assets/icon.ico",
      "uninstallerIcon": "../assets/icon.ico"
    }
  }
}
```

## Advanced: Custom Signing Script

Create `frontend/electron/sign.js`:

```javascript
const { execSync } = require('child_process');
const path = require('path');

exports.default = async function(config) {
  const { path: filePath } = config;
  
  // Sign the executable
  const signCommand = `signtool sign /f "${process.env.CSC_LINK}" /p "${process.env.CSC_KEY_PASSWORD}" /t http://timestamp.digicert.com /d "FlashDash" /du "https://freedomos.vulcantech.co" "${filePath}"`;
  
  try {
    execSync(signCommand, { stdio: 'inherit' });
    console.log('✓ Code signing successful');
  } catch (error) {
    console.error('✗ Code signing failed:', error.message);
    throw error;
  }
};
```

## Bypassing SmartScreen Without Certificate

### Method 1: Reputation Building

1. **Distribute through trusted channels**:
   - GitHub Releases
   - Microsoft Store
   - Your own website with HTTPS

2. **Build reputation**:
   - Get downloads from trusted sources
   - Users mark as "safe" after first run
   - Over time, SmartScreen learns to trust

### Method 2: Using Authenticode Timestamping

Even with self-signed cert, use timestamping:
```bash
signtool sign /f cert.pfx /p password /t http://timestamp.digicert.com /d "FlashDash" app.exe
```

### Method 3: Add Publisher Information

Update `package.json`:
```json
{
  "build": {
    "win": {
      "publisherName": "VulcanTech",
      "verifyUpdateCodeSignature": false
    }
  }
}
```

## Complete Build Script

Create `build-windows.sh`:

```bash
#!/bin/bash

set -e

echo "🔨 Building FlashDash for Windows..."

cd frontend/electron

# Check if certificate is set
if [ -z "$CSC_LINK" ]; then
    echo "⚠️  Warning: No code signing certificate set (CSC_LINK)"
    echo "   Building unsigned executable (SmartScreen warning will appear)"
    echo "   Set CSC_LINK and CSC_KEY_PASSWORD to sign the executable"
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build for Windows
echo "🏗️  Building Windows EXE..."
npm run build:win

echo "✅ Build complete!"
echo "📦 Output: frontend/build/FlashDash Setup *.exe"
```

## Testing the Build

1. **Test on clean Windows VM**:
   - Download and run the installer
   - Check SmartScreen behavior
   - Verify app functionality

2. **Check signature**:
   ```powershell
   Get-AuthenticodeSignature "FlashDash Setup.exe"
   ```

3. **Verify timestamp**:
   ```powershell
   signtool verify /pa /v "FlashDash Setup.exe"
   ```

## Troubleshooting

### "Certificate file not found"
- Check `CSC_LINK` path is correct
- Use absolute path or relative to project root

### "Invalid certificate password"
- Verify `CSC_KEY_PASSWORD` is correct
- Check certificate hasn't expired

### "Timestamp server unavailable"
- Try different timestamp server:
  - `http://timestamp.digicert.com`
  - `http://timestamp.verisign.com/scripts/timstamp.dll`
  - `http://timestamp.comodoca.com`

### SmartScreen still shows warning
- **With self-signed cert**: Expected behavior
- **With valid cert**: May take time for reputation to build
- **EV certificate**: Usually bypasses immediately

## Best Practices

1. **Always use timestamping**: Allows verification even after certificate expires
2. **Use EV certificate**: Best SmartScreen bypass
3. **Distribute through trusted channels**: GitHub, Microsoft Store, etc.
4. **Keep certificate secure**: Never commit certificates to git
5. **Test on clean systems**: Verify behavior before distribution

## Cost Comparison

| Method | Cost | SmartScreen Bypass | Recommended For |
|--------|------|-------------------|-----------------|
| No signing | Free | ❌ Warning always | Development |
| Self-signed | Free | ⚠️ Warning (can bypass) | Testing |
| Standard Code Signing | $200-400/year | ✅ After reputation | Production |
| EV Code Signing | $300-500/year | ✅ Immediate bypass | Enterprise |

## Quick Reference

```bash
# Build unsigned (SmartScreen warning)
npm run build:win

# Build with code signing (set env vars first)
export CSC_LINK="./cert.pfx"
export CSC_KEY_PASSWORD="password"
npm run build:win

# Build with custom config
electron-builder --win --config.win.certificateFile=./cert.pfx --config.win.certificatePassword=password
```

## Next Steps

1. Choose signing method based on your needs
2. Obtain certificate (if using code signing)
3. Configure environment variables
4. Build and test
5. Distribute through trusted channels

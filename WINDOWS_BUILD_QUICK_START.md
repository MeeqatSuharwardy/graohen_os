# Windows Build Quick Start Guide

Quick reference for building FlashDash Windows EXE and bypassing SmartScreen.

## 🚀 Quick Build (No Signing)

**macOS/Linux:**
```bash
./build-windows.sh
```

**Windows PowerShell:**
```powershell
.\build-windows.ps1
```

**Manual:**
```bash
cd frontend/electron
npm install
npm run build:win
```

**Output**: `frontend/build/FlashDash Setup 1.0.0.exe`

⚠️ **SmartScreen Warning**: Users will see "Windows protected your PC" warning. They can click "More info" → "Run anyway".

---

## 🔐 Build with Code Signing (Bypass SmartScreen)

### Step 1: Get a Code Signing Certificate

**Option A: Buy a Certificate** (Recommended for production)
- **EV Certificate**: ~$300-500/year (best SmartScreen bypass)
- **Standard Certificate**: ~$200-400/year
- Providers: DigiCert, Sectigo, SSL.com

**Option B: Create Self-Signed** (For testing)
```powershell
# Windows PowerShell (as Administrator)
New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=FlashDash" -KeyUsage DigitalSignature -FriendlyName "FlashDash Code Signing" -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(10)

$cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object {$_.Subject -like "*FlashDash*"}
$password = ConvertTo-SecureString -String "YourPassword123!" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath "flashdash-cert.pfx" -Password $password
```

### Step 2: Set Environment Variables

**macOS/Linux:**
```bash
export CSC_LINK="./flashdash-cert.pfx"
export CSC_KEY_PASSWORD="YourPassword123!"
```

**Windows PowerShell:**
```powershell
$env:CSC_LINK = ".\flashdash-cert.pfx"
$env:CSC_KEY_PASSWORD = "YourPassword123!"
```

**Windows CMD:**
```cmd
set CSC_LINK=.\flashdash-cert.pfx
set CSC_KEY_PASSWORD=YourPassword123!
```

### Step 3: Build

**macOS/Linux:**
```bash
./build-windows.sh --sign
```

**Windows PowerShell:**
```powershell
.\build-windows.ps1 -Sign
```

**Manual:**
```bash
cd frontend/electron
npm run build:win
```

The executable will be automatically signed!

---

## 📋 Build Output

After building, you'll find:
- **Installer**: `frontend/build/FlashDash Setup 1.0.0.exe`
- **Unpacked**: `frontend/build/win-unpacked/` (for testing)

---

## ✅ Verify Signature

**Windows:**
```powershell
Get-AuthenticodeSignature "FlashDash Setup.exe"
```

Or:
```cmd
signtool verify /pa "FlashDash Setup.exe"
```

---

## 🎯 SmartScreen Bypass Methods

### Method 1: Code Signing Certificate (Best)
- ✅ **EV Certificate**: Immediate SmartScreen bypass
- ✅ **Standard Certificate**: Bypass after reputation builds
- ⚠️ **Self-Signed**: Reduces warnings but doesn't fully bypass

### Method 2: Reputation Building
1. Distribute through trusted channels (GitHub Releases)
2. Get downloads from trusted users
3. Over time, SmartScreen learns to trust

### Method 3: Microsoft Store
- Submit to Microsoft Store
- Microsoft handles signing
- No SmartScreen warnings

---

## 🔧 Troubleshooting

### "Certificate file not found"
- Check `CSC_LINK` path is correct
- Use absolute path if relative doesn't work

### "Invalid certificate password"
- Verify `CSC_KEY_PASSWORD` is correct
- Check certificate hasn't expired

### SmartScreen still shows warning
- **Self-signed**: Expected - users can bypass manually
- **Valid cert**: May take time for reputation to build
- **EV cert**: Should bypass immediately

### Build fails
```bash
# Clean and rebuild
cd frontend/electron
rm -rf node_modules dist
npm install
npm run build:win
```

---

## 📦 Distribution Tips

1. **Host on GitHub Releases**: Trusted source, helps reputation
2. **Use HTTPS website**: Secure distribution
3. **Provide checksums**: SHA256 hashes for verification
4. **Clear instructions**: Tell users about SmartScreen if unsigned

---

## 💰 Cost Comparison

| Method | Cost | SmartScreen | Best For |
|--------|------|-------------|----------|
| No signing | Free | ❌ Warning | Development |
| Self-signed | Free | ⚠️ Warning | Testing |
| Standard Cert | $200-400/yr | ✅ After time | Production |
| EV Cert | $300-500/yr | ✅ Immediate | Enterprise |

---

## 🎬 Complete Example

```bash
# 1. Create self-signed certificate (Windows)
New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=FlashDash" ...

# 2. Export to PFX
Export-PfxCertificate -Cert $cert -FilePath "cert.pfx" -Password $pass

# 3. Set environment variables
export CSC_LINK="./cert.pfx"
export CSC_KEY_PASSWORD="password"

# 4. Build
./build-windows.sh --sign

# 5. Test on Windows VM
# 6. Distribute via GitHub Releases
```

---

## 📚 Full Documentation

See `WINDOWS_BUILD_GUIDE.md` for complete details.

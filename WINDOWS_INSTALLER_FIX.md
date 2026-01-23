# 🔧 Windows EXE Installation Error Fix

## Common Installation Errors

### Error 1: "This app can't run on your PC"
**Cause**: Windows SmartScreen blocking unsigned executable

**Fix**: 
1. Right-click EXE → Properties
2. Check "Unblock" (if available)
3. Run as Administrator
4. Click "More info" → "Run anyway" when warned

### Error 2: "NSIS Error" or "Installer corrupted"
**Cause**: File corruption or incomplete download

**Fix**:
1. Re-download the EXE
2. Check file size matches (should be ~82 MB)
3. Try downloading again

### Error 3: "Access Denied" or Permission Error
**Cause**: Insufficient permissions

**Fix**:
1. Right-click EXE → "Run as Administrator"
2. Or disable UAC temporarily

### Error 4: "Windows protected your PC"
**Cause**: Windows Defender blocking unsigned app

**Fix**:
1. Click "More info"
2. Click "Run anyway"
3. Or add exception in Windows Defender

## 🔧 Rebuild with Better Settings

If installation keeps failing, we can rebuild with different settings:

1. **Simpler installer** (portable version)
2. **Better error handling**
3. **Proper file permissions**

## 📝 What Error Are You Seeing?

Please provide:
- Exact error message
- When it occurs (during download, during install, after install)
- Windows version (Windows 10/11)

This will help me provide a specific fix.

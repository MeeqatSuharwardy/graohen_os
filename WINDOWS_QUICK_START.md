# 🪟 Windows Quick Start Guide

Complete step-by-step guide for Windows users to run FlashDash.

## Prerequisites Installation

### 1. Install Python 3.11+

1. Download from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```powershell
   python --version
   ```
   Should show: `Python 3.11.x` or higher

### 2. Install Node.js 20+

1. Download from [nodejs.org](https://nodejs.org/)
2. Use LTS version (recommended)
3. Verify installation:
   ```powershell
   node --version
   ```
   Should show: `v20.x.x` or higher

### 3. Install pnpm

```powershell
npm install -g pnpm
```

Verify:
```powershell
pnpm --version
```

### 4. Install ADB & Fastboot

1. Download [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools)
2. Extract to `C:\platform-tools`
3. Add to PATH:
   - Open "Environment Variables" (search in Start menu)
   - Edit "Path" under "User variables"
   - Add: `C:\platform-tools`
   - Click OK
4. Verify (restart PowerShell after adding to PATH):
   ```powershell
   adb --version
   fastboot --version
   ```

## Setup Steps

### Step 1: Clone Repository

```powershell
git clone <repository-url>
cd graohen_os
```

### Step 2: Backend Setup

```powershell
# Navigate to backend
cd backend\py-service

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
Copy-Item env.example .env
```

### Step 3: Frontend Setup

```powershell
# Return to project root
cd ..\..

# Install dependencies
pnpm install

# Create frontend .env file
New-Item -Path "frontend\packages\desktop\.env" -ItemType File -Force
Add-Content -Path "frontend\packages\desktop\.env" -Value "VITE_API_BASE_URL=http://localhost:8000"
```

## Running the Application

### Option 1: Using PowerShell Scripts (Easiest)

**Terminal 1 - Backend:**
```powershell
.\start-backend.ps1
```

**Terminal 2 - Frontend:**
```powershell
.\start-frontend.ps1
```

### Option 2: Manual Commands

**Terminal 1 - Backend:**
```powershell
cd backend\py-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```powershell
pnpm run dev
```

## Verification

### Check Backend Status

```powershell
.\check-backend.ps1
```

Or manually:
```powershell
# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8000/health"

# Test devices endpoint
Invoke-WebRequest -Uri "http://localhost:8000/devices"
```

### Check Electron App

1. Electron window should open automatically
2. Press `F12` to open DevTools
3. Check console for:
   - `API Base URL: http://localhost:8000`
   - "Service Running" badge
   - No error messages

## Common Windows Issues

### Execution Policy Error

**Error:** `cannot be loaded because running scripts is disabled`

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Python Not Found

**Error:** `python: command not found`

**Solution:**
1. Reinstall Python
2. Check "Add Python to PATH" during installation
3. Restart PowerShell after installation

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual number)
taskkill /PID <PID> /F
```

### ADB Not Found

**Error:** `adb: command not found`

**Solution:**
1. Verify ADB is installed: `C:\platform-tools\adb.exe`
2. Add `C:\platform-tools` to PATH (see Prerequisites)
3. Restart PowerShell after adding to PATH

### Virtual Environment Activation Fails

**Error:** `Activate.ps1 cannot be loaded`

**Solution:**
```powershell
# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activation again
.\venv\Scripts\Activate.ps1
```

## Quick Commands Reference

### Backend

```powershell
# Start backend
cd backend\py-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Stop backend
# Press Ctrl+C

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Frontend

```powershell
# Start Electron app
pnpm run dev

# Install dependencies
pnpm install

# Clear cache
Remove-Item -Recurse -Force frontend\packages\desktop\node_modules\.vite
```

### Testing

```powershell
# Check if backend is running
Test-NetConnection -ComputerName localhost -Port 8000

# Test API
Invoke-WebRequest -Uri "http://localhost:8000/health"
Invoke-WebRequest -Uri "http://localhost:8000/devices"
```

## File Locations

- **Backend config**: `backend\py-service\.env`
- **Frontend config**: `frontend\packages\desktop\.env`
- **Backend logs**: Check PowerShell terminal output
- **Frontend logs**: Check Electron DevTools console (F12)

## Next Steps

1. ✅ Backend running on port 8000
2. ✅ Electron app opens successfully
3. ✅ No errors in console
4. 🔌 Connect Pixel device via USB
5. 📱 Enable USB debugging on device
6. ✅ See device appear in Electron app
7. 📦 Add GrapheneOS bundle (see [BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md))
8. 🚀 Start flashing!

## Getting Help

- Check [README.md](./README.md) for general instructions
- See [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md) for detailed setup
- Review [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for API details

---

**Ready to flash GrapheneOS on Windows!** 🎉

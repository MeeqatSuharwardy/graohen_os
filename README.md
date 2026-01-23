# FlashDash - GrapheneOS Installer Demo

A comprehensive platform for GrapheneOS installation, encrypted email service, and secure file storage.

## 🚀 Quick Start Demo

Get FlashDash running locally in minutes!

### Prerequisites

#### Windows
- **Python 3.11+**: Download from [python.org](https://www.python.org/downloads/)
- **Node.js 20+**: Download from [nodejs.org](https://nodejs.org/)
- **pnpm**: Install via `npm install -g pnpm`
- **ADB & Fastboot**: Download [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) and add to PATH

#### macOS/Linux
- **Python 3.11+**: `brew install python@3.11` (macOS) or `sudo apt-get install python3.11` (Linux)
- **Node.js 20+**: `brew install node` (macOS) or use [nvm](https://github.com/nvm-sh/nvm)
- **pnpm**: `npm install -g pnpm`
- **ADB & Fastboot**: `brew install android-platform-tools` (macOS) or `sudo apt-get install android-tools-adb android-tools-fastboot` (Linux)

## 📦 Installation & Setup

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd graohen_os
```

### Step 2: Backend Setup

#### Windows (PowerShell)
```powershell
# Navigate to backend
cd backend\py-service

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If activation fails, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
Copy-Item env.example .env

# Edit .env (optional - defaults work for local)
# Notepad .env
```

#### macOS/Linux
```bash
# Navigate to backend
cd backend/py-service

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp env.example .env
```

### Step 3: Frontend Setup

#### Windows (PowerShell)
```powershell
# From project root
cd ..

# Install dependencies
pnpm install

# Create frontend .env file
New-Item -Path "frontend\packages\desktop\.env" -ItemType File -Force
Add-Content -Path "frontend\packages\desktop\.env" -Value "VITE_API_BASE_URL=http://localhost:8000"
```

#### macOS/Linux
```bash
# From project root
cd ..

# Install dependencies
pnpm install

# Create frontend .env file
echo "VITE_API_BASE_URL=http://localhost:8000" > frontend/packages/desktop/.env
```

## 🎯 Running the Demo

### Terminal 1: Start Backend

#### Windows (PowerShell)
```powershell
# Navigate to backend
cd backend\py-service

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### macOS/Linux
```bash
# Navigate to backend
cd backend/py-service

# Activate virtual environment
source venv/bin/activate

# Start backend server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Terminal 2: Start Electron App

#### Windows (PowerShell)
```powershell
# From project root
pnpm run dev
```

#### macOS/Linux
```bash
# From project root
pnpm run dev
```

**Expected Result:**
- Electron window opens
- "Service Running" badge appears
- Device list loads (empty `[]` if no devices connected)

## ✅ Verify Everything Works

### Test Backend Endpoints

#### Windows (PowerShell)
```powershell
# Health check
Invoke-WebRequest -Uri "http://localhost:8000/health" | Select-Object -ExpandProperty Content

# Devices endpoint
Invoke-WebRequest -Uri "http://localhost:8000/devices" | Select-Object -ExpandProperty Content
```

#### macOS/Linux
```bash
# Health check
curl http://localhost:8000/health

# Devices endpoint
curl http://localhost:8000/devices
```

**Expected Responses:**
- Health: `{"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}`
- Devices: `[]` (empty array) or device list

### Test Electron App

1. Open Electron app (should auto-open when `pnpm run dev` runs)
2. Check DevTools console (F12 or Cmd+Option+I)
3. Should see: `API Base URL: http://localhost:8000`
4. Should see: "Service Running" badge
5. No `ERR_EMPTY_RESPONSE` or `405` errors

## 🛠️ Quick Commands Reference

### Backend Commands

#### Windows
```powershell
# Start backend
cd backend\py-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Stop backend
# Press Ctrl+C in terminal
```

#### macOS/Linux
```bash
# Start backend
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Stop backend
# Press Ctrl+C in terminal
```

### Frontend Commands

```bash
# Start Electron app (all platforms)
pnpm run dev

# Build Electron app
pnpm run build

# Install dependencies
pnpm install
```

### Testing Commands

#### Windows (PowerShell)
```powershell
# Check if backend is running
Test-NetConnection -ComputerName localhost -Port 8000

# Test API endpoints
Invoke-WebRequest -Uri "http://localhost:8000/health"
Invoke-WebRequest -Uri "http://localhost:8000/devices"
```

#### macOS/Linux
```bash
# Check if backend is running
lsof -i :8000

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/devices
```

## 📋 Configuration Files

### Backend: `backend/py-service/.env`

**Minimal configuration (defaults work):**
```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
```

**Full configuration (optional):**
```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# ADB and Fastboot paths
# Windows: C:\platform-tools\adb.exe
# macOS/Linux: /usr/local/bin/adb
ADB_PATH=/usr/local/bin/adb
FASTBOOT_PATH=/usr/local/bin/fastboot

# Directories
GRAPHENE_BUNDLES_ROOT=./bundles
APK_STORAGE_DIR=./apks
LOG_DIR=./logs

# CORS
CORS_ORIGINS=*
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Frontend: `frontend/packages/desktop/.env`

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## 🐛 Troubleshooting

### Backend Not Starting

#### Windows
```powershell
# Check Python version
python --version  # Should be 3.11+

# Recreate virtual environment
cd backend\py-service
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

#### macOS/Linux
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Recreate virtual environment
cd backend/py-service
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Port Already in Use

#### Windows (PowerShell)
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

#### macOS/Linux
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### ERR_EMPTY_RESPONSE or 405 Errors

1. **Restart backend** (most important!)
2. **Clear Electron cache:**
   ```bash
   # Windows
   Remove-Item -Recurse -Force frontend\packages\desktop\node_modules\.vite
   
   # macOS/Linux
   rm -rf frontend/packages/desktop/node_modules/.vite
   ```
3. **Restart Electron app**

### Devices Endpoint Hanging

1. **Check ADB/Fastboot:**
   ```bash
   # Windows
   adb devices
   fastboot devices
   
   # macOS/Linux
   adb devices
   fastboot devices
   ```

2. **Restart ADB server:**
   ```bash
   adb kill-server
   adb start-server
   ```

3. **Restart backend** after fixing ADB

### Electron Not Connecting

1. **Verify .env file:**
   ```bash
   # Windows
   Get-Content frontend\packages\desktop\.env
   
   # macOS/Linux
   cat frontend/packages/desktop/.env
   ```
   Should show: `VITE_API_BASE_URL=http://localhost:8000`

2. **Clear cache and restart:**
   ```bash
   # Windows
   Remove-Item -Recurse -Force frontend\packages\desktop\node_modules\.vite
   pnpm run dev
   
   # macOS/Linux
   rm -rf frontend/packages/desktop/node_modules/.vite
   pnpm run dev
   ```

## 📚 Project Structure

```
graohen_os/
├── backend/
│   └── py-service/          # FastAPI backend
│       ├── app/
│       │   ├── api/v1/      # API endpoints
│       │   ├── routes/      # Device/flash routes
│       │   └── config.py    # Configuration
│       ├── requirements.txt
│       └── .env             # Backend config
├── frontend/
│   ├── packages/
│   │   ├── desktop/        # Electron app
│   │   │   └── .env        # Frontend config
│   │   └── web/            # Web app
│   └── package.json
├── bundles/                # GrapheneOS builds (see BUNDLE_STRUCTURE.md)
├── docker-compose.yml      # Docker setup (optional)
└── README.md              # This file
```

## 🎯 Features

### GrapheneOS Flashing
- **Desktop Electron App**: Full-featured desktop application
- **Web Flasher**: Browser-based flashing (WebUSB)
- **Device Detection**: Automatic device identification
- **Build Management**: Support for multiple GrapheneOS builds

### API Endpoints

- **Health Check**: `GET /health`
- **List Devices**: `GET /devices`
- **Identify Device**: `GET /devices/{device_id}/identify`
- **Reboot Bootloader**: `POST /devices/{device_id}/reboot/bootloader`
- **API Documentation**: `http://localhost:8000/docs` (when backend is running)

## 📖 Additional Documentation

- **[LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md)** - Detailed local setup guide
- **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - Complete API reference
- **[BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md)** - How to add GrapheneOS builds
- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Production deployment guide

## 🔧 Development Scripts

### Windows (PowerShell)

```powershell
# Start backend
.\start-backend.ps1

# Start frontend
.\start-frontend.ps1

# Check backend status
.\check-backend.ps1
```

### macOS/Linux

```bash
# Start backend
./start-backend.sh

# Start frontend
./start-frontend.sh

# Check backend status
./check-backend.sh

# Run verification
./test-local-setup.sh
```

## ✅ Checklist

Before running the demo, ensure:

- [ ] Python 3.11+ installed
- [ ] Node.js 20+ installed
- [ ] pnpm installed globally
- [ ] ADB and Fastboot installed and in PATH
- [ ] Backend virtual environment created
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed (`pnpm install`)
- [ ] `.env` files created (backend and frontend)
- [ ] Backend running on port 8000
- [ ] Electron app starts without errors

## 🚀 Next Steps

1. **Connect a Pixel device** via USB
2. **Enable USB debugging** on the device
3. **Authorize computer** when prompted on device
4. **See device appear** in Electron app
5. **Add GrapheneOS bundle** to `bundles/` directory (see [BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md))
6. **Start flashing** GrapheneOS!

## 📞 Support

For issues and questions:
- Check [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md) for detailed setup
- Review [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for API details
- See [BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md) for bundle setup

---

**Ready to flash GrapheneOS? Start with the Quick Start Demo above!** 🎉

**Last Updated**: January 2025  
**Version**: 1.0.0

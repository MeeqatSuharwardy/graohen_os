# Final Local Development Solution

## Complete Working Setup

### Step 1: Start Backend Server

**Terminal 1:**
```bash
cd backend/py-service

# Create virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate

# Install dependencies (first time only)
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file (first time only)
cp env.example .env

# Start server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Step 2: Verify Backend

**In a new terminal:**
```bash
# Test health endpoint
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}

# Test devices endpoint
curl http://localhost:8000/devices

# Should return: [] (empty array if no devices) or device list
```

### Step 3: Configure Frontend

**File:** `frontend/packages/desktop/.env`
```bash
VITE_API_BASE_URL=http://localhost:8000
```

**Verify:**
```bash
cat frontend/packages/desktop/.env
# Should show: VITE_API_BASE_URL=http://localhost:8000
```

### Step 4: Start Electron App

**Terminal 2:**
```bash
# From project root
pnpm run dev
```

**Or:**
```bash
cd frontend
pnpm dev
```

## Complete Verification

### 1. Backend Status
```bash
./check-backend.sh
```

Should show:
- ✓ Port 8000 is in use
- ✓ Health endpoint: OK
- ✓ Devices endpoint: OK

### 2. Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Devices list
curl http://localhost:8000/devices

# API documentation
open http://localhost:8000/docs
```

### 3. Electron App

1. Electron window should open
2. Check DevTools console (Cmd+Option+I)
3. Should see: `API Base URL: http://localhost:8000`
4. Should see: "Service Running" badge
5. No `ERR_EMPTY_RESPONSE` errors

## Troubleshooting

### Backend Not Starting

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
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### ERR_EMPTY_RESPONSE Error

**Cause:** Backend crashed or hanging

**Solution:**
1. Check backend logs for errors
2. Restart backend server
3. Check if ADB/Fastboot commands are hanging:
   ```bash
   adb devices
   fastboot devices
   ```

### Devices Endpoint Hanging

**Fixed:** Updated devices endpoint to use async/await with timeouts

**If still hanging:**
1. Check ADB/Fastboot are installed:
   ```bash
   which adb
   which fastboot
   ```
2. Test ADB manually:
   ```bash
   adb devices
   ```
3. Restart backend after fixes

### Port Already in Use

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
# Update .env: VITE_API_BASE_URL=http://localhost:8001
```

### Electron Not Connecting

1. **Check .env file:**
   ```bash
   cat frontend/packages/desktop/.env
   # Should be: VITE_API_BASE_URL=http://localhost:8000
   ```

2. **Clear cache and restart:**
   ```bash
   rm -rf frontend/packages/desktop/node_modules/.vite
   pnpm run dev
   ```

3. **Check console logs** in Electron DevTools

## Quick Start Scripts

### Start Backend
```bash
./start-backend.sh
```

### Start Frontend
```bash
./start-frontend.sh
```

### Check Backend Status
```bash
./check-backend.sh
```

## Final Checklist

- [ ] Backend running on port 8000
- [ ] Health endpoint responds: `curl http://localhost:8000/health`
- [ ] Devices endpoint responds: `curl http://localhost:8000/devices`
- [ ] `.env` file configured: `VITE_API_BASE_URL=http://localhost:8000`
- [ ] Electron app starts: `pnpm run dev`
- [ ] No ERR_EMPTY_RESPONSE errors
- [ ] "Service Running" badge shows in Electron app

## API Endpoints

- **Health:** `GET http://localhost:8000/health`
- **Devices:** `GET http://localhost:8000/devices`
- **Device Identify:** `GET http://localhost:8000/devices/{serial}/identify`
- **Reboot Bootloader:** `POST http://localhost:8000/devices/{serial}/reboot/bootloader`
- **API Docs:** `http://localhost:8000/docs`

---

**Everything is now configured and working for local development!**

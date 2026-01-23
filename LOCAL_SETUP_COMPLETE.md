# Complete Local Setup Guide

## Quick Start

### 1. Start Backend (Terminal 1)

```bash
cd backend/py-service

# Create virtual environment if needed
python3 -m venv venv
source venv/bin/activate

# Install dependencies if needed
pip install -r requirements.txt

# Start server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Backend will be available at:** `http://localhost:8000`

### 2. Start Electron App (Terminal 2)

```bash
# From project root
pnpm run dev
```

**Or from frontend directory:**
```bash
cd frontend
pnpm dev
```

## Verify Setup

### Check Backend

```bash
# Run check script
./check-backend.sh

# Or manually test
curl http://localhost:8000/health
curl http://localhost:8000/devices
```

### Check Electron App

1. Electron window should open automatically
2. Check browser console for API calls
3. Should see "Service Running" badge if backend is connected

## Configuration Files

### Backend Configuration

**File:** `backend/py-service/.env` (create from `env.example`)

```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Electron App Configuration

**File:** `frontend/packages/desktop/.env`

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Troubleshooting

### ERR_EMPTY_RESPONSE Error

**Cause:** Backend not running or wrong port

**Solution:**
1. Check if backend is running: `./check-backend.sh`
2. Verify port: `lsof -i :8000`
3. Start backend if not running
4. Restart Electron app after backend starts

### 404 Error

**Cause:** Wrong API URL or route not found

**Solution:**
1. Check `.env` file: `cat frontend/packages/desktop/.env`
2. Should be: `VITE_API_BASE_URL=http://localhost:8000`
3. Restart Electron app after changing `.env`
4. Check backend routes: `curl http://localhost:8000/docs`

### Connection Refused

**Cause:** Backend not running

**Solution:**
```bash
# Start backend
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Port Already in Use

**Cause:** Another process using port 8000

**Solution:**
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
# Then update .env: VITE_API_BASE_URL=http://localhost:8001
```

## API Endpoints

- **Health:** `http://localhost:8000/health`
- **Devices:** `http://localhost:8000/devices`
- **API Docs:** `http://localhost:8000/docs`

## Development Workflow

1. **Start Backend** (Terminal 1):
   ```bash
   cd backend/py-service
   source venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Electron** (Terminal 2):
   ```bash
   pnpm run dev
   ```

3. **Make Changes:**
   - Backend: Auto-reloads on file changes
   - Frontend: Hot module replacement (HMR) enabled

4. **Test:**
   - Backend: `http://localhost:8000/docs`
   - Electron: Check window and console

## Quick Fixes

### Backend Not Starting

```bash
cd backend/py-service
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Electron Not Connecting

1. Check `.env` file exists: `cat frontend/packages/desktop/.env`
2. Should have: `VITE_API_BASE_URL=http://localhost:8000`
3. Restart Electron app
4. Check backend is running: `curl http://localhost:8000/health`

### Clear Cache

```bash
# Electron app cache
rm -rf frontend/packages/desktop/node_modules/.vite

# Restart Electron
pnpm run dev
```

---

**Everything should work on localhost:8000 now!**

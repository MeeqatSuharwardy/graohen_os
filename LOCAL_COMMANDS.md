# Local Development Commands (Without Docker)

Quick reference for running the application locally.

## Quick Start - Electron App

**Run `pnpm run dev` from project root to start Electron app:**

```bash
# From project root
pnpm run dev
```

This starts the Electron desktop app. Make sure backend is running first!

## Prerequisites

```bash
# Install Python 3.11+
python3 --version

# Install Node.js 20+
node --version

# Install pnpm globally
npm install -g pnpm

# Install ADB and Fastboot
# macOS:
brew install android-platform-tools

# Ubuntu:
sudo apt-get install android-tools-adb android-tools-fastboot
```

## Quick Start

### Option 1: Use Start Scripts

```bash
# Terminal 1: Backend
./start-backend.sh

# Terminal 2: Frontend
./start-frontend.sh
```

### Option 2: Manual Commands

**Backend:**
```bash
cd backend/py-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edit .env if needed
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
pnpm install
echo "VITE_API_BASE_URL=http://localhost:8000" > apps/web-flasher/.env
pnpm --filter @flashdash/web-flasher dev
```

## Backend Commands

### Setup (First Time)
```bash
cd backend/py-service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp env.example .env
mkdir -p bundles apks logs
```

### Start Server
```bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Test Backend
```bash
curl http://localhost:8000/health
open http://localhost:8000/docs
```

### Stop Backend
```bash
# Press Ctrl+C in the terminal running the server
```

## Frontend Commands

### Setup (First Time)
```bash
cd frontend
pnpm install
echo "VITE_API_BASE_URL=http://localhost:8000" > apps/web-flasher/.env
```

### Start Development Server
```bash
cd frontend
pnpm --filter @flashdash/web-flasher dev
```

### Start All Frontend Apps
```bash
cd frontend
pnpm dev
```

### Start Individual Apps
```bash
# Web Flasher
pnpm --filter @flashdash/web-flasher dev

# Web App
pnpm --filter web dev

# Desktop App
pnpm --filter desktop dev
```

### Build Frontend
```bash
cd frontend
pnpm build
```

### Stop Frontend
```bash
# Press Ctrl+C in the terminal running the dev server
```

## Environment Variables

### Backend (`.env` in `backend/py-service/`)
```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
ALLOWED_HOSTS=localhost,127.0.0.1
API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
```

### Frontend (`.env` in `frontend/apps/web-flasher/`)
```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :8000
lsof -i :5173

# Kill process
kill -9 <PID>
```

### Backend Not Starting
```bash
# Check Python version
python3 --version

# Recreate virtual environment
cd backend/py-service
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Not Connecting to Backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify environment variable
cat frontend/apps/web-flasher/.env

# Check CORS settings in backend .env
```

### Dependencies Issues
```bash
# Backend
cd backend/py-service
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

## Service URLs

- **Backend API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **Frontend**: `http://localhost:5173` (or next available port)

## Development Workflow

1. **Start Backend** (Terminal 1):
   ```bash
   ./start-backend.sh
   ```

2. **Start Frontend** (Terminal 2):
   ```bash
   ./start-frontend.sh
   ```

3. **Make Changes**:
   - Backend auto-reloads on file changes
   - Frontend has hot module replacement (HMR)

4. **Test**:
   - Backend: `http://localhost:8000/docs`
   - Frontend: `http://localhost:5173`

---

**All commands run locally without Docker for faster development.**

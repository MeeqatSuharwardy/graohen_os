# Local Development Setup (Without Docker)

Run the application locally without Docker for development.

## Prerequisites

### 1. Python 3.11+
```bash
# Check Python version
python3 --version

# Install Python 3.11+ if needed
# macOS: brew install python@3.11
# Ubuntu: sudo apt-get install python3.11 python3.11-venv
```

### 2. Node.js 20+ and pnpm
```bash
# Check Node.js version
node --version

# Install Node.js if needed
# macOS: brew install node
# Ubuntu: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs

# Install pnpm globally
npm install -g pnpm
```

### 3. ADB and Fastboot
```bash
# macOS
brew install android-platform-tools

# Ubuntu/Debian
sudo apt-get install android-tools-adb android-tools-fastboot

# Verify installation
adb --version
fastboot --version
```

## Backend Setup

### 1. Navigate to Backend Directory
```bash
cd backend/py-service
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create Environment File
```bash
# Copy example env file
cp env.example .env

# Edit .env file with your settings
# For local development, you can use defaults or customize:
```

**Minimal `.env` for local development:**
```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# ADB and Fastboot paths (adjust for your system)
ADB_PATH=/usr/local/bin/adb
FASTBOOT_PATH=/usr/local/bin/fastboot

# Bundles directory (create if needed)
GRAPHENE_BUNDLES_ROOT=./bundles
APK_STORAGE_DIR=./apks
LOG_DIR=./logs

# CORS (allow local frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
ALLOWED_HOSTS=localhost,127.0.0.1

# API URLs (for local development)
API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
```

### 5. Create Required Directories
```bash
mkdir -p bundles apks logs
```

### 6. Start Backend Server
```bash
# Option 1: Using uvicorn directly
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Option 2: Using Python module
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Option 3: Run main.py directly (if configured)
python app/main.py
```

**Backend will be available at:** `http://localhost:8000`

**API Documentation:** `http://localhost:8000/docs`

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd frontend
```

### 2. Install Dependencies
```bash
# Install all workspace dependencies
pnpm install
```

### 3. Set Environment Variables

Create `.env` file in `frontend/apps/web-flasher/`:

```bash
cd apps/web-flasher
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
cd ../..
```

### 4. Start Frontend Development Server

**Option 1: Start all frontend apps**
```bash
# From frontend/ directory
pnpm dev
```

**Option 2: Start individual apps**

**Web Flasher (Main App):**
```bash
pnpm --filter @flashdash/web-flasher dev
# Runs on http://localhost:5173 (or next available port)
```

**Web App:**
```bash
pnpm --filter web dev
# Runs on http://localhost:5174 (or next available port)
```

**Desktop App:**
```bash
pnpm --filter desktop dev
# Opens Electron window
```

## Running Both Services

### Terminal 1: Backend
```bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd frontend
pnpm --filter @flashdash/web-flasher dev
```

## Quick Start Scripts

### Backend Start Script (`start-backend.sh`)
```bash
#!/bin/bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Make it executable:
```bash
chmod +x start-backend.sh
./start-backend.sh
```

### Frontend Start Script (`start-frontend.sh`)
```bash
#!/bin/bash
cd frontend
export VITE_API_BASE_URL=http://localhost:8000
pnpm --filter @flashdash/web-flasher dev
```

Make it executable:
```bash
chmod +x start-frontend.sh
./start-frontend.sh
```

## Verify Setup

### Test Backend
```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

### Test Frontend
```bash
# Open in browser
open http://localhost:5173
```

## Common Issues

### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Frontend Can't Connect to Backend
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `VITE_API_BASE_URL` in frontend `.env` file
3. Check CORS settings in backend `.env`

### ADB/Fastboot Not Found
```bash
# Check if installed
which adb
which fastboot

# Add to PATH if needed
export PATH=$PATH:/path/to/platform-tools
```

### Python Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Dependencies Issues
```bash
# Clean install
rm -rf node_modules
rm pnpm-lock.yaml
pnpm install
```

## Development Workflow

1. **Start Backend** (Terminal 1):
   ```bash
   cd backend/py-service
   source venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Start Frontend** (Terminal 2):
   ```bash
   cd frontend
   pnpm --filter @flashdash/web-flasher dev
   ```

3. **Make Changes**:
   - Backend: Auto-reloads on file changes
   - Frontend: Hot module replacement (HMR) enabled

4. **Test**:
   - Backend: `http://localhost:8000/docs`
   - Frontend: `http://localhost:5173`

## Environment Variables Summary

### Backend (`.env` in `backend/py-service/`)
```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Frontend (`.env` in `frontend/apps/web-flasher/`)
```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Stopping Services

- **Backend**: Press `Ctrl+C` in backend terminal
- **Frontend**: Press `Ctrl+C` in frontend terminal

---

**All services run locally without Docker for faster development iteration.**

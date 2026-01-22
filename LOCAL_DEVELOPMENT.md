# Local Development Guide

Complete guide for running FlashDash locally on your development machine.

## Quick Start

### Option 1: Docker (Easiest - Recommended)

```bash
# Clone repository
git clone <your-repo-url>
cd graohen_os

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Access services:
# - Frontend: http://localhost:81
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Option 2: Manual Setup (Backend + Frontend Separately)

See sections below for detailed setup.

---

## Prerequisites

- **Docker & Docker Compose** (for Option 1)
- **Python 3.11+** (for backend)
- **Node.js 20+** and **pnpm** (for frontend)
- **Git**

---

## Option 1: Docker Local Development

### Step 1: Clone and Setup

```bash
git clone <your-repo-url>
cd graohen_os
```

### Step 2: Create Local Environment File

```bash
cp .env.example .env
```

Edit `.env` (optional - defaults work for localhost):

```bash
# Local development settings
FRONTEND_DOMAIN=localhost
BACKEND_DOMAIN=localhost
EMAIL_DOMAIN=localhost
API_BASE_URL=http://localhost:8000
VITE_API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:81
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Step 3: Start Docker Container

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Step 4: Access Services

- **Frontend**: http://localhost:81
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Step 5: Stop Services

```bash
docker-compose down
```

---

## Option 2: Manual Local Development

### Backend Setup

#### Step 1: Install Python Dependencies

```bash
cd backend/py-service

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 2: Create Environment File

```bash
cp .env.example .env
```

Edit `.env`:

```bash
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=true
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_DOMAIN=localhost
EXTERNAL_HTTPS_BASE_URL=http://localhost:8000
```

#### Step 3: Run Backend

```bash
# From backend/py-service directory
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend will be available at: http://localhost:8000

---

### Frontend Setup

#### Step 1: Install Dependencies

```bash
cd frontend

# Install pnpm if not installed
npm install -g pnpm

# Install all dependencies
pnpm install
```

#### Step 2: Create Environment File

```bash
# Create .env file in frontend/packages/web
cd packages/web
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

#### Step 3: Run Frontend Development Server

**Main Web App:**
```bash
cd frontend
pnpm dev:web
# Runs on http://localhost:5173
```

**Web Flasher:**
```bash
cd frontend
pnpm dev:web-flasher
# Runs on http://localhost:5174
```

**Desktop App (Electron):**
```bash
cd frontend
pnpm dev:desktop
```

---

## Local Development URLs

### Backend
- **API Base**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Frontend
- **Main Web App**: http://localhost:5173 (dev server)
- **Web Flasher**: http://localhost:5174 (dev server)
- **Docker Frontend**: http://localhost:81 (if using Docker)

---

## Environment Variables for Local Development

### Backend (.env in backend/py-service/)

```bash
# Server
PY_HOST=127.0.0.1
PY_PORT=8000

# Environment
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# CORS - Allow localhost origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:81
ALLOWED_HOSTS=localhost,127.0.0.1

# Email (for local testing)
EMAIL_DOMAIN=localhost
EXTERNAL_HTTPS_BASE_URL=http://localhost:8000

# Database (optional for local dev)
DATABASE_URL=sqlite:///./local.db
# Or use PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/grapheneos_db

# Redis (optional for local dev)
REDIS_URL=redis://localhost:6379/0
```

### Frontend (.env in frontend/packages/web/)

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_WEB_DEMO_MODE=false
```

---

## Running Tests

### Backend Tests

```bash
cd backend/py-service
source venv/bin/activate
pytest
```

### Frontend Tests

```bash
cd frontend
pnpm test
```

---

## Hot Reload / Auto-Reload

### Backend (with uvicorn --reload)

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Changes to Python files will automatically restart the server.

### Frontend (Vite dev server)

```bash
pnpm dev:web
```

Changes to frontend files will automatically reload in the browser.

---

## Common Local Development Tasks

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
```

### 2. List Connected Devices

```bash
curl http://localhost:8000/devices
```

### 3. List Available Bundles

```bash
curl http://localhost:8000/bundles
```

### 4. Access API Documentation

Open in browser: http://localhost:8000/docs

### 5. View Backend Logs

**Docker:**
```bash
docker-compose logs -f backend
```

**Manual:**
Logs will appear in the terminal where uvicorn is running.

### 6. View Frontend Logs

**Docker:**
```bash
docker-compose logs -f frontend
```

**Manual:**
Logs appear in the terminal where `pnpm dev` is running.

---

## Troubleshooting Local Development

### Port Already in Use

**Backend (port 8000):**
```bash
# Find process using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Mac/Linux
taskkill /PID <PID> /F  # Windows
```

**Frontend (port 5173):**
```bash
lsof -i :5173
kill -9 <PID>
```

### Docker Container Won't Start

```bash
# Check logs
docker-compose logs

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Frontend Can't Connect to Backend

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check CORS settings** in backend `.env`:
   ```bash
   CORS_ORIGINS=http://localhost:5173
   ```

3. **Check VITE_API_BASE_URL** in frontend `.env`:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000
   ```

### Database Connection Errors

For local development, you can use SQLite instead of PostgreSQL:

```bash
# In backend/py-service/.env
DATABASE_URL=sqlite:///./local.db
```

---

## Development Workflow

### Typical Development Session

1. **Start Backend:**
   ```bash
   cd backend/py-service
   source venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. **Start Frontend (in new terminal):**
   ```bash
   cd frontend
   pnpm dev:web
   ```

3. **Make Changes:**
   - Backend: Edit Python files → Auto-reloads
   - Frontend: Edit React files → Auto-reloads in browser

4. **Test Changes:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000/docs

---

## Local File Structure

```
graohen_os/
├── backend/
│   └── py-service/
│       ├── .env              # Backend environment variables
│       ├── venv/              # Python virtual environment
│       └── app/               # Backend code
├── frontend/
│   ├── packages/
│   │   └── web/
│   │       └── .env          # Frontend environment variables
│   └── apps/
├── bundles/                   # GrapheneOS bundles (for testing)
├── downloads/                 # Desktop app builds
└── docker-compose.yml         # Docker configuration
```

---

## Quick Reference Commands

```bash
# Docker - Start everything
docker-compose up -d

# Docker - View logs
docker-compose logs -f

# Docker - Stop everything
docker-compose down

# Backend - Run manually
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --reload

# Frontend - Run manually
cd frontend
pnpm dev:web

# Check services
curl http://localhost:8000/health
curl http://localhost:81/health  # Docker frontend
```

---

## Next Steps

- See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for API endpoints
- See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for production deployment
- See [BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md) for bundle management

# Run Locally - Quick Start Guide

## Option 1: Docker (Easiest)

### Quick Start

```bash
# Clone repository
git clone <your-repo-url>
cd graohen_os

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access services:
# - Frontend: http://localhost:81
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Stop Services

```bash
docker-compose down
```

---

## Option 2: Manual Setup (Backend + Frontend Separately)

### Backend Setup

```bash
cd backend/py-service

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend available at: **http://localhost:8000**

### Frontend Setup

```bash
cd frontend

# Install pnpm if needed
npm install -g pnpm

# Install dependencies
pnpm install

# Create .env file for local API
echo "VITE_API_BASE_URL=http://localhost:8000" > packages/web/.env

# Run frontend dev server
pnpm dev:web
```

Frontend available at: **http://localhost:5173**

---

## Local Access URLs

- **Frontend (Docker)**: http://localhost:81
- **Frontend (Dev Server)**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Environment Variables for Local

### Create `.env` file in project root (optional):

```bash
# Local development settings
DEBUG=true
LOG_LEVEL=DEBUG
VITE_API_BASE_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:81
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## Quick Test

```bash
# Test backend
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

---

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>
```

### Docker Container Won't Start

```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Development Workflow

1. **Start Backend**: `uvicorn app.main:app --reload` (or Docker)
2. **Start Frontend**: `pnpm dev:web` (or Docker)
3. **Make Changes**: Files auto-reload
4. **Test**: http://localhost:5173 (dev) or http://localhost:81 (Docker)

---

For detailed setup, see [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md)

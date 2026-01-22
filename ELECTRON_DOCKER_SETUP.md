# Electron App with Docker Setup

## Overview

The Electron desktop app runs **locally on your machine** and connects to the Docker backend. This guide shows how to automatically start the Electron app when Docker starts.

## Quick Start

### Option 1: Auto-Start Script (Recommended)

**Run this script locally** (not in Docker) to automatically launch Electron when Docker backend is ready:

```bash
# Make script executable
chmod +x start-electron-with-docker.sh

# Run script (it will wait for Docker and start Electron)
./start-electron-with-docker.sh
```

The script will:
1. ✅ Wait for Docker backend to be ready
2. ✅ Configure Electron to use Docker backend (`http://localhost:8000`)
3. ✅ Launch Electron app automatically

### Option 2: Manual Start

**Step 1: Start Docker**

```bash
docker-compose up -d
```

**Step 2: Wait for backend**

```bash
# Wait until backend is ready
curl http://localhost:8000/health
```

**Step 3: Start Electron**

```bash
cd frontend/packages/desktop

# Create .env file pointing to Docker backend
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# Start Electron
pnpm dev
```

---

## Configuration

### Electron Environment File

Create `.env` file in `frontend/packages/desktop/`:

```bash
# Point to Docker backend
VITE_API_BASE_URL=http://localhost:8000
```

### Docker Backend URL

The Electron app connects to:
- **Local Docker**: `http://localhost:8000`
- **Production**: `https://freedomos.vulcantech.co`

---

## Development Workflow

### Typical Session

1. **Start Docker:**
   ```bash
   docker-compose up -d
   ```

2. **Start Electron (auto-launch script):**
   ```bash
   ./start-electron-with-docker.sh
   ```

   Or manually:
   ```bash
   cd frontend/packages/desktop
   echo "VITE_API_BASE_URL=http://localhost:8000" > .env
   pnpm dev
   ```

3. **Make Changes:**
   - Electron will auto-reload
   - Backend changes require Docker restart: `docker-compose restart`

---

## Building Electron App

### Build for Current Platform

```bash
cd frontend/packages/desktop

# Build for your platform
pnpm build        # Windows
pnpm build:mac    # macOS
pnpm build:linux  # Linux
```

### Build All Platforms (requires Docker or multiple machines)

```bash
cd frontend/packages/desktop
pnpm build:mac && pnpm build:win && pnpm build:linux
```

Outputs will be in `frontend/packages/desktop/dist/`

---

## Integration with Docker

### Option 1: Build Electron During Docker Build (Optional)

If you want Electron builds available in Docker, add to Dockerfile:

```dockerfile
# In frontend-builder stage, add:
RUN pnpm --filter desktop build:linux || echo "Skipping Electron build"
```

Then copy builds to downloads directory:

```dockerfile
# In final stage:
COPY --from=frontend-builder /app/packages/desktop/dist/*.AppImage /app/downloads/ || true
COPY --from=frontend-builder /app/packages/desktop/dist/*.deb /app/downloads/ || true
```

**Note:** Electron builds are platform-specific, so building in Docker only works for Linux.

### Option 2: Download Electron Builds

Electron builds can be downloaded from:
- **Windows**: `http://localhost:81/downloads/FlashDash-Setup-*.exe`
- **macOS**: `http://localhost:81/downloads/FlashDash-*.dmg`
- **Linux**: `http://localhost:81/downloads/FlashDash-*.AppImage`

---

## Troubleshooting

### Electron Can't Connect to Backend

1. **Check Docker is running:**
   ```bash
   docker ps
   ```

2. **Check backend is accessible:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check Electron .env file:**
   ```bash
   cat frontend/packages/desktop/.env
   # Should have: VITE_API_BASE_URL=http://localhost:8000
   ```

### Electron Won't Start

1. **Install dependencies:**
   ```bash
   cd frontend/packages/desktop
   pnpm install
   ```

2. **Check Node.js version:**
   ```bash
   node --version  # Should be 20+
   ```

3. **Check pnpm is installed:**
   ```bash
   pnpm --version
   ```

### Backend Not Ready

The auto-start script waits up to 60 seconds for the backend. If it times out:

```bash
# Check Docker logs
docker-compose logs

# Restart Docker
docker-compose restart

# Try again
./start-electron-with-docker.sh
```

---

## Scripts Created

1. **`start-electron-with-docker.sh`** - Auto-launch Electron when Docker starts
2. **`docker/start-with-electron.sh`** - Enhanced Docker startup script

---

## Usage Examples

### Development Mode

```bash
# Terminal 1: Start Docker
docker-compose up -d

# Terminal 2: Start Electron (auto-launch)
./start-electron-with-docker.sh
```

### Production Mode

```bash
# Start Docker
docker-compose up -d

# Electron connects to production backend
# Update .env: VITE_API_BASE_URL=https://freedomos.vulcantech.co
cd frontend/packages/desktop
pnpm dev
```

---

## Summary

- ✅ **Docker** runs backend and frontend web app
- ✅ **Electron** runs locally and connects to Docker backend
- ✅ **Auto-launch script** starts Electron when Docker is ready
- ✅ **Electron** uses `http://localhost:8000` for local Docker backend

The Electron app is a desktop application that runs on your local machine, not inside Docker. It connects to the Docker backend via HTTP.

# Electron App Development Setup

## Quick Start

Run `pnpm run dev` from the project root to start the Electron app.

```bash
pnpm run dev
```

This will:
1. Build the Electron main process
2. Start Vite dev server on port 5174
3. Watch TypeScript files for changes
4. Launch the Electron window

## Prerequisites

### 1. Install Dependencies

```bash
cd frontend
pnpm install
```

### 2. Setup Environment

The Electron app needs to know where the backend API is running.

**Option A: Use setup script**
```bash
./setup-electron-dev.sh
```

**Option B: Manual setup**
```bash
cd frontend/packages/desktop
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

## Running Electron App

### From Project Root
```bash
pnpm run dev
```

### From Frontend Directory
```bash
cd frontend
pnpm dev
```

### Direct Desktop Package
```bash
cd frontend/packages/desktop
pnpm dev
```

## Backend Must Be Running

The Electron app connects to the backend API. Make sure the backend is running:

**Terminal 1: Backend**
```bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2: Electron App**
```bash
pnpm run dev
```

## Environment Configuration

The Electron app uses environment variables from `.env` file in `frontend/packages/desktop/`.

**Local Development (.env):**
```bash
VITE_API_BASE_URL=http://localhost:8000
```

**Production:**
```bash
VITE_API_BASE_URL=https://freedomos.vulcantech.co
```

## How It Works

When you run `pnpm run dev`:

1. **Root `package.json`** → runs `cd frontend && pnpm dev`
2. **Frontend `package.json`** → runs `pnpm --filter desktop dev`
3. **Desktop `package.json`** → runs:
   - `pnpm build:electron` - Builds Electron main process
   - `concurrently` runs:
     - `vite` - Starts Vite dev server on port 5174
     - `tsc -p tsconfig.electron.json --watch` - Watches TypeScript
     - `wait-on http://localhost:5174 && electron .` - Waits for Vite, then launches Electron

## Ports Used

- **5174**: Vite dev server (for Electron app frontend)
- **8000**: Backend API (must be running)

## Troubleshooting

### Electron Window Doesn't Open

1. Check if Vite is running:
   ```bash
   curl http://localhost:5174
   ```

2. Check Electron process:
   ```bash
   ps aux | grep electron
   ```

3. Check logs in the terminal running `pnpm run dev`

### Can't Connect to Backend

1. Verify backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check `.env` file:
   ```bash
   cat frontend/packages/desktop/.env
   ```

3. Should show: `VITE_API_BASE_URL=http://localhost:8000`

### Port 5174 Already in Use

Vite will automatically use the next available port, but Electron is hardcoded to use 5174. Kill the process:

```bash
lsof -i :5174
kill -9 <PID>
```

### Build Errors

```bash
cd frontend/packages/desktop
rm -rf dist-electron node_modules
cd ../..
pnpm install
pnpm run dev
```

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

3. **Make Changes**:
   - Frontend code: Hot reloads automatically
   - Electron main process: Rebuilds on TypeScript changes
   - Backend: Auto-reloads on Python changes

## Available Scripts

From project root:
- `pnpm run dev` - Start Electron app
- `pnpm run dev:desktop` - Same as above
- `pnpm run dev:web` - Start web app instead
- `pnpm run dev:web-flasher` - Start web flasher app
- `pnpm run dev:all` - Start all apps (desktop, web, web-flasher)

---

**Now `pnpm run dev` starts the Electron app!**

# FlashDash - GrapheneOS Flashing Dashboard

A production-ready monorepo for flashing GrapheneOS to Pixel devices via a React + Electron desktop app and React web app.

## ⚠️ SAFETY DISCLAIMER

**WARNING: Flashing custom firmware can permanently damage your device, void warranties, and result in data loss. This tool is provided as-is with no warranties. Use at your own risk.**

- Always backup your data before flashing
- Ensure your device is a supported Pixel model
- Verify bundle integrity before flashing
- This tool requires technical knowledge of Android flashing procedures

## Project Structure

```
repo-root/
  frontend/          # React monorepo (pnpm workspaces)
    packages/
      ui/           # Shared UI components library
      desktop/      # Electron desktop app
      web/          # Web landing + demo dashboard
  backend/          # Python FastAPI service
    py-service/
      app/          # FastAPI application
      tests/        # Test suite
```

## Prerequisites

- **Node.js** 18+ and **pnpm** 8+
- **Python** 3.11+
- **ADB** and **Fastboot** tools installed and accessible
- **GrapheneOS source** synced locally (via `repo init` / `repo sync`)
- **GrapheneOS bundles** prepared offline in a local directory

## Quick Start

### 1. Backend Setup

```bash
# Create virtual environment
python -m venv backend/.venv

# Activate virtual environment
source backend/.venv/bin/activate  # On macOS/Linux
# OR
backend\.venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r backend/py-service/requirements.txt

# Copy and configure environment
cp backend/py-service/.env.example backend/py-service/.env
# Edit backend/py-service/.env with your paths
```

### 2. Frontend Setup

```bash
# Install dependencies
pnpm -C frontend install

# Copy environment files
cp frontend/.env.example frontend/packages/desktop/.env
cp frontend/.env.example frontend/packages/web/.env
# Edit .env files with your configuration
```

### 3. Run Development

**Terminal 1 - Backend:**
```bash
cd backend/py-service
source ../../.venv/bin/activate  # or activate on Windows
uvicorn app.main:app --reload --host 127.0.0.1 --port 17890
```

**Terminal 2 - Frontend:**
```bash
pnpm -C frontend dev
```

This will start:
- Desktop app (Electron)
- Web app (http://localhost:5173)

## Environment Configuration

### Backend (.env)

All paths must be absolute. See `backend/py-service/.env.example` for required variables:

- `ADB_PATH` - Path to adb executable
- `FASTBOOT_PATH` - Path to fastboot executable
- `GRAPHENE_SOURCE_ROOT` - Path to GrapheneOS source (synced via repo)
- `GRAPHENE_BUNDLES_ROOT` - Path to offline bundles directory
- `LOG_DIR` - Directory for log files
- `SUPPORTED_CODENAMES` - Comma-separated list of supported Pixel codenames

### Frontend (.env)

See `frontend/packages/desktop/.env` and `frontend/packages/web/.env` for configuration.

## Bundle Structure

Bundles must be organized as:

```
BUNDLES_ROOT/
  {codename}/
    {version}/
      image.zip
      image.zip.sha256
      image.zip.sig (optional)
      flash-all.sh
      flash-all.bat
      metadata.json (recommended)
```

Example:
```
BUNDLES_ROOT/
  cheetah/
    2025.12.01/
      image.zip
      image.zip.sha256
      flash-all.sh
      flash-all.bat
      metadata.json
```

## Features

### Desktop App
- Device detection (ADB/Fastboot)
- Bundle selection and verification
- Live flashing with SSE log streaming
- Safety gates (typed confirmations, dry-run mode)
- Optional source sync + build (Linux only)

### Web App
- Premium landing page with download CTAs
- OS detection for correct download links
- Custom protocol handler (`flashdash://open`)
- Demo mode with mocked dashboard
- Read-only dashboard (no flashing)

## Building for Production

### Desktop App
```bash
pnpm -C frontend build:desktop
# Outputs to frontend/packages/desktop/out/
```

### Web App
```bash
pnpm -C frontend build:web
# Outputs to frontend/packages/web/dist/
```

### Purchase Number
```bash
Use this purchase number: 100016754321
# Outputs to frontend/packages/web/dist/
```

## API Endpoints

See `backend/py-service/app/main.py` for complete API documentation.

Key endpoints:
- `GET /health` - Service health check
- `GET /devices` - List connected devices
- `GET /device/{id}/identify` - Identify device codename
- `POST /bundles/index` - Index available bundles
- `POST /flash/start` - Start flashing process
- `GET /flash/jobs/{job_id}/stream` - SSE log stream

## Development Notes

- All paths must be configured via `.env` files (no hardcoded paths)
- Flashing is orchestrated by Python backend (not browser)
- Only Pixel devices are supported
- Bundles must exist locally (no runtime downloads)
- Build feature requires Linux and `BUILD_ENABLE=true`

## License

[Your License Here]

## Support

For issues and questions, please open an issue on the repository.


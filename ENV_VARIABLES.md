# Environment Variables Reference

This document lists all environment variables used in the FlashDash project.

## Backend (.env)

Location: `backend/py-service/.env`

### Server Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PY_HOST` | string | `127.0.0.1` | Host for the FastAPI service |
| `PY_PORT` | integer | `17890` | Port for the FastAPI service |

### Tool Paths (Absolute paths required)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ADB_PATH` | string | `/usr/local/bin/adb` | Path to ADB executable |
| `FASTBOOT_PATH` | string | `/usr/local/bin/fastboot` | Path to Fastboot executable |

**Platform-specific examples:**
- **macOS/Linux**: `/usr/local/bin/adb`, `/usr/bin/adb`
- **Windows**: `C:\platform-tools\adb.exe`

### GrapheneOS Paths (Absolute paths required)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GRAPHENE_SOURCE_ROOT` | string | `""` | Path to GrapheneOS source code (synced via repo) |
| `GRAPHENE_BUNDLES_ROOT` | string | `""` | Path to directory containing factory image bundles |

**Bundle Structure:**
```
{GRAPHENE_BUNDLES_ROOT}/
  {codename}/
    {version}/
      image.zip
      image.zip.sha256
      flash-all.sh
      flash-all.bat
      metadata.json
```

### Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_DIR` | string | `./logs` | Directory for log files |

### Supported Devices

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SUPPORTED_CODENAMES` | string | `"cheetah,panther,..."` | Comma-separated list of supported Pixel codenames |

**Default codenames:**
- `cheetah` - Pixel 7 Pro
- `panther` - Pixel 7
- `raven` - Pixel 6 Pro
- `oriole` - Pixel 6
- `husky` - Pixel 8 Pro
- `shiba` - Pixel 8
- `akita` - Pixel 8a
- `felix` - Pixel Fold
- `tangorpro` - Pixel Tablet
- `lynx` - Pixel 7a
- `bluejay` - Pixel 6a
- `barbet` - Pixel 5a
- `redfin` - Pixel 5

### Safety Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DRY_RUN_DEFAULT` | boolean | `true` | Enable dry-run mode by default |
| `SCRIPT_TIMEOUT_SEC` | integer | `1800` | Timeout for flash scripts (seconds) |
| `ALLOW_ADVANCED_FASTBOOT` | boolean | `false` | Allow advanced fastboot commands |
| `REQUIRE_TYPED_CONFIRMATION` | boolean | `true` | Require typed confirmation for dangerous operations |

### Build Configuration (Optional - Linux only)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BUILD_ENABLE` | boolean | `false` | Enable building GrapheneOS from source |
| `BUILD_OUTPUT_DIR` | string | `""` | Output directory for built images |
| `BUILD_TIMEOUT_SEC` | integer | `14400` | Timeout for build process (seconds) |

## Frontend - Desktop (.env)

Location: `frontend/packages/desktop/.env`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VITE_API_BASE_URL` | string | `http://127.0.0.1:17890` | Backend API base URL |
| `VITE_APP_NAME` | string | `FlashDash` | Application name |
| `VITE_APP_VERSION` | string | `1.0.0` | Application version |
| `VITE_DEV_MODE` | boolean | `false` | Enable development mode features |

## Frontend - Web (.env)

Location: `frontend/packages/web/.env`

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VITE_API_BASE_URL` | string | `http://127.0.0.1:17890` | Backend API base URL |
| `VITE_APP_NAME` | string | `FlashDash` | Application name |
| `VITE_APP_VERSION` | string | `1.0.0` | Application version |
| `VITE_DEMO_MODE` | boolean | `false` | Enable demo/mock mode |

## Quick Setup

### Backend

```bash
cd backend/py-service
cp env.example .env
# Edit .env with your paths
```

### Frontend Desktop

```bash
cd frontend/packages/desktop
cp env.example .env
# Edit .env if needed
```

### Frontend Web

```bash
cd frontend/packages/web
cp env.example .env
# Edit .env if needed
```

## Example .env Files

See:
- `backend/py-service/env.example`
- `frontend/packages/desktop/env.example`
- `frontend/packages/web/env.example`


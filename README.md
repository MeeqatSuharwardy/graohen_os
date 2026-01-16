# FlashDash - GrapheneOS Flashing Dashboard

A production-ready monorepo for flashing GrapheneOS to Pixel devices via a React + Electron desktop app and React web app with WebUSB/WebADB support.

## ⚠️ SAFETY DISCLAIMER

**WARNING: Flashing custom firmware can permanently damage your device, void warranties, and result in data loss. This tool is provided as-is with no warranties. Use at your own risk.**

- Always backup your data before flashing
- Ensure your device is a supported Pixel model
- Verify bundle integrity before flashing
- This tool requires technical knowledge of Android flashing procedures

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Quick Start](#quick-start)
6. [Setup Instructions](#setup-instructions)
7. [Configuration](#configuration)
8. [Environment Variables](#environment-variables)
9. [Running the Project](#running-the-project)
10. [API Documentation](#api-documentation)
11. [Device Management](#device-management)
12. [Deployment](#deployment)
13. [WebUSB/WebADB Flasher](#webusbwebadb-flasher)
14. [Troubleshooting](#troubleshooting)
15. [Security](#security)

---

## Overview

FlashDash is a comprehensive solution for flashing GrapheneOS onto Google Pixel devices. It consists of:

- **Backend API** (Python FastAPI) - Device detection, flash job management, APK upload/install
- **Desktop App** (Electron + React) - Device flashing with backend integration
- **Web App** (React) - Landing page and dashboard
- **WebUSB Flasher** (Coming Soon) - Client-side flashing via browser WebUSB/WebADB APIs

### Key Features

- ✅ Device detection via ADB/Fastboot
- ✅ Bootloader unlock workflow
- ✅ Complete flashing automation
- ✅ Real-time progress logging
- ✅ APK upload and installation
- ✅ Password-protected APK upload form
- ✅ Cross-platform support (macOS, Windows, Linux)
- ✅ WebUSB/WebADB support (in development)

### Domain Configuration

- **os.fxmail.ai** - Main API backend
- **fxmail.ai** - Email server only
- **drive.fxmail.ai** - Encrypted drive service

---

## Project Structure

```
graohen_os/
├── backend/
│   └── py-service/
│       ├── app/
│       │   ├── main.py              # FastAPI application
│       │   ├── config.py            # Configuration
│       │   ├── routes/              # API routes
│       │   │   ├── devices.py       # Device management
│       │   │   ├── bundles.py       # Bundle management
│       │   │   ├── flash.py         # Flash operations
│       │   │   └── apks.py          # APK management
│       │   ├── utils/               # Utilities
│       │   │   └── tools.py         # ADB/Fastboot helpers
│       │   └── services/            # Business logic
│       ├── requirements.txt
│       └── .env                     # Environment variables
│
├── frontend/
│   ├── packages/
│   │   ├── ui/                      # Shared UI components
│   │   ├── desktop/                 # Electron desktop app
│   │   │   ├── src/
│   │   │   │   ├── App.tsx          # Main app with tabs
│   │   │   │   ├── pages/
│   │   │   │   │   ├── Dashboard.tsx # Flash tab
│   │   │   │   │   └── APKs.tsx     # APK tab
│   │   │   │   └── lib/
│   │   │   │       └── api.ts       # API client
│   │   │   └── electron/            # Electron main process
│   │   ├── web/                     # React web app
│   │   ├── device-manager/          # WebUSB/WebADB (in development)
│   │   ├── flasher/                 # Flash state machine (in development)
│   │   └── flasher-ui/              # Google Pixel-style UI (in development)
│   ├── pnpm-workspace.yaml
│   └── package.json
│
└── bundles/                         # GrapheneOS factory images
    └── {codename}/
        └── {version}/
```

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Electron/Web Desktop App                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Flash Tab   │  │  APKs Tab    │  │  Device List │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────┬───────────────────────────────┘
                         │ HTTP/HTTPS
                         │ https://os.fxmail.ai
                         │
┌────────────────────────▼───────────────────────────────┐
│              FastAPI Backend (Python)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ /devices     │  │ /flash       │  │ /apks        │ │
│  │ /bundles     │  │ /jobs        │  │ /upload      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────────────┬───────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
┌───────▼────────┐              ┌────────▼────────┐
│  ADB/Fastboot  │              │  Device (USB)   │
│  Commands      │              │  Pixel Device   │
└────────────────┘              └─────────────────┘
```

### Component Breakdown

#### Frontend
- **Dashboard.tsx** - Main flash workflow with device detection
- **APKs.tsx** - APK installation interface
- **Device Detection** - Real-time polling of ADB/Fastboot devices
- **Flash Progress** - SSE log streaming for real-time updates

#### Backend
- **FastAPI Routes** - RESTful API endpoints
- **Device Management** - ADB/Fastboot device detection and identification
- **Flash Jobs** - Background flash execution with progress tracking
- **APK Management** - Upload, list, and install APKs via ADB

### Data Flow

1. **Device Detection**: Frontend polls `/devices` → Backend runs `adb devices` / `fastboot devices`
2. **Flash Job**: Frontend POST `/flash/unlock-and-flash` → Backend spawns `flasher.py` → SSE log stream
3. **APK Upload**: Password-protected form at `/apks/upload` → Backend stores APK → Frontend lists available APKs
4. **APK Install**: Frontend POST `/apks/install` → Backend runs `adb install`

---

## Prerequisites

### Development

- **Node.js** 18+ and **pnpm** 8+
- **Python** 3.11+
- **ADB** and **Fastboot** tools installed and accessible

### Production (VPS/Server)

- **Ubuntu** 22.04+ (or similar Linux distribution)
- **Nginx** (reverse proxy)
- **Certbot** (SSL certificates)
- **PostgreSQL** (optional, for database features)
- **Redis** (optional, for caching/rate limiting)

### Browser (for WebUSB/WebADB)

- **Chrome/Edge** or Chromium-based browser
- **HTTPS** or **localhost** (required for WebUSB API)

---

## Quick Start

### 1. Clone Repository

```bash
git clone YOUR_REPOSITORY_URL graohen_os
cd graohen_os
```

### 2. Backend Setup

```bash
cd backend/py-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your paths (see Configuration section)
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Copy environment files (if needed)
cp .env.example packages/desktop/.env
cp .env.example packages/web/.env
```

### 4. Run Development Servers

**Terminal 1 - Backend:**
```bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 17890
```

**Terminal 2 - Frontend:**
```bash
cd frontend
pnpm dev
```

This starts:
- Desktop app (Electron) - auto-opens
- Web app - http://localhost:5173
- Backend API - http://127.0.0.1:17890

---

## Setup Instructions

### Backend Setup

#### 1. Install Python Dependencies

```bash
cd backend/py-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Install ADB/Fastboot

**macOS:**
```bash
brew install android-platform-tools
```

**Linux:**
```bash
# Option A: Install from package manager
sudo apt install android-tools-adb android-tools-fastboot

# Option B: Download latest platform-tools
cd /tmp
wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
sudo mv platform-tools /opt/android-platform-tools
sudo ln -sf /opt/android-platform-tools/adb /usr/local/bin/adb
sudo ln -sf /opt/android-platform-tools/fastboot /usr/local/bin/fastboot
```

**Windows:**
- Download from: https://developer.android.com/tools/releases/platform-tools
- Add to PATH or configure `ADB_PATH` and `FASTBOOT_PATH` in `.env`

#### 3. Create Required Directories

```bash
# Bundle storage
mkdir -p /path/to/bundles

# APK storage
mkdir -p /root/graohen_os/apks

# Logs directory
mkdir -p backend/py-service/logs
```

#### 4. Configure USB Device Access (Linux)

```bash
# Create udev rules
sudo cat > /etc/udev/rules.d/51-android.rules << 'EOF'
# Google devices
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666"
# Samsung
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Frontend Setup

#### 1. Install Node.js and pnpm

```bash
# Install Node.js 18+
# Then install pnpm
npm install -g pnpm
```

#### 2. Install Dependencies

```bash
cd frontend
pnpm install
```

#### 3. Build Shared Packages (if needed)

```bash
# Build UI package
pnpm --filter ui build

# Build other packages as needed
```

---

## Configuration

### Backend Configuration (`.env`)

Create `backend/py-service/.env`:

```bash
# Application
APP_NAME=GrapheneOS Installer API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# Server
PY_HOST=0.0.0.0
PY_PORT=17890

# API Configuration
API_V1_PREFIX=/api/v1
ALLOWED_HOSTS=os.fxmail.ai,drive.fxmail.ai,localhost,127.0.0.1

# CORS Configuration
CORS_ORIGINS=https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai

# ADB and Fastboot Paths (absolute paths required)
ADB_PATH=/usr/local/bin/adb
FASTBOOT_PATH=/usr/local/bin/fastboot

# Bundle Storage (absolute path required)
GRAPHENE_BUNDLE_PATH=/root/graohen_os/bundles

# APK Storage
APK_STORAGE_DIR=/root/graohen_os/apks

# Email Domain Configuration
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# Database (optional)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/grapheneos_db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=./logs

# Supported Devices
SUPPORTED_CODENAMES=cheetah,panther,raven,oriole,husky,shiba,akita,felix,tangorpro,lynx,bluejay,barbet,redfin
```

### Frontend Configuration

**Desktop App** (`frontend/packages/desktop/.env`):
```bash
VITE_API_BASE_URL=https://os.fxmail.ai
```

**Web App** (`frontend/packages/web/.env`):
```bash
VITE_API_BASE_URL=https://os.fxmail.ai
```

---

## Environment Variables

### Backend Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PY_HOST` | string | `0.0.0.0` | FastAPI server host |
| `PY_PORT` | integer | `17890` | FastAPI server port |
| `ADB_PATH` | string | `/usr/local/bin/adb` | Path to ADB executable |
| `FASTBOOT_PATH` | string | `/usr/local/bin/fastboot` | Path to Fastboot executable |
| `GRAPHENE_BUNDLE_PATH` | string | `~/.graphene-installer/bundles` | Root directory for GrapheneOS bundles |
| `APK_STORAGE_DIR` | string | `/root/graohen_os/apks` | Directory for uploaded APKs |
| `EMAIL_DOMAIN` | string | `fxmail.ai` | Email domain |
| `CORS_ORIGINS` | string | `https://os.fxmail.ai,...` | Allowed CORS origins |
| `ALLOWED_HOSTS` | string | `os.fxmail.ai,...` | Allowed host headers |

### Frontend Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VITE_API_BASE_URL` | string | `http://127.0.0.1:17890` | Backend API base URL |
| `VITE_APP_NAME` | string | `FlashDash` | Application name |
| `VITE_APP_VERSION` | string | `1.0.0` | Application version |

### Device Codenames

Supported Pixel device codenames:
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

---

## Running the Project

### Development Mode

**Backend:**
```bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 17890
```

**Frontend:**
```bash
cd frontend
pnpm dev
```

### Production Mode

**Backend (systemd service):**
```bash
# Create service file
sudo cat > /etc/systemd/system/graphene-flasher.service << 'EOF'
[Unit]
Description=GrapheneOS Flasher Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/graohen_os/backend/py-service
Environment="PATH=/root/graohen_os/backend/py-service/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/graohen_os/backend/py-service/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 17890
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable graphene-flasher
sudo systemctl start graphene-flasher

# Check status
sudo systemctl status graphene-flasher
```

**Frontend Build:**
```bash
# Build desktop app
cd frontend
pnpm --filter desktop build

# Build web app
pnpm --filter web build
```

### Building for Production

```bash
# Build all frontend packages
cd frontend
pnpm build

# Outputs:
# - Desktop: frontend/packages/desktop/out/
# - Web: frontend/packages/web/dist/
```

---

## API Documentation

### Base URL

- **Local Development**: `http://127.0.0.1:17890`
- **Production**: `https://os.fxmail.ai`
- **API v1 Prefix**: `/api/v1`

### Key Endpoints

#### Health & Status

- `GET /health` - Health check endpoint
- `GET /tools/check` - Check ADB/Fastboot availability

#### Device Management

- `GET /devices` - List all connected devices
- `GET /devices/{device_id}/identify` - Identify device codename
- `POST /devices/{device_id}/reboot/bootloader` - Reboot to bootloader

#### Flash Operations

- `POST /flash/unlock-and-flash` - Unlock bootloader and flash GrapheneOS
- `GET /flash/jobs/{job_id}` - Get flash job status
- `GET /flash/jobs/{job_id}/stream` - Stream flash logs (SSE)
- `POST /flash/jobs/{job_id}/cancel` - Cancel flash job

#### Bundle Management

- `POST /bundles/index` - Index available bundles
- `GET /bundles/for/{codename}` - Get bundle for device codename
- `POST /bundles/verify` - Verify bundle integrity

#### APK Management

- `GET /apks/upload` - Password-protected APK upload form (password: `AllHailToEagle`)
- `POST /apks/upload` - Upload APK file
- `GET /apks/list` - List all uploaded APKs
- `POST /apks/install` - Install APK on connected device

#### Authentication (API v1)

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login with credentials
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout and revoke tokens

#### Email Service (API v1)

- `POST /api/v1/email/send` - Send encrypted email
- `GET /api/v1/email/{email_id}` - Get email (authenticated)
- `POST /api/v1/email/{email_id}/unlock` - Unlock passcode-protected email

#### Drive Service (API v1)

- `POST /api/v1/drive/upload` - Upload encrypted file
- `GET /api/v1/drive/file/{file_id}` - Get file metadata
- `GET /api/v1/drive/file/{file_id}/download` - Download file

### Example API Calls

```bash
# Health check
curl http://127.0.0.1:17890/health

# List devices
curl http://127.0.0.1:17890/devices

# Start flash job
curl -X POST http://127.0.0.1:17890/flash/unlock-and-flash \
  -H "Content-Type: application/json" \
  -d '{"device_serial": "DEVICE_SERIAL", "skip_unlock": false}'

# List APKs
curl http://127.0.0.1:17890/apks/list

# Install APK
curl -X POST http://127.0.0.1:17890/apks/install \
  -H "Content-Type: application/json" \
  -d '{"device_serial": "DEVICE_SERIAL", "apk_filename": "app.apk"}'
```

### Interactive API Documentation

- **Swagger UI**: `http://127.0.0.1:17890/docs` (when `DEBUG=True`)
- **ReDoc**: `http://127.0.0.1:17890/redoc` (when `DEBUG=True`)

---

## Device Management

### Device States

- **`device`** - Device is in ADB mode (normal Android mode with USB debugging)
- **`fastboot`** - Device is in Fastboot/Bootloader mode (required for flashing)
- **`unauthorized`** - Device needs USB debugging authorization
- **`offline`** - Device is not responding

### Device Detection

The app automatically detects devices via:
1. **ADB devices** - For devices in normal Android mode
2. **Fastboot devices** - For devices in bootloader mode
3. **Real-time polling** - Frontend polls `/devices` endpoint every 3 seconds

### Required Mode for Flashing

**Fastboot Mode (Bootloader) is required for flashing GrapheneOS.**

The app can automatically:
1. Detect if device is in ADB mode
2. Reboot it to Fastboot mode
3. Wait for device to enter Fastboot
4. Start flashing process

### Manual Fastboot Mode Entry

**Method 1: Using ADB**
```bash
adb reboot bootloader
```

**Method 2: Hardware Buttons (Device OFF)**
1. Turn off device completely
2. Hold **Power** + **Volume Down** simultaneously
3. Keep holding until Fastboot screen appears

**Method 3: Hardware Buttons (Device ON)**
1. Long press **Power** button
2. Long press "Power off" or "Restart"
3. Immediately hold **Volume Down** when device starts rebooting

### Device Identification

The backend automatically identifies devices by:
1. Querying device properties via ADB/Fastboot
2. Extracting codename (e.g., `panther` for Pixel 7)
3. Matching against supported codenames list

---

## Deployment

### VPS Deployment (Digital Ocean, AWS, etc.)

#### 1. Server Setup

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3.10 python3.10-venv python3-pip nginx certbot postgresql redis-server

# Install ADB/Fastboot
cd /tmp
wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
mv platform-tools /opt/android-platform-tools
ln -sf /opt/android-platform-tools/adb /usr/local/bin/adb
ln -sf /opt/android-platform-tools/fastboot /usr/local/bin/fastboot
```

#### 2. Project Installation

```bash
# Navigate to project location
cd /root
git clone YOUR_REPOSITORY_URL graohen_os
cd graohen_os/backend/py-service

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p /root/graohen_os/bundles
mkdir -p /root/graohen_os/apks
mkdir -p /root/graohen_os/backend/py-service/logs
```

#### 3. DNS Configuration

Configure DNS records in your DNS provider:

**os.fxmail.ai (Main API):**
```
Type: A
Name: os
Value: YOUR_VPS_IP
TTL: 3600
```

**drive.fxmail.ai (Encrypted Drive):**
```
Type: A
Name: drive
Value: YOUR_VPS_IP
TTL: 3600
```

#### 4. SSL Certificate Setup

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Obtain certificates
certbot certonly --standalone -d os.fxmail.ai
certbot certonly --standalone -d drive.fxmail.ai

# Auto-renewal is enabled by default
systemctl status certbot.timer
```

#### 5. Nginx Configuration

**Main API Domain (os.fxmail.ai):**
```bash
cat > /etc/nginx/sites-available/os.fxmail.ai << 'EOF'
server {
    listen 80;
    server_name os.fxmail.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name os.fxmail.ai;

    ssl_certificate /etc/letsencrypt/live/os.fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/os.fxmail.ai/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:17890;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/os.fxmail.ai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

#### 6. Firewall Setup

```bash
# Install UFW
apt install ufw

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw allow from 127.0.0.1 to any port 17890  # Backend (localhost only)

ufw enable
ufw status verbose
```

#### 7. Systemd Service

Create service file (see [Running the Project](#running-the-project) section).

### Desktop Electron App Distribution

The Electron app can be distributed as:
- **macOS**: `.dmg` file
- **Windows**: `.exe` installer (NSIS)
- **Linux**: `.AppImage` file

Build commands:
```bash
cd frontend/packages/desktop
pnpm build
# Outputs to frontend/packages/desktop/out/
```

---

## WebUSB/WebADB Flasher

### Architecture (In Development)

A new frontend is being developed that uses WebUSB and WebADB APIs for client-side flashing, replicating the Google Pixel Web Flash Tool UI.

**Key Features:**
- Client-side device detection via `navigator.usb`
- Client-side flashing via WebADB libraries
- No backend required for flashing (APKs still use backend)
- Same UI/UX as Google Pixel Web Flasher

**Structure:**
```
frontend/
├── packages/
│   ├── device-manager/    # WebUSB + WebADB device detection
│   ├── flasher/           # Flash state machine
│   └── flasher-ui/        # Google Pixel-style UI components
└── apps/
    ├── web-flasher/       # React web app (Chrome)
    └── electron-flasher/  # Electron wrapper
```

**Browser Requirements:**
- Chrome/Edge or Chromium-based browser
- HTTPS or localhost (required for WebUSB)
- User must manually approve USB device access

**Status**: Foundation packages created, full implementation in progress.

See `frontend/packages/device-manager/` for current implementation.

---

## Troubleshooting

### Backend Issues

#### Service Won't Start

```bash
# Check logs
journalctl -u graphene-flasher -n 50

# Check if port is in use
netstat -tulpn | grep 17890

# Test Python environment
cd backend/py-service
source venv/bin/activate
python -c "import uvicorn; print('OK')"
```

#### Device Not Detected

**Check ADB/Fastboot:**
```bash
adb devices
fastboot devices

# Check paths
which adb
which fastboot

# Verify paths in .env match actual locations
```

**Linux USB Permissions:**
```bash
# Check if device is visible
lsusb | grep -i google

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Try running as root (for testing)
sudo adb devices
```

**Device Shows as "Unauthorized":**
1. Enable USB debugging on device
2. Check "Always allow from this computer" when prompted
3. Or revoke and re-authorize:
   ```bash
   adb kill-server
   adb start-server
   # Check device for authorization prompt
   ```

#### Fastboot Device Not Detected

```bash
# Verify device is in fastboot mode (check device screen)
fastboot devices

# Check USB connection
lsusb | grep -i google

# Reboot to fastboot
adb reboot bootloader
# Wait 5-10 seconds
fastboot devices
```

### Frontend Issues

#### Can't Connect to Backend

```bash
# Verify backend is running
curl http://127.0.0.1:17890/health

# Check CORS configuration in backend .env
# Should include your frontend origin

# Check VITE_API_BASE_URL in frontend .env
```

#### Electron App Not Opening

```bash
# Check if port 5174 is available (dev server)
# Check Electron logs in terminal

# Try rebuilding
cd frontend/packages/desktop
pnpm build
```

### Nginx Issues

#### 502 Bad Gateway

```bash
# Check if backend is running
systemctl status graphene-flasher

# Check nginx error logs
tail -f /var/log/nginx/os.fxmail.ai.error.log

# Verify backend is accessible locally
curl http://127.0.0.1:17890/health
```

#### SSL Certificate Issues

```bash
# Check certificate expiration
certbot certificates

# Renew certificates manually
certbot renew

# Test renewal
certbot renew --dry-run
```

### Network Issues

#### Port Already in Use

```bash
# Find process using port 17890
lsof -ti:17890

# Kill process
lsof -ti:17890 | xargs kill -9

# Or change port in .env and service file
```

#### Firewall Blocking

```bash
# Check firewall status
ufw status verbose

# Allow required ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp

# Allow backend port from localhost only
ufw allow from 127.0.0.1 to any port 17890
```

### Common Errors

#### "Device not found"

- **Cause**: Device not in correct mode or USB connection issue
- **Solution**: Check device state, verify USB cable, try different USB port

#### "Fastboot command timed out"

- **Cause**: Device slow to respond or USB disconnected during operation
- **Solution**: Normal during device reboots, script should handle automatically

#### "flashing unlock is not allowed"

- **Cause**: OEM unlocking disabled in Developer Options
- **Solution**: Enable OEM unlocking in Settings → Developer Options

#### "could not clear partition"

- **Cause**: AVB custom key partition doesn't exist (normal on fresh devices) OR bootloader protection triggered
- **Solution**: Script handles this automatically - if persistent, check bootloader state

---

## Security

### Backend Security

- **CORS Configuration**: Only allows specific domains (`os.fxmail.ai`, `drive.fxmail.ai`)
- **Rate Limiting**: Redis-based per IP/user
- **Brute Force Protection**: Automatic lockout after failed attempts
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options
- **HTTPS**: Enforced via Nginx with Let's Encrypt certificates

### Authentication

- **JWT Tokens**: Access tokens (30 min) + Refresh tokens (7 days)
- **Token Rotation**: New refresh token issued on refresh
- **Token Revocation**: Redis-based revocation on logout

### APK Upload Security

- **Password Protection**: Upload form requires password (`AllHailToEagle`)
- **File Validation**: Only `.apk` files accepted
- **Storage**: APKs stored in `/root/graohen_os/apks`

### Best Practices

1. **Change Default Passwords**: Update `SECRET_KEY` in production
2. **Firewall**: Only expose ports 80, 443 publicly
3. **SSL Certificates**: Keep certificates renewed automatically
4. **Logs**: Monitor logs for suspicious activity
5. **Updates**: Keep system and dependencies updated

### Security Checklist

- [ ] Changed `SECRET_KEY` in `.env`
- [ ] Configured firewall (UFW)
- [ ] SSL certificates installed and auto-renewal enabled
- [ ] Security headers configured in Nginx
- [ ] Backend port (17890) not publicly accessible
- [ ] CORS properly configured
- [ ] `.env` file permissions set to 600
- [ ] Database credentials changed (if using database)

---

## Bundle Structure

GrapheneOS bundles must be organized as:

```
{GRAPHENE_BUNDLE_PATH}/
└── {codename}/
    └── {version}/
        ├── image.zip              # Factory image archive
        ├── image.zip.sha256       # SHA256 checksum
        ├── image.zip.sig          # Signature (optional)
        ├── flash-all.sh           # Flash script (Linux/macOS)
        ├── flash-all.bat          # Flash script (Windows)
        └── metadata.json          # Metadata (recommended)
```

**Example:**
```
/root/graohen_os/bundles/
└── panther/
    └── 2025122500/
        ├── image.zip
        ├── image.zip.sha256
        ├── flash-all.sh
        └── flash-all.bat
```

### Bundle Download

Bundles can be downloaded from:
```
https://releases.grapheneos.org/{codename}-factory-{version}.zip
```

**Example URLs:**
- Pixel 7 Pro: `https://releases.grapheneos.org/cheetah-factory-2024122200.zip`
- Pixel 7: `https://releases.grapheneos.org/panther-factory-2024122200.zip`
- Pixel 8 Pro: `https://releases.grapheneos.org/husky-factory-2024122200.zip`

---

## Flashing Workflow

### Complete Unlock & Flash Process

1. **Preflight Checks**
   - Verify ADB/Fastboot available
   - Check device connection
   - Verify OEM unlocking enabled (if locking)
   - Check bundle availability

2. **Device Detection**
   - Device detected in ADB or Fastboot mode
   - Device codename identified
   - Bundle selected (automatic or manual)

3. **Bootloader Unlock** (if needed)
   - Reboot to bootloader
   - Execute `fastboot flashing unlock`
   - Wait for user confirmation on device
   - Verify unlock status

4. **Flashing Process**
   - Flash bootloader (to other slot)
   - Flash radio
   - Flash core partitions (boot, vendor_boot, dtbo, vbmeta, etc.)
   - Erase userdata & metadata
   - Flash super partition (14 split images)

5. **Final Reboot**
   - Reboot device
   - Device boots into GrapheneOS
   - First boot may take 5-10 minutes

### Flash-Only Mode

For devices with already unlocked bootloaders:
- Skip unlock step
- Directly proceed to flashing

---

## Quick Reference

### Important Paths

- **Project Root**: `/root/graohen_os` (or your chosen path)
- **Backend**: `/root/graohen_os/backend/py-service`
- **Bundles**: `/root/graohen_os/bundles`
- **APKs**: `/root/graohen_os/apks`
- **Logs**: `/root/graohen_os/backend/py-service/logs`

### Service Management

```bash
# Backend service
systemctl status graphene-flasher
systemctl restart graphene-flasher
systemctl stop graphene-flasher
systemctl start graphene-flasher

# View logs
journalctl -u graphene-flasher -f

# Nginx
systemctl status nginx
systemctl restart nginx
systemctl reload nginx
```

### Test Commands

```bash
# Health check
curl http://127.0.0.1:17890/health
curl https://os.fxmail.ai/health

# Device detection
curl http://127.0.0.1:17890/devices

# APK list
curl http://127.0.0.1:17890/apks/list

# Check ADB/Fastboot
adb devices
fastboot devices
```

### Purchase Number

For testing/development, use purchase number: `100016754321`

---

## Development Notes

### Code Organization

- **Backend**: Python FastAPI with route-based organization
- **Frontend**: React monorepo with shared UI packages
- **Device Logic**: Centralized in `app/utils/tools.py`
- **Flash Logic**: Handled by `flasher.py` script

### Key Technologies

- **Backend**: FastAPI, Python 3.11+, Uvicorn
- **Frontend**: React, TypeScript, Vite, Electron
- **UI**: TailwindCSS, shadcn/ui components
- **Device Communication**: ADB/Fastboot (platform-tools)
- **WebUSB/WebADB**: @yume-chan/adb (in development)

### Best Practices

- All paths configured via `.env` files (no hardcoded paths)
- Flash operations orchestrated by Python backend
- Only Pixel devices supported (verified via codename)
- Bundles must exist locally (no runtime downloads)
- Real-time progress via SSE log streaming

---

## Support & Resources

### Getting Help

1. Check logs: `journalctl -u graphene-flasher -n 100`
2. Verify device detection: `adb devices` and `fastboot devices`
3. Test endpoints: Use curl to test API endpoints
4. Check configuration: Verify `.env` settings

### Useful Links

- [GrapheneOS Releases](https://releases.grapheneos.org/)
- [Google Pixel Web Flasher](https://flash.android.com/)
- [WebUSB API Specification](https://wicg.github.io/webusb/)
- [WebADB Library](https://github.com/yume-chan/ya-webadb)

---

## License

[Your License Here]

---

**Last Updated**: January 2026  
**Version**: 1.0.0

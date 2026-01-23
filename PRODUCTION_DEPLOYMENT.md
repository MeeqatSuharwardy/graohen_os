# 🚀 Production Deployment Guide - Nginx + Systemd (No Docker)

Complete guide to deploy FlashDash backend and frontend in production using Nginx reverse proxy and systemd service (Linux) or Windows Service.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Backend Deployment](#backend-deployment)
4. [Frontend Build & Deployment](#frontend-build--deployment)
5. [Nginx Configuration](#nginx-configuration)
6. [SSL Setup](#ssl-setup)
7. [Service Management](#service-management)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Windows Server
- **RAM**: Minimum 2GB (4GB+ recommended)
- **CPU**: 2+ cores
- **Disk**: 20GB+ free space
- **Network**: Public IP address, ports 80/443 open

### Software Requirements

- Python 3.11+
- Node.js 20+
- pnpm
- Nginx
- ADB & Fastboot (for device flashing)
- PostgreSQL (optional, for email/drive features)
- Redis (optional, for caching)

---

## Server Setup

### Step 1: Update System

#### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt upgrade -y
```

#### Linux (CentOS/RHEL)
```bash
sudo yum update -y
```

### Step 2: Install Required Software

#### Linux
```bash
# Install Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install pnpm
sudo npm install -g pnpm

# Install Nginx
sudo apt install -y nginx

# Install ADB & Fastboot
sudo apt install -y android-tools-adb android-tools-fastboot

# Install PostgreSQL (optional)
sudo apt install -y postgresql postgresql-contrib

# Install Redis (optional)
sudo apt install -y redis-server
```

#### Windows
```powershell
# Install Python 3.11+ from python.org
# Install Node.js 20+ from nodejs.org
# Install pnpm
npm install -g pnpm

# Install Nginx for Windows from nginx.org
# Install ADB & Fastboot from developer.android.com
```

### Step 3: Create Application Directory

#### Linux
```bash
# Create directory (if not exists)
sudo mkdir -p /root/graohen_os
sudo chown root:root /root/graohen_os
```

#### Windows
```powershell
# Create directory (if not exists)
New-Item -ItemType Directory -Path "C:\graohen_os" -Force
```

---

## Backend Deployment

### Step 1: Clone Repository

#### Linux
```bash
cd /root
git clone <repository-url> graohen_os
cd /root/graohen_os
```

#### Windows
```powershell
cd C:\
git clone <repository-url> graohen_os
cd C:\graohen_os
```

### Step 2: Setup Backend

#### Linux
```bash
cd /root/graohen_os/backend/py-service

# Create virtual environment
python3.11 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp env.example .env
nano .env
```

#### Windows
```powershell
cd C:\graohen_os\backend\py-service

# Create virtual environment
python -m venv venv

# Activate and install dependencies
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
Copy-Item env.example .env
notepad .env
```

### Step 3: Configure Backend

Edit `backend/py-service/.env`:

```bash
# Server Configuration
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=false
ENVIRONMENT=production

# Domain Configuration
ALLOWED_HOSTS=freedomos.vulcantech.co
CORS_ORIGINS=https://freedomos.vulcantech.co

# API URLs
API_BASE_URL=https://freedomos.vulcantech.co/backend
EXTERNAL_HTTPS_BASE_URL=https://freedomos.vulcantech.co

# ADB/Fastboot Paths
ADB_PATH=/usr/bin/adb
FASTBOOT_PATH=/usr/bin/fastboot

# Directories
GRAPHENE_BUNDLES_ROOT=/root/graohen_os/bundles
APK_STORAGE_DIR=/root/graohen_os/apks
LOG_DIR=/root/graohen_os/logs

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-change-this-in-production

# Database (if using)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/flashdash_db

# Redis (if using)
REDIS_URL=redis://localhost:6379/0
```

### Step 4: Create Systemd Service (Linux)

```bash
sudo nano /etc/systemd/system/flashdash-backend.service
```

Add configuration:

```ini
[Unit]
Description=FlashDash Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/graohen_os/backend/py-service
Environment="PATH=/root/graohen_os/backend/py-service/venv/bin"
ExecStart=/root/graohen_os/backend/py-service/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=flashdash-backend

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable flashdash-backend
sudo systemctl start flashdash-backend
sudo systemctl status flashdash-backend
```

### Step 5: Create Windows Service (Windows)

Use NSSM (Non-Sucking Service Manager):

```powershell
# Download NSSM from nssm.cc
# Extract and run:
.\nssm.exe install FlashDashBackend

# Configure:
# Path: C:\graohen_os\backend\py-service\venv\Scripts\python.exe
# Arguments: -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Working Directory: C:\graohen_os\backend\py-service
# Service Name: FlashDashBackend

# Start service
net start FlashDashBackend
```

---

## Frontend Build & Deployment

### Step 1: Install Dependencies

#### Linux
```bash
cd /root/graohen_os/frontend

# Install all dependencies
pnpm install
```

#### Windows
```powershell
cd C:\graohen_os\frontend

# Install all dependencies
pnpm install
```

### Step 2: Build Frontend Dependencies First

**IMPORTANT**: Build workspace packages in the correct order before building the web-flasher app.

#### Linux
```bash
cd /root/graohen_os/frontend

# Build dependencies in order
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build

# Create production .env
echo "VITE_API_BASE_URL=https://your-backend-domain.com" > packages/desktop/.env
echo "VITE_API_BASE_URL=https://your-backend-domain.com" > packages/web/.env
echo "VITE_API_BASE_URL=https://your-backend-domain.com" > apps/web-flasher/.env

# Build web frontend
pnpm --filter @flashdash/web-flasher build

# Or use the convenience script (builds all dependencies automatically)
pnpm build:web-flasher
```

#### Windows
```powershell
cd C:\graohen_os\frontend

# Build dependencies in order
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build

# Create production .env
"VITE_API_BASE_URL=https://your-backend-domain.com" | Out-File -FilePath "packages\desktop\.env" -Encoding utf8
"VITE_API_BASE_URL=https://your-backend-domain.com" | Out-File -FilePath "packages\web\.env" -Encoding utf8
"VITE_API_BASE_URL=https://your-backend-domain.com" | Out-File -FilePath "apps\web-flasher\.env" -Encoding utf8

# Build web frontend
pnpm --filter @flashdash/web-flasher build

# Or use the convenience script
pnpm build:web-flasher
```

**Note**: If you get errors about missing `@flashdash/flasher-ui` or `@flashdash/flasher`, make sure to build them first using the commands above.

### Step 3: Build Windows EXE (For Download)

**You are currently here**: `cd /root/graohen_os/frontend/packages/desktop`

#### Build Windows EXE on Linux Server

**Note**: Building Windows EXE on Linux requires Wine. For best results, build on a Windows machine and upload the EXE, or use Wine on Linux.

```bash
# You are here: /root/graohen_os/frontend/packages/desktop

# Install Wine (if not already installed)
sudo apt update
sudo apt install -y wine64 wine32

# Set up Wine (first time only)
winecfg  # Accept defaults, close the window

# Build Windows EXE
export WINEPREFIX=~/.wine
export DISPLAY=:0
pnpm build:win

# The EXE will be in: /root/graohen_os/frontend/packages/desktop/dist/
# Look for: FlashDash Setup 1.0.0.exe (or similar name based on version)
```

**Alternative**: If Wine doesn't work, build on a Windows machine:
1. Build on Windows: `cd C:\graohen_os\frontend\packages\desktop && pnpm build:win`
2. Upload the EXE from `dist/` folder to your server

### Step 4: Deploy Frontend Files

#### Linux
```bash
# Copy built web files to web directory
sudo mkdir -p /var/www/flashdash
sudo cp -r /root/graohen_os/frontend/apps/web-flasher/dist/* /var/www/flashdash/
sudo chown -R www-data:www-data /var/www/flashdash

# Create downloads directory for EXE
sudo mkdir -p /var/www/flashdash/downloads

# Copy Windows EXE to downloads directory
# Find the EXE file (it may have a name like "FlashDash Setup 1.0.0.exe")
EXE_FILE=$(find /root/graohen_os/frontend/packages/desktop/dist -name "*.exe" | head -1)
if [ -n "$EXE_FILE" ]; then
    sudo cp "$EXE_FILE" /var/www/flashdash/downloads/FlashDash-Setup-1.0.0.exe
    sudo chown www-data:www-data /var/www/flashdash/downloads/*.exe
    echo "EXE copied successfully: $EXE_FILE"
else
    echo "WARNING: No EXE file found. Build may have failed or EXE needs to be uploaded manually."
fi
```

---

## Nginx Configuration

### Step 1: Create Single Domain Nginx Config

**Domain**: `freedomos.vulcantech.co`
- Frontend served from root `/`
- Backend proxied from `/backend`
- Downloads served from `/downloads`

#### Linux
```bash
sudo nano /etc/nginx/sites-available/freedomos
```

Add configuration:

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name freedomos.vulcantech.co;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# Main server block
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    # SSL Certificates (update paths after Let's Encrypt setup)
    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Root directory for frontend
    root /var/www/flashdash;
    index index.html;

    # Backend API proxy - /backend/* routes to backend service
    location /backend {
        # Remove /backend prefix when proxying
        rewrite ^/backend/?(.*) /$1 break;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts for long-running operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;

        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;

        # CORS Headers
        add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
        add_header Access-Control-Allow-Credentials "true" always;

        # Handle preflight requests
        if ($request_method = OPTIONS) {
            return 204;
        }
    }

    # Legacy API routes (also proxy to backend)
    location ~ ^/(api|devices|bundles|flash|health|tools) {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS Headers
        add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # Downloads directory (Windows EXE, macOS DMG, Linux AppImage)
    location /downloads {
        alias /var/www/flashdash/downloads;
        autoindex off;
        
        # Set proper headers for downloads
        add_header Content-Disposition "attachment";
        add_header Content-Type "application/octet-stream";
        
        # Cache control for downloads
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Serve static frontend files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Step 2: Enable Site

#### Linux
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## SSL Setup

### Option 1: Let's Encrypt (Recommended)

#### Linux
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate for freedomos.vulcantech.co
sudo certbot --nginx -d freedomos.vulcantech.co

# Auto-renewal (already configured)
sudo certbot renew --dry-run
```

#### Windows
```powershell
# Use Certbot for Windows or Win-ACME
# Download from: https://www.win-acme.com/
```

### Option 2: Cloudflare SSL (Flexible Mode)

If using Cloudflare, you can use Cloudflare SSL:

1. Set Cloudflare SSL mode to "Flexible"
2. Nginx listens on HTTP (port 80) only
3. Cloudflare handles SSL termination

Update Nginx configs to listen on port 80 only and remove SSL certificates.

---

## Service Management

### Backend Service

#### Linux
```bash
# Start
sudo systemctl start flashdash-backend

# Stop
sudo systemctl stop flashdash-backend

# Restart
sudo systemctl restart flashdash-backend

# Status
sudo systemctl status flashdash-backend

# View logs
sudo journalctl -u flashdash-backend -f
```

#### Windows
```powershell
# Start
net start FlashDashBackend

# Stop
net stop FlashDashBackend

# Status
sc query FlashDashBackend
```

### Nginx Service

#### Linux
```bash
# Start
sudo systemctl start nginx

# Stop
sudo systemctl stop nginx

# Restart
sudo systemctl restart nginx

# Reload (without downtime)
sudo systemctl reload nginx

# Status
sudo systemctl status nginx

# View logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

#### Windows
```powershell
# Start
.\nginx.exe

# Stop
.\nginx.exe -s stop

# Reload
.\nginx.exe -s reload

# View logs
Get-Content C:\nginx\logs\error.log -Wait
```

---

## Verification

### Step 1: Check Backend Service

```bash
# Linux
sudo systemctl status flashdash-backend

# Windows
sc query FlashDashBackend
```

### Step 2: Test Backend API

```bash
# Health check via proxy
curl https://freedomos.vulcantech.co/backend/health

# Should return:
# {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}

# Devices endpoint via proxy
curl https://freedomos.vulcantech.co/backend/devices

# Should return: [] or device list

# Also test legacy routes (direct)
curl https://freedomos.vulcantech.co/health
curl https://freedomos.vulcantech.co/devices
```

### Step 3: Test Frontend

1. Open browser: `https://freedomos.vulcantech.co`
2. Should see FlashDash interface
3. Check browser console (F12) for errors
4. Verify API calls work (should go to `/backend` endpoints)

### Step 4: Test Downloads

1. Visit: `https://freedomos.vulcantech.co/downloads/FlashDash-Setup-1.0.0.exe`
2. Should download the Windows EXE file
3. Verify file size matches the built EXE

### Step 4: Check Nginx Status

```bash
# Linux
sudo nginx -t
sudo systemctl status nginx

# Windows
.\nginx.exe -t
```

---

## Troubleshooting

### Frontend Build Errors

#### Error: Cannot find module '@flashdash/flasher-ui'

**Solution**: Build workspace dependencies first:

```bash
cd /root/graohen_os/frontend

# Build dependencies in order
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build

# Then build web-flasher
pnpm --filter @flashdash/web-flasher build
```

#### Error: Type errors in FlasherPage.tsx

**Solution**: The `date` property was removed from `BuildInfo` type. If you see errors about `date`, make sure the code doesn't use it (already fixed in the codebase).

### Backend Not Starting

#### Check logs:
```bash
# Linux
sudo journalctl -u flashdash-backend -n 50

# Windows
# Check Windows Event Viewer or service logs
```

#### Common issues:
- **Port already in use**: Change `PY_PORT` in `.env` or kill process using port 8000
- **Permission denied**: Check file permissions and user ownership
- **Module not found**: Reinstall dependencies in virtual environment

### Nginx 502 Bad Gateway

1. **Check backend is running:**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

2. **Check Nginx error logs:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Verify proxy_pass URL** matches backend address

### Frontend Not Loading

1. **Check file permissions:**
   ```bash
   sudo ls -la /var/www/flashdash
   ```

2. **Check Nginx access logs:**
   ```bash
   sudo tail -f /var/log/nginx/access.log
   ```

3. **Verify root directory** in Nginx config matches actual location

### SSL Certificate Issues

1. **Check certificate expiration:**
   ```bash
   sudo certbot certificates
   ```

2. **Renew certificates:**
   ```bash
   sudo certbot renew
   ```

3. **Verify certificate paths** in Nginx config

### CORS Errors

1. **Check CORS_ORIGINS** in backend `.env` includes `https://freedomos.vulcantech.co`
2. **Verify Nginx CORS headers** in `/backend` location block
3. **Check browser console** for specific CORS error messages
4. **Verify API calls** use `/backend` prefix (e.g., `/backend/health`)

### Downloads Not Working

1. **Check downloads directory exists:**
   ```bash
   ls -la /var/www/flashdash/downloads/
   ```

2. **Verify EXE file is present:**
   ```bash
   ls -lh /var/www/flashdash/downloads/*.exe
   ```

3. **Check file permissions:**
   ```bash
   sudo chown www-data:www-data /var/www/flashdash/downloads/*
   ```

4. **Test download URL:**
   ```bash
   curl -I https://freedomos.vulcantech.co/downloads/FlashDash-Setup-1.0.0.exe
   ```

---

## Security Checklist

- [ ] Changed `SECRET_KEY` in backend `.env`
- [ ] SSL certificates installed and valid
- [ ] Firewall configured (only ports 80/443 open)
- [ ] Backend running (root user is acceptable for /root directory)
- [ ] File permissions set correctly
- [ ] Regular backups configured
- [ ] Log rotation configured
- [ ] Monitoring set up
- [ ] Rate limiting configured (optional)

---

## Maintenance

### Update Backend

```bash
cd /root/graohen_os
git pull
cd backend/py-service
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart flashdash-backend
```

### Update Frontend

```bash
cd /root/graohen_os/frontend
pnpm install

# Build dependencies first
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build

# Build web-flasher
pnpm --filter @flashdash/web-flasher build

# Deploy
sudo cp -r apps/web-flasher/dist/* /var/www/flashdash/
sudo systemctl reload nginx
```

### Update Windows EXE

```bash
cd /root/graohen_os/frontend/packages/desktop

# Rebuild EXE
pnpm build:win

# Find and copy new EXE
EXE_FILE=$(find dist -name "*.exe" | head -1)
if [ -n "$EXE_FILE" ]; then
    sudo cp "$EXE_FILE" /var/www/flashdash/downloads/FlashDash-Setup-1.0.0.exe
    sudo chown www-data:www-data /var/www/flashdash/downloads/*.exe
fi
```

### Backup

```bash
# Backup database (if using)
pg_dump flashdash_db > backup_$(date +%Y%m%d).sql

# Backup bundles
tar -czf bundles_backup_$(date +%Y%m%d).tar.gz /root/graohen_os/bundles
```

---

## Quick Reference

### Important Files

- **Backend Config**: `/root/graohen_os/backend/py-service/.env`
- **Backend Service**: `/etc/systemd/system/flashdash-backend.service`
- **Nginx Config**: `/etc/nginx/sites-available/freedomos`
- **Frontend Files**: `/var/www/flashdash/`
- **Downloads Directory**: `/var/www/flashdash/downloads/`
- **Bundles Directory**: `/root/graohen_os/bundles/`
- **Windows EXE Location**: `/root/graohen_os/frontend/packages/desktop/dist/`

### Important Commands

```bash
# Restart everything
sudo systemctl restart flashdash-backend
sudo systemctl reload nginx

# Check status
sudo systemctl status flashdash-backend
sudo systemctl status nginx

# View logs
sudo journalctl -u flashdash-backend -f
sudo tail -f /var/log/nginx/error.log

# Test API (via proxy)
curl https://freedomos.vulcantech.co/backend/health
curl https://freedomos.vulcantech.co/health

# Test downloads
curl -I https://freedomos.vulcantech.co/downloads/FlashDash-Setup-1.0.0.exe

# Build frontend (with dependencies)
cd /root/graohen_os/frontend
pnpm build:web-flasher
```

### URLs

- **Main Website**: `https://freedomos.vulcantech.co`
- **Backend API**: `https://freedomos.vulcantech.co/backend`
- **Health Check**: `https://freedomos.vulcantech.co/backend/health`
- **Devices**: `https://freedomos.vulcantech.co/backend/devices`
- **Download EXE**: `https://freedomos.vulcantech.co/downloads/FlashDash-Setup-1.0.0.exe`
```

---

**Your FlashDash installation is now live in production!** 🎉

For local development, see [README.md](./README.md) or [LOCAL_DEVELOPMENT.md](./LOCAL_DEVELOPMENT.md).

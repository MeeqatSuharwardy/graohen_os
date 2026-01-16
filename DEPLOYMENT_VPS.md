# Deployment Guide - Ubuntu VPS

Complete guide for deploying the GrapheneOS installer on Ubuntu VPS with domain configuration, build management, and online flashing support.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial VPS Setup](#initial-vps-setup)
- [Backend Deployment](#backend-deployment)
- [Frontend Build & Deployment](#frontend-build--deployment)
- [Nginx Configuration](#nginx-configuration)
- [SSL Certificate Setup](#ssl-certificate-setup)
- [Build Management](#build-management)
- [Domain Configuration](#domain-configuration)
- [Verification & Testing](#verification--testing)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Ubuntu 20.04+ VPS with root/sudo access
- Domain names configured (e.g., `os.fxmail.ai`, `drive.fxmail.ai`, `fxmail.ai`)
- Basic knowledge of Linux, Nginx, and systemd

---

## Initial VPS Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required Packages

```bash
sudo apt install -y \
    python3 python3-pip python3-venv \
    nginx \
    certbot python3-certbot-nginx \
    git \
    curl \
    build-essential \
    nodejs npm \
    adb fastboot \
    udev
```

### 3. Install pnpm (for frontend builds)

```bash
npm install -g pnpm
```

### 4. Install ADB/Fastboot (if not in repos)

For Ubuntu 20.04+, ADB/Fastboot are usually available. If not:

```bash
# Add Android SDK Platform Tools repository
sudo apt install -y android-tools-adb android-tools-fastboot
```

### 5. Create Project Directory

```bash
sudo mkdir -p /root/graohen_os
sudo chown $USER:$USER /root/graohen_os
cd /root/graohen_os
```

---

## Backend Deployment

### 1. Clone or Upload Repository

```bash
cd /root/graohen_os
git clone <your-repo-url> .  # or upload files via scp/sftp
```

### 2. Setup Python Virtual Environment

```bash
cd /root/graohen_os/backend/py-service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Backend Environment

Create `.env` file:

```bash
cd /root/graohen_os/backend/py-service
cat > .env << EOF
# API Configuration
API_HOST=0.0.0.0
API_PORT=17890

# CORS - Allow all origins (adjust for production)
CORS_ORIGINS=*

# Device Paths
ADB_PATH=/usr/bin/adb
FASTBOOT_PATH=/usr/bin/fastboot

# Bundle Storage
GRAPHENE_BUNDLES_ROOT=/root/graohen_os/bundles

# APK Storage
APK_STORAGE_DIR=/root/graohen_os/apks

# Allowed Hosts
ALLOWED_HOSTS=os.fxmail.ai,drive.fxmail.ai,fxmail.ai,localhost,127.0.0.1

# Logging
LOG_LEVEL=INFO
EOF
```

### 4. Create Required Directories

```bash
mkdir -p /root/graohen_os/bundles
mkdir -p /root/graohen_os/apks
```

### 5. Create Systemd Service

```bash
sudo cat > /etc/systemd/system/graphene-backend.service << EOF
[Unit]
Description=GrapheneOS Backend API
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
```

### 6. Start Backend Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable graphene-backend
sudo systemctl start graphene-backend
sudo systemctl status graphene-backend
```

---

## Frontend Build & Deployment

### 1. Install Frontend Dependencies

```bash
cd /root/graohen_os/frontend
pnpm install
```

### 2. Build Frontend Applications

```bash
# Build all frontend apps
pnpm build

# Or build individually:
# pnpm build:desktop  # Electron app
# pnpm build:web      # Main web app
# pnpm build:web-flasher  # Online flasher (IMPORTANT for /flash route)
```

**IMPORTANT:** The `web-flasher` app must be built for the `/flash` route to work!

### 3. Create Frontend Directories

```bash
sudo mkdir -p /var/www/os.fxmail.ai
sudo mkdir -p /var/www/os.fxmail.ai/flash
sudo chown -R $USER:$USER /var/www/os.fxmail.ai
```

### 4. Copy Built Files

```bash
# Main web app
cp -r /root/graohen_os/frontend/packages/web/dist/* /var/www/os.fxmail.ai/

# Web flasher app (for /flash route)
cp -r /root/graohen_os/frontend/apps/web-flasher/dist/* /var/www/os.fxmail.ai/flash/
```

---

## Nginx Configuration

### 1. Create Nginx Configuration

```bash
sudo cat > /etc/nginx/sites-available/os.fxmail.ai << EOF
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name os.fxmail.ai www.os.fxmail.ai;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name os.fxmail.ai www.os.fxmail.ai;

    # SSL Configuration (will be updated by Certbot)
    ssl_certificate /etc/letsencrypt/live/os.fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/os.fxmail.ai/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Frontend root
    root /var/www/os.fxmail.ai;
    index index.html;

    # Logging
    access_log /var/log/nginx/os.fxmail.ai.access.log;
    error_log /var/log/nginx/os.fxmail.ai.error.log;

    # API Backend Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:17890/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Web Flasher App (Browser-based flashing)
    # This is served at /flash route
    location /flash {
        alias /var/www/os.fxmail.ai/flash;
        try_files \$uri \$uri/ /flash/index.html;
        index index.html;
        
        # CORS headers for WebUSB
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range' always;
    }

    # Static files
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF
```

### 2. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/os.fxmail.ai /etc/nginx/sites-enabled/
sudo nginx -t
```

---

## SSL Certificate Setup

### 1. Obtain SSL Certificate

```bash
sudo certbot --nginx -d os.fxmail.ai -d www.os.fxmail.ai
```

### 2. Test Auto-Renewal

```bash
sudo certbot renew --dry-run
```

---

## Build Management

### 1. Bundle Directory Structure

GrapheneOS builds should be placed in the following structure:

```
/root/graohen_os/bundles/
├── panther/                          # Device codename (Pixel 7)
│   ├── 2025122500/                   # Build version
│   │   ├── panther-install-2025122500/  # Extracted install directory
│   │   │   ├── bootloader-panther-cloudripper-*.img
│   │   │   ├── radio-panther-*.img
│   │   │   ├── boot.img
│   │   │   ├── vendor_boot.img
│   │   │   ├── init_boot.img
│   │   │   ├── dtbo.img
│   │   │   ├── vbmeta.img
│   │   │   ├── vendor_kernel_boot.img
│   │   │   ├── pvmfw.img
│   │   │   ├── super_1.img
│   │   │   ├── super_2.img
│   │   │   └── ... (super_14.img)
│   │   ├── image.zip
│   │   ├── flash-all.sh
│   │   └── metadata.json
│   └── 2025122600/                   # Another version
│       └── ...
├── oriole/                           # Pixel 6
│   └── ...
└── raven/                            # Pixel 6 Pro
    └── ...
```

### 2. Adding New Builds

#### Option A: Download from GrapheneOS Releases

```bash
# Set variables
CODENAME="panther"  # Device codename
VERSION="2025122500"  # Build version

# Create directory
mkdir -p /root/graohen_os/bundles/${CODENAME}/${VERSION}
cd /root/graohen_os/bundles/${CODENAME}/${VERSION}

# Download factory image
wget https://releases.grapheneos.org/${CODENAME}-factory-${VERSION}.zip

# Extract image.zip
unzip ${CODENAME}-factory-${VERSION}.zip

# Extract the inner image.zip (contains install directory)
unzip image.zip

# Verify structure
ls -la panther-install-*/
```

#### Option B: Upload via SCP/SFTP

```bash
# On your local machine
scp -r panther-install-2025122500/ user@your-vps:/root/graohen_os/bundles/panther/2025122500/
```

### 3. Verify Build

```bash
cd /root/graohen_os/bundles/panther/2025122500/panther-install-2025122500
ls -la

# Should show:
# - bootloader-*.img
# - radio-*.img
# - boot.img
# - super_*.img (1-14)
# - etc.
```

### 4. Restart Backend (to reindex bundles)

```bash
sudo systemctl restart graphene-backend
```

### 5. Test Build Availability

```bash
curl http://127.0.0.1:17890/bundles/for/panther
```

---

## Domain Configuration

### 1. DNS A Records

Configure these DNS records to point to your VPS IP:

```
A    @                    <your-vps-ip>    # Root domain
A    www                  <your-vps-ip>    # WWW subdomain
A    os                   <your-vps-ip>    # Main backend
A    drive                <your-vps-ip>    # Encrypted drive (if used)
```

### 2. Verify DNS Propagation

```bash
dig os.fxmail.ai +short
# Should return your VPS IP
```

---

## Verification & Testing

### 1. Backend Health Check

```bash
curl http://127.0.0.1:17890/health
# Should return: {"status":"ok"}
```

### 2. Backend API Test

```bash
# List available bundles
curl https://os.fxmail.ai/api/bundles/for/panther

# List devices (requires ADB devices connected)
curl https://os.fxmail.ai/api/devices
```

### 3. Frontend Access

- Main app: `https://os.fxmail.ai`
- Online flasher: `https://os.fxmail.ai/flash`

### 4. Test Flash Online (Browser)

**IMPORTANT:** The web-flasher app must be built and deployed for the `/flash` route to work!

1. **Verify build exists:**
   ```bash
   ls -la /var/www/os.fxmail.ai/flash/index.html
   # Should show the file exists
   ```

2. **Test in browser:**
   - Open `https://os.fxmail.ai` in Chrome/Edge (HTTPS required for WebUSB)
   - Click "Flash Online (Browser)" button
   - Should redirect to `https://os.fxmail.ai/flash`
   - If you see "This site can't be reached", check that:
     - Web-flasher is built: `pnpm build:web-flasher`
     - Files are copied: `ls -la /var/www/os.fxmail.ai/flash/`
     - Nginx is configured correctly and reloaded

3. **Connect device:**
   - Connect device via USB
   - Grant USB permissions when prompted
   - Select build and flash

---

## Troubleshooting

### Issue: Flash Online (Browser) shows "This site can't be reached"

**Solution:**

1. **Ensure web-flasher is built:**
   ```bash
   cd /root/graohen_os/frontend
   pnpm build:web-flasher
   ```

2. **Copy build files to correct location:**
   ```bash
   cp -r /root/graohen_os/frontend/apps/web-flasher/dist/* /var/www/os.fxmail.ai/flash/
   ```

3. **Verify Nginx configuration:**
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Check file permissions:**
   ```bash
   ls -la /var/www/os.fxmail.ai/flash/
   # Should show index.html and assets/
   ```

5. **Check Nginx logs:**
   ```bash
   sudo tail -f /var/log/nginx/os.fxmail.ai.error.log
   ```

### Issue: Backend not starting

**Check logs:**
```bash
sudo journalctl -u graphene-backend -f
```

**Common issues:**
- Missing Python dependencies: `pip install -r requirements.txt`
- Port already in use: `sudo lsof -i :17890`
- Missing directories: Create `/root/graohen_os/bundles` and `/root/graohen_os/apks`

### Issue: Bundles not found

**Verify bundle structure:**
```bash
# Check bundle path
ls -la /root/graohen_os/bundles/panther/2025122500/

# Should contain panther-install-2025122500/ directory
```

**Restart backend to reindex:**
```bash
sudo systemctl restart graphene-backend
```

### Issue: CORS errors

**Update backend `.env`:**
```bash
CORS_ORIGINS=*
```

**Restart backend:**
```bash
sudo systemctl restart graphene-backend
```

### Issue: WebUSB not working

**Requirements:**
- Must use HTTPS (not HTTP)
- Chrome/Edge browser (WebUSB support)
- User must manually grant USB permissions
- Device must be unlocked with USB debugging enabled

---

## Maintenance

### Update Backend

```bash
cd /root/graohen_os/backend/py-service
source venv/bin/activate
git pull  # or upload new files
pip install -r requirements.txt
sudo systemctl restart graphene-backend
```

### Update Frontend

```bash
cd /root/graohen_os/frontend
git pull  # or upload new files
pnpm install
pnpm build
cp -r packages/web/dist/* /var/www/os.fxmail.ai/
cp -r apps/web-flasher/dist/* /var/www/os.fxmail.ai/flash/
```

### View Logs

```bash
# Backend logs
sudo journalctl -u graphene-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/os.fxmail.ai.access.log
sudo tail -f /var/log/nginx/os.fxmail.ai.error.log
```

---

## Security Notes

1. **Firewall:** Configure UFW to allow only necessary ports:
   ```bash
   sudo ufw allow 22/tcp   # SSH
   sudo ufw allow 80/tcp   # HTTP (for Let's Encrypt)
   sudo ufw allow 443/tcp  # HTTPS
   sudo ufw enable
   ```

2. **SSL:** Always use HTTPS in production. WebUSB requires HTTPS.

3. **API Access:** Consider adding authentication for production use.

4. **Backup:** Regularly backup `/root/graohen_os/bundles/` directory.

---

## Quick Reference

```bash
# Start services
sudo systemctl start graphene-backend
sudo systemctl start nginx

# Stop services
sudo systemctl stop graphene-backend
sudo systemctl stop nginx

# Restart services
sudo systemctl restart graphene-backend
sudo systemctl restart nginx

# Check status
sudo systemctl status graphene-backend
sudo systemctl status nginx

# Rebuild frontend
cd /root/graohen_os/frontend && pnpm build

# Add new build
mkdir -p /root/graohen_os/bundles/<codename>/<version>
# Extract build files to: /root/graohen_os/bundles/<codename>/<version>/<codename>-install-<version>/
```

---

For more details, see the main [README.md](README.md).


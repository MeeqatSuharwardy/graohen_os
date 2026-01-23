# 🚀 VPS Backend Deployment Guide

Deploy FlashDash backend to Ubuntu VPS with domain `freedomos.vulcantech.co` - No code changes required.

## 📋 Prerequisites

- Ubuntu 20.04+ VPS with root/sudo access
- Domain `freedomos.vulcantech.co` pointing to your VPS IP
- SSH access to the VPS
- Local codebase ready to deploy

## 🔧 Step 1: Server Preparation

### Connect to VPS

```bash
ssh root@your-vps-ip
# or
ssh root@freedomos.vulcantech.co
```

### Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Install Required Software

```bash
# Install Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Nginx
sudo apt install -y nginx

# Install ADB & Fastboot (for device flashing)
sudo apt install -y android-tools-adb android-tools-fastboot

# Install Git (if not already installed)
sudo apt install -y git

# Install PostgreSQL (optional, for email/drive features)
sudo apt install -y postgresql postgresql-contrib

# Install Redis (optional, for caching)
sudo apt install -y redis-server
```

## 📦 Step 2: Deploy Backend Code

### Create Directory

```bash
sudo mkdir -p /root/graohen_os
cd /root
```

### Clone Repository

**Option A: From Git Repository**
```bash
git clone <your-repository-url> graohen_os
cd /root/graohen_os
```

**Option B: Upload from Local Machine**
```bash
# On your local machine
cd /path/to/graohen_os
tar -czf graohen_os.tar.gz --exclude='node_modules' --exclude='venv' --exclude='.git' .
scp graohen_os.tar.gz root@freedomos.vulcantech.co:/root/

# On VPS
cd /root
tar -xzf graohen_os.tar.gz -C graohen_os
cd /root/graohen_os
```

## ⚙️ Step 3: Setup Backend

### Navigate to Backend Directory

```bash
cd /root/graohen_os/backend/py-service
```

### Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Create Environment File

```bash
cp env.example .env
nano .env
```

**Configure `.env` file:**

```bash
# Server Configuration
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=false
ENVIRONMENT=production

# Domain Configuration
ALLOWED_HOSTS=freedomos.vulcantech.co,localhost,127.0.0.1
CORS_ORIGINS=https://freedomos.vulcantech.co,http://localhost:3000,http://localhost:5173

# API URLs
API_BASE_URL=https://freedomos.vulcantech.co
EXTERNAL_HTTPS_BASE_URL=https://freedomos.vulcantech.co

# ADB/Fastboot Paths
ADB_PATH=/usr/bin/adb
FASTBOOT_PATH=/usr/bin/fastboot

# Directories
GRAPHENE_BUNDLES_ROOT=/root/graohen_os/bundles
APK_STORAGE_DIR=/root/graohen_os/apks
LOG_DIR=/root/graohen_os/logs

# Security (CHANGE THIS IN PRODUCTION!)
SECRET_KEY=your-super-secret-key-change-this-in-production-use-long-random-string

# Database (if using)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flashdash_db

# Redis (if using)
REDIS_URL=redis://localhost:6379/0
```

**Save and exit**: `Ctrl+X`, then `Y`, then `Enter`

### Create Required Directories

```bash
mkdir -p /root/graohen_os/bundles
mkdir -p /root/graohen_os/apks
mkdir -p /root/graohen_os/logs
```

## 🔄 Step 4: Create Systemd Service

### Create Service File

```bash
sudo nano /etc/systemd/system/flashdash-backend.service
```

**Add this configuration:**

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

**Save and exit**: `Ctrl+X`, then `Y`, then `Enter`

### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable flashdash-backend
sudo systemctl start flashdash-backend
sudo systemctl status flashdash-backend
```

**Expected output**: Should show `active (running)`

## 🌐 Step 5: Configure Nginx

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

**Add this configuration:**

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name freedomos.vulcantech.co;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    # SSL Certificates (will be updated after Let's Encrypt setup)
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

    # CORS Headers
    add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    add_header Access-Control-Allow-Credentials "true" always;

    # Handle preflight requests
    if ($request_method = OPTIONS) {
        return 204;
    }

    # Proxy all requests to backend
    location / {
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
    }

    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

**Save and exit**: `Ctrl+X`, then `Y`, then `Enter`

### Enable Site

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration (will show errors about SSL certs - that's OK for now)
sudo nginx -t
```

**Note**: SSL certificate errors are expected at this stage. We'll fix them in the next step.

## 🔒 Step 6: Setup SSL with Let's Encrypt

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Get SSL Certificate

```bash
sudo certbot --nginx -d freedomos.vulcantech.co
```

**Follow the prompts:**
- Enter your email address
- Agree to terms
- Choose whether to redirect HTTP to HTTPS (recommended: Yes)

### Verify Certificate

```bash
sudo certbot certificates
```

### Test Auto-Renewal

```bash
sudo certbot renew --dry-run
```

## ✅ Step 7: Final Configuration

### Test Nginx Configuration

```bash
sudo nginx -t
```

**Should show**: `syntax is ok` and `test is successful`

### Reload Nginx

```bash
sudo systemctl reload nginx
```

### Check Services Status

```bash
# Check backend service
sudo systemctl status flashdash-backend

# Check Nginx service
sudo systemctl status nginx
```

## 🧪 Step 8: Verification

### Test Backend API

```bash
# Health check
curl https://freedomos.vulcantech.co/health

# Should return:
# {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}

# Devices endpoint
curl https://freedomos.vulcantech.co/devices

# Should return: [] or device list

# API documentation
curl https://freedomos.vulcantech.co/docs
```

### Test from Browser

1. Open: `https://freedomos.vulcantech.co/health`
2. Should see JSON response: `{"status":"healthy",...}`
3. Open: `https://freedomos.vulcantech.co/docs`
4. Should see Swagger API documentation

## 🔥 Step 9: Configure Firewall

### Allow Required Ports

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## 📝 Step 10: Service Management

### Backend Service Commands

```bash
# Start backend
sudo systemctl start flashdash-backend

# Stop backend
sudo systemctl stop flashdash-backend

# Restart backend
sudo systemctl restart flashdash-backend

# Check status
sudo systemctl status flashdash-backend

# View logs
sudo journalctl -u flashdash-backend -f
```

### Nginx Service Commands

```bash
# Start Nginx
sudo systemctl start nginx

# Stop Nginx
sudo systemctl stop nginx

# Restart Nginx
sudo systemctl restart nginx

# Reload Nginx (without downtime)
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx

# View error logs
sudo tail -f /var/log/nginx/error.log

# View access logs
sudo tail -f /var/log/nginx/access.log
```

## 🐛 Troubleshooting

### Backend Not Starting

**Check logs:**
```bash
sudo journalctl -u flashdash-backend -n 50
```

**Common issues:**
- Port 8000 already in use: `sudo lsof -i :8000` and kill the process
- Permission denied: Check file permissions
- Module not found: Reinstall dependencies: `pip install -r requirements.txt`

### Nginx 502 Bad Gateway

**Check backend is running:**
```bash
curl http://127.0.0.1:8000/health
```

**Check Nginx error logs:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**Verify proxy_pass URL** matches backend address (`http://127.0.0.1:8000`)

### SSL Certificate Issues

**Check certificate:**
```bash
sudo certbot certificates
```

**Renew certificate:**
```bash
sudo certbot renew
```

**Verify certificate paths** in Nginx config match actual paths

### CORS Errors

1. **Check CORS_ORIGINS** in backend `.env` includes `https://freedomos.vulcantech.co`
2. **Verify Nginx CORS headers** are set correctly
3. **Check browser console** for specific CORS error messages

## 📋 Quick Reference

### Important Files

- **Backend Config**: `/root/graohen_os/backend/py-service/.env`
- **Backend Service**: `/etc/systemd/system/flashdash-backend.service`
- **Nginx Config**: `/etc/nginx/sites-available/freedomos`
- **Backend Logs**: `sudo journalctl -u flashdash-backend -f`
- **Nginx Logs**: `/var/log/nginx/error.log`

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

# Test API
curl https://freedomos.vulcantech.co/health
curl https://freedomos.vulcantech.co/devices
```

### URLs

- **Backend API**: `https://freedomos.vulcantech.co`
- **Health Check**: `https://freedomos.vulcantech.co/health`
- **Devices**: `https://freedomos.vulcantech.co/devices`
- **API Docs**: `https://freedomos.vulcantech.co/docs`

## 🔄 Updating Backend

### Pull Latest Code

```bash
cd /root/graohen_os
git pull
```

### Update Dependencies

```bash
cd /root/graohen_os/backend/py-service
source venv/bin/activate
pip install -r requirements.txt
```

### Restart Service

```bash
sudo systemctl restart flashdash-backend
```

## ✅ Deployment Checklist

- [ ] VPS Ubuntu 20.04+ ready
- [ ] Domain `freedomos.vulcantech.co` DNS pointing to VPS IP
- [ ] Python 3.11+ installed
- [ ] Nginx installed
- [ ] Backend code deployed to `/root/graohen_os`
- [ ] Virtual environment created and dependencies installed
- [ ] `.env` file configured
- [ ] Systemd service created and enabled
- [ ] Backend service running
- [ ] Nginx configured and enabled
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Health endpoint responding: `https://freedomos.vulcantech.co/health`
- [ ] API documentation accessible: `https://freedomos.vulcantech.co/docs`

---

**Your backend is now live on `https://freedomos.vulcantech.co`!** 🎉

For frontend deployment, see [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md).

# Domain Setup & Configuration Guide

Complete guide for configuring domains (os.fxmail.ai, drive.fxmail.ai, fxmail.ai) and verifying all services are running correctly.

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [DNS Configuration](#dns-configuration)
4. [SSL Certificate Setup](#ssl-certificate-setup)
5. [Nginx Configuration](#nginx-configuration)
6. [Backend Configuration](#backend-configuration)
7. [Frontend Configuration](#frontend-configuration)
8. [Verification & Testing](#verification--testing)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers setting up three domains:
- **os.fxmail.ai** - Main API backend (FastAPI)
- **drive.fxmail.ai** - Encrypted drive service
- **fxmail.ai** - Email server only

All domains use:
- **HTTPS** with Let's Encrypt SSL certificates
- **Nginx** as reverse proxy
- **SSL termination** at Nginx level

---

## Prerequisites

### On Your VPS (Digital Ocean Ubuntu 22.04+)

1. **Server with root access**
2. **Static IP address** (Digital Ocean Droplet)
3. **Nginx installed**
4. **Certbot installed**
5. **Domain DNS access** (your DNS provider panel)

### Required Ports

- **80** (HTTP) - For Let's Encrypt verification
- **443** (HTTPS) - For SSL traffic
- **22** (SSH) - For server access
- **17890** (Backend) - Localhost only (not exposed publicly)

---

## DNS Configuration

### Step 1: Get Your VPS IP Address

```bash
# On your VPS, get the public IP
curl ifconfig.me
# Or check in Digital Ocean dashboard
```

### Step 2: Configure DNS Records

Log in to your DNS provider (e.g., Cloudflare, Namecheap, etc.) and create these records:

#### A Records

**Main API Domain (os.fxmail.ai):**
```
Type: A
Name: os
Value: YOUR_VPS_IP_ADDRESS
TTL: 3600 (or Auto)
Proxy: OFF (disable Cloudflare proxy if using Cloudflare)
```

**Drive Service Domain (drive.fxmail.ai):**
```
Type: A
Name: drive
Value: YOUR_VPS_IP_ADDRESS
TTL: 3600 (or Auto)
Proxy: OFF
```

**Email Domain (fxmail.ai):**
```
Type: A
Name: @ (or leave blank for root domain)
Value: YOUR_VPS_IP_ADDRESS
TTL: 3600 (or Auto)
Proxy: OFF
```

#### Verification

Wait for DNS propagation (can take 5 minutes to 48 hours, usually < 1 hour):

```bash
# Check DNS resolution
dig os.fxmail.ai +short
dig drive.fxmail.ai +short
dig fxmail.ai +short

# All should return your VPS IP address
```

Or test locally:
```bash
nslookup os.fxmail.ai
nslookup drive.fxmail.ai
nslookup fxmail.ai
```

---

## SSL Certificate Setup

### Step 1: Install Certbot

```bash
# Update system
apt update && apt upgrade -y

# Install Certbot
apt install -y certbot python3-certbot-nginx
```

### Step 2: Obtain SSL Certificates

**Important**: DNS records must be configured and propagated before obtaining certificates.

#### Option A: Standalone Mode (Before Nginx Configuration)

```bash
# Stop Nginx temporarily (if running)
systemctl stop nginx

# Obtain certificates
certbot certonly --standalone -d os.fxmail.ai
certbot certonly --standalone -d drive.fxmail.ai
certbot certonly --standalone -d fxmail.ai

# Start Nginx again
systemctl start nginx
```

#### Option B: Nginx Plugin Mode (After Nginx Configuration)

```bash
# Configure Nginx first (see Nginx Configuration section)
# Then obtain certificates
certbot --nginx -d os.fxmail.ai
certbot --nginx -d drive.fxmail.ai
certbot --nginx -d fxmail.ai
```

### Step 3: Verify Certificates

```bash
# List all certificates
certbot certificates

# Check certificate paths
ls -la /etc/letsencrypt/live/os.fxmail.ai/
ls -la /etc/letsencrypt/live/drive.fxmail.ai/
ls -la /etc/letsencrypt/live/fxmail.ai/

# Expected files:
# - fullchain.pem (certificate + chain)
# - privkey.pem (private key)
```

### Step 4: Enable Auto-Renewal

Certbot auto-renewal is enabled by default:

```bash
# Check renewal timer
systemctl status certbot.timer

# Test renewal (dry run)
certbot renew --dry-run

# Manual renewal (if needed)
certbot renew
```

---

## Nginx Configuration

### Step 1: Create Nginx Configurations

#### Main API Domain (os.fxmail.ai)

```bash
cat > /etc/nginx/sites-available/os.fxmail.ai << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name os.fxmail.ai;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name os.fxmail.ai;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/os.fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/os.fxmail.ai/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Max upload size (for APK uploads)
    client_max_body_size 100M;
    client_body_timeout 300s;
    
    # Proxy to backend
    # Serve web-flasher under /flash path (built static files)
    location /flash {
        alias /root/graohen_os/frontend/apps/web-flasher/dist;
        try_files $uri $uri/ /flash/index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Serve web app under root
    location / {
        alias /root/graohen_os/frontend/packages/web/dist;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API endpoints - proxy to backend
    location /api {
        proxy_pass http://127.0.0.1:17890;
        proxy_http_version 1.1;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Timeouts (important for flash jobs)
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering (disable for SSE)
        proxy_buffering off;
    }
    
    # Backend API routes (health, devices, bundles, apks, tools, etc.)
    # Note: /flash is NOT included here as it's served as static files above
    location ~ ^/(health|devices|bundles|apks|tools) {
        proxy_pass http://127.0.0.1:17890;
        proxy_http_version 1.1;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Timeouts (important for flash jobs)
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Buffering (disable for SSE)
        proxy_buffering off;
    }
    
    # Downloads directory for Electron builds
    location /downloads {
        alias /var/www/flashdash/downloads;
        add_header Content-Disposition "attachment";
    }
}
EOF
```

#### Drive Service Domain (drive.fxmail.ai)

```bash
cat > /etc/nginx/sites-available/drive.fxmail.ai << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name drive.fxmail.ai;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name drive.fxmail.ai;

    ssl_certificate /etc/letsencrypt/live/drive.fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/drive.fxmail.ai/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    client_max_body_size 500M;  # Larger for drive uploads
    
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
```

#### Email Domain (fxmail.ai)

```bash
cat > /etc/nginx/sites-available/fxmail.ai << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name fxmail.ai www.fxmail.ai;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name fxmail.ai www.fxmail.ai;

    ssl_certificate /etc/letsencrypt/live/fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fxmail.ai/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:17890;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

### Step 2: Enable Sites

```bash
# Create symbolic links
ln -sf /etc/nginx/sites-available/os.fxmail.ai /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/drive.fxmail.ai /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/fxmail.ai /etc/nginx/sites-enabled/

# Remove default site (if exists)
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t
```

### Step 3: Reload Nginx

```bash
# If test passes, reload
systemctl reload nginx

# Check status
systemctl status nginx
```

---

## Backend Configuration

### Step 1: Update `.env` File

Edit `/root/graohen_os/backend/py-service/.env`:

```bash
# Application
APP_NAME=GrapheneOS Installer API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# Server (listen on all interfaces, but only accessible via Nginx)
PY_HOST=0.0.0.0
PY_PORT=17890

# API Configuration
API_V1_PREFIX=/api/v1
ALLOWED_HOSTS=os.fxmail.ai,drive.fxmail.ai,fxmail.ai,localhost,127.0.0.1

# CORS Configuration (PRODUCTION - use your actual domains)
CORS_ORIGINS=https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai

# ADB and Fastboot Paths
ADB_PATH=/usr/local/bin/adb
FASTBOOT_PATH=/usr/local/bin/fastboot

# Bundle Storage
GRAPHENE_BUNDLE_PATH=/root/graohen_os/bundles

# APK Storage
APK_STORAGE_DIR=/root/graohen_os/apks

# Email Domain Configuration
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# Security
SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING_IN_PRODUCTION

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/root/graohen_os/backend/py-service/logs
```

### Step 2: Restart Backend Service

```bash
# Restart backend
systemctl restart graphene-flasher

# Check status
systemctl status graphene-flasher

# View logs
journalctl -u graphene-flasher -f
```

---

## Frontend Configuration

### Step 1: Update Environment Variables

#### Desktop App (`frontend/packages/desktop/.env`)

```bash
# PRODUCTION - Use domain
VITE_API_BASE_URL=https://os.fxmail.ai
```

#### Web App (`frontend/packages/web/.env`)

```bash
# PRODUCTION - Use domain
VITE_API_BASE_URL=https://os.fxmail.ai
```

#### Web Flasher (`frontend/apps/web-flasher/.env`)

```bash
# PRODUCTION - Use domain
VITE_API_BASE_URL=https://os.fxmail.ai
```

### Step 2: Rebuild Frontend (if needed)

```bash
cd /root/graohen_os/frontend
pnpm install
pnpm build
```

---

## Verification & Testing

### Step 1: Test DNS Resolution

```bash
# From your local machine
nslookup os.fxmail.ai
nslookup drive.fxmail.ai
nslookup fxmail.ai

# All should return your VPS IP
```

### Step 2: Test SSL Certificates

```bash
# Check SSL certificate
openssl s_client -connect os.fxmail.ai:443 -servername os.fxmail.ai < /dev/null

# Online SSL checker
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=os.fxmail.ai
```

### Step 3: Test HTTP Redirects

```bash
# Test HTTP to HTTPS redirect
curl -I http://os.fxmail.ai
# Should return: HTTP/1.1 301 Moved Permanently
# Location: https://os.fxmail.ai/

# Test all domains
curl -I http://drive.fxmail.ai
curl -I http://fxmail.ai
```

### Step 4: Test HTTPS Endpoints

```bash
# Health check
curl https://os.fxmail.ai/health

# Expected response:
# {"status":"healthy","version":"1.0.0"}

# Test API endpoints
curl https://os.fxmail.ai/devices
curl https://os.fxmail.ai/apks/list

# Test other domains
curl https://drive.fxmail.ai/health
curl https://fxmail.ai/health
```

### Step 5: Test Frontend Connection

1. **Desktop App**: Open Electron app and verify it connects to `https://os.fxmail.ai`
2. **Web App**: Visit `https://os.fxmail.ai` in browser
3. **Check Network Tab**: Verify API calls go to `https://os.fxmail.ai`

### Step 6: Full API Test Script

```bash
#!/bin/bash
# test-domains.sh

BASE_URL="https://os.fxmail.ai"

echo "Testing os.fxmail.ai..."

# Health check
echo -n "Health check: "
curl -s "$BASE_URL/health" | jq .

# Devices
echo -n "Devices: "
curl -s "$BASE_URL/devices" | jq .

# APKs list
echo -n "APKs list: "
curl -s "$BASE_URL/apks/list" | jq .

# Tools check
echo -n "Tools check: "
curl -s "$BASE_URL/tools/check" | jq .

echo "All tests completed!"
```

Run:
```bash
chmod +x test-domains.sh
./test-domains.sh
```

---

## Troubleshooting

### DNS Issues

**Problem**: Domain not resolving

**Solution**:
```bash
# Check DNS propagation
dig os.fxmail.ai +short

# Flush DNS cache (on your local machine)
# macOS:
sudo dscacheutil -flushcache
# Linux:
sudo systemd-resolve --flush-caches
# Windows:
ipconfig /flushdns
```

### SSL Certificate Issues

**Problem**: Certificate not obtained

**Solution**:
```bash
# Check if ports 80/443 are open
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Verify DNS resolution from VPS
dig os.fxmail.ai +short

# Retry certificate generation
certbot certonly --standalone -d os.fxmail.ai
```

**Problem**: Certificate expired or renewal failed

**Solution**:
```bash
# Manual renewal
certbot renew --force-renewal

# Check renewal logs
journalctl -u certbot.timer -f
```

### Nginx Issues

**Problem**: 502 Bad Gateway

**Solution**:
```bash
# Check if backend is running
systemctl status graphene-flasher
curl http://127.0.0.1:17890/health

# Check Nginx error logs
tail -f /var/log/nginx/os.fxmail.ai.error.log

# Restart services
systemctl restart graphene-flasher
systemctl restart nginx
```

**Problem**: Nginx configuration error

**Solution**:
```bash
# Test configuration
nginx -t

# Check syntax
nginx -T

# Check specific site
nginx -T | grep -A 50 "os.fxmail.ai"
```

### Backend Connection Issues

**Problem**: CORS errors in browser

**Solution**:
```bash
# Verify CORS_ORIGINS in .env includes your domain
grep CORS_ORIGINS /root/graohen_os/backend/py-service/.env

# Should include:
# CORS_ORIGINS=https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai

# Restart backend
systemctl restart graphene-flasher
```

**Problem**: Backend not accessible

**Solution**:
```bash
# Check if backend is listening
netstat -tulpn | grep 17890

# Check firewall
ufw status verbose
# Should show: 17890/tcp (ALLOW IN) only from 127.0.0.1

# Test local connection
curl http://127.0.0.1:17890/health
```

### Firewall Issues

**Problem**: Can't access domains from outside

**Solution**:
```bash
# Check firewall status
ufw status verbose

# Allow required ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp

# Ensure backend port is localhost only
ufw deny 17890/tcp
# Nginx will proxy to localhost
```

---

## Quick Checklist

- [ ] DNS records configured (A records for os, drive, root)
- [ ] DNS propagation confirmed (`dig os.fxmail.ai`)
- [ ] SSL certificates obtained (`certbot certificates`)
- [ ] Nginx configurations created
- [ ] Nginx sites enabled
- [ ] Nginx configuration tested (`nginx -t`)
- [ ] Nginx reloaded (`systemctl reload nginx`)
- [ ] Backend `.env` updated (ALLOWED_HOSTS, CORS_ORIGINS)
- [ ] Backend restarted (`systemctl restart graphene-flasher`)
- [ ] Frontend `.env` updated (VITE_API_BASE_URL)
- [ ] HTTP redirects working (`curl -I http://os.fxmail.ai`)
- [ ] HTTPS endpoints working (`curl https://os.fxmail.ai/health`)
- [ ] SSL certificate valid (check with SSL Labs)
- [ ] Firewall configured (ports 80, 443 open, 17890 localhost only)

---

## Maintenance

### Regular Tasks

1. **Monitor SSL Certificates**
   ```bash
   certbot certificates
   # Auto-renewal is enabled by default
   ```

2. **Check Nginx Logs**
   ```bash
   tail -f /var/log/nginx/os.fxmail.ai.access.log
   tail -f /var/log/nginx/os.fxmail.ai.error.log
   ```

3. **Check Backend Logs**
   ```bash
   journalctl -u graphene-flasher -f
   ```

4. **Test Endpoints Weekly**
   ```bash
   curl https://os.fxmail.ai/health
   curl https://drive.fxmail.ai/health
   curl https://fxmail.ai/health
   ```

---

**Last Updated**: January 2026  
**Version**: 1.0.0


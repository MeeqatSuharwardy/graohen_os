# FlashDash - Final Deployment Guide

Complete step-by-step guide for deploying FlashDash to production with Docker, Cloudflare, and domain configuration.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Domain Setup (Cloudflare)](#domain-setup-cloudflare)
3. [Server Preparation](#server-preparation)
4. [Docker Deployment](#docker-deployment)
5. [Build Files Setup](#build-files-setup)
6. [Environment Configuration](#environment-configuration)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Prerequisites

### Required Accounts & Services
- ✅ Domain registered (`fxmail.ai`)
- ✅ Cloudflare account with domain added
- ✅ VPS/Server with:
  - Ubuntu 20.04+ or similar Linux distribution
  - Minimum 2GB RAM, 2 CPU cores
  - 50GB+ disk space
  - Public IP address
  - Root/sudo access

### Required Software
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git
- Basic command-line knowledge

---

## Domain Setup (Cloudflare)

### Step 1: Add DNS Records

1. Login to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain `fxmail.ai`
3. Go to **DNS** → **Records**
4. Add the following A records:

#### Frontend Subdomain
```
Type: A
Name: frontend
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

#### Backend Subdomain
```
Type: A
Name: backend
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

#### Downloads Subdomain (Optional)
```
Type: A
Name: os
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

**Replace `YOUR_SERVER_IP` with your actual server's public IP address.**

### Step 2: Configure SSL/TLS

1. Go to **SSL/TLS** → **Overview**
2. Set encryption mode to **Full (strict)**
3. This ensures end-to-end encryption between Cloudflare and your server

### Step 3: Verify DNS Propagation

Wait 5-15 minutes, then verify:

```bash
# Check DNS resolution
dig frontend.fxmail.ai
dig backend.fxmail.ai
dig os.fxmail.ai

# Should return your server IP
```

---

## Server Preparation

### Step 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Step 3: Configure Firewall

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### Step 4: Clone Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/flashdash.git
cd flashdash

# Or if using SSH
git clone git@github.com:yourusername/flashdash.git
cd flashdash
```

### Step 5: Install Git LFS (for build files)

```bash
# Install Git LFS
sudo apt-get install git-lfs
git lfs install

# Pull LFS files
git lfs pull
```

---

## Docker Deployment

### Step 1: Configure Environment

Create `.env` file in project root:

```bash
cat > .env << EOF
# Domain Configuration
FRONTEND_DOMAIN=frontend.fxmail.ai
BACKEND_DOMAIN=backend.fxmail.ai
API_BASE_URL=https://backend.fxmail.ai

# Backend Configuration
PY_HOST=0.0.0.0
PY_PORT=8000
BUNDLES_DIR=/app/bundles
GRAPHENE_BUNDLES_ROOT=/app/bundles
APK_STORAGE_DIR=/app/apks
DEBUG=false
LOG_LEVEL=INFO
EOF
```

### Step 2: Prepare Directories

```bash
# Create required directories
mkdir -p bundles downloads logs

# Set permissions
chmod 755 bundles downloads logs
```

### Step 3: Build Frontend with API URL

```bash
cd frontend

# Install dependencies
pnpm install

# Build UI package
pnpm --filter ui build

# Build web app with production API URL
VITE_API_BASE_URL=https://backend.fxmail.ai pnpm --filter web build

# Build web-flasher
pnpm --filter @flashdash/web-flasher build

cd ..
```

### Step 4: Build Docker Image

```bash
# Build the Docker image
docker-compose build

# This will:
# - Build Python backend
# - Build frontend applications
# - Configure Nginx
# - Set up all services
```

### Step 5: Start Services

```bash
# Start in detached mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Build Files Setup

### Step 1: Verify Build Files

The desktop app builds should already be in the repository (via Git LFS):

```bash
# Verify builds exist
./check-builds.sh

# Should show:
# ✓ Windows build found
# ✓ macOS build found
# ✓ Linux AppImage found
```

### Step 2: Verify Download Directory

```bash
# Check files are present
ls -lh downloads/windows/
ls -lh downloads/mac/
ls -lh downloads/linux/

# Files should be:
# - downloads/windows/@flashdashdesktop Setup 1.0.0.exe
# - downloads/mac/FlashDash-1.0.0.dmg
# - downloads/linux/flashdash-1.0.0.AppImage
```

### Step 3: Test Downloads

```bash
# Test download endpoint (from server)
curl -I http://localhost/downloads/@flashdashdesktop%20Setup%201.0.0.exe

# Should return HTTP 200
```

---

## Environment Configuration

### Frontend Environment Variables

Create `frontend/packages/web/.env.production`:

```env
VITE_API_BASE_URL=https://backend.fxmail.ai
VITE_DOWNLOAD_BASE_URL=https://os.fxmail.ai/download
VITE_WEB_FLASHER_URL=https://frontend.fxmail.ai/flash
```

### Docker Environment Variables

Already configured in `.env` file (see Docker Deployment section).

### Nginx Configuration

The Nginx configuration is automatically set up in the Docker container:
- `frontend.fxmail.ai` → Serves React frontend
- `backend.fxmail.ai` → Proxies to FastAPI backend
- `/downloads` → Serves desktop app installers

---

## SSL/TLS Configuration

### Option 1: Cloudflare Proxy (Recommended)

With Cloudflare proxy enabled (orange cloud), SSL is handled automatically:
- ✅ HTTPS enabled automatically
- ✅ SSL certificates managed by Cloudflare
- ✅ No server-side SSL configuration needed

### Option 2: Origin Certificates (Advanced)

If you want additional security:

1. Go to Cloudflare → **SSL/TLS** → **Origin Server**
2. Click **Create Certificate**
3. Select:
   - Private key type: RSA (2048)
   - Hostnames: `frontend.fxmail.ai`, `backend.fxmail.ai`, `*.fxmail.ai`
4. Copy the **Origin Certificate** and **Private Key**
5. Update Dockerfile to include SSL certificates (see advanced configuration)

---

## Verification

### Step 1: Check Docker Services

```bash
# Check container status
docker-compose ps

# Should show:
# flashdash   Up   (healthy)
```

### Step 2: Test Backend

```bash
# Test backend health
curl https://backend.fxmail.ai/health

# Should return:
# {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

### Step 3: Test Frontend

```bash
# Test frontend
curl -I https://frontend.fxmail.ai

# Should return HTTP 200
```

### Step 4: Test Downloads

```bash
# Test Windows download
curl -I "https://os.fxmail.ai/download/@flashdashdesktop%20Setup%201.0.0.exe"

# Test macOS download
curl -I "https://os.fxmail.ai/download/FlashDash-1.0.0.dmg"

# Test Linux download
curl -I "https://os.fxmail.ai/download/flashdash-1.0.0.AppImage"

# All should return HTTP 200
```

### Step 5: Browser Testing

1. Open `https://frontend.fxmail.ai` in browser
2. Verify:
   - ✅ Page loads correctly
   - ✅ CSS and JavaScript load
   - ✅ No console errors
   - ✅ Downloads page accessible
   - ✅ Download links work

### Step 6: API Testing

```bash
# Test API endpoints
curl https://backend.fxmail.ai/devices
curl https://backend.fxmail.ai/bundles
curl https://backend.fxmail.ai/health
```

---

## Troubleshooting

### Issue: DNS Not Resolving

**Symptoms**: Domain doesn't resolve to server IP

**Solution**:
```bash
# Check DNS records in Cloudflare
# Verify server IP is correct
# Wait for DNS propagation (up to 24 hours, usually < 1 hour)
dig frontend.fxmail.ai
```

### Issue: SSL Certificate Errors

**Symptoms**: Browser shows SSL warnings

**Solution**:
1. Verify Cloudflare SSL mode is set to **Full (strict)**
2. Check server time is synchronized: `sudo ntpdate -s time.nist.gov`
3. Verify firewall allows port 443

### Issue: Backend Not Accessible

**Symptoms**: API returns connection errors

**Solution**:
```bash
# Check backend logs
docker logs flashdash | grep backend

# Check backend is running
docker exec flashdash ps aux | grep uvicorn

# Test locally
docker exec flashdash curl http://localhost:8000/health
```

### Issue: Frontend Can't Connect to Backend

**Symptoms**: Frontend loads but API calls fail

**Solution**:
1. Verify `VITE_API_BASE_URL` is set correctly in build
2. Check CORS headers in nginx config
3. Verify backend domain resolves correctly

### Issue: Downloads Not Working

**Symptoms**: Download links return 404

**Solution**:
```bash
# Check files exist
docker exec flashdash ls -la /app/downloads/

# Check nginx config
docker exec flashdash nginx -t

# Check file permissions
docker exec flashdash chmod 644 /app/downloads/**/*
```

### Issue: Docker Container Won't Start

**Symptoms**: Container exits immediately

**Solution**:
```bash
# Check logs
docker-compose logs

# Check for port conflicts
sudo netstat -tulpn | grep -E ':(80|8000)'

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull
git lfs pull  # If build files updated

# Rebuild frontend
cd frontend
pnpm install
VITE_API_BASE_URL=https://backend.fxmail.ai pnpm --filter web build
cd ..

# Rebuild and restart Docker
docker-compose down
docker-compose build
docker-compose up -d
```

### Viewing Logs

```bash
# All logs
docker-compose logs -f

# Backend only
docker logs flashdash -f | grep backend

# Last 100 lines
docker logs flashdash --tail 100
```

### Monitoring

```bash
# Container stats
docker stats flashdash

# Disk usage
docker system df

# Check health
docker inspect flashdash | grep -A 5 Health
```

### Backup

```bash
# Backup bundles
tar -czf bundles-backup-$(date +%Y%m%d).tar.gz bundles/

# Backup downloads
tar -czf downloads-backup-$(date +%Y%m%d).tar.gz downloads/

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

---

## Quick Reference

### Important URLs

- **Frontend**: https://frontend.fxmail.ai
- **Backend API**: https://backend.fxmail.ai
- **API Docs**: https://backend.fxmail.ai/docs
- **Health Check**: https://backend.fxmail.ai/health
- **Downloads**: https://os.fxmail.ai/download

### Important Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Rebuild
docker-compose build --no-cache
docker-compose up -d

# Check status
docker-compose ps
./check-builds.sh
```

### File Locations

- **Bundles**: `./bundles/` (mounted to `/app/bundles` in container)
- **Downloads**: `./downloads/` (mounted to `/app/downloads` in container)
- **Logs**: `./logs/` (mounted to `/app/logs` in container)
- **Config**: `docker-compose.yml`, `.env`

---

## Deployment Checklist

Use this checklist to ensure everything is configured:

### Pre-Deployment
- [ ] Domain registered and added to Cloudflare
- [ ] DNS A records added (frontend, backend, os)
- [ ] SSL/TLS mode set to Full (strict)
- [ ] Server provisioned with Docker installed
- [ ] Firewall configured (ports 80, 443, 22)
- [ ] Repository cloned
- [ ] Git LFS installed and files pulled

### Build & Configuration
- [ ] Frontend dependencies installed
- [ ] Frontend built with correct API URL
- [ ] `.env` file created with domain configuration
- [ ] Build files verified (`./check-builds.sh`)
- [ ] Directories created (bundles, downloads, logs)

### Docker Deployment
- [ ] Docker image built successfully
- [ ] Container started and running
- [ ] Health checks passing
- [ ] Logs show no errors

### Verification
- [ ] DNS resolves correctly
- [ ] Frontend accessible via HTTPS
- [ ] Backend API responding
- [ ] Download links working
- [ ] No console errors in browser
- [ ] All endpoints tested

### Post-Deployment
- [ ] Monitoring set up
- [ ] Backup strategy configured
- [ ] Documentation updated
- [ ] Team notified

---

## Support & Resources

### Documentation Files
- `CLOUDFLARE_SETUP.md` - Detailed Cloudflare configuration
- `DOCKER_DOMAIN_SETUP.md` - Docker domain configuration
- `DOCKER_QUICK_START.md` - Quick Docker deployment
- `API_DOCUMENTATION.md` - API reference
- `BUILD_STATUS.md` - Build file information

### Useful Links
- [Cloudflare Dashboard](https://dash.cloudflare.com)
- [Docker Documentation](https://docs.docker.com)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

## Summary

This guide covers the complete deployment process:

1. ✅ **Domain Setup**: Configure Cloudflare DNS and SSL
2. ✅ **Server Prep**: Install Docker and dependencies
3. ✅ **Docker Deploy**: Build and start containers
4. ✅ **Build Files**: Verify desktop app builds
5. ✅ **Verification**: Test all endpoints and services
6. ✅ **Maintenance**: Ongoing updates and monitoring

**Status**: Ready for production deployment! 🚀

---

**Last Updated**: January 2025
**Version**: 1.0.0

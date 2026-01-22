# FlashDash Deployment Guide

Complete step-by-step guide for deploying FlashDash on Ubuntu VPS with Docker, including email and drive services.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Domain Setup](#domain-setup)
3. [Server Preparation](#server-preparation)
4. [Docker Deployment](#docker-deployment)
5. [SSL/TLS Configuration](#ssltls-configuration)
6. [Email Service Setup](#email-service-setup)
7. [Drive Service Setup](#drive-service-setup)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Prerequisites

### Required Accounts & Services

- ✅ Domain registered (`vulcantech.tech`)
- ✅ Cloudflare account with domain added (recommended)
- ✅ Ubuntu 20.04+ VPS with:
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

## Domain Setup

### Step 1: Configure DNS Records

Add the following A records in your DNS provider (Cloudflare recommended):

#### Frontend Domain
```
Type: A
Name: frontend
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

#### Backend Domain
```
Type: A
Name: backend
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

#### Email Domain (Root)
```
Type: A
Name: @ (or leave blank)
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

#### Drive Domain
```
Type: A
Name: drive
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

**Replace `YOUR_SERVER_IP` with your actual server's public IP address.**

### Step 2: Verify DNS Propagation

Wait 5-15 minutes, then verify:

```bash
dig frontend.vulcantech.tech
dig backend.vulcantech.tech
dig vulcantech.tech

# All should return your server IP
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
git clone <your-repo-url> flashdash
cd flashdash

# Or if using SSH
git clone git@github.com:yourusername/flashdash.git
cd flashdash
```

### Step 5: Install Git LFS (if needed)

```bash
# Install Git LFS
sudo apt-get install git-lfs
git lfs install

# Pull LFS files (if any)
git lfs pull
```

---

## Docker Deployment

### Step 1: Configure Environment

Create `.env` file in project root (or copy from `.env.example`):

```bash
# Copy example file
cp .env.example .env

# Or create manually
cat > .env << EOF
# Domain Configuration
# frontend.vulcantech.tech - Main web application (React frontend)
FRONTEND_DOMAIN=frontend.vulcantech.tech

# backend.vulcantech.tech - API server (FastAPI backend - handles email, drive, and all backend)
BACKEND_DOMAIN=backend.vulcantech.tech

# vulcantech.tech - Email service (main domain for email addresses like howie@vulcantech.tech)
EMAIL_DOMAIN=vulcantech.tech

# backend.vulcantech.tech - Drive/file storage service (same as backend)
DRIVE_DOMAIN=backend.vulcantech.tech

# API Base URL - Used by frontend to connect to backend
API_BASE_URL=https://backend.vulcantech.tech

# External HTTPS Base URL - Base URL for email links
EXTERNAL_HTTPS_BASE_URL=https://vulcantech.tech

# Backend Configuration
PY_HOST=0.0.0.0
PY_PORT=8000
BUNDLES_DIR=/app/bundles
GRAPHENE_BUNDLES_ROOT=/app/bundles
APK_STORAGE_DIR=/app/apks
DEBUG=false
LOG_LEVEL=INFO

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-long-random-secret-key-here-change-this
CORS_ORIGINS=https://frontend.vulcantech.tech,https://backend.vulcantech.tech,https://vulcantech.tech
ALLOWED_HOSTS=frontend.vulcantech.tech,backend.vulcantech.tech,vulcantech.tech,localhost,127.0.0.1

# Database (if using PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flashdash_db

# Redis (if using Redis)
REDIS_URL=redis://localhost:6379/0
EOF
```

**IMPORTANT**: Change `SECRET_KEY` to a long random string in production!

### Step 2: Prepare Directories

```bash
# Create required directories
mkdir -p bundles downloads logs apks

# Set permissions
chmod 755 bundles downloads logs apks
```

### Step 3: Build Docker Image

```bash
# Build the Docker image
docker-compose build

# This will:
# - Build Python backend
# - Build frontend applications
# - Configure Nginx
# - Set up all services
```

### Step 4: Start Services

```bash
# Start in detached mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## SSL/TLS Configuration

### Option 1: Cloudflare Proxy (Recommended)

With Cloudflare proxy enabled (orange cloud), SSL is handled automatically:
- ✅ HTTPS enabled automatically
- ✅ SSL certificates managed by Cloudflare
- ✅ No server-side SSL configuration needed

**Configuration**:
1. Go to Cloudflare Dashboard → SSL/TLS
2. Set encryption mode to **Full (strict)**
3. Enable **Always Use HTTPS**

### Option 2: Let's Encrypt (Advanced)

If you want server-side SSL certificates:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificates (if not using Cloudflare proxy)
sudo certbot certonly --standalone -d frontend.vulcantech.tech -d backend.vulcantech.tech -d vulcantech.tech

# Update nginx configuration to use certificates
# (See advanced configuration section)
```

---

## Email Service Setup

### Creating Email Addresses

Email addresses are automatically generated when sending emails. Users can register with any email address ending in `@vulcantech.tech`:

**Example Flow**:

1. **Register user**:
```bash
curl -X POST https://backend.vulcantech.tech/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "howie@vulcantech.tech",
    "password": "secure-password-123"
  }'
```

2. **Login**:
```bash
curl -X POST https://backend.fxmail.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "howie@vulcantech.tech",
    "password": "secure-password-123"
  }'
```

3. **Send encrypted email**:
```bash
curl -X POST https://vulcantech.tech/api/v1/email/send \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Hello from howie@vulcantech.tech",
    "body": "This is an encrypted email!",
    "passcode": "optional-passcode",
    "expires_in_hours": 168
  }'
```

### Email Configuration

Email service is configured via environment variables:

- `EMAIL_DOMAIN`: Email domain (default: `vulcantech.tech`)
- `EXTERNAL_HTTPS_BASE_URL`: Base URL for email links (default: `https://vulcantech.tech`)

These are set in `docker-compose.yml` and can be overridden in `.env`.

---

## Drive Service Setup

### Uploading Files

Drive service supports encrypted file uploads with passcode protection:

**Example Flow**:

1. **Upload file**:
```bash
curl -X POST https://backend.vulcantech.tech/api/v1/drive/upload \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf" \
  -F "passcode=secret123" \
  -F "expires_in_hours=168"
```

2. **Get file info**:
```bash
curl -X GET https://backend.vulcantech.tech/api/v1/drive/file/{file_id} \
  -H "Authorization: Bearer <access_token>"
```

3. **Unlock file** (if passcode protected):
```bash
curl -X POST https://backend.vulcantech.tech/api/v1/drive/file/{file_id}/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "secret123"
  }'
```

4. **Download file**:
```bash
curl -X GET "https://drive.fxmail.ai/api/v1/drive/download/{file_id}?token=<signed_token>" \
  -o downloaded_file.pdf
```

### Drive Configuration

Drive service configuration:
- Maximum file size: 500MB (configured in nginx)
- Storage: Redis (encrypted content)
- Expiration: Configurable per file (1-8760 hours)

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

### Step 4: Test Email Service

```bash
# Test email service
curl https://fxmail.ai/health

# Should return healthy status
```

### Step 5: Test Drive Service

```bash
# Test drive service
curl https://drive.fxmail.ai/health

# Should return healthy status
```

### Step 6: Browser Testing

1. Open `https://frontend.fxmail.ai` in browser
2. Verify:
   - ✅ Page loads correctly
   - ✅ CSS and JavaScript load
   - ✅ No console errors
   - ✅ API calls work (check Network tab)

### Step 7: API Testing

```bash
# Test API endpoints
curl https://backend.fxmail.ai/devices
curl https://backend.fxmail.ai/bundles
curl https://backend.fxmail.ai/health

# Test email API
curl -X POST https://backend.vulcantech.tech/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@fxmail.ai","password":"test123456"}'

# Test drive API
curl -X GET https://drive.fxmail.ai/api/v1/drive/file/test123
```

---

## Troubleshooting

### Issue: DNS Not Resolving

**Symptoms**: Domain doesn't resolve to server IP

**Solution**:
```bash
# Check DNS records in Cloudflare/DNS provider
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
1. Verify `API_BASE_URL` is set correctly in frontend build
2. Check CORS headers in nginx config
3. Verify backend domain resolves correctly
4. Check browser console for CORS errors

### Issue: Email Service Not Working

**Symptoms**: Email endpoints return errors

**Solution**:
```bash
# Check email service logs
docker logs flashdash | grep email

# Verify EMAIL_DOMAIN is set correctly
docker exec flashdash env | grep EMAIL_DOMAIN

# Test email endpoint
curl https://fxmail.ai/api/v1/email/send
```

### Issue: Drive Service Not Working

**Symptoms**: File uploads fail

**Solution**:
```bash
# Check drive service logs
docker logs flashdash | grep drive

# Verify file size limits in nginx config
docker exec flashdash cat /etc/nginx/sites-available/default | grep client_max_body_size

# Test drive endpoint
curl https://drive.fxmail.ai/api/v1/drive/upload
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

# Email service
docker logs flashdash -f | grep email

# Drive service
docker logs flashdash -f | grep drive

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

# Backup database (if using PostgreSQL)
docker exec flashdash pg_dump -U postgres flashdash_db > db-backup-$(date +%Y%m%d).sql
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart flashdash

# Stop services
docker-compose down

# Start services
docker-compose up -d
```

---

## Quick Reference

### Important URLs

- **Frontend**: https://frontend.fxmail.ai
- **Backend API**: https://backend.fxmail.ai
- **Email Service**: https://fxmail.ai
- **Drive Service**: https://drive.fxmail.ai
- **API Docs**: https://backend.fxmail.ai/docs

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
- [ ] DNS A records added (frontend, backend, email, drive)
- [ ] SSL/TLS mode set to Full (strict)
- [ ] Server provisioned with Docker installed
- [ ] Firewall configured (ports 80, 443, 22)
- [ ] Repository cloned
- [ ] Git LFS installed and files pulled (if needed)

### Build & Configuration
- [ ] `.env` file created with domain configuration
- [ ] `SECRET_KEY` changed to secure random string
- [ ] Directories created (bundles, downloads, logs, apks)
- [ ] Environment variables verified

### Docker Deployment
- [ ] Docker image built successfully
- [ ] Container started and running
- [ ] Health checks passing
- [ ] Logs show no errors

### Verification
- [ ] DNS resolves correctly
- [ ] Frontend accessible via HTTPS
- [ ] Backend API responding
- [ ] Email service working
- [ ] Drive service working
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
- `README.md` - Project overview and quick start
- `API_DOCUMENTATION.md` - Complete API reference
- `DEPLOYMENT_GUIDE.md` - This file

### Useful Links
- [Cloudflare Dashboard](https://dash.cloudflare.com)
- [Docker Documentation](https://docs.docker.com)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

## Summary

This guide covers the complete deployment process:

1. ✅ **Domain Setup**: Configure DNS and SSL
2. ✅ **Server Prep**: Install Docker and dependencies
3. ✅ **Docker Deploy**: Build and start containers
4. ✅ **SSL/TLS**: Configure HTTPS
5. ✅ **Email Service**: Set up encrypted email
6. ✅ **Drive Service**: Set up file storage
7. ✅ **Verification**: Test all endpoints and services
8. ✅ **Maintenance**: Ongoing updates and monitoring

**Status**: Ready for production deployment! 🚀

---

**Last Updated**: January 2025
**Version**: 1.0.0

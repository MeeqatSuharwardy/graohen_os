# VPS Production Setup - freedomos.vulcantech.co

## Overview

This guide sets up FlashDash for **production deployment only** on VPS using `freedomos.vulcantech.co`.

**No local development setup** - everything runs in Docker on the VPS.

## Server Information

- **IP**: 138.197.24.229
- **Domain**: freedomos.vulcantech.co
- **Email Domain**: vulcantech.tech
- **Password**: Dubai123@

## Quick Start

### 1. SSH into Server

```bash
ssh root@138.197.24.229
# Password: Dubai123@
```

### 2. Run Production Setup

```bash
cd ~/graohen_os
chmod +x VPS_COMPLETE_SETUP.sh
./VPS_COMPLETE_SETUP.sh
```

The script will:
- Install Docker and Docker Compose
- Configure Nginx reverse proxy
- Build and start the production container
- Set up firewall rules
- Verify all services

### 3. Verify Deployment

```bash
# Check container
docker ps | grep flashdash

# Test backend
curl http://localhost:8000/health

# Test frontend (port 81)
curl http://localhost:81/health

# Run verification script
chmod +x VERIFY_VPS_SETUP.sh
./VERIFY_VPS_SETUP.sh
```

## Production Configuration

### Docker Compose

All services configured for `freedomos.vulcantech.co`:
- **Frontend**: `https://freedomos.vulcantech.co`
- **Backend API**: `https://freedomos.vulcantech.co`
- **Email Service**: `https://freedomos.vulcantech.co` (uses vulcantech.tech domain)
- **Drive Service**: `https://freedomos.vulcantech.co`

### Environment Variables

```yaml
DEBUG: false
ENVIRONMENT: production
FRONTEND_DOMAIN: freedomos.vulcantech.co
BACKEND_DOMAIN: freedomos.vulcantech.co
EMAIL_DOMAIN: vulcantech.tech
API_BASE_URL: https://freedomos.vulcantech.co
VITE_API_BASE_URL: https://freedomos.vulcantech.co
CORS_ORIGINS: *
ALLOWED_HOSTS: freedomos.vulcantech.co,vulcantech.tech
```

### Nginx Configuration

**System Nginx** (port 80):
- Proxies to Docker container on port 81
- Handles `freedomos.vulcantech.co`

**Docker Nginx** (port 81):
- Serves frontend and proxies API to backend (port 8000)
- Handles `freedomos.vulcantech.co` and `vulcantech.tech`

## Cloudflare DNS Setup

1. **Add A Record:**
   - **Name**: `freedomos`
   - **Content**: `138.197.24.229`
   - **Proxy**: ✅ Proxied
   - **TTL**: Auto

2. **Set SSL/TLS Mode:**
   - Go to SSL/TLS → Overview
   - Set to **"Flexible"** (Cloudflare handles SSL)

## Service Endpoints

### Backend API

- Health: `https://freedomos.vulcantech.co/health`
- API Docs: `https://freedomos.vulcantech.co/docs`
- Devices: `https://freedomos.vulcantech.co/api/v1/devices`
- Bundles: `https://freedomos.vulcantech.co/bundles`

### Frontend

- Main App: `https://freedomos.vulcantech.co`
- Web Flasher: `https://freedomos.vulcantech.co/flash`

### Email Service

- Create Email: `POST https://freedomos.vulcantech.co/api/v1/emails/create`
- Email Domain: `vulcantech.tech` (e.g., `howie@vulcantech.tech`)

### Drive Service

- Upload: `POST https://freedomos.vulcantech.co/api/v1/drive/upload`
- Files: `GET https://freedomos.vulcantech.co/api/v1/drive/files`

## Monitoring

### Check Container Status

```bash
docker ps
docker logs flashdash -f
docker-compose logs -f
```

### Check Nginx

```bash
nginx -t
systemctl status nginx
tail -f /var/log/nginx/error.log
```

### Check Backend Health

```bash
curl http://localhost:8000/health
curl https://freedomos.vulcantech.co/health
```

## Troubleshooting

### Container Not Running

```bash
docker-compose logs
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port Conflicts

```bash
# Check what's using ports
lsof -i :80
lsof -i :81
lsof -i :8000

# Stop conflicting services
systemctl stop nginx  # Only if needed
```

### Nginx Errors

```bash
# Test configuration
nginx -t

# Check logs
tail -f /var/log/nginx/error.log

# Reload
systemctl reload nginx
```

### Backend Not Responding

```bash
# Check container logs
docker logs flashdash -f

# Test from inside container
docker exec flashdash curl http://localhost:8000/health

# Check environment variables
docker exec flashdash env | grep -E "(API|DOMAIN|CORS)"
```

### Domain Not Working

1. **Check DNS:**
   ```bash
   dig freedomos.vulcantech.co
   # Should return: 138.197.24.229
   ```

2. **Check Cloudflare:**
   - DNS record exists and is proxied
   - SSL/TLS mode is "Flexible"

3. **Wait for propagation** (usually 5-10 minutes)

## Production Checklist

- [ ] Docker container running
- [ ] Backend responding on port 8000
- [ ] Frontend accessible on port 81
- [ ] System Nginx proxying correctly
- [ ] Domain accessible via HTTPS
- [ ] All API endpoints working
- [ ] Email service functional
- [ ] Drive service functional
- [ ] Cloudflare DNS configured
- [ ] SSL/TLS mode set to "Flexible"
- [ ] Firewall rules configured
- [ ] Logs being monitored

## Maintenance

### Update Application

```bash
cd ~/graohen_os
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs flashdash -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Restart Services

```bash
# Restart container
docker-compose restart

# Restart Nginx
systemctl restart nginx
```

---

**All services are configured for production use on `freedomos.vulcantech.co` only.**

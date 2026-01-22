# VPS Server Setup - Backend Domain Configuration

## Overview

Backend will run on **`freedomos.vulcantech.co`** while frontend can run on IP address or any domain. Frontend will automatically connect to the backend at `freedomos.vulcantech.co`.

## Domain Configuration

- **Backend**: `freedomos.vulcantech.co` (all API, email, drive services)
- **Frontend**: Can run on IP address or any domain (connects to backend automatically)
- **Email Domain**: `vulcantech.tech` (for email addresses like howie@vulcantech.tech)

## Step-by-Step VPS Setup

### Step 1: Update Files on VPS Server

SSH into your VPS:

```bash
ssh root@YOUR_VPS_IP
cd ~/graohen_os
```

#### Update docker-compose.yml

```bash
nano docker-compose.yml
```

Update the environment variables section:

```yaml
environment:
  - PY_HOST=0.0.0.0
  - PY_PORT=8000
  - BUNDLES_DIR=/app/bundles
  - GRAPHENE_BUNDLES_ROOT=/app/bundles
  - APK_STORAGE_DIR=/app/apks
  - DEBUG=false
  - LOG_LEVEL=INFO
  - FRONTEND_DOMAIN=${FRONTEND_DOMAIN:-frontend.vulcantech.tech}
  - BACKEND_DOMAIN=${BACKEND_DOMAIN:-freedomos.vulcantech.co}
  - EMAIL_DOMAIN=${EMAIL_DOMAIN:-vulcantech.tech}
  - DRIVE_DOMAIN=${DRIVE_DOMAIN:-freedomos.vulcantech.co}
  - API_BASE_URL=${API_BASE_URL:-https://freedomos.vulcantech.co}
  - EXTERNAL_HTTPS_BASE_URL=${EXTERNAL_HTTPS_BASE_URL:-https://vulcantech.tech}
  - VITE_API_BASE_URL=${VITE_API_BASE_URL:-https://freedomos.vulcantech.co}
  - CORS_ORIGINS=${CORS_ORIGINS:-*}
  - ALLOWED_HOSTS=${ALLOWED_HOSTS:-freedomos.vulcantech.co,vulcantech.tech,localhost,127.0.0.1}
```

#### Update docker/nginx-site.conf

```bash
nano docker/nginx-site.conf
```

Update the backend server block:

```nginx
# Backend API server block (handles backend, email, and drive)
# Primary backend domain: freedomos.vulcantech.co
server {
    listen 80;
    server_name freedomos.vulcantech.co backend.vulcantech.tech;

    # CORS headers for API
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    # Handle preflight requests
    if ($request_method = OPTIONS) {
        return 204;
    }

    # API routes - proxy to Python backend
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Increase timeouts for long-running operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

#### Update backend config (if needed)

```bash
nano backend/py-service/app/config.py
```

Ensure these settings:

```python
ALLOWED_HOSTS: str = "localhost,127.0.0.1,freedomos.vulcantech.co,vulcantech.tech"

CORS_ORIGINS: str = "*"  # Or specific origins if needed
```

### Step 2: Set Cloudflare DNS

Go to Cloudflare Dashboard → DNS and add/update:

**Backend Domain:**
```
Type: A
Name: freedomos
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

**Email Domain (if not already set):**
```
Type: A
Name: @ (or leave blank)
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

### Step 3: Set Cloudflare SSL/TLS

1. Go to Cloudflare Dashboard → SSL/TLS
2. Set encryption mode to **"Full"** (not "Flexible")
3. This ensures Cloudflare connects to your origin via HTTPS

### Step 4: Rebuild Frontend with Backend URL

The frontend needs to be rebuilt with the backend URL. You have two options:

#### Option A: Set Environment Variable Before Build (Recommended)

Create or update `.env` file in project root:

```bash
nano .env
```

Add:
```bash
VITE_API_BASE_URL=https://freedomos.vulcantech.co
```

Then rebuild:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Option B: Update Dockerfile to Use Environment Variable

The Dockerfile should already pass `VITE_API_BASE_URL` to the frontend build. If not, update the Dockerfile build step for the web package:

```dockerfile
# In Dockerfile, find the web build step and add:
RUN VITE_API_BASE_URL=${VITE_API_BASE_URL:-https://freedomos.vulcantech.co} pnpm --filter web build
```

### Step 5: Rebuild and Restart Container

```bash
# Stop current container
docker-compose down

# Rebuild with new configuration
docker-compose build --no-cache

# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Step 6: Verify Configuration

Test backend:

```bash
# From VPS
curl http://localhost:8000/health

# From outside (should work via domain)
curl https://freedomos.vulcantech.co/health

# Test CORS (should allow all origins)
curl -H "Origin: http://YOUR_FRONTEND_IP" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://freedomos.vulcantech.co/health \
     -v
```

Test frontend (if running on IP):

```bash
# Access frontend via IP
curl http://YOUR_VPS_IP

# Frontend should automatically connect to backend at freedomos.vulcantech.co
```

## Quick Update Script

Run this script on your VPS to quickly update everything:

```bash
#!/bin/bash
# Run this in ~/graohen_os directory

echo "Updating backend domain to freedomos.vulcantech.co..."

# Update docker-compose.yml
sed -i 's/BACKEND_DOMAIN=.*/BACKEND_DOMAIN=freedomos.vulcantech.co/g' docker-compose.yml
sed -i 's/DRIVE_DOMAIN=.*/DRIVE_DOMAIN=freedomos.vulcantech.co/g' docker-compose.yml
sed -i 's|API_BASE_URL=.*|API_BASE_URL=https://freedomos.vulcantech.co|g' docker-compose.yml
sed -i 's|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=https://freedomos.vulcantech.co|g' docker-compose.yml
sed -i 's/CORS_ORIGINS=.*/CORS_ORIGINS=*/g' docker-compose.yml
sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=freedomos.vulcantech.co,vulcantech.tech,localhost,127.0.0.1/g' docker-compose.yml

# Update nginx config
sed -i 's/server_name backend\.vulcantech\.tech;/server_name freedomos.vulcantech.co backend.vulcantech.tech;/g' docker/nginx-site.conf

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > .env
else
    if ! grep -q "VITE_API_BASE_URL" .env; then
        echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" >> .env
    else
        sed -i 's|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=https://freedomos.vulcantech.co|g' .env
    fi
fi

echo "✅ Configuration updated"
echo "Now run: docker-compose down && docker-compose build --no-cache && docker-compose up -d"
```

## Frontend Configuration

The frontend automatically uses `VITE_API_BASE_URL` environment variable. This is set during Docker build.

**If frontend is running separately** (not in Docker), create a `.env` file in the frontend directory:

```bash
cd frontend/packages/web
echo "VITE_API_BASE_URL=https://freedomos.vulcantech.co" > .env
pnpm build
```

## Testing

### Test Backend API

```bash
# Health check
curl https://freedomos.vulcantech.co/health

# List devices
curl https://freedomos.vulcantech.co/devices

# API docs
curl https://freedomos.vulcantech.co/docs
```

### Test Frontend Connection

1. Open frontend (via IP or domain)
2. Open browser DevTools → Network tab
3. Check that API calls go to `https://freedomos.vulcantech.co`
4. Verify no CORS errors

### Test Email Service

```bash
curl -X POST https://freedomos.vulcantech.co/api/v1/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "test@example.com",
    "subject": "Test",
    "body": "Test email"
  }'
```

## Troubleshooting

### CORS Errors

If you see CORS errors, ensure:
1. `CORS_ORIGINS=*` in docker-compose.yml
2. Backend config allows all origins
3. Nginx has CORS headers configured

### Frontend Can't Connect to Backend

1. Check `VITE_API_BASE_URL` is set correctly
2. Verify backend is accessible: `curl https://freedomos.vulcantech.co/health`
3. Check browser console for errors
4. Verify DNS: `dig freedomos.vulcantech.co`

### Backend Not Responding

1. Check container logs: `docker logs flashdash -f`
2. Check nginx config: `docker exec flashdash nginx -t`
3. Test backend directly: `curl http://localhost:8000/health`
4. Check firewall: `sudo ufw status`

## Summary

After setup:
- ✅ Backend runs on `https://freedomos.vulcantech.co`
- ✅ Frontend can run on IP address or any domain
- ✅ Frontend automatically connects to backend at `freedomos.vulcantech.co`
- ✅ Email addresses use `@vulcantech.tech` domain
- ✅ All API, email, and drive services accessible via `freedomos.vulcantech.co`

# Quick VPS Setup Guide

## Server Access

```bash
ssh root@138.197.24.229
# Password: Dubai123@
```

## One-Command Setup

Once connected to the server, run:

```bash
cd ~ && \
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/graohen_os/main/VPS_COMPLETE_SETUP.sh -o VPS_COMPLETE_SETUP.sh && \
chmod +x VPS_COMPLETE_SETUP.sh && \
./VPS_COMPLETE_SETUP.sh
```

**OR** if you already have the repo cloned:

```bash
cd ~/graohen_os
chmod +x VPS_COMPLETE_SETUP.sh
./VPS_COMPLETE_SETUP.sh
```

## Manual Setup (Copy-Paste)

If the script doesn't work, copy-paste these commands one by one:

### 1. Update System
```bash
apt-get update && apt-get upgrade -y
```

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
systemctl enable docker && systemctl start docker
```

### 3. Install Docker Compose
```bash
apt-get install -y docker-compose-plugin
```

### 4. Navigate to Project
```bash
cd ~/graohen_os
```

### 5. Update docker-compose.yml
```bash
cat > docker-compose.yml << 'EOF'
services:
  flashdash:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: https://freedomos.vulcantech.co
    container_name: flashdash
    ports:
      - "81:80"
      - "8000:8000"
    volumes:
      - ./bundles:/app/bundles
      - ./downloads:/app/downloads
      - ./logs:/app/logs
    environment:
      - PY_HOST=0.0.0.0
      - PY_PORT=8000
      - BUNDLES_DIR=/app/bundles
      - GRAPHENE_BUNDLES_ROOT=/app/bundles
      - APK_STORAGE_DIR=/app/apks
      - DEBUG=false
      - LOG_LEVEL=INFO
      - FRONTEND_DOMAIN=localhost
      - BACKEND_DOMAIN=freedomos.vulcantech.co
      - EMAIL_DOMAIN=vulcantech.tech
      - DRIVE_DOMAIN=freedomos.vulcantech.co
      - API_BASE_URL=https://freedomos.vulcantech.co
      - EXTERNAL_HTTPS_BASE_URL=https://vulcantech.tech
      - VITE_API_BASE_URL=https://freedomos.vulcantech.co
      - CORS_ORIGINS=*
      - ALLOWED_HOSTS=freedomos.vulcantech.co,vulcantech.tech,localhost,127.0.0.1
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
EOF
```

### 6. Configure Nginx (HTTP only for Cloudflare)
```bash
cat > /etc/nginx/sites-available/freedomos << 'EOF'
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

    location / {
        proxy_pass http://127.0.0.1:81;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### 7. Configure Firewall
```bash
ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 81/tcp && ufw allow 8000/tcp
ufw --force enable
```

### 8. Build and Start Docker
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 9. Verify Setup
```bash
sleep 10
docker ps
curl http://localhost:8000/health
curl http://localhost:81/health
```

## Verify Everything Works

Run the verification script:

```bash
chmod +x VERIFY_VPS_SETUP.sh
./VERIFY_VPS_SETUP.sh
```

Or manually check:

```bash
# Check container
docker ps | grep flashdash

# Check backend
curl http://localhost:8000/health

# Check frontend
curl http://localhost:81/health

# Check logs
docker-compose logs -f
```

## Cloudflare DNS Setup

1. Go to Cloudflare Dashboard → DNS
2. Add A record:
   - **Name**: `freedomos`
   - **Content**: `138.197.24.229`
   - **Proxy**: ✅ Proxied
   - **TTL**: Auto

3. Set SSL/TLS mode:
   - Go to SSL/TLS → Overview
   - Set to **"Flexible"**

## Troubleshooting

### Container won't start
```bash
docker-compose logs
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port conflict
```bash
lsof -i :80
lsof -i :81
# Stop conflicting services
```

### Nginx error
```bash
nginx -t
# Fix errors, then:
systemctl reload nginx
```

### Backend not responding
```bash
docker logs flashdash -f
docker exec flashdash curl http://localhost:8000/health
```

## Quick Test Commands

```bash
# Backend health
curl http://localhost:8000/health

# Frontend (port 81)
curl http://localhost:81

# Domain (after DNS configured)
curl https://freedomos.vulcantech.co/health
```

---

**After setup, your services will be available at:**
- Backend API: `http://localhost:8000` (internal) / `https://freedomos.vulcantech.co` (external)
- Frontend: `http://localhost:81` (internal) / `https://freedomos.vulcantech.co` (external)

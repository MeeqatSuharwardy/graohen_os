# VPS Server Setup Commands

## Server Information

- **IP**: 138.197.24.229
- **Password**: Dubai123@
- **Domain**: freedomos.vulcantech.co

## Step 1: SSH into Server

```bash
ssh root@138.197.24.229
# Password: Dubai123@
```

## Step 2: Run Complete Setup Script

Once connected to the server, run:

```bash
# Download or create the setup script
cd ~
wget https://raw.githubusercontent.com/YOUR_REPO/graohen_os/main/VPS_COMPLETE_SETUP.sh
# OR if script is already on server:
cd ~/graohen_os

# Make executable and run
chmod +x VPS_COMPLETE_SETUP.sh
./VPS_COMPLETE_SETUP.sh
```

## Step 3: Manual Setup (If Script Doesn't Work)

### 2.1: Update System

```bash
apt-get update
apt-get upgrade -y
```

### 2.2: Install Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh
systemctl enable docker
systemctl start docker
```

### 2.3: Install Docker Compose

```bash
apt-get install -y docker-compose-plugin
```

### 2.4: Navigate to Project

```bash
cd ~/graohen_os
# Or clone if needed:
# git clone <your-repo-url> graohen_os
# cd graohen_os
```

### 2.5: Update docker-compose.yml

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

### 2.6: Configure Nginx

```bash
cat > /etc/nginx/sites-available/freedomos << 'EOF'
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
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
nginx -t
systemctl reload nginx
```

### 2.7: Configure Firewall

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 81/tcp
ufw allow 8000/tcp
ufw --force enable
```

### 2.8: Build and Start Docker

```bash
cd ~/graohen_os
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 2.9: Verify Everything Works

```bash
# Check container
docker ps

# Check logs
docker-compose logs -f

# Test backend
curl http://localhost:8000/health

# Test port 81
curl http://localhost:81/health

# Test domain (if DNS is configured)
curl https://freedomos.vulcantech.co/health
```

## Step 4: Verify Configuration

### Check Docker Container

```bash
docker ps | grep flashdash
docker logs flashdash --tail 50
```

### Check Nginx

```bash
nginx -t
systemctl status nginx
curl -I http://localhost:81
```

### Check Backend

```bash
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### Check Domain (if DNS configured)

```bash
curl https://freedomos.vulcantech.co/health
```

## Step 5: Set Cloudflare DNS

1. Go to Cloudflare Dashboard → DNS
2. Add A record:
   - **Name**: `freedomos`
   - **Content**: `138.197.24.229`
   - **Proxy**: ✅ Proxied (Orange Cloud)
   - **TTL**: Auto

3. Set SSL/TLS mode:
   - Go to SSL/TLS → Overview
   - Set to **"Flexible"** (since nginx uses HTTP only)

## Troubleshooting

### Container Won't Start

```bash
docker-compose logs
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port 80 Conflict

```bash
# Check what's using port 80
lsof -i :80

# Stop system nginx if needed
systemctl stop nginx
systemctl disable nginx
```

### Nginx Configuration Error

```bash
nginx -t
# Fix errors shown
systemctl reload nginx
```

### Backend Not Responding

```bash
docker logs flashdash -f
docker exec flashdash curl http://localhost:8000/health
```

## Quick Verification Commands

Run these after setup:

```bash
# 1. Docker status
docker ps

# 2. Backend health
curl http://localhost:8000/health

# 3. Frontend (port 81)
curl http://localhost:81

# 4. Nginx status
systemctl status nginx

# 5. Domain (if configured)
curl https://freedomos.vulcantech.co/health
```

---

## Complete One-Liner Setup

If you want to run everything at once (after SSH):

```bash
cd ~ && \
(wget -O VPS_COMPLETE_SETUP.sh https://raw.githubusercontent.com/YOUR_REPO/graohen_os/main/VPS_COMPLETE_SETUP.sh || echo "Script not available, using manual setup") && \
chmod +x VPS_COMPLETE_SETUP.sh && \
./VPS_COMPLETE_SETUP.sh
```

Or copy-paste the entire `VPS_COMPLETE_SETUP.sh` script content directly into the SSH session.

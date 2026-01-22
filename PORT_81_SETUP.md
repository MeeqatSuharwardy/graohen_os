# Port 81 Setup - Docker Container Configuration

## Overview

Your Docker container is now configured to use **port 81** for HTTP instead of port 80, to avoid conflict with system nginx that's handling SSL/domains on port 80.

## Configuration

- **Docker HTTP**: Port `81` (maps to container port 80)
- **Docker HTTPS**: Port `444` (maps to container port 443)
- **Backend API**: Port `8000` (unchanged)
- **System Nginx**: Port `80` and `443` (for SSL/domains)

## Access URLs

### Direct Access (via IP)
- **HTTP**: `http://YOUR_VPS_IP:81`
- **HTTPS**: `https://YOUR_VPS_IP:444` (if SSL configured)
- **Backend API**: `http://YOUR_VPS_IP:8000`

### Domain Access (via Cloudflare/System Nginx)
- **Backend**: `https://freedomos.vulcantech.co` (via system nginx proxy)
- **Frontend**: `https://frontend.vulcantech.tech` (via system nginx proxy)

## Setting Up Reverse Proxy (Optional)

If you want to access the Docker container via domain (freedomos.vulcantech.co) through system nginx:

### Step 1: Configure System Nginx

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

Add this configuration:

```nginx
# Backend API proxy - forwards to Docker container on port 81
server {
    listen 80;
    server_name freedomos.vulcantech.co;

    # Redirect HTTP to HTTPS (if you have SSL)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    # SSL certificates (your existing SSL setup)
    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;

    # CORS headers
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    # Handle preflight requests
    if ($request_method = OPTIONS) {
        return 204;
    }

    # Proxy to Docker container on port 81
    location / {
        proxy_pass http://127.0.0.1:81;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Increase timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### Step 2: Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Test

```bash
# Test via domain (through system nginx)
curl https://freedomos.vulcantech.co/health

# Test directly on port 81
curl http://localhost:81/health
```

## Firewall Configuration

Make sure port 81 is open (if needed):

```bash
sudo ufw allow 81/tcp
sudo ufw allow 444/tcp  # If using HTTPS
```

## Verification

After starting Docker container:

```bash
# Check container is running
docker ps

# Check port 81 is listening
sudo lsof -i :81 | grep docker

# Test HTTP on port 81
curl http://localhost:81/health

# Test backend API
curl http://localhost:8000/health

# Test via domain (if reverse proxy configured)
curl https://freedomos.vulcantech.co/health
```

## Summary

- ✅ Docker container uses port **81** for HTTP
- ✅ System nginx continues using port **80** for SSL/domains
- ✅ No conflicts between services
- ✅ Access Docker container directly: `http://YOUR_VPS_IP:81`
- ✅ Access via domain: `https://freedomos.vulcantech.co` (if reverse proxy configured)

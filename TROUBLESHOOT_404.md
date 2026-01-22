# Troubleshooting 404 Error on freedomos.vulcantech.co

## Quick Diagnostic Steps

Run these commands on your VPS to diagnose the issue:

### Step 1: Check Docker Container is Running

```bash
docker ps
# Should show flashdash container running
```

### Step 2: Test Direct Access to Port 81

```bash
curl http://localhost:81/health
# Should return: {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

### Step 3: Check Nginx Configuration

```bash
# Check if configuration file exists
sudo ls -la /etc/nginx/sites-available/freedomos
sudo ls -la /etc/nginx/sites-enabled/freedomos

# Check nginx configuration
sudo nginx -t

# Check which server block is handling the request
sudo grep -r "freedomos.vulcantech.co" /etc/nginx/
```

### Step 4: Check Nginx Error Logs

```bash
sudo tail -50 /var/log/nginx/error.log
```

### Step 5: Check if Site is Enabled

```bash
# List enabled sites
ls -la /etc/nginx/sites-enabled/

# Should see freedomos symlink
```

---

## Common Issues and Fixes

### Issue 1: Nginx Configuration Not Enabled

**Problem:** Configuration file exists but site is not enabled

**Fix:**
```bash
sudo ln -s /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
sudo nginx -t
sudo systemctl reload nginx
```

### Issue 2: Docker Container Not Running on Port 81

**Problem:** Container stopped or not listening

**Fix:**
```bash
cd ~/graohen_os
docker-compose up -d
docker ps
curl http://localhost:81/health
```

### Issue 3: Wrong Server Block Handling Request

**Problem:** Default nginx site is handling the request instead of freedomos config

**Fix:**
```bash
# Check default site
sudo cat /etc/nginx/sites-enabled/default

# If it has server_name _ or server_name freedomos.vulcantech.co, remove or comment it out
sudo nano /etc/nginx/sites-enabled/default

# Or disable default site
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Issue 4: SSL Certificate Issues

**Problem:** SSL certificate errors causing nginx to serve default site

**Fix:**
```bash
# Check SSL certificate
sudo ls -la /etc/letsencrypt/live/freedomos.vulcantech.co/

# If using Cloudflare SSL only, comment out SSL cert lines in config
sudo nano /etc/nginx/sites-available/freedomos
# Comment out:
# ssl_certificate ...
# ssl_certificate_key ...

sudo nginx -t
sudo systemctl reload nginx
```

### Issue 5: Port 81 Not Accessible

**Problem:** Docker container not binding to port 81 correctly

**Fix:**
```bash
# Check docker-compose.yml has correct port mapping
cat docker-compose.yml | grep "81:80"

# Should see: - "81:80"

# Restart container
docker-compose restart
docker ps
```

---

## Complete Setup Verification

Run this complete check:

```bash
#!/bin/bash
echo "=== Docker Container Check ==="
docker ps | grep flashdash
echo ""

echo "=== Port 81 Direct Access ==="
curl -s http://localhost:81/health || echo "❌ Port 81 not accessible"
echo ""

echo "=== Nginx Configuration Check ==="
sudo nginx -t
echo ""

echo "=== Enabled Sites ==="
ls -la /etc/nginx/sites-enabled/ | grep freedomos
echo ""

echo "=== Nginx Server Blocks ==="
sudo grep -r "server_name.*freedomos" /etc/nginx/sites-enabled/
echo ""

echo "=== Recent Nginx Errors ==="
sudo tail -10 /var/log/nginx/error.log
echo ""

echo "=== Test Domain Access ==="
curl -s https://freedomos.vulcantech.co/health || echo "❌ Domain not working"
```

---

## Quick Fix Script

If configuration is missing, run this:

```bash
#!/bin/bash
cd ~/graohen_os

# Create nginx config if missing
if [ ! -f /etc/nginx/sites-available/freedomos ]; then
    echo "Creating nginx configuration..."
    sudo tee /etc/nginx/sites-available/freedomos > /dev/null << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

# HTTPS server - proxies to Docker container on port 81
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    # SSL certificates (comment out if using Cloudflare SSL only)
    # ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # CORS headers
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

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
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF
fi

# Enable site
sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos

# Test and reload
sudo nginx -t && sudo systemctl reload nginx && echo "✅ Nginx reloaded" || echo "❌ Nginx config error"

# Test
echo ""
echo "Testing..."
curl -s http://localhost:81/health && echo " ✅ Port 81 works"
curl -s https://freedomos.vulcantech.co/health && echo " ✅ Domain works" || echo " ❌ Domain not working"
```

---

## Most Likely Issue

Based on the 404 error, the most common causes are:

1. **Nginx configuration not enabled** - Site file exists but symlink missing
2. **Default nginx site taking precedence** - Default site has higher priority
3. **Docker container not running** - Container stopped or crashed

Run these commands to fix:

```bash
# 1. Ensure Docker is running
cd ~/graohen_os
docker-compose up -d

# 2. Test port 81 directly
curl http://localhost:81/health

# 3. Ensure nginx config is enabled
sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos

# 4. Disable default site if it conflicts
sudo rm /etc/nginx/sites-enabled/default 2>/dev/null

# 5. Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx

# 6. Test domain
curl https://freedomos.vulcantech.co/health
```

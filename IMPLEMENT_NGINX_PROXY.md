# Implement Nginx Reverse Proxy Setup

## Quick Implementation

### Option 1: Use the Setup Script (Easiest)

**On your VPS server:**

```bash
cd ~/graohen_os

# Copy the setup script to server (or create it)
# Then run:
sudo bash setup-nginx-proxy.sh
```

The script will:
1. ✅ Check if nginx is installed
2. ✅ Check for SSL certificates
3. ✅ Create nginx configuration
4. ✅ Enable the site
5. ✅ Test configuration
6. ✅ Reload nginx

---

### Option 2: Manual Setup

**Step 1: Create Nginx Configuration**

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

**Step 2: Copy this configuration:**

```nginx
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

    # SSL certificates (update path if different)
    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    # If using Cloudflare SSL only (no Let's Encrypt), comment out the above lines
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

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
```

**Step 3: Enable the Site**

```bash
sudo ln -s /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
```

**Step 4: Test Configuration**

```bash
sudo nginx -t
```

**Step 5: Reload Nginx**

```bash
sudo systemctl reload nginx
```

**Step 6: Test**

```bash
curl https://freedomos.vulcantech.co/health
```

---

## SSL Certificate Setup

### If Using Cloudflare SSL Only

If you're using Cloudflare SSL (easiest), comment out the SSL certificate lines:

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

Comment out these lines:
```nginx
# ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
```

Then reload:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### If Using Let's Encrypt

```bash
# Stop Docker container temporarily
cd ~/graohen_os
docker-compose down

# Get certificate
sudo certbot certonly --standalone -d freedomos.vulcantech.co

# Start Docker container
docker-compose up -d

# Reload nginx
sudo systemctl reload nginx
```

---

## Verification

After setup, verify everything works:

```bash
# 1. Check nginx is running
sudo systemctl status nginx

# 2. Check Docker container is running
docker ps

# 3. Test direct access (port 81)
curl http://localhost:81/health

# 4. Test via domain (through nginx proxy)
curl https://freedomos.vulcantech.co/health

# 5. Check nginx logs if issues
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## Troubleshooting

### 502 Bad Gateway

**Problem:** Nginx can't connect to Docker container

**Solution:**
```bash
# Check Docker container is running
docker ps

# Check container is listening on port 81
docker exec flashdash netstat -tlnp | grep :80

# Test direct connection
curl http://127.0.0.1:81/health
```

### SSL Certificate Errors

**Problem:** SSL certificate not found

**Solution:**
```bash
# Check certificate exists
sudo ls -la /etc/letsencrypt/live/freedomos.vulcantech.co/

# If using Cloudflare only, comment out SSL cert lines in nginx config
```

### Nginx Configuration Errors

**Problem:** `nginx -t` fails

**Solution:**
```bash
# Check syntax
sudo nginx -t

# Check for duplicate server_name
sudo grep -r "server_name freedomos.vulcantech.co" /etc/nginx/

# Remove duplicates if found
```

---

## Summary

After implementation:

- ✅ **System nginx** handles SSL/HTTPS on port 443
- ✅ **System nginx** proxies to Docker container on port 81
- ✅ **Docker container** runs on port 81 (no conflict with system nginx)
- ✅ **Domain access**: `https://freedomos.vulcantech.co` → proxies to → `http://127.0.0.1:81`
- ✅ **Direct access**: `http://YOUR_VPS_IP:81` (still works)

---

## Files Created

1. **`nginx-freedomos.conf`** - Nginx configuration file
2. **`setup-nginx-proxy.sh`** - Automated setup script
3. **`IMPLEMENT_NGINX_PROXY.md`** - This guide

Copy these files to your VPS and run the setup script, or follow the manual steps above.

# SSL/TLS Setup Guide for freedomos.vulcantech.co

## Overview

You have two options for SSL/TLS:
1. **Cloudflare SSL** (Recommended - Easiest) - Cloudflare handles SSL termination
2. **Let's Encrypt/Certbot** (Direct SSL on server) - SSL certificates on your VPS

## Option 1: Cloudflare SSL (Recommended)

Since your domain is already proxied through Cloudflare (orange cloud), this is the easiest option.

### Step 1: Configure Cloudflare SSL/TLS

1. **Go to Cloudflare Dashboard**
   - Navigate to: `SSL/TLS` → `Overview`

2. **Set Encryption Mode**
   - Select: **"Full"** or **"Full (strict)"**
   - **"Full"**: Cloudflare → Server (HTTPS), allows self-signed certs
   - **"Full (strict)"**: Cloudflare → Server (HTTPS), requires valid SSL cert
   - For now, use **"Full"** (we'll add Let's Encrypt later if needed)

3. **Verify Settings**
   - SSL/TLS encryption mode: **Full**
   - Always Use HTTPS: **On** (optional, but recommended)
   - Automatic HTTPS Rewrites: **On** (optional)

### Step 2: Update Nginx for HTTPS (Optional but Recommended)

Even with Cloudflare, you can add HTTPS support on your server:

```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP
cd ~/graohen_os

# Install certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot certonly --standalone -d freedomos.vulcantech.co

# Or if you have multiple domains
sudo certbot certonly --standalone -d freedomos.vulcantech.co -d vulcantech.tech
```

### Step 3: Update Nginx Configuration

Update `docker/nginx-site.conf` to support HTTPS:

```bash
nano docker/nginx-site.conf
```

Add HTTPS server block for backend:

```nginx
# Backend API server block - HTTPS
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co backend.vulcantech.tech;

    # SSL certificates (if using Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

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

# Backend API server block - HTTP (redirect to HTTPS)
server {
    listen 80;
    server_name freedomos.vulcantech.co backend.vulcantech.tech;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}
```

### Step 4: Mount SSL Certificates in Docker

Update `docker-compose.yml`:

```yaml
volumes:
  - ./bundles:/app/bundles
  - ./downloads:/app/downloads
  - ./logs:/app/logs
  - /etc/letsencrypt:/etc/letsencrypt:ro  # Mount SSL certificates
```

### Step 5: Restart Container

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Step 6: Test HTTPS

```bash
# Test HTTPS endpoint
curl https://freedomos.vulcantech.co/health

# Should return:
# {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

---

## Option 2: Let's Encrypt with Certbot (Direct SSL)

If you want SSL certificates directly on your server (not just Cloudflare):

### Step 1: Install Certbot

```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# Install certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx
```

### Step 2: Stop Docker Container Temporarily

```bash
cd ~/graohen_os
docker-compose down
```

This is needed because certbot needs to bind to port 80 for verification.

### Step 3: Get SSL Certificate

```bash
# Get certificate for backend domain
sudo certbot certonly --standalone -d freedomos.vulcantech.co

# If you want certificates for other domains too
sudo certbot certonly --standalone -d freedomos.vulcantech.co -d vulcantech.tech -d frontend.vulcantech.tech
```

**Follow the prompts:**
- Enter your email address
- Agree to terms of service
- Choose whether to share email with EFF (optional)

### Step 4: Verify Certificates

```bash
# Check certificates
sudo ls -la /etc/letsencrypt/live/freedomos.vulcantech.co/

# Should see:
# cert.pem
# chain.pem
# fullchain.pem
# privkey.pem
```

### Step 5: Update Nginx Configuration

Update `docker/nginx-site.conf` with HTTPS configuration (see Option 1, Step 3 above).

### Step 6: Update Docker Compose

Add SSL certificate volume mount:

```yaml
volumes:
  - ./bundles:/app/bundles
  - ./downloads:/app/downloads
  - ./logs:/app/logs
  - /etc/letsencrypt:/etc/letsencrypt:ro  # Read-only mount for SSL certs
```

### Step 7: Update Dockerfile (if needed)

Ensure nginx can access certificates. The volume mount should handle this, but verify:

```dockerfile
# In Dockerfile, ensure nginx can read certs
RUN chmod -R 755 /etc/letsencrypt || true
```

### Step 8: Expose HTTPS Port

Update `docker-compose.yml`:

```yaml
ports:
  - "80:80"
  - "443:443"  # Add HTTPS port
  - "8000:8000"
```

### Step 9: Restart Container

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

### Step 10: Test SSL

```bash
# Test HTTPS
curl https://freedomos.vulcantech.co/health

# Test SSL certificate
openssl s_client -connect freedomos.vulcantech.co:443 -servername freedomos.vulcantech.co

# Check certificate expiry
sudo certbot certificates
```

### Step 11: Set Up Auto-Renewal

Let's Encrypt certificates expire every 90 days. Set up auto-renewal:

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot should auto-renew, but verify cron job exists
sudo systemctl status certbot.timer

# Enable certbot timer (if not already enabled)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

**Note:** After certificate renewal, you'll need to reload nginx:

```bash
# Add to crontab or create renewal hook
sudo nano /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

```bash
#!/bin/bash
docker exec flashdash nginx -s reload
```

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

---

## Quick Setup Script (Option 2 - Let's Encrypt)

Run this script on your VPS:

```bash
#!/bin/bash
# SSL Setup Script for freedomos.vulcantech.co

set -e

echo "Setting up SSL for freedomos.vulcantech.co..."

# Install certbot
echo "Installing certbot..."
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Stop Docker container
echo "Stopping Docker container..."
cd ~/graohen_os
docker-compose down

# Get SSL certificate
echo "Getting SSL certificate..."
sudo certbot certonly --standalone -d freedomos.vulcantech.co --non-interactive --agree-tos --email YOUR_EMAIL@example.com

# Update docker-compose.yml to mount SSL certificates
echo "Updating docker-compose.yml..."
if ! grep -q "/etc/letsencrypt:/etc/letsencrypt:ro" docker-compose.yml; then
    sed -i '/volumes:/a\      - /etc/letsencrypt:/etc/letsencrypt:ro' docker-compose.yml
fi

# Update docker-compose.yml to expose port 443
if ! grep -q '"443:443"' docker-compose.yml; then
    sed -i 's/- "80:80"/- "80:80"\n      - "443:443"/' docker-compose.yml
fi

# Update nginx config (you'll need to manually add HTTPS server block)
echo "⚠️  Please manually update docker/nginx-site.conf to add HTTPS server block"
echo "See SSL_SETUP_GUIDE.md for nginx configuration"

# Rebuild and start
echo "Rebuilding and starting container..."
docker-compose build
docker-compose up -d

echo "✅ SSL setup complete!"
echo "Test with: curl https://freedomos.vulcantech.co/health"
```

---

## Recommended: Cloudflare SSL (Easiest)

**For most users, Cloudflare SSL is recommended:**

1. ✅ Already set up (domain is proxied)
2. ✅ No server configuration needed
3. ✅ Automatic SSL
4. ✅ DDoS protection included
5. ✅ CDN benefits

**Just set Cloudflare SSL mode to "Full" and you're done!**

---

## Verification

After setup, verify SSL:

```bash
# Test HTTPS endpoint
curl https://freedomos.vulcantech.co/health

# Check SSL certificate
openssl s_client -connect freedomos.vulcantech.co:443 -servername freedomos.vulcantech.co < /dev/null 2>/dev/null | openssl x509 -noout -dates

# Test from browser
# Open: https://freedomos.vulcantech.co/health
# Should show valid SSL certificate
```

---

## Troubleshooting

### SSL Certificate Not Working

1. **Check Cloudflare SSL mode:**
   - Should be "Full" or "Full (strict)"

2. **Check certificate files:**
   ```bash
   sudo ls -la /etc/letsencrypt/live/freedomos.vulcantech.co/
   ```

3. **Check nginx config:**
   ```bash
   docker exec flashdash nginx -t
   ```

4. **Check port 443 is open:**
   ```bash
   sudo netstat -tlnp | grep :443
   sudo ufw allow 443/tcp
   ```

### Certificate Renewal Issues

```bash
# Test renewal
sudo certbot renew --dry-run

# Manual renewal
sudo certbot renew

# Reload nginx after renewal
docker exec flashdash nginx -s reload
```

### Cloudflare SSL Issues

1. **Check SSL mode:** Dashboard → SSL/TLS → Overview
2. **Check DNS:** Ensure domain is proxied (orange cloud)
3. **Wait for propagation:** SSL changes can take 5-15 minutes

---

## Summary

**Quickest Setup (Cloudflare):**
1. Go to Cloudflare Dashboard → SSL/TLS
2. Set encryption mode to **"Full"**
3. Done! ✅

**Full SSL Setup (Let's Encrypt):**
1. Install certbot
2. Get certificate: `sudo certbot certonly --standalone -d freedomos.vulcantech.co`
3. Update nginx config with HTTPS server block
4. Mount certificates in docker-compose.yml
5. Expose port 443
6. Restart container

Your backend is now accessible via HTTPS! 🎉

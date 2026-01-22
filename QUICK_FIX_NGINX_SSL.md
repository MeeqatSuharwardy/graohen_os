# Quick Fix: Nginx SSL Certificate Error

## Problem

Nginx requires SSL certificates when using `listen 443 ssl`, but you're using Cloudflare SSL which doesn't require server-side certificates.

## Solution: Use HTTP Only (Cloudflare Handles SSL)

Since Cloudflare is handling SSL termination, configure nginx to listen on **port 80 only**. Cloudflare will connect to your server via HTTP, and Cloudflare handles HTTPS for end users.

### Quick Fix Command

Run this on your VPS:

```bash
sudo tee /etc/nginx/sites-available/freedomos > /dev/null << 'EOF'
# HTTP server - Cloudflare handles SSL termination
server {
    listen 80;
    server_name freedomos.vulcantech.co;

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

sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### Verify Cloudflare SSL Mode

Make sure Cloudflare SSL/TLS mode is set to **"Flexible"** (not "Full"):

1. Go to Cloudflare Dashboard → SSL/TLS → Overview
2. Set encryption mode to **"Flexible"**
3. This allows Cloudflare → Your Server via HTTP (no SSL needed on server)

---

## Alternative: Use HTTPS with Self-Signed Certificate

If you want to use HTTPS on the server (Cloudflare "Full" mode), generate a self-signed certificate:

```bash
# Generate self-signed certificate
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/freedomos.key \
    -out /etc/nginx/ssl/freedomos.crt \
    -subj "/CN=freedomos.vulcantech.co"

# Update nginx config to use self-signed cert
sudo tee /etc/nginx/sites-available/freedomos > /dev/null << 'EOF'
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;
    
    ssl_certificate /etc/nginx/ssl/freedomos.crt;
    ssl_certificate_key /etc/nginx/ssl/freedomos.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://127.0.0.1:81;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
sudo nginx -t && sudo systemctl reload nginx
```

Then set Cloudflare SSL mode to **"Full"** (accepts self-signed certificates).

---

## Recommended: HTTP Only (Simplest)

**For Cloudflare SSL, use HTTP only:**

```bash
sudo tee /etc/nginx/sites-available/freedomos > /dev/null << 'EOF'
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

sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

**Set Cloudflare SSL mode to "Flexible"** and you're done!

---

## Test After Fix

```bash
# Test nginx config
sudo nginx -t

# Test domain
curl https://freedomos.vulcantech.co/health

# Should return: {"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

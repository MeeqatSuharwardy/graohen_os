# 🔧 CORS Fix - Remove Duplicate Headers from Nginx

## Problem

CORS error: **"The 'Access-Control-Allow-Origin' header contains multiple values '*, https://freedomos.vulcantech.co'"**

**Root Cause**: Both the backend (FastAPI) and Nginx are setting CORS headers, causing duplicates.

## ✅ Solution

**Remove CORS headers from Nginx** - Let the backend handle CORS since it's already configured correctly.

## 📝 Update Nginx Configuration

On your VPS, edit the Nginx config:

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

**Remove or comment out these lines**:

```nginx
# Remove these CORS headers - backend handles CORS
# add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
# add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
# add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
# add_header Access-Control-Allow-Credentials "true" always;

# Remove this OPTIONS handler - backend handles it
# if ($request_method = OPTIONS) {
#     return 204;
# }
```

**Keep only the proxy settings**:

```nginx
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers (keep these)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy to backend - NO CORS headers here
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

## 🔄 Apply Changes

```bash
# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## ✅ Backend CORS Configuration

The backend is already configured to:
- ✅ Allow all origins (`allow_origins=["*"]`)
- ✅ Include `http://localhost:5174` for local development
- ✅ Handle OPTIONS preflight requests automatically

## 🧪 Test

After updating Nginx:

1. **Test from local frontend** (`http://localhost:5174`):
   ```bash
   curl -H "Origin: http://localhost:5174" \
        -H "Access-Control-Request-Method: GET" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS \
        https://freedomos.vulcantech.co/health \
        -v
   ```

2. **Should see single CORS header**:
   ```
   Access-Control-Allow-Origin: *
   ```

3. **No duplicate headers** - Problem solved! ✅

---

**Status**: Backend handles CORS correctly. Remove CORS headers from Nginx to fix duplicate header issue.

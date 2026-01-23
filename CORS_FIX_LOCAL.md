# 🔧 CORS Fix for Local Frontend Development

## Problem

CORS error when running frontend locally (`http://localhost:5174`):
```
Access-Control-Allow-Origin header contains multiple values '*, https://freedomos.vulcantech.co'
```

## Root Cause

Both **backend** and **Nginx** are setting CORS headers, causing duplicates.

## ✅ Solution

### Option 1: Remove CORS Headers from Nginx (Recommended)

**On your VPS**, edit Nginx config and remove CORS headers:

```bash
ssh root@freedomos.vulcantech.co
sudo nano /etc/nginx/sites-available/freedomos
```

**Remove these lines**:
```nginx
# Remove these - backend handles CORS
add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
add_header Access-Control-Allow-Credentials "true" always;

if ($request_method = OPTIONS) {
    return 204;
}
```

**Then reload Nginx**:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: Use Backend Directly (For Local Development)

If you're running backend locally, connect directly to `http://localhost:8000` instead of going through Nginx:

**Update frontend `.env`**:
```bash
# In frontend/packages/web/.env or frontend/apps/web-flasher/.env
VITE_API_BASE_URL=http://localhost:8000
```

**Start backend locally**:
```bash
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## ✅ Backend CORS Configuration

The backend is already configured to:
- ✅ Allow all origins (`allow_origins=["*"]`)
- ✅ Includes `http://localhost:5174` automatically
- ✅ Handles OPTIONS preflight requests

## 🧪 Test

After fixing:

1. **Start local frontend**:
   ```bash
   cd frontend/packages/web
   pnpm dev
   ```

2. **Should work** - No CORS errors! ✅

---

**Quick Fix**: Remove CORS headers from Nginx on VPS, then reload Nginx.

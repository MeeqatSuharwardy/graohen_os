# 🔧 Fix CORS Duplicate Headers on VPS

## Problem

CORS error persists because Nginx on VPS is still adding CORS headers, causing duplicates with backend.

## ✅ Quick Fix

### Option 1: Run Fix Script (Easiest)

1. **Upload the fix script** to your VPS:
   ```bash
   scp fix-nginx-cors.sh root@freedomos.vulcantech.co:/root/
   ```

2. **SSH to VPS and run**:
   ```bash
   ssh root@freedomos.vulcantech.co
   chmod +x /root/fix-nginx-cors.sh
   /root/fix-nginx-cors.sh
   ```

### Option 2: Manual Fix

1. **SSH to VPS**:
   ```bash
   ssh root@freedomos.vulcantech.co
   ```

2. **Edit Nginx config**:
   ```bash
   sudo nano /etc/nginx/sites-available/freedomos
   ```

3. **Find and DELETE these lines**:
   ```nginx
   add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
   add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
   add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
   add_header Access-Control-Allow-Credentials "true" always;

   if ($request_method = OPTIONS) {
       return 204;
   }
   ```

4. **Save and exit** (Ctrl+X, Y, Enter)

5. **Test and reload**:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## ✅ Verify Fix

After fixing, test from your local machine:

```bash
curl -H "Origin: http://localhost:5174" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://freedomos.vulcantech.co/health \
     -v 2>&1 | grep -i "access-control"
```

**Should see only ONE** `Access-Control-Allow-Origin: *` header (from backend).

## 🧪 Test Local Frontend

After fixing Nginx:

1. **Start local frontend**:
   ```bash
   cd frontend/packages/web
   pnpm dev
   ```

2. **Open browser**: `http://localhost:5174`

3. **Should work** - No CORS errors! ✅

---

**The fix script will automatically backup and fix your Nginx config.**

# ⚡ Quick CORS Fix - Run on VPS

## 🚀 One-Command Fix

**SSH to your VPS and run:**

```bash
ssh root@freedomos.vulcantech.co
```

**Then run this command:**

```bash
sudo sed -i '/add_header Access-Control-Allow-Origin/d; /add_header Access-Control-Allow-Methods/d; /add_header Access-Control-Allow-Headers/d; /add_header Access-Control-Allow-Credentials/d; /if ($request_method = OPTIONS)/,/^[[:space:]]*}/d' /etc/nginx/sites-available/freedomos && sudo nginx -t && sudo systemctl reload nginx && echo "✅ CORS headers removed from Nginx"
```

## ✅ Done!

After running this command:
- ✅ CORS headers removed from Nginx
- ✅ Backend handles all CORS (including localhost:5174)
- ✅ Local frontend will work

## 🧪 Test

Refresh your local frontend (`http://localhost:5174`) - CORS errors should be gone!

---

**Or use the fix script**: Upload `fix-nginx-cors.sh` to VPS and run it.

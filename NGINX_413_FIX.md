# Fix 413 Request Entity Too Large Error

## Problem

When uploading APK files, you're getting a `413 Request Entity Too Large` error from nginx. This happens because nginx's default `client_max_body_size` is 1MB, which is too small for APK files (typically 10-100MB+).

## Solution

Increase the `client_max_body_size` limit in your nginx configuration.

## Steps to Fix

### 1. SSH into your VPS

```bash
ssh root@freedomos.vulcantech.co
# or
ssh root@your-vps-ip
```

### 2. Edit Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

### 3. Add `client_max_body_size` Directive

Add the following line **inside the `server` block** (preferably at the top, right after the `server_name` line):

```nginx
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    
    # Allow large file uploads (500MB for APKs)
    client_max_body_size 500M;
    
    # ... rest of your configuration
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Or if you have SSL configured:**

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name freedomos.vulcantech.co;
    
    # SSL configuration...
    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    # Allow large file uploads (500MB for APKs)
    client_max_body_size 500M;
    
    # ... rest of your configuration
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Test Nginx Configuration

```bash
sudo nginx -t
```

You should see:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 5. Reload Nginx

```bash
sudo systemctl reload nginx
```

### 6. Verify the Fix

Try uploading an APK again. The 413 error should be resolved.

## Alternative: Set Global Limit

If you want to set this limit globally for all sites, edit the main nginx config:

```bash
sudo nano /etc/nginx/nginx.conf
```

Add inside the `http` block:

```nginx
http {
    # ... other settings
    
    # Allow large file uploads globally
    client_max_body_size 500M;
    
    # ... rest of configuration
}
```

Then reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Recommended Size Limits

- **100M**: For small APKs (most apps)
- **500M**: For large APKs (games, complex apps) - **Recommended**
- **1G**: For very large files (if needed)

## Quick One-Liner Fix

If you want to quickly add the directive without manually editing:

```bash
# Backup config first
sudo cp /etc/nginx/sites-available/freedomos /etc/nginx/sites-available/freedomos.backup

# Add client_max_body_size after server_name line
sudo sed -i '/server_name/a\    client_max_body_size 500M;' /etc/nginx/sites-available/freedomos

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

## Verify Current Configuration

Check if the setting is already there:

```bash
grep -i "client_max_body_size" /etc/nginx/sites-available/freedomos
```

If nothing is returned, the setting is not configured.

## Troubleshooting

### Still Getting 413 Error?

1. **Check if the directive was added correctly:**
   ```bash
   sudo grep -A 5 "server_name" /etc/nginx/sites-available/freedomos
   ```

2. **Check nginx error logs:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Verify nginx reloaded:**
   ```bash
   sudo systemctl status nginx
   ```

4. **Try restarting nginx instead of reload:**
   ```bash
   sudo systemctl restart nginx
   ```

### Check Backend Limits Too

Make sure your FastAPI backend also allows large uploads. Check `backend/py-service/app/routes/apks.py` - it should handle large files, but verify there are no size limits set there.

## Complete Example Configuration

Here's a complete example of what your nginx config should look like:

```nginx
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    
    # Allow large file uploads (500MB)
    client_max_body_size 500M;
    
    # Increase timeouts for large uploads
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase buffer sizes for large uploads
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
}
```

## Summary

1. ✅ Edit `/etc/nginx/sites-available/freedomos`
2. ✅ Add `client_max_body_size 500M;` inside the `server` block
3. ✅ Test: `sudo nginx -t`
4. ✅ Reload: `sudo systemctl reload nginx`
5. ✅ Try uploading APK again

The 413 error should now be resolved! 🎉

# Domain Update Instructions - vulcantech.tech

## Domain Configuration

The following domains are configured:

- **`vulcantech.tech`** - Main domain for email service (e.g., howie@vulcantech.tech)
- **`backend.vulcantech.tech`** - Backend API (handles email, drive, and all backend services)
- **`frontend.vulcantech.tech`** - Frontend web app and file downloads

## Files Updated

The following files have been updated with the new domains:

1. ✅ `docker-compose.yml` - Environment variables
2. ✅ `docker/nginx-site.conf` - Nginx server blocks
3. ✅ `backend/py-service/app/config.py` - Backend configuration

## What to Update on Your Server

### Step 1: Update Files on Server

SSH into your VPS and navigate to the project directory:

```bash
cd ~/graohen_os
```

#### Option A: Pull Latest Changes (if using Git)

```bash
git pull origin main
# or
git pull origin master
```

#### Option B: Manual Update

If you need to manually update files, edit these files on the server:

**1. Update `docker-compose.yml`:**
```bash
nano docker-compose.yml
```

Update these environment variables:
```yaml
- FRONTEND_DOMAIN=frontend.vulcantech.tech
- BACKEND_DOMAIN=backend.vulcantech.tech
- EMAIL_DOMAIN=vulcantech.tech
- DRIVE_DOMAIN=backend.vulcantech.tech
- API_BASE_URL=https://backend.vulcantech.tech
- EXTERNAL_HTTPS_BASE_URL=https://vulcantech.tech
- CORS_ORIGINS=https://frontend.vulcantech.tech,https://backend.vulcantech.tech,https://vulcantech.tech
- ALLOWED_HOSTS=frontend.vulcantech.tech,backend.vulcantech.tech,vulcantech.tech,localhost,127.0.0.1
```

**2. Update `docker/nginx-site.conf`:**
```bash
nano docker/nginx-site.conf
```

Update all `server_name` directives:
- `frontend.fxmail.ai` → `frontend.vulcantech.tech`
- `backend.fxmail.ai` → `backend.vulcantech.tech`
- `fxmail.ai` → `vulcantech.tech`
- `drive.fxmail.ai` → `backend.vulcantech.tech` (or remove if not needed)

**3. Update `.env` file (if exists):**
```bash
nano .env
```

Update these variables:
```bash
FRONTEND_DOMAIN=frontend.vulcantech.tech
BACKEND_DOMAIN=backend.vulcantech.tech
EMAIL_DOMAIN=vulcantech.tech
DRIVE_DOMAIN=backend.vulcantech.tech
API_BASE_URL=https://backend.vulcantech.tech
EXTERNAL_HTTPS_BASE_URL=https://vulcantech.tech
CORS_ORIGINS=https://frontend.vulcantech.tech,https://backend.vulcantech.tech,https://vulcantech.tech
ALLOWED_HOSTS=frontend.vulcantech.tech,backend.vulcantech.tech,vulcantech.tech,localhost,127.0.0.1
```

### Step 2: Update Cloudflare DNS

Go to Cloudflare Dashboard → DNS and update/add these A records:

1. **Frontend:**
   - Type: A
   - Name: `frontend`
   - Content: `YOUR_SERVER_IP`
   - Proxy: ✅ Proxied (Orange Cloud)
   - TTL: Auto

2. **Backend:**
   - Type: A
   - Name: `backend`
   - Content: `YOUR_SERVER_IP`
   - Proxy: ✅ Proxied (Orange Cloud)
   - TTL: Auto

3. **Main Domain (Email):**
   - Type: A
   - Name: `@` (or leave blank)
   - Content: `YOUR_SERVER_IP`
   - Proxy: ✅ Proxied (Orange Cloud)
   - TTL: Auto

**Remove old `drive` subdomain** if it exists (drive is now handled by backend.vulcantech.tech)

### Step 3: Update Cloudflare SSL/TLS Settings

1. Go to Cloudflare Dashboard → SSL/TLS
2. Set encryption mode to **"Full"** (not "Flexible")
3. This ensures Cloudflare connects to your origin via HTTPS

### Step 4: Rebuild and Restart Docker Container

After updating files, rebuild and restart:

```bash
# Stop current container
docker-compose down

# Rebuild with new configuration
docker-compose build --no-cache

# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Step 5: Verify Configuration

Test that everything works:

```bash
# Check container is running
docker ps

# Test backend health
curl http://localhost:8000/health

# Test frontend (from server)
curl -I http://localhost

# Test from outside (replace with your domain)
curl -I https://frontend.vulcantech.tech
curl https://backend.vulcantech.tech/health
curl https://vulcantech.tech/health
```

### Step 6: Verify DNS Propagation

Wait 5-15 minutes, then verify DNS:

```bash
dig frontend.vulcantech.tech
dig backend.vulcantech.tech
dig vulcantech.tech

# All should return your server IP
```

## Quick Update Script

You can use this script to quickly update domains on the server:

```bash
#!/bin/bash
# Run this on your VPS in the project directory

# Update docker-compose.yml
sed -i 's/fxmail\.ai/vulcantech.tech/g' docker-compose.yml
sed -i 's/drive\.fxmail\.ai/backend.vulcantech.tech/g' docker-compose.yml

# Update nginx config
sed -i 's/fxmail\.ai/vulcantech.tech/g' docker/nginx-site.conf
sed -i 's/drive\.fxmail\.ai/backend.vulcantech.tech/g' docker/nginx-site.conf

# Update .env if exists
if [ -f .env ]; then
    sed -i 's/fxmail\.ai/vulcantech.tech/g' .env
    sed -i 's/drive\.fxmail\.ai/backend.vulcantech.tech/g' .env
fi

echo "✅ Domain references updated"
echo "Now rebuild: docker-compose down && docker-compose build --no-cache && docker-compose up -d"
```

## Domain Structure Summary

| Domain | Purpose | Handles |
|--------|---------|---------|
| `vulcantech.tech` | Main domain | Email service (howie@vulcantech.tech) |
| `backend.vulcantech.tech` | Backend API | Email API, Drive API, all backend services |
| `frontend.vulcantech.tech` | Frontend | Web app, downloads (exe files), static files |

## Troubleshooting

### If domains don't work after update:

1. **Check DNS propagation:**
   ```bash
   dig frontend.vulcantech.tech +short
   ```

2. **Check Cloudflare proxy status:**
   - Make sure orange cloud is enabled
   - SSL/TLS mode is "Full"

3. **Check firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

4. **Check container logs:**
   ```bash
   docker logs flashdash -f
   ```

5. **Test nginx config:**
   ```bash
   docker exec flashdash nginx -t
   ```

## Notes

- The `drive` subdomain is no longer needed - drive functionality is handled by `backend.vulcantech.tech`
- Email addresses will be in the format: `username@vulcantech.tech`
- All backend services (email, drive, API) are accessible via `backend.vulcantech.tech`
- Frontend and downloads are accessible via `frontend.vulcantech.tech`

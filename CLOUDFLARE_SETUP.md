# Cloudflare Domain Setup Guide

This guide explains how to set up `fxmail.ai` domain on Cloudflare with subdomains for FlashDash.

## Domain Structure

- **fxmail.ai** - Main domain (for email server - not part of FlashDash)
- **frontend.fxmail.ai** - Frontend web application
- **backend.fxmail.ai** - Backend API server

## Prerequisites

1. Domain `fxmail.ai` registered and managed by Cloudflare
2. Cloudflare account with DNS access
3. Server with public IP address
4. Docker and Docker Compose installed on server

## Step 1: Add DNS Records in Cloudflare

### 1.1 Login to Cloudflare

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain `fxmail.ai`

### 1.2 Add A Records

Navigate to **DNS** → **Records** and add the following records:

#### Frontend Subdomain
```
Type: A
Name: frontend
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

#### Backend Subdomain
```
Type: A
Name: backend
Content: YOUR_SERVER_IP
Proxy: ✅ Proxied (Orange Cloud)
TTL: Auto
```

**Note**: Replace `YOUR_SERVER_IP` with your actual server's public IP address.

### 1.3 Verify DNS Records

After adding records, verify they're working:

```bash
# Check frontend subdomain
dig frontend.fxmail.ai

# Check backend subdomain
dig backend.fxmail.ai
```

Both should resolve to your server's IP address.

## Step 2: Configure SSL/TLS in Cloudflare

### 2.1 SSL/TLS Settings

1. Go to **SSL/TLS** → **Overview**
2. Set encryption mode to **Full (strict)**
   - This ensures end-to-end encryption between Cloudflare and your server

### 2.2 Origin Certificates (Optional but Recommended)

For better security, you can use Cloudflare Origin Certificates:

1. Go to **SSL/TLS** → **Origin Server**
2. Click **Create Certificate**
3. Select:
   - Private key type: RSA (2048)
   - Hostnames: 
     - `frontend.fxmail.ai`
     - `backend.fxmail.ai`
     - `*.fxmail.ai` (wildcard)
4. Click **Create**
5. Save the **Origin Certificate** and **Private Key**

## Step 3: Update Docker Configuration

### 3.1 Update Environment Variables

Update `docker-compose.yml` to include domain configuration:

```yaml
environment:
  - FRONTEND_DOMAIN=frontend.fxmail.ai
  - BACKEND_DOMAIN=backend.fxmail.ai
  - API_BASE_URL=https://backend.fxmail.ai
```

### 3.2 Update Frontend Build

The frontend needs to know the backend URL. Set this during build:

```bash
VITE_API_BASE_URL=https://backend.fxmail.ai pnpm build
```

Or add to `.env.production`:

```env
VITE_API_BASE_URL=https://backend.fxmail.ai
```

## Step 4: Configure Nginx for SSL (If Using Origin Certificates)

If you're using Cloudflare Origin Certificates, update the Dockerfile to include SSL configuration.

### 4.1 Update nginx-site.conf

Add SSL server blocks for HTTPS:

```nginx
# Frontend HTTPS
server {
    listen 443 ssl http2;
    server_name frontend.fxmail.ai;
    
    ssl_certificate /etc/nginx/ssl/origin.crt;
    ssl_certificate_key /etc/nginx/ssl/origin.key;
    
    # ... rest of frontend config
}

# Backend HTTPS
server {
    listen 443 ssl http2;
    server_name backend.fxmail.ai;
    
    ssl_certificate /etc/nginx/ssl/origin.crt;
    ssl_certificate_key /etc/nginx/ssl/origin.key;
    
    # ... rest of backend config
}
```

## Step 5: Firewall Configuration

Ensure your server firewall allows HTTP/HTTPS traffic:

```bash
# UFW (Ubuntu)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Or iptables
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## Step 6: Deploy and Test

### 6.1 Rebuild Docker Container

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 6.2 Test Frontend

```bash
curl -I https://frontend.fxmail.ai
```

Should return HTTP 200.

### 6.3 Test Backend

```bash
curl https://backend.fxmail.ai/health
```

Should return:
```json
{"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

## Step 7: Cloudflare Page Rules (Optional)

### 7.1 Force HTTPS Redirect

Create a page rule:
- URL: `http://frontend.fxmail.ai/*`
- Setting: **Always Use HTTPS**

### 7.2 Cache Static Assets

Create a page rule:
- URL: `frontend.fxmail.ai/assets/*`
- Setting: **Cache Level: Cache Everything**
- Edge Cache TTL: **1 month**

## Step 8: Download URLs Configuration

The download URLs are configured in the frontend:

- Windows: `https://os.fxmail.ai/download/@flashdashdesktop%20Setup%201.0.0.exe`
- macOS: `https://os.fxmail.ai/download/FlashDash-1.0.0.dmg`
- Linux: `https://os.fxmail.ai/download/flashdash-1.0.0.AppImage`

**Note**: These point to `os.fxmail.ai`, which should be a separate subdomain or CDN for serving downloads.

### 8.1 Setup os.fxmail.ai (Optional)

If you want to serve downloads from a subdomain:

1. Add DNS A record:
   ```
   Type: A
   Name: os
   Content: YOUR_SERVER_IP
   Proxy: ✅ Proxied
   ```

2. Add nginx server block for `os.fxmail.ai` pointing to `/app/downloads`

## Troubleshooting

### DNS Not Resolving

1. Check DNS records in Cloudflare
2. Wait for DNS propagation (can take up to 24 hours, usually < 1 hour)
3. Clear DNS cache: `sudo systemd-resolve --flush-caches` (Linux)

### SSL Certificate Errors

1. Ensure Cloudflare SSL mode is set to **Full (strict)**
2. If using Origin Certificates, ensure they're properly installed
3. Check certificate expiration dates

### Backend Not Accessible

1. Check firewall rules
2. Verify backend is running: `docker logs flashdash`
3. Test locally: `curl http://localhost:8000/health`
4. Check nginx logs: `docker exec flashdash tail -f /var/log/nginx/error.log`

### CORS Errors

1. Ensure CORS headers are set in nginx config
2. Check `Access-Control-Allow-Origin` header
3. Verify frontend is using correct backend URL

## Security Recommendations

1. **Enable Cloudflare WAF** (Web Application Firewall)
2. **Set up Rate Limiting** for API endpoints
3. **Enable Bot Fight Mode** to prevent automated attacks
4. **Use Cloudflare Access** for additional authentication (optional)
5. **Enable Always Use HTTPS** via Page Rules
6. **Set up Security Headers** in Cloudflare Transform Rules

## Monitoring

### Cloudflare Analytics

Monitor traffic and performance:
- **Analytics** → **Web Traffic**
- **Analytics** → **Security Events**

### Server Monitoring

Monitor Docker container health:
```bash
docker stats flashdash
docker logs flashdash --tail 100 -f
```

## Quick Reference

### DNS Records Summary
```
frontend.fxmail.ai  → A → YOUR_SERVER_IP (Proxied)
backend.fxmail.ai   → A → YOUR_SERVER_IP (Proxied)
os.fxmail.ai        → A → YOUR_SERVER_IP (Proxied) [Optional]
```

### SSL/TLS Settings
- Encryption mode: **Full (strict)**
- Minimum TLS Version: **1.2**
- Opportunistic Encryption: **On**

### Ports Required
- **80** (HTTP) - Cloudflare will proxy to this
- **443** (HTTPS) - If using Origin Certificates
- **8000** (Backend) - Internal only, not exposed

---

**Status**: Ready for production deployment with Cloudflare.

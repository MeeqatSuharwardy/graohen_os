# Docker Domain Configuration

## Overview

This document explains how to configure Docker deployment with domain-based routing for FlashDash.

## Domain Structure

- **frontend.fxmail.ai** - Serves the React frontend application
- **backend.fxmail.ai** - Serves the FastAPI backend API
- **os.fxmail.ai** - Serves download files (optional, can use frontend subdomain)

## Quick Start

### 1. Update Environment Variables

Create a `.env` file in the project root:

```env
# Domain Configuration
FRONTEND_DOMAIN=frontend.fxmail.ai
BACKEND_DOMAIN=backend.fxmail.ai
API_BASE_URL=https://backend.fxmail.ai

# Backend Configuration
PY_HOST=0.0.0.0
PY_PORT=8000
BUNDLES_DIR=/app/bundles
GRAPHENE_BUNDLES_ROOT=/app/bundles
APK_STORAGE_DIR=/app/apks
DEBUG=false
LOG_LEVEL=INFO
```

### 2. Build Frontend with API URL

Before building the frontend, set the API base URL:

```bash
cd frontend
VITE_API_BASE_URL=https://backend.fxmail.ai pnpm --filter web build
```

Or create `frontend/packages/web/.env.production`:

```env
VITE_API_BASE_URL=https://backend.fxmail.ai
```

### 3. Prepare Download Files

Place the desktop app installers in the `downloads` directory:

```bash
mkdir -p downloads
# Copy your build files
cp path/to/@flashdashdesktop\ Setup\ 1.0.0.exe downloads/
cp path/to/FlashDash-1.0.0.dmg downloads/
cp path/to/flashdash-1.0.0.AppImage downloads/
```

### 4. Start Docker Container

```bash
docker-compose up -d --build
```

## Nginx Configuration

The nginx configuration (`docker/nginx-site.conf`) includes:

### Frontend Server Block
- Listens on port 80
- Server name: `frontend.fxmail.ai`
- Serves static frontend files
- Handles `/flash` route for web flasher
- Serves `/downloads` for desktop app installers

### Backend Server Block
- Listens on port 80
- Server name: `backend.fxmail.ai`
- Proxies all requests to Python backend (port 8000)
- Includes CORS headers for cross-origin requests

### Default Server Block
- Fallback for localhost or other domains
- Useful for local development

## Download URLs

The frontend uses these download URLs:

- **Windows**: `https://os.fxmail.ai/download/@flashdashdesktop%20Setup%201.0.0.exe`
- **macOS**: `https://os.fxmail.ai/download/FlashDash-1.0.0.dmg`
- **Linux**: `https://os.fxmail.ai/download/flashdash-1.0.0.AppImage`

### Option 1: Use Frontend Domain

If you don't want a separate `os.fxmail.ai` subdomain, update the URLs to:

- **Windows**: `https://frontend.fxmail.ai/downloads/@flashdashdesktop%20Setup%201.0.0.exe`
- **macOS**: `https://frontend.fxmail.ai/downloads/FlashDash-1.0.0.dmg`
- **Linux**: `https://frontend.fxmail.ai/downloads/flashdash-1.0.0.AppImage`

Update in:
- `frontend/packages/web/src/pages/Landing.tsx`
- `frontend/packages/web/src/pages/Downloads.tsx`
- `frontend/packages/web/src/pages/Dashboard.tsx`

### Option 2: Setup os.fxmail.ai Subdomain

1. Add DNS A record in Cloudflare:
   ```
   Type: A
   Name: os
   Content: YOUR_SERVER_IP
   Proxy: ✅ Proxied
   ```

2. Add nginx server block for `os.fxmail.ai` (similar to frontend block)

## Testing

### Test Frontend

```bash
# Test locally
curl -H "Host: frontend.fxmail.ai" http://localhost

# Test via domain (after DNS setup)
curl https://frontend.fxmail.ai
```

### Test Backend

```bash
# Test locally
curl -H "Host: backend.fxmail.ai" http://localhost/health

# Test via domain (after DNS setup)
curl https://backend.fxmail.ai/health
```

### Test Downloads

```bash
# Test download endpoint
curl -I https://frontend.fxmail.ai/downloads/@flashdashdesktop%20Setup%201.0.0.exe
```

## Environment Variables Reference

### Docker Compose Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_DOMAIN` | `frontend.fxmail.ai` | Frontend domain name |
| `BACKEND_DOMAIN` | `backend.fxmail.ai` | Backend domain name |
| `API_BASE_URL` | `https://backend.fxmail.ai` | API base URL for frontend |
| `PY_HOST` | `0.0.0.0` | Python backend host |
| `PY_PORT` | `8000` | Python backend port |

### Frontend Build Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://127.0.0.1:17890` | Backend API URL |

## Production Deployment Checklist

- [ ] DNS records configured in Cloudflare
- [ ] SSL/TLS configured (Full strict mode)
- [ ] Frontend built with correct `VITE_API_BASE_URL`
- [ ] Download files placed in `downloads/` directory
- [ ] Environment variables set in `.env` file
- [ ] Docker container built and running
- [ ] Firewall rules configured (ports 80, 443)
- [ ] Health checks passing
- [ ] Frontend accessible at `https://frontend.fxmail.ai`
- [ ] Backend accessible at `https://backend.fxmail.ai`
- [ ] Downloads accessible

## Troubleshooting

### Frontend Can't Connect to Backend

1. Check `VITE_API_BASE_URL` is set correctly
2. Verify backend is accessible: `curl https://backend.fxmail.ai/health`
3. Check browser console for CORS errors
4. Verify nginx CORS headers are set

### Downloads Not Working

1. Check files exist in `downloads/` directory
2. Verify file permissions: `chmod 644 downloads/*`
3. Check nginx autoindex is enabled
4. Test direct URL: `curl -I https://frontend.fxmail.ai/downloads/filename`

### DNS Not Resolving

1. Check DNS records in Cloudflare
2. Wait for propagation (up to 24 hours)
3. Test with `dig frontend.fxmail.ai`
4. Clear local DNS cache

## Security Considerations

1. **HTTPS Only**: Use Cloudflare SSL/TLS (Full strict mode)
2. **CORS**: Properly configured for frontend-backend communication
3. **Rate Limiting**: Configure in Cloudflare
4. **WAF**: Enable Cloudflare Web Application Firewall
5. **Headers**: Security headers configured in nginx

---

**Next Steps**: See [CLOUDFLARE_SETUP.md](./CLOUDFLARE_SETUP.md) for Cloudflare configuration details.

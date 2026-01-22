# VPS Deployment Checklist

## Pre-Deployment

- [ ] Server IP: `138.197.24.229`
- [ ] Domain: `freedomos.vulcantech.co`
- [ ] Email Domain: `vulcantech.tech`
- [ ] Cloudflare DNS configured
- [ ] Cloudflare SSL mode set to "Flexible"

## Step 1: SSH into Server

```bash
ssh root@138.197.24.229
# Password: Dubai123@
```

## Step 2: Run Setup Script

```bash
cd ~/graohen_os
chmod +x VPS_COMPLETE_SETUP.sh
./VPS_COMPLETE_SETUP.sh
```

**OR** use manual setup from `QUICK_VPS_SETUP.md`

## Step 3: Verify Configuration

### 3.1 Check Docker Container

```bash
docker ps | grep flashdash
```

Expected output: Container should be running

### 3.2 Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

### 3.3 Check Port 81 (Frontend)

```bash
curl http://localhost:81/health
```

Expected output: Should return backend health or frontend HTML

### 3.4 Check Nginx Configuration

```bash
nginx -t
systemctl status nginx
```

Expected output: Configuration test passed, nginx running

### 3.5 Check System Nginx Proxy

```bash
curl http://localhost/health
```

Expected output: Should proxy to port 81

## Step 4: Cloudflare DNS Setup

1. **Go to Cloudflare Dashboard**
   - Navigate to DNS → Records

2. **Add A Record:**
   - **Type**: A
   - **Name**: `freedomos`
   - **Content**: `138.197.24.229`
   - **Proxy**: ✅ Proxied (Orange Cloud)
   - **TTL**: Auto

3. **Set SSL/TLS Mode:**
   - Go to SSL/TLS → Overview
   - Set to **"Flexible"** (Cloudflare handles SSL, server uses HTTP)

## Step 5: Test Domain Access

### 5.1 Test HTTP (should redirect or work)

```bash
curl http://freedomos.vulcantech.co/health
```

### 5.2 Test HTTPS (after DNS propagates)

```bash
curl https://freedomos.vulcantech.co/health
```

Expected output:
```json
{"status":"healthy","version":"1.0.0","service":"GrapheneOS Installer API"}
```

## Step 6: Verify All Services

### 6.1 Backend API

```bash
curl https://freedomos.vulcantech.co/api/v1/devices
curl https://freedomos.vulcantech.co/bundles
```

### 6.2 Frontend

Open in browser:
- `https://freedomos.vulcantech.co`
- `https://freedomos.vulcantech.co/flash`

### 6.3 Email Service

```bash
curl -X POST https://freedomos.vulcantech.co/api/v1/emails/create \
  -H "Content-Type: application/json" \
  -d '{"email": "test@vulcantech.tech"}'
```

### 6.4 Drive Service

```bash
curl https://freedomos.vulcantech.co/api/v1/drive/files
```

## Troubleshooting

### Container Not Running

```bash
docker-compose logs
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Port Conflict

```bash
lsof -i :80
lsof -i :81
lsof -i :8000
# Stop conflicting services
```

### Nginx Error

```bash
nginx -t
# Fix errors shown
systemctl reload nginx
```

### Backend Not Responding

```bash
docker logs flashdash -f
docker exec flashdash curl http://localhost:8000/health
```

### Domain Not Working

1. Check DNS propagation:
   ```bash
   dig freedomos.vulcantech.co
   ```

2. Check Cloudflare proxy status (should be proxied)

3. Check SSL/TLS mode (should be "Flexible")

4. Wait for DNS propagation (can take up to 24 hours, usually 5-10 minutes)

## Final Verification

Run the verification script:

```bash
chmod +x VERIFY_VPS_SETUP.sh
./VERIFY_VPS_SETUP.sh
```

## Success Criteria

- [ ] Docker container running
- [ ] Backend responding on port 8000
- [ ] Frontend accessible on port 81
- [ ] Nginx proxy working
- [ ] Domain accessible via HTTPS
- [ ] All API endpoints working
- [ ] Email service functional
- [ ] Drive service functional

## Post-Deployment

- [ ] Monitor logs: `docker-compose logs -f`
- [ ] Set up monitoring/alerting
- [ ] Configure backups
- [ ] Document any custom configurations

---

**Quick Test Commands:**

```bash
# All-in-one test
curl -s https://freedomos.vulcantech.co/health && \
curl -s http://localhost:8000/health && \
curl -s http://localhost:81 && \
echo "✓ All services responding"
```

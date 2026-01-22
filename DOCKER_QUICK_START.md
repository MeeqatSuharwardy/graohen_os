# Docker Quick Start Guide

Complete guide to build, run, and verify the FlashDash Docker deployment.

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- At least 2GB free RAM
- Ports 80 and 8000 available

## Quick Start

### 1. Build and Start

```bash
# Build and start the container
docker-compose up -d --build
```

This will:
- Build the Docker image (backend + frontend)
- Start the container
- Expose ports 80 (frontend) and 8000 (backend)

### 2. Verify Deployment

```bash
# Run comprehensive verification
./docker/verify.sh

# Or quick test
./docker/test-docker.sh
```

### 3. Access the Application

- **Frontend**: http://localhost/
- **Web Flasher**: http://localhost/flash
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Common Commands

### View Logs

```bash
# All logs
docker-compose logs -f

# Backend logs only
docker logs flashdash -f | grep backend

# Last 50 lines
docker logs flashdash --tail 50
```

### Restart Services

```bash
# Restart container
docker-compose restart

# Rebuild and restart
docker-compose up -d --build
```

### Stop Services

```bash
# Stop container
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Check Status

```bash
# Container status
docker ps | grep flashdash

# Container health
docker inspect flashdash | grep -A 5 Health

# Resource usage
docker stats flashdash --no-stream
```

## Troubleshooting

### Container Won't Start

1. **Check logs:**
   ```bash
   docker-compose logs
   ```

2. **Check if ports are in use:**
   ```bash
   # Linux/Mac
   lsof -i :80
   lsof -i :8000
   
   # Or use netstat
   netstat -tuln | grep -E ':(80|8000)'
   ```

3. **Rebuild from scratch:**
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Backend Not Responding

1. **Check backend logs:**
   ```bash
   docker exec flashdash tail -f /app/logs/backend.log
   ```

2. **Test backend directly:**
   ```bash
   docker exec flashdash curl http://localhost:8000/health
   ```

3. **Check if Python process is running:**
   ```bash
   docker exec flashdash ps aux | grep uvicorn
   ```

### Frontend Not Loading

1. **Check nginx logs:**
   ```bash
   docker exec flashdash tail -f /var/log/nginx/error.log
   ```

2. **Verify frontend files exist:**
   ```bash
   docker exec flashdash ls -la /app/frontend/web
   docker exec flashdash ls -la /app/frontend/web-flasher
   ```

3. **Test nginx configuration:**
   ```bash
   docker exec flashdash nginx -t
   ```

4. **Restart nginx:**
   ```bash
   docker exec flashdash nginx -s reload
   ```

### Build Fails

1. **Check build logs:**
   ```bash
   docker-compose build --progress=plain 2>&1 | tee build.log
   ```

2. **Common issues:**
   - Missing dependencies in package.json
   - Frontend build errors
   - Python dependency conflicts

3. **Clean build:**
   ```bash
   docker-compose down
   docker system prune -a
   docker-compose build --no-cache
   ```

## Verification Checklist

After deployment, verify:

- [ ] Container is running: `docker ps | grep flashdash`
- [ ] Backend health: `curl http://localhost:8000/health`
- [ ] Frontend loads: `curl http://localhost/`
- [ ] Web flasher loads: `curl http://localhost/flash`
- [ ] API proxy works: `curl http://localhost/api/health`
- [ ] No errors in logs: `docker logs flashdash | grep -i error`

## Environment Variables

You can customize the deployment by setting environment variables in `docker-compose.yml`:

```yaml
environment:
  - PY_HOST=0.0.0.0
  - PY_PORT=8000
  - BUNDLES_DIR=/app/bundles
  - DEBUG=false
  - LOG_LEVEL=INFO
```

## Volumes

The following directories are mounted:

- `./bundles` → `/app/bundles` - GrapheneOS build bundles
- `./downloads` → `/app/downloads` - Desktop app downloads
- `./logs` → `/app/logs` - Application logs

## Production Deployment

For production:

1. **Use environment file:**
   ```bash
   docker-compose --env-file .env.prod up -d
   ```

2. **Set up reverse proxy** (nginx, Traefik) with SSL

3. **Configure resource limits:**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

4. **Set up log rotation**

5. **Enable monitoring** (Prometheus, Grafana)

## Support

For detailed information:
- **Docker Deployment**: See `DOCKER_DEPLOYMENT.md`
- **API Documentation**: See `API_DOCUMENTATION.md`
- **Verification**: Run `./docker/verify.sh`

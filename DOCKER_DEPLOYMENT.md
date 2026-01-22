# Docker Deployment Guide

This guide explains how to deploy FlashDash using Docker.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 2GB RAM
- USB device access (for Linux hosts)

## Quick Start

1. **Build and start the container:**
   ```bash
   docker-compose up -d --build
   ```

2. **Verify deployment:**
   ```bash
   ./docker/verify.sh
   ```

3. **Access the application:**
   - Frontend: http://localhost/
   - Web Flasher: http://localhost/flash
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Building

### Build the Docker image:
```bash
docker build -t flashdash:latest .
```

### Build with docker-compose:
```bash
docker-compose build
```

## Running

### Using docker-compose (recommended):
```bash
docker-compose up -d
```

### Using docker directly:
```bash
docker run -d \
  --name flashdash \
  -p 80:80 \
  -p 8000:8000 \
  -v $(pwd)/bundles:/app/bundles \
  -v $(pwd)/downloads:/app/downloads \
  --privileged \
  flashdash:latest
```

## Volumes

The following directories are mounted as volumes:

- `./bundles` → `/app/bundles` - GrapheneOS build bundles
- `./downloads` → `/app/downloads` - Desktop app downloads
- `./logs` → `/app/logs` - Application logs

## USB Device Access (Linux)

For USB device access on Linux hosts, the container runs with `--privileged` flag and mounts `/dev/bus/usb`.

**Note:** USB device access only works on Linux hosts. On macOS/Windows, use the desktop app instead.

## Environment Variables

You can override environment variables in `docker-compose.yml`:

```yaml
environment:
  - PY_HOST=0.0.0.0
  - PY_PORT=8000
  - BUNDLES_DIR=/app/bundles
  - DEBUG=false
  - LOG_LEVEL=INFO
```

## Health Checks

The container includes a health check that verifies the backend is responding:

```bash
docker ps  # Check health status
```

## Logs

View container logs:
```bash
docker-compose logs -f
```

Or for a specific service:
```bash
docker logs flashdash -f
```

## Stopping

```bash
docker-compose down
```

## Troubleshooting

### Container won't start
1. Check logs: `docker-compose logs`
2. Verify ports 80 and 8000 are not in use
3. Check disk space: `df -h`

### Backend not responding
1. Check backend logs: `docker logs flashdash | grep backend`
2. Verify Python dependencies installed correctly
3. Check if ADB/Fastboot are available in container: `docker exec flashdash which adb`

### Frontend not loading
1. Check nginx logs: `docker exec flashdash tail -f /var/log/nginx/error.log`
2. Verify frontend build exists: `docker exec flashdash ls -la /app/frontend/web`
3. Check nginx configuration: `docker exec flashdash nginx -t`

### USB devices not detected
1. Verify container has privileged access: `docker inspect flashdash | grep Privileged`
2. Check USB device permissions on host
3. Verify `/dev/bus/usb` is mounted: `docker exec flashdash ls -la /dev/bus/usb`

## Production Deployment

For production, consider:

1. **Use a reverse proxy** (nginx, Traefik) in front of the container
2. **Enable SSL/TLS** with Let's Encrypt
3. **Set up log rotation** for container logs
4. **Use Docker secrets** for sensitive configuration
5. **Configure resource limits** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

## Updating

To update the application:

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Verification Script

After deployment, run the verification script:

```bash
./docker/verify.sh
```

This checks:
- Container is running
- Backend health endpoint
- Frontend accessibility
- Web flasher accessibility
- API endpoints

## Architecture

The Docker container runs:

1. **Nginx** (port 80) - Serves frontend and proxies API requests
2. **Python Backend** (port 8000) - FastAPI application

Both services are started by the `start.sh` script.

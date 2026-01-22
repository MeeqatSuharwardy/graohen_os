# Docker Scripts

This directory contains scripts and configuration files for Docker deployment.

## Files

- **nginx.conf**: Main Nginx configuration
- **nginx-site.conf**: Site-specific Nginx configuration for routing
- **start.sh**: Container startup script (starts nginx and backend)
- **verify.sh**: Comprehensive verification script (checks all services)
- **test-docker.sh**: Quick test script (basic connectivity checks)

## Usage

### Start Container
```bash
docker-compose up -d --build
```

### Verify Deployment
```bash
./docker/verify.sh
```

### Quick Test
```bash
./docker/test-docker.sh
```

## Script Details

### start.sh
- Starts Nginx web server
- Starts Python backend (uvicorn)
- Monitors both processes
- Provides health checks
- Logs to /app/logs/backend.log

### verify.sh
- Checks Docker installation
- Verifies container is running
- Tests all endpoints
- Checks container health
- Reviews logs for errors
- Provides detailed status report

### test-docker.sh
- Quick connectivity test
- Tests main endpoints
- Fast verification for development

## Troubleshooting

If scripts fail:
1. Ensure scripts are executable: `chmod +x docker/*.sh`
2. Check Docker is running: `docker ps`
3. Review container logs: `docker logs flashdash`

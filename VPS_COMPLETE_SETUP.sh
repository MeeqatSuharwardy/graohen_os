#!/bin/bash
# Complete VPS Setup Script for freedomos.vulcantech.co
# Run this script on your VPS: ssh root@138.197.24.229
# Password: Dubai123@

set -e

echo "=========================================="
echo "FlashDash VPS Complete Setup"
echo "Server: 138.197.24.229"
echo "Domain: freedomos.vulcantech.co"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# Install Docker if not installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
fi

# Install Docker Compose if not installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Installing Docker Compose...${NC}"
    apt-get install -y docker-compose-plugin
fi

# Install nginx if not installed
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Installing nginx...${NC}"
    apt-get install -y nginx
fi

# Install curl if not installed
if ! command -v curl &> /dev/null; then
    apt-get install -y curl
fi

# Navigate to project directory
PROJECT_DIR="$HOME/graohen_os"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${YELLOW}Project directory not found. Cloning or creating...${NC}"
    # If git repo, clone it, otherwise create directory
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p bundles downloads logs

# Stop any existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true

# Update docker-compose.yml with production settings
echo -e "${YELLOW}Updating docker-compose.yml for production...${NC}"
cat > docker-compose.yml << 'EOF'
services:
  flashdash:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: https://freedomos.vulcantech.co
    container_name: flashdash
    ports:
      - "81:80"
      - "8000:8000"
    volumes:
      - ./bundles:/app/bundles
      - ./downloads:/app/downloads
      - ./logs:/app/logs
    environment:
      - PY_HOST=0.0.0.0
      - PY_PORT=8000
      - BUNDLES_DIR=/app/bundles
      - GRAPHENE_BUNDLES_ROOT=/app/bundles
      - APK_STORAGE_DIR=/app/apks
      - DEBUG=false
      - LOG_LEVEL=INFO
      - ENVIRONMENT=production
      - FRONTEND_DOMAIN=freedomos.vulcantech.co
      - BACKEND_DOMAIN=freedomos.vulcantech.co
      - EMAIL_DOMAIN=vulcantech.tech
      - DRIVE_DOMAIN=freedomos.vulcantech.co
      - API_BASE_URL=https://freedomos.vulcantech.co
      - EXTERNAL_HTTPS_BASE_URL=https://vulcantech.tech
      - VITE_API_BASE_URL=https://freedomos.vulcantech.co
      - CORS_ORIGINS=*
      - ALLOWED_HOSTS=freedomos.vulcantech.co,vulcantech.tech
    restart: unless-stopped
    devices:
      - /dev/bus/usb:/dev/bus/usb
    privileged: true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
EOF

# Create nginx configuration for freedomos.vulcantech.co
echo -e "${YELLOW}Configuring nginx...${NC}"
cat > /etc/nginx/sites-available/freedomos << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

# HTTPS server - proxies to Docker container on port 81
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    # SSL certificates (commented for Cloudflare SSL)
    # ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # CORS headers
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

    # Proxy to Docker container on port 81
    location / {
        proxy_pass http://127.0.0.1:81;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos

# Remove default site if it conflicts
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
echo -e "${YELLOW}Testing nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration has errors${NC}"
    exit 1
fi

# Reload nginx
systemctl reload nginx
echo -e "${GREEN}✓ Nginx reloaded${NC}"

# Configure firewall
echo -e "${YELLOW}Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 81/tcp
    ufw allow 8000/tcp
    ufw --force enable
    echo -e "${GREEN}✓ Firewall configured${NC}"
fi

# Build and start Docker container
echo -e "${YELLOW}Building Docker container...${NC}"
docker-compose build --no-cache

echo -e "${YELLOW}Starting Docker container...${NC}"
docker-compose up -d

# Wait for services to start
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check Docker container status
echo -e "${YELLOW}Checking Docker container...${NC}"
if docker ps | grep -q flashdash; then
    echo -e "${GREEN}✓ Docker container is running${NC}"
else
    echo -e "${RED}✗ Docker container is not running${NC}"
    docker-compose logs
    exit 1
fi

# Test backend health
echo -e "${YELLOW}Testing backend health...${NC}"
for i in {1..10}; do
    if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is responding${NC}"
        break
    fi
    echo "Waiting for backend... ($i/10)"
    sleep 2
done

# Test port 81
echo -e "${YELLOW}Testing port 81...${NC}"
if curl -f -s http://localhost:81/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Port 81 is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Port 81 not responding (may need more time)${NC}"
fi

# Test nginx proxy
echo -e "${YELLOW}Testing nginx proxy...${NC}"
if curl -f -s http://localhost/health > /dev/null 2>&1 || curl -f -s https://freedomos.vulcantech.co/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx proxy is working${NC}"
else
    echo -e "${YELLOW}⚠ Nginx proxy test skipped (domain may not be configured yet)${NC}"
fi

# Display status
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "  - Backend API: http://localhost:8000"
echo "  - Frontend: http://localhost:81"
echo "  - Domain: https://freedomos.vulcantech.co"
echo ""
echo "Check status:"
echo "  docker ps"
echo "  docker-compose logs -f"
echo ""
echo "Test endpoints:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:81/health"
echo "  curl https://freedomos.vulcantech.co/health"
echo ""
echo "=========================================="

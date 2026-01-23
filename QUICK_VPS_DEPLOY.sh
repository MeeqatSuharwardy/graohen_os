#!/bin/bash
# Quick VPS Backend Deployment Script
# Run this script on your Ubuntu VPS as root

set -e

echo "=========================================="
echo "FlashDash Backend VPS Deployment"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Update System
echo -e "${YELLOW}Step 1: Updating system...${NC}"
apt update && apt upgrade -y

# Step 2: Install Required Software
echo -e "${YELLOW}Step 2: Installing required software...${NC}"
apt install -y python3.11 python3.11-venv python3-pip nginx android-tools-adb android-tools-fastboot git

# Step 3: Create Directory
echo -e "${YELLOW}Step 3: Creating directory structure...${NC}"
mkdir -p /root/graohen_os
mkdir -p /root/graohen_os/bundles
mkdir -p /root/graohen_os/apks
mkdir -p /root/graohen_os/logs

echo -e "${GREEN}✓ Directories created${NC}"

# Step 4: Clone/Deploy Code
echo -e "${YELLOW}Step 4: Deploying code...${NC}"
echo "Please choose deployment method:"
echo "1) Clone from Git repository"
echo "2) Upload code manually (skip this step)"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    read -p "Enter Git repository URL: " repo_url
    cd /root
    git clone "$repo_url" graohen_os
    echo -e "${GREEN}✓ Code cloned${NC}"
else
    echo "Please upload your code to /root/graohen_os manually"
    read -p "Press Enter when code is uploaded..."
fi

# Step 5: Setup Backend
echo -e "${YELLOW}Step 5: Setting up backend...${NC}"
cd /root/graohen_os/backend/py-service

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Backend dependencies installed${NC}"

# Step 6: Create .env file
echo -e "${YELLOW}Step 6: Creating .env file...${NC}"
if [ -f "env.example" ]; then
    cp env.example .env
    echo -e "${GREEN}✓ .env file created from env.example${NC}"
    echo -e "${YELLOW}⚠ Please edit /root/graohen_os/backend/py-service/.env with your configuration${NC}"
else
    cat > .env << EOF
PY_HOST=127.0.0.1
PY_PORT=8000
DEBUG=false
ENVIRONMENT=production
ALLOWED_HOSTS=freedomos.vulcantech.co,localhost,127.0.0.1
CORS_ORIGINS=https://freedomos.vulcantech.co
API_BASE_URL=https://freedomos.vulcantech.co
EXTERNAL_HTTPS_BASE_URL=https://freedomos.vulcantech.co
ADB_PATH=/usr/bin/adb
FASTBOOT_PATH=/usr/bin/fastboot
GRAPHENE_BUNDLES_ROOT=/root/graohen_os/bundles
APK_STORAGE_DIR=/root/graohen_os/apks
LOG_DIR=/root/graohen_os/logs
SECRET_KEY=change-this-secret-key-in-production
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Step 7: Create Systemd Service
echo -e "${YELLOW}Step 7: Creating systemd service...${NC}"
cat > /etc/systemd/system/flashdash-backend.service << 'EOF'
[Unit]
Description=FlashDash Backend API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/graohen_os/backend/py-service
Environment="PATH=/root/graohen_os/backend/py-service/venv/bin"
ExecStart=/root/graohen_os/backend/py-service/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=flashdash-backend

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable flashdash-backend
systemctl start flashdash-backend

echo -e "${GREEN}✓ Systemd service created and started${NC}"

# Step 8: Configure Nginx
echo -e "${YELLOW}Step 8: Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/freedomos << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    add_header Access-Control-Allow-Origin "https://freedomos.vulcantech.co" always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    add_header Access-Control-Allow-Credentials "true" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
EOF

ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

echo -e "${GREEN}✓ Nginx configured${NC}"

# Step 9: Setup SSL
echo -e "${YELLOW}Step 9: Setting up SSL...${NC}"
apt install -y certbot python3-certbot-nginx

echo -e "${YELLOW}⚠ Running certbot for SSL certificate...${NC}"
echo "You will need to:"
echo "1. Enter your email address"
echo "2. Agree to terms"
echo "3. Choose to redirect HTTP to HTTPS (recommended: Yes)"
echo ""
read -p "Press Enter to continue with certbot..."

certbot --nginx -d freedomos.vulcantech.co

# Step 10: Configure Firewall
echo -e "${YELLOW}Step 10: Configuring firewall...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo -e "${GREEN}✓ Firewall configured${NC}"

# Step 11: Reload Nginx
echo -e "${YELLOW}Step 11: Reloading Nginx...${NC}"
nginx -t && systemctl reload nginx

echo -e "${GREEN}✓ Nginx reloaded${NC}"

# Final Status
echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Backend Status:"
systemctl status flashdash-backend --no-pager -l | head -10
echo ""
echo "Test your backend:"
echo "  curl https://freedomos.vulcantech.co/health"
echo ""
echo "API Documentation:"
echo "  https://freedomos.vulcantech.co/docs"
echo ""
echo "View logs:"
echo "  sudo journalctl -u flashdash-backend -f"
echo ""

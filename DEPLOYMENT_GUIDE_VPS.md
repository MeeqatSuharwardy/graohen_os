# Complete Deployment Guide: VPS Production Setup

This comprehensive guide covers deploying the GrapheneOS Installer backend with Email and Drive services on a VPS (Digital Ocean, AWS, etc.) with proper domain configuration, security, and testing.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [VPS Initial Setup](#vps-initial-setup)
3. [System Dependencies](#system-dependencies)
4. [Project Installation](#project-installation)
5. [Email Domain Configuration (fxmail.ai)](#email-domain-configuration-fxmailai)
6. [Drive Upload Domain Configuration](#drive-upload-domain-configuration)
7. [Environment Configuration](#environment-configuration)
8. [Database & Redis Setup](#database--redis-setup)
9. [Security & Firewall Configuration](#security--firewall-configuration)
10. [Service Configuration (systemd)](#service-configuration-systemd)
11. [Testing APIs & Security](#testing-apis--security)
12. [Monitoring & Maintenance](#monitoring--maintenance)
13. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- VPS with Ubuntu 22.04+ (2GB+ RAM, 2+ CPU cores recommended)
- Domain name configured (fxmail.ai for email service)
- DNS access for domain configuration
- SSH access to VPS
- Root or sudo access

---

## VPS Initial Setup

### 1. Connect to VPS

```bash
ssh root@YOUR_VPS_IP
```

### 2. Update System

```bash
apt update && apt upgrade -y
apt install -y curl wget git ufw fail2ban
```

### 3. Create Project Directory

```bash
# Project will be located at /root/graohen_os
mkdir -p /root/graohen_os
cd /root/graohen_os
```

---

## System Dependencies

### 1. Install Python 3.10

```bash
# Install Python 3.10
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# Verify
python3.10 --version  # Should show Python 3.10.x
```

### 2. Install ADB and Fastboot

```bash
# Download latest platform-tools
cd /tmp
wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
mv platform-tools /opt/android-platform-tools

# Create symlinks
ln -sf /opt/android-platform-tools/adb /usr/local/bin/adb
ln -sf /opt/android-platform-tools/fastboot /usr/local/bin/fastboot
chmod +x /usr/local/bin/adb /usr/local/bin/fastboot

# Verify
adb version
fastboot --version
```

### 3. Install PostgreSQL

```bash
apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE grapheneos_db;
CREATE USER grapheneos_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE grapheneos_db TO grapheneos_user;
ALTER USER grapheneos_user CREATEDB;
\q
EOF
```

### 4. Install Redis

```bash
apt install -y redis-server

# Configure Redis
sed -i 's/^supervised no/supervised systemd/' /etc/redis/redis.conf
sed -i 's/^bind 127.0.0.1/bind 127.0.0.1/' /etc/redis/redis.conf

# Start and enable Redis
systemctl start redis-server
systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return PONG
```

---

## Project Installation

### 1. Clone or Upload Project

**Option A: Git Clone**

```bash
cd /root/graohen_os
git clone YOUR_REPOSITORY_URL .
```

**Option B: Upload via SCP (from local machine)**

```bash
# From your local machine
scp -r /path/to/graohen_os/* root@YOUR_VPS_IP:/root/graohen_os/
```

### 2. Setup Python Virtual Environment

```bash
cd /root/graohen_os/backend/py-service
python3.10 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt
```

### 3. Create Required Directories

```bash
mkdir -p /root/graohen_os/backend/py-service/logs
mkdir -p /root/graohen_os/bundles
chmod 755 /root/graohen_os/bundles
```

---

## Email Domain Configuration (fxmail.ai)

### 1. DNS Configuration for fxmail.ai

Configure the following DNS records for your domain:

#### A Record (Main Domain)
```
Type: A
Name: @
Value: YOUR_VPS_IP
TTL: 3600
```

#### A Record (www subdomain)
```
Type: A
Name: www
Value: YOUR_VPS_IP
TTL: 3600
```

#### MX Record (Email Routing - Optional, if using SMTP)
```
Type: MX
Name: @
Priority: 10
Value: mail.fxmail.ai
TTL: 3600
```

#### CNAME Record (Email Subdomain)
```
Type: CNAME
Name: mail
Value: fxmail.ai
TTL: 3600
```

#### SPF Record (Email Authentication)
```
Type: TXT
Name: @
Value: v=spf1 ip4:YOUR_VPS_IP include:_spf.google.com ~all
TTL: 3600
```

#### DKIM Record (Email Authentication)
```
Type: TXT
Name: default._domainkey
Value: [Your DKIM key from email service provider]
TTL: 3600
```

#### DMARC Record (Email Authentication)
```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=none; rua=mailto:admin@fxmail.ai
TTL: 3600
```

### 2. SSL Certificate Setup

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# If using Nginx (recommended)
apt install -y nginx

# Generate SSL certificate
certbot certonly --standalone -d fxmail.ai -d www.fxmail.ai

# Certificates will be stored at:
# /etc/letsencrypt/live/fxmail.ai/fullchain.pem
# /etc/letsencrypt/live/fxmail.ai/privkey.pem
```

### 3. Nginx Configuration for Email Service

Create Nginx configuration:

```bash
cat > /etc/nginx/sites-available/fxmail.ai << 'EOF'
server {
    listen 80;
    server_name fxmail.ai www.fxmail.ai;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name fxmail.ai www.fxmail.ai;

    ssl_certificate /etc/letsencrypt/live/fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fxmail.ai/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to FastAPI backend
    location / {
        proxy_pass http://127.0.0.1:17890;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # File upload size limit (for drive service)
    client_max_body_size 100M;
    
    # Logging
    access_log /var/log/nginx/fxmail.ai.access.log;
    error_log /var/log/nginx/fxmail.ai.error.log;
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/fxmail.ai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t
systemctl reload nginx
```

---

## Drive Upload Domain Configuration

### 1. DNS Configuration for Drive Service

If using a separate subdomain for drive service (e.g., `drive.fxmail.ai`):

#### A Record
```
Type: A
Name: drive
Value: YOUR_VPS_IP
TTL: 3600
```

### 2. Nginx Configuration for Drive Service

```bash
cat > /etc/nginx/sites-available/drive.fxmail.ai << 'EOF'
server {
    listen 80;
    server_name drive.fxmail.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name drive.fxmail.ai;

    ssl_certificate /etc/letsencrypt/live/fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fxmail.ai/privkey.pem;
    
    # SSL Configuration (same as main domain)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Large file upload support (100MB)
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    
    # Timeouts for large uploads
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:17890;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    access_log /var/log/nginx/drive.fxmail.ai.access.log;
    error_log /var/log/nginx/drive.fxmail.ai.error.log;
}
EOF

# Enable and reload
ln -sf /etc/nginx/sites-available/drive.fxmail.ai /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 3. SSL Certificate for Drive Subdomain

```bash
certbot certonly --standalone -d drive.fxmail.ai
# Or use wildcard certificate for *.fxmail.ai
```

---

## Environment Configuration

### 1. Create .env File

```bash
cd /root/graohen_os/backend/py-service
cat > .env << 'EOF'
# Application
APP_NAME=GrapheneOS Installer API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# Server
PY_HOST=0.0.0.0
PY_PORT=17890

# API
API_V1_PREFIX=/api/v1
ALLOWED_HOSTS=fxmail.ai,www.fxmail.ai,drive.fxmail.ai,YOUR_VPS_IP

# Database
DATABASE_URL=postgresql+asyncpg://grapheneos_user:CHANGE_THIS_PASSWORD@localhost:5432/grapheneos_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=False

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=10

# Security - CHANGE THESE IN PRODUCTION!
SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_STRING_USE_openssl_rand_hex_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS - Add your frontend domains
CORS_ORIGINS=https://fxmail.ai,https://www.fxmail.ai,https://drive.fxmail.ai

# Email Configuration
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# AWS (Optional - for S3 file storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
AWS_S3_BUCKET=

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_DIR=/root/graohen_os/backend/py-service/logs

# GrapheneOS / Device Flashing
ADB_PATH=/usr/local/bin/adb
FASTBOOT_PATH=/usr/local/bin/fastboot
GRAPHENE_SOURCE_ROOT=
GRAPHENE_BUNDLES_ROOT=/root/graohen_os/bundles
SUPPORTED_CODENAMES=cheetah,panther,raven,oriole,husky,shiba,akita,felix,tangorpro,lynx,bluejay,barbet,redfin

# Safety
DRY_RUN_DEFAULT=True
SCRIPT_TIMEOUT_SEC=1800
ALLOW_ADVANCED_FASTBOOT=False
REQUIRE_TYPED_CONFIRMATION=False

# Build
BUILD_ENABLE=False
BUILD_OUTPUT_DIR=
BUILD_TIMEOUT_SEC=14400
EOF

# Secure the .env file
chmod 600 .env
```

### 2. Generate Secure Secret Key

```bash
# Generate a secure secret key
openssl rand -hex 32

# Add it to .env file
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$(openssl rand -hex 32)/" .env
```

---

## Database & Redis Setup

### 1. Run Database Migrations

```bash
cd /root/graohen_os/backend/py-service
source venv/bin/activate

# Initialize Alembic (if not already done)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 2. Verify Redis Connection

```bash
redis-cli ping  # Should return PONG
```

---

## Security & Firewall Configuration

### 1. Configure UFW Firewall

```bash
# Reset UFW to defaults
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (IMPORTANT - do this first!)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow backend port (only from localhost via Nginx)
# Don't expose 17890 publicly - use Nginx reverse proxy

# Enable UFW
ufw --force enable

# Check status
ufw status verbose
```

### 2. Configure Fail2Ban

```bash
# Create jail for FastAPI
cat > /etc/fail2ban/jail.d/fastapi.conf << 'EOF'
[fastapi]
enabled = true
port = 17890
filter = fastapi
logpath = /root/graohen_os/backend/py-service/logs/*.log
maxretry = 5
bantime = 3600
findtime = 600
EOF

# Create filter
cat > /etc/fail2ban/filter.d/fastapi.conf << 'EOF'
[Definition]
failregex = ^.*"status_code":\s*(401|403|429).*$
ignoreregex =
EOF

# Restart Fail2Ban
systemctl restart fail2ban
systemctl enable fail2ban
```

### 3. Security Headers (Already in Nginx config)

The Nginx configuration includes:
- HSTS (HTTP Strict Transport Security)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

### 4. Rate Limiting

The application includes built-in rate limiting via:
- Redis-based rate limiting
- Security middleware
- Brute force protection

---

## Service Configuration (systemd)

### 1. Create systemd Service

```bash
cat > /etc/systemd/system/grapheneos-api.service << 'EOF'
[Unit]
Description=GrapheneOS Installer API Service
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/graohen_os/backend/py-service
Environment="PATH=/root/graohen_os/backend/py-service/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/root/graohen_os/backend/py-service"
ExecStart=/root/graohen_os/backend/py-service/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 17890 --workers 4
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=grapheneos-api

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable grapheneos-api
systemctl start grapheneos-api

# Check status
systemctl status grapheneos-api
```

### 2. View Logs

```bash
# View service logs
journalctl -u grapheneos-api -f

# View recent logs
journalctl -u grapheneos-api -n 100
```

---

## Testing APIs & Security

### 1. Run Automated Test Suite

```bash
# Make test script executable
chmod +x /root/graohen_os/backend/py-service/test_api.sh

# Run tests against local server
cd /root/graohen_os/backend/py-service
./test_api.sh http://localhost:17890

# Run tests against production domain
./test_api.sh https://fxmail.ai
```

The test script will verify:
- Health endpoints
- Authentication (registration/login)
- Protected endpoints
- Unauthorized access protection
- Rate limiting
- CORS configuration
- Security headers

### 2. Test Server Startup

```bash
# Check if service is running
systemctl status grapheneos-api

# Test API health endpoint
curl http://localhost:17890/health

# Test through Nginx
curl https://fxmail.ai/health
```

### 2. Test Authentication APIs

```bash
# Register a new user
curl -X POST https://fxmail.ai/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'

# Login
curl -X POST https://fxmail.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'

# Save the access_token from response
```

### 3. Test Email Service

```bash
# Send encrypted email (requires authentication)
ACCESS_TOKEN="your_access_token_here"

curl -X POST https://fxmail.ai/api/v1/email/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Test Email",
    "body": "This is a test encrypted email",
    "passcode": "1234",
    "expires_in_hours": 24,
    "self_destruct": false
  }'

# Get email (requires authentication)
EMAIL_ID="email_id_from_send_response"

curl -X GET https://fxmail.ai/api/v1/email/$EMAIL_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Unlock passcode-protected email (public endpoint)
curl -X POST https://fxmail.ai/api/v1/email/$EMAIL_ID/unlock \
  -H "Content-Type: application/json" \
  -d '{
    "passcode": "1234"
  }'
```

### 4. Test Drive Service

```bash
# Upload file (requires authentication)
curl -X POST https://fxmail.ai/api/v1/drive/upload \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/path/to/testfile.txt" \
  -F "passcode=optional_passcode" \
  -F "expires_in_hours=168"

# Get file info
FILE_ID="file_id_from_upload_response"

curl -X GET "https://fxmail.ai/api/v1/drive/file/$FILE_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Download file
curl -X GET "https://fxmail.ai/api/v1/drive/file/$FILE_ID/download" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -o downloaded_file.txt
```

### 5. Test Security Layers

```bash
# Test rate limiting (make multiple rapid requests)
for i in {1..10}; do
  curl -X POST https://fxmail.ai/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong"}'
  echo ""
done
# Should return 429 Too Many Requests after threshold

# Test CORS
curl -X OPTIONS https://fxmail.ai/api/v1/auth/login \
  -H "Origin: https://example.com" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Test security headers
curl -I https://fxmail.ai/health
# Should show security headers in response
```

### 6. Test Firewall

```bash
# Try to access backend directly (should fail if firewall configured correctly)
curl http://YOUR_VPS_IP:17890/health
# Should timeout or be blocked

# Access through domain (should work)
curl https://fxmail.ai/health
# Should return 200 OK
```

---

## Monitoring & Maintenance

### 1. Log Monitoring

```bash
# Application logs
tail -f /root/graohen_os/backend/py-service/logs/*.log

# Nginx logs
tail -f /var/log/nginx/fxmail.ai.access.log
tail -f /var/log/nginx/fxmail.ai.error.log

# System logs
journalctl -u grapheneos-api -f
```

### 2. Health Check Script

```bash
cat > /usr/local/bin/check-api-health.sh << 'EOF'
#!/bin/bash
API_URL="https://fxmail.ai/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL)

if [ "$RESPONSE" != "200" ]; then
    echo "API health check failed: HTTP $RESPONSE"
    systemctl restart grapheneos-api
    exit 1
else
    echo "API is healthy"
    exit 0
fi
EOF

chmod +x /usr/local/bin/check-api-health.sh

# Add to crontab (check every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check-api-health.sh") | crontab -
```

### 3. SSL Certificate Renewal

```bash
# Certbot auto-renewal (should be enabled by default)
systemctl status certbot.timer

# Manual renewal test
certbot renew --dry-run

# Renewal will be automatic via systemd timer
```

### 4. Database Backup

```bash
# Create backup script
cat > /usr/local/bin/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump grapheneos_db > $BACKUP_DIR/grapheneos_db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "grapheneos_db_*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/grapheneos_db_$DATE.sql"
EOF

chmod +x /usr/local/bin/backup-db.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-db.sh") | crontab -
```

---

## Troubleshooting

### 1. Service Won't Start

```bash
# Check service status
systemctl status grapheneos-api

# Check logs
journalctl -u grapheneos-api -n 50

# Check if port is in use
netstat -tulpn | grep 17890

# Test manual startup
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 17890
```

### 2. Database Connection Issues

```bash
# Check PostgreSQL status
systemctl status postgresql

# Test connection
psql -U grapheneos_user -d grapheneos_db -h localhost

# Check database URL in .env
grep DATABASE_URL /root/graohen_os/backend/py-service/.env
```

### 3. Redis Connection Issues

```bash
# Check Redis status
systemctl status redis-server

# Test connection
redis-cli ping

# Check Redis URL in .env
grep REDIS_URL /root/graohen_os/backend/py-service/.env
```

### 4. Email Domain Not Working

```bash
# Check DNS resolution
dig fxmail.ai
nslookup fxmail.ai

# Check Nginx configuration
nginx -t
systemctl status nginx

# Check SSL certificate
certbot certificates

# Test email domain in config
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python -c "from app.config import settings; print(f'EMAIL_DOMAIN: {settings.EMAIL_DOMAIN}')"
```

### 5. Drive Upload Fails

```bash
# Check file size limits in Nginx
grep client_max_body_size /etc/nginx/sites-available/*.ai

# Check disk space
df -h

# Check application logs
tail -f /root/graohen_os/backend/py-service/logs/*.log
```

### 6. Security Issues

```bash
# Check firewall
ufw status verbose

# Check Fail2Ban
fail2ban-client status fastapi

# Check security headers
curl -I https://fxmail.ai/health | grep -i "x-frame\|x-content\|strict-transport"
```

---

## Quick Reference

### Important Paths
- Project: `/root/graohen_os/backend/py-service`
- Logs: `/root/graohen_os/backend/py-service/logs`
- Bundles: `/root/graohen_os/bundles`
- Config: `/root/graohen_os/backend/py-service/.env`
- Service: `/etc/systemd/system/grapheneos-api.service`

### Important Commands
```bash
# Service management
systemctl start grapheneos-api
systemctl stop grapheneos-api
systemctl restart grapheneos-api
systemctl status grapheneos-api

# View logs
journalctl -u grapheneos-api -f

# Test API
curl https://fxmail.ai/health

# Check service
systemctl status nginx postgresql redis-server grapheneos-api
```

### Configuration Files
- Email Domain: Set in `.env` as `EMAIL_DOMAIN=fxmail.ai`
- External URL: Set in `.env` as `EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai`
- Nginx: `/etc/nginx/sites-available/fxmail.ai`
- SSL: `/etc/letsencrypt/live/fxmail.ai/`

---

## Security Checklist

- [ ] Changed default SECRET_KEY in .env
- [ ] Changed database password
- [ ] Configured firewall (UFW)
- [ ] Enabled Fail2Ban
- [ ] SSL certificates installed and auto-renewal enabled
- [ ] Security headers configured in Nginx
- [ ] .env file permissions set to 600
- [ ] Service running as appropriate user
- [ ] Database backups configured
- [ ] Rate limiting tested
- [ ] CORS properly configured
- [ ] Backend port (17890) not publicly accessible

---

## Next Steps

1. Configure your frontend to use `https://fxmail.ai` as API endpoint
2. Set up monitoring and alerting
3. Configure automated backups
4. Set up log rotation
5. Review and adjust rate limits based on usage
6. Set up CI/CD pipeline for deployments

---

**Note**: This guide assumes you have root access and the project is located at `/root/graohen_os`. Adjust paths accordingly if your setup differs.


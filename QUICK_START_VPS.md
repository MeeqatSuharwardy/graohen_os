# Quick Start Guide - VPS Deployment

## Quick Setup Checklist

### 1. Initial Server Setup (5 minutes)

```bash
# Connect to VPS
ssh root@YOUR_VPS_IP

# Update system
apt update && apt upgrade -y
apt install -y python3.10 python3.10-venv python3-pip postgresql redis-server nginx certbot git

# Install ADB/Fastboot
cd /tmp && wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
mv platform-tools /opt/android-platform-tools
ln -sf /opt/android-platform-tools/adb /usr/local/bin/adb
ln -sf /opt/android-platform-tools/fastboot /usr/local/bin/fastboot
```

### 2. Project Setup (5 minutes)

```bash
# Navigate to project location
cd /root/graohen_os/backend/py-service

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Database Setup (2 minutes)

```bash
# Create database
sudo -u postgres psql << EOF
CREATE DATABASE grapheneos_db;
CREATE USER grapheneos_user WITH PASSWORD 'YOUR_SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE grapheneos_db TO grapheneos_user;
\q
EOF

# Start services
systemctl start postgresql redis-server
systemctl enable postgresql redis-server
```

### 4. Environment Configuration (3 minutes)

```bash
cd /root/graohen_os/backend/py-service

# Create .env file
cat > .env << 'EOF'
# Email Domain Configuration
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# Database
DATABASE_URL=postgresql+asyncpg://grapheneos_user:YOUR_SECURE_PASSWORD@localhost:5432/grapheneos_db

# Security - Generate with: openssl rand -hex 32
SECRET_KEY=YOUR_GENERATED_SECRET_KEY

# Server
PY_HOST=0.0.0.0
PY_PORT=17890

# CORS
CORS_ORIGINS=https://fxmail.ai,https://www.fxmail.ai

# Other settings (see full .env template in DEPLOYMENT_GUIDE_VPS.md)
EOF

chmod 600 .env
```

### 5. DNS Configuration for fxmail.ai

Configure these DNS records:

```
A Record:
  Name: @
  Value: YOUR_VPS_IP
  TTL: 3600

A Record:
  Name: www
  Value: YOUR_VPS_IP
  TTL: 3600

TXT Record (SPF):
  Name: @
  Value: v=spf1 ip4:YOUR_VPS_IP ~all
  TTL: 3600
```

### 6. SSL Certificate (2 minutes)

```bash
# Get SSL certificate
certbot certonly --standalone -d fxmail.ai -d www.fxmail.ai

# Auto-renewal is enabled by default
systemctl status certbot.timer
```

### 7. Nginx Configuration (3 minutes)

```bash
# Create Nginx config
cat > /etc/nginx/sites-available/fxmail.ai << 'EOF'
server {
    listen 80;
    server_name fxmail.ai www.fxmail.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name fxmail.ai www.fxmail.ai;
    
    ssl_certificate /etc/letsencrypt/live/fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fxmail.ai/privkey.pem;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:17890;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/fxmail.ai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

### 8. Firewall Setup (1 minute)

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

### 9. Create Systemd Service (2 minutes)

```bash
cat > /etc/systemd/system/grapheneos-api.service << 'EOF'
[Unit]
Description=GrapheneOS Installer API
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

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable grapheneos-api
systemctl start grapheneos-api
```

### 10. Test Everything (2 minutes)

```bash
# Check service status
systemctl status grapheneos-api

# Test health endpoint
curl https://fxmail.ai/health

# Run automated tests
cd /root/graohen_os/backend/py-service
chmod +x test_api.sh
./test_api.sh https://fxmail.ai
```

## Where Email Domain is Configured

The email domain `fxmail.ai` is configured in:

1. **Environment File** (`.env`):
   ```bash
   EMAIL_DOMAIN=fxmail.ai
   EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai
   ```

2. **Application Config** (`app/config.py`):
   - Default values are set, but `.env` overrides them

3. **Email Service** (`app/services/email_service.py`):
   - Reads from `settings.EMAIL_DOMAIN`

## Domain Settings Summary

### For Email Service (fxmail.ai):
- ✅ A Record pointing to VPS IP
- ✅ SSL Certificate (Let's Encrypt)
- ✅ Nginx reverse proxy
- ✅ SPF/DKIM/DMARC records (for email delivery)
- ✅ Environment variable: `EMAIL_DOMAIN=fxmail.ai`

### For Drive Upload:
- ✅ Same domain or subdomain (drive.fxmail.ai)
- ✅ Large file upload support (100MB in Nginx)
- ✅ Same SSL certificate
- ✅ Same Nginx configuration with `client_max_body_size 100M`

## Quick Commands

```bash
# Service management
systemctl start/stop/restart grapheneos-api
systemctl status grapheneos-api

# View logs
journalctl -u grapheneos-api -f

# Test API
curl https://fxmail.ai/health

# Check all services
systemctl status nginx postgresql redis-server grapheneos-api
```

## Troubleshooting

**Service won't start?**
```bash
journalctl -u grapheneos-api -n 50
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 17890
```

**Email domain not working?**
```bash
# Check DNS
dig fxmail.ai

# Check config
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python -c "from app.config import settings; print(settings.EMAIL_DOMAIN)"
```

**Drive upload fails?**
```bash
# Check Nginx file size limit
grep client_max_body_size /etc/nginx/sites-available/fxmail.ai

# Check disk space
df -h
```

For detailed information, see `DEPLOYMENT_GUIDE_VPS.md`


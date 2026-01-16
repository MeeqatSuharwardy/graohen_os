# Deployment Guide: Digital Ocean with Domain Setup

This guide walks you through deploying the GrapheneOS Desktop Installer backend on Digital Ocean with proper domain configuration:
- **os.fxmail.ai** - Main API backend
- **fxmail.ai** - Email server only
- **drive.fxmail.ai** - Encrypted drive service

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Digital Ocean Droplet Setup](#digital-ocean-droplet-setup)
3. [DNS Configuration](#dns-configuration)
4. [Backend Installation](#backend-installation)
5. [ADB/Fastboot Setup](#adbfastboot-setup)
6. [Nginx Reverse Proxy Setup](#nginx-reverse-proxy-setup)
7. [SSL Certificate Setup](#ssl-certificate-setup)
8. [Frontend Configuration](#frontend-configuration)
9. [Device Detection Troubleshooting](#device-detection-troubleshooting)
10. [Running the Services](#running-the-services)
11. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Digital Ocean account
- SSH access to your droplet
- Domain access to `fxmail.ai` with DNS management
- USB device connected to Digital Ocean server (via USB passthrough or physical access)

---

## Digital Ocean Droplet Setup

### 1. Create a Droplet

1. Log in to Digital Ocean dashboard
2. Click "Create" → "Droplets"
3. Choose configuration:
   - **Image**: Ubuntu 22.04 LTS (or later)
   - **Plan**: Basic (minimum 2GB RAM recommended)
   - **Region**: Choose closest to your location
   - **Authentication**: SSH keys (recommended) or password
   - **Hostname**: `graphene-flasher` (or your choice)

### 2. Connect to Droplet

```bash
ssh root@YOUR_DROPLET_IP
```

### 3. Update System

```bash
apt update && apt upgrade -y
```

---

## Backend Installation

### 1. Install Python and Dependencies

```bash
# Install Python 3.8+ and pip
apt install -y python3 python3-pip python3-venv git curl wget

# Install udev rules for Android devices (required for device detection)
apt install -y android-sdk-platform-tools-common

# Verify installation
python3 --version
pip3 --version
```

### 2. Clone Repository (or upload files)

**Option A: If repository is on GitHub/GitLab**

```bash
cd /root
git clone YOUR_REPOSITORY_URL graohen_os
cd graohen_os/backend/py-service
```

**Option B: Upload files via SCP**

```bash
# On your local machine
scp -r backend/ root@YOUR_DROPLET_IP:/root/graohen_os/backend/
```

### 3. Create Virtual Environment

```bash
cd /root/graohen_os/backend/py-service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Create .env file
cat > /root/graohen_os/backend/py-service/.env << 'EOF'
# Application
APP_NAME=GrapheneOS Installer API
APP_VERSION=1.0.0
DEBUG=False
ENVIRONMENT=production

# FastAPI Configuration
PY_HOST=0.0.0.0
PY_PORT=17890

# API Configuration
API_V1_PREFIX=/api/v1
ALLOWED_HOSTS=os.fxmail.ai,drive.fxmail.ai,localhost,127.0.0.1

# CORS Configuration - Allow frontend domains
CORS_ORIGINS=https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai

# ADB and Fastboot Paths
ADB_PATH=/usr/bin/adb
FASTBOOT_PATH=/usr/bin/fastboot

# Bundle Storage
GRAPHENE_BUNDLE_PATH=/root/graohen_os/bundles

# Email Domain Configuration
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai
EOF
```

### 5. Create Required Directories

```bash
# Create bundle storage directory
mkdir -p /root/graohen_os/bundles
chmod 755 /root/graohen_os/bundles

# Create APK storage directory (for uploaded APKs)
mkdir -p /root/graohen_os/apks
chmod 755 /root/graohen_os/apks
```

---

## ADB/Fastboot Setup

### 1. Install Platform Tools

**Option A: Install from Android SDK Platform Tools**

```bash
# Download latest platform-tools
cd /tmp
wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
unzip platform-tools-latest-linux.zip
mv platform-tools /opt/android-platform-tools

# Create symlinks
ln -sf /opt/android-platform-tools/adb /usr/local/bin/adb
ln -sf /opt/android-platform-tools/fastboot /usr/local/bin/fastboot

# Verify
adb version
fastboot --version
```

**Option B: Install from package manager (may be outdated)**

```bash
apt install -y android-tools-adb android-tools-fastboot
```

### 2. Configure USB Device Access

Since devices need to be physically connected or accessed via USB:

**If device is physically connected to the server:**

```bash
# Check if device is detected
lsusb

# Should show something like:
# Bus 001 Device 003: ID 18d1:4ee0 Google Inc. Nexus/Pixel Device (charging)
```

**Configure udev rules:**

```bash
# Create udev rules file
cat > /etc/udev/rules.d/51-android.rules << 'EOF'
# Google devices
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0664", GROUP="plugdev"
# Add more vendor IDs as needed
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0664", GROUP="plugdev"  # Samsung
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Add current user to plugdev group (if group exists)
usermod -aG plugdev $USER
# Or create the group if it doesn't exist
groupadd -f plugdev
```

**Note**: For Digital Ocean droplets, USB passthrough requires specific hardware. Consider:
- Using a dedicated server with USB access
- Running ADB over network (adb connect)

### 3. Verify Device Detection

```bash
# Check if ADB can see devices
adb devices

# If device shows as "unauthorized", authorize it:
adb devices -l

# For fastboot devices:
fastboot devices
```

---

## DNS Configuration

### 1. Configure DNS Records

In your DNS provider (e.g., Cloudflare, Namecheap, etc.), add the following A records:

#### Main API Domain (os.fxmail.ai)
```
Type: A
Name: os
Value: YOUR_DROPLET_IP
TTL: 3600
```

#### Encrypted Drive Domain (drive.fxmail.ai)
```
Type: A
Name: drive
Value: YOUR_DROPLET_IP
TTL: 3600
```

#### Email Server Domain (fxmail.ai) - Optional
```
Type: A
Name: @
Value: YOUR_DROPLET_IP (or separate IP if email is on different server)
TTL: 3600
```

**Note**: `fxmail.ai` is used for email server only, not for the API backend.

### 2. Verify DNS Propagation

```bash
# Check DNS resolution
dig os.fxmail.ai +short
dig drive.fxmail.ai +short

# Should return your droplet IP
```

---

## Nginx Reverse Proxy Setup

### 1. Install Nginx

```bash
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

### 2. Configure Main API Domain (os.fxmail.ai)

```bash
cat > /etc/nginx/sites-available/os.fxmail.ai << 'EOF'
server {
    listen 80;
    server_name os.fxmail.ai;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name os.fxmail.ai;

    ssl_certificate /etc/letsencrypt/live/os.fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/os.fxmail.ai/privkey.pem;
    
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
        
        # Timeouts for long-running operations (flashing)
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # File upload size limit
    client_max_body_size 100M;
    
    # Logging
    access_log /var/log/nginx/os.fxmail.ai.access.log;
    error_log /var/log/nginx/os.fxmail.ai.error.log;
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/os.fxmail.ai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
```

### 3. Configure Encrypted Drive Domain (drive.fxmail.ai)

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

    ssl_certificate /etc/letsencrypt/live/drive.fxmail.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/drive.fxmail.ai/privkey.pem;
    
    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
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

# Enable site
ln -sf /etc/nginx/sites-available/drive.fxmail.ai /etc/nginx/sites-enabled/
```

### 4. Test Nginx Configuration

```bash
# Test configuration
nginx -t

# If test passes, reload nginx
systemctl reload nginx
```

---

## SSL Certificate Setup

### 1. Install Certbot

```bash
apt install -y certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificates

```bash
# For main API domain
certbot certonly --standalone -d os.fxmail.ai

# For encrypted drive domain
certbot certonly --standalone -d drive.fxmail.ai
```

**Note**: If you want to use a wildcard certificate for `*.fxmail.ai`, you'll need DNS-based validation and Certbot with DNS plugin configured.

### 3. Update Nginx Configurations

After obtaining certificates, ensure your Nginx configs reference the correct certificate paths (already configured above).

### 4. Enable Auto-Renewal

```bash
# Certbot auto-renewal is enabled by default via systemd timer
systemctl status certbot.timer

# Test renewal
certbot renew --dry-run
```

### 5. Reload Nginx with SSL

```bash
# After certificates are obtained, reload nginx
nginx -t && systemctl reload nginx
```

---

## Device Detection Troubleshooting

### Common Issues and Solutions

#### Issue 1: Device Not Detected via USB

**Problem**: `adb devices` shows no devices

**Solutions**:

1. **Check USB connection:**
   ```bash
   lsusb
   dmesg | tail -20  # Check kernel messages
   ```

2. **Check udev rules:**
   ```bash
   udevadm info /dev/bus/usb/001/XXX  # Replace XXX with device number
   ```

3. **Try running as root:**
   ```bash
   sudo adb devices
   ```

4. **Kill existing ADB server:**
   ```bash
   adb kill-server
   adb start-server
   adb devices
   ```

5. **Use ADB over network** (if device is on same network):
   ```bash
   # On device: Enable wireless debugging in Developer Options
   # Then connect:
   adb connect DEVICE_IP:PORT
   ```

#### Issue 2: Permission Denied Errors

**Solution**:

```bash
# Create udev rules with proper permissions
cat > /etc/udev/rules.d/99-android.rules << 'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666"
EOF

udevadm control --reload-rules
udevadm trigger

# Add user to groups
usermod -aG plugdev,dialout $USER
```

#### Issue 3: Device Shows as "Unauthorized"

**Solution**:

1. On device: Enable USB debugging
2. Check "Always allow from this computer" when prompted
3. Or revoke and re-authorize:
   ```bash
   adb kill-server
   adb start-server
   # Check device for authorization prompt
   ```

#### Issue 4: Fastboot Device Not Detected

**Solutions**:

1. **Check if device is in fastboot mode:**
   ```bash
   fastboot devices
   fastboot devices -l  # More verbose
   ```

2. **Check USB vendor ID:**
   ```bash
   lsusb | grep -i google
   ```

3. **Use specific USB port:**
   ```bash
   fastboot -s DEVICE_SERIAL devices
   ```

4. **Install fastboot driver/rules:**
   ```bash
   # Add udev rule for fastboot
   cat >> /etc/udev/rules.d/51-android.rules << 'EOF'
   # Fastboot mode (bootloader)
   SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", MODE="0666"
   EOF
   udevadm control --reload-rules
   ```

---

## Running the Services

### 1. Create Systemd Service for Backend

```bash
cat > /etc/systemd/system/graphene-flasher.service << 'EOF'
[Unit]
Description=GrapheneOS Flasher Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/graohen_os/backend/py-service
Environment="PATH=/root/graohen_os/backend/py-service/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/graohen_os/backend/py-service/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 17890
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
systemctl daemon-reload
systemctl enable graphene-flasher
systemctl start graphene-flasher

# Check status
systemctl status graphene-flasher

# View logs
journalctl -u graphene-flasher -f
```

### 2. Start and Enable Services

```bash
# Reload systemd and start backend
systemctl daemon-reload
systemctl enable graphene-flasher
systemctl start graphene-flasher

# Check status
systemctl status graphene-flasher

# View logs
journalctl -u graphene-flasher -f
```

### 3. Verify Nginx and Backend

```bash
# Check backend is running
curl http://localhost:17890/health

# Should return:
# {"status":"healthy","service":"FlashDash API"}

# Check nginx is proxying correctly
curl https://os.fxmail.ai/health

# Should return the same health check response
```

---

## Frontend Configuration

### 1. Desktop Electron App

The frontend is a desktop Electron application that can be downloaded and run on your local machine. The app will:
- Detect ADB devices connected to your computer
- Send device information to the backend API
- Allow flashing GrapheneOS from the "Flash" tab
- Allow installing APKs from the "APKs" tab

**Download and Setup:**
1. Download the Electron app (built from `frontend/packages/desktop`)
2. Extract/install on your desktop
3. Configure the API endpoint in the app's `.env` file:

```env
# Use the main API domain
VITE_API_BASE_URL=https://os.fxmail.ai
```

**Important**: 
- The Electron app runs on your desktop and connects to the backend at `https://os.fxmail.ai`
- The app detects ADB devices locally and sends device information to the backend
- Use `https://os.fxmail.ai` for the main API backend
- Remove the trailing slash if present

### 2. Build Desktop App (Optional - if building from source)

If building the desktop app from source:

```bash
cd frontend/packages/desktop
npm install
npm run build

# The built app will be in the 'out' directory
# On macOS: .dmg file
# On Windows: .exe installer
# On Linux: .AppImage file
```

### 3. APK Upload Form

To upload APKs that can be installed via the Electron app:

1. Navigate to `https://os.fxmail.ai/apks/upload` in a web browser
2. Enter the password: `AllHailToEagle`
3. Upload APK files (.apk extension)
4. The uploaded APKs will appear in the "APKs" tab of the Electron app

### 4. Test Connection

```bash
# Test health endpoint
curl https://os.fxmail.ai/health

# Should return:
# {"status":"healthy","service":"FlashDash API"}

# Test devices endpoint
curl https://os.fxmail.ai/devices

# Test tools check
curl https://os.fxmail.ai/tools/check

# Test APK list endpoint
curl https://os.fxmail.ai/apks/list
```

---

## Troubleshooting

### Backend Service Issues

**Service won't start:**

```bash
# Check logs
journalctl -u graphene-flasher -n 50

# Check if port is in use
netstat -tulpn | grep 17890

# Check Python environment
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python -c "import uvicorn; print('OK')"
```

**Port already in use:**

```bash
# Find and kill process
lsof -ti:17890 | xargs kill -9

# Or change port in .env and service file
```

### Nginx Issues

**Nginx won't start:**

```bash
# Check configuration syntax
nginx -t

# Check nginx status
systemctl status nginx

# Check error logs
tail -f /var/log/nginx/error.log

# Check if port 80/443 are available
netstat -tulpn | grep -E ':(80|443)'
```

**SSL Certificate Issues:**

```bash
# Check certificate expiration
certbot certificates

# Renew certificates manually
certbot renew

# Check certificate paths in nginx config
ls -la /etc/letsencrypt/live/os.fxmail.ai/
ls -la /etc/letsencrypt/live/drive.fxmail.ai/
```

**Domain not resolving:**

```bash
# Check DNS from server
dig os.fxmail.ai +short
dig drive.fxmail.ai +short

# Check DNS from external service
nslookup os.fxmail.ai 8.8.8.8
```

### CORS Issues

If you see CORS errors in the frontend:

1. Check backend CORS configuration in `.env` file:
   ```bash
   # Should include your frontend domains
   CORS_ORIGINS=https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai
   ```

2. Verify CORS in backend `app/config.py`:
   ```python
   CORS_ORIGINS: str = "https://os.fxmail.ai,https://drive.fxmail.ai,https://fxmail.ai"
   ```

3. Restart backend after changing CORS:
   ```bash
   systemctl restart graphene-flasher
   ```

4. Test CORS:
   ```bash
   curl -H "Origin: https://os.fxmail.ai" \
        -H "Access-Control-Request-Method: GET" \
        -X OPTIONS \
        https://os.fxmail.ai/health
   ```

### Device Detection Issues

**Check backend logs:**

```bash
journalctl -u graphene-flasher -f | grep -i device
```

**Test ADB/Fastboot directly:**

```bash
# As root
adb devices
fastboot devices

# Check if tools are in PATH
which adb
which fastboot

# Test identify_device function
cd /root/graohen_os/backend/py-service
source venv/bin/activate
python3 -c "from app.utils.tools import identify_device; print(identify_device('YOUR_DEVICE_SERIAL'))"
```

**Enable debug logging:**

Edit `/root/graohen_os/backend/py-service/app/main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    ...
)
```

### Network Issues

**Check firewall:**

```bash
# UFW (if enabled)
ufw status

# Allow HTTP and HTTPS (ports 80 and 443)
ufw allow 80/tcp
ufw allow 443/tcp

# Allow SSH (if not already allowed)
ufw allow 22/tcp

# Backend port 17890 should NOT be exposed publicly - only accessible via nginx
# Only allow from localhost:
ufw allow from 127.0.0.1 to any port 17890

# Enable firewall
ufw enable
ufw status verbose
```

**Test connections:**

```bash
# From server - test backend directly
curl http://localhost:17890/health

# From server - test via nginx
curl https://os.fxmail.ai/health

# From external machine - test public domain
curl https://os.fxmail.ai/health

# Test drive domain
curl https://drive.fxmail.ai/health
```

---

## Security Considerations

### 1. Backend Security

- CORS is configured to allow only specific domains (`os.fxmail.ai`, `drive.fxmail.ai`, `fxmail.ai`)
- Add authentication to API endpoints as needed
- HTTPS is enforced via nginx with SSL certificates
- Keep system updated: `apt update && apt upgrade`

### 2. Firewall Setup

```bash
# Install UFW
apt install ufw

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (IMPORTANT - do this first!)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Backend port 17890 should NOT be publicly accessible
# Only allow from localhost (nginx connects locally)
ufw allow from 127.0.0.1 to any port 17890

# Enable firewall
ufw enable
ufw status verbose
```

### 3. SSL/TLS Security

- SSL certificates are automatically renewed via certbot
- Strong SSL configuration in nginx (TLSv1.2, TLSv1.3 only)
- Security headers enabled (HSTS, X-Frame-Options, etc.)
- Monitor certificate expiration: `certbot certificates`

---

## Monitoring

### View Service Logs

```bash
# Backend logs
journalctl -u graphene-flasher -f

# Nginx access logs
tail -f /var/log/nginx/os.fxmail.ai.access.log
tail -f /var/log/nginx/drive.fxmail.ai.access.log

# Nginx error logs
tail -f /var/log/nginx/os.fxmail.ai.error.log
tail -f /var/log/nginx/drive.fxmail.ai.error.log

# Combined logs
journalctl -u graphene-flasher -u nginx -f
```

### Health Checks

Create a monitoring script:

```bash
cat > /usr/local/bin/check-graphene-service.sh << 'EOF'
#!/bin/bash
# Check if backend is running
if ! curl -f http://localhost:17890/health > /dev/null 2>&1; then
    echo "Backend is down!"
    systemctl restart graphene-flasher
fi

# Check if nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "Nginx is down!"
    systemctl restart nginx
fi

# Check if domain is accessible
if ! curl -f https://os.fxmail.ai/health > /dev/null 2>&1; then
    echo "Domain os.fxmail.ai is not accessible!"
fi
EOF

chmod +x /usr/local/bin/check-graphene-service.sh

# Add to crontab (check every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check-graphene-service.sh") | crontab -
```

---

## Quick Reference

### Service Management

```bash
# Backend
systemctl status graphene-flasher
systemctl restart graphene-flasher
systemctl stop graphene-flasher
systemctl start graphene-flasher

# Nginx
systemctl status nginx
systemctl restart nginx
systemctl reload nginx
systemctl stop nginx
systemctl start nginx
```

### Get Public URLs

```bash
# Main API domain
echo "API: https://os.fxmail.ai"

# Encrypted drive domain
echo "Drive: https://drive.fxmail.ai"

# Email domain (email server only, not API)
echo "Email: https://fxmail.ai"
```

### Test Backend

```bash
# Test main API domain
curl https://os.fxmail.ai/health
curl https://os.fxmail.ai/devices
curl https://os.fxmail.ai/tools/check

# Test drive domain
curl https://drive.fxmail.ai/health

# Test local backend directly
curl http://localhost:17890/health
```

---

## Next Steps

1. **Verify DNS**: Ensure `os.fxmail.ai` and `drive.fxmail.ai` resolve to your droplet IP
2. **Verify SSL**: Check that SSL certificates are valid with `certbot certificates`
3. **Update frontend**: Set `VITE_API_BASE_URL` to `https://os.fxmail.ai`
4. **Test connection**: Verify frontend can connect to backend via the domain
5. **Connect device**: Ensure device is detected via `adb devices`
6. **Start flashing**: Test the full workflow

---

## Support

If you encounter issues:

1. Check backend logs: `journalctl -u graphene-flasher -n 100`
2. Check nginx logs: `tail -f /var/log/nginx/os.fxmail.ai.error.log`
3. Verify device detection: `adb devices` and `fastboot devices`
4. Test endpoints: Use curl to test API endpoints
5. Check nginx status: `systemctl status nginx`
6. Verify DNS: `dig os.fxmail.ai +short` and `dig drive.fxmail.ai +short`
7. Check SSL certificates: `certbot certificates`

---

## Domain Summary

- **os.fxmail.ai** - Main API backend for GrapheneOS installer
- **drive.fxmail.ai** - Encrypted drive service (same backend, different nginx config)
- **fxmail.ai** - Email server only (not used for API backend)

**Important**: 
- The backend API runs on port 17890 internally
- Nginx proxies `os.fxmail.ai` and `drive.fxmail.ai` to the backend
- Port 17890 should NOT be exposed publicly - only accessible via nginx
- All domains use HTTPS with Let's Encrypt SSL certificates


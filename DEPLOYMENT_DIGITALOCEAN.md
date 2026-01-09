# Deployment Guide: Digital Ocean with ngrok

This guide walks you through deploying the GrapheneOS Desktop Installer backend on Digital Ocean and exposing it via ngrok (when no domain is available).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Digital Ocean Droplet Setup](#digital-ocean-droplet-setup)
3. [Backend Installation](#backend-installation)
4. [ADB/Fastboot Setup](#adbfastboot-setup)
5. [ngrok Setup](#ngrok-setup)
6. [Frontend Configuration](#frontend-configuration)
7. [Device Detection Troubleshooting](#device-detection-troubleshooting)
8. [Running the Services](#running-the-services)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Digital Ocean account
- SSH access to your droplet
- ngrok account (free tier works)
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
cd /opt
git clone YOUR_REPOSITORY_URL graohen_os
cd graohen_os/backend/py-service
```

**Option B: Upload files via SCP**

```bash
# On your local machine
scp -r backend/ root@YOUR_DROPLET_IP:/opt/graohen_os/backend/
```

### 3. Create Virtual Environment

```bash
cd /opt/graohen_os/backend/py-service
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Create .env file
cat > /opt/graohen_os/backend/py-service/.env << 'EOF'
# FastAPI Configuration
PY_HOST=0.0.0.0
PY_PORT=17890

# ADB and Fastboot Paths
ADB_PATH=/usr/bin/adb
FASTBOOT_PATH=/usr/bin/fastboot

# Bundle Storage
GRAPHENE_BUNDLE_PATH=/opt/graohen_os/bundles
EOF
```

### 5. Create Required Directories

```bash
mkdir -p /opt/graohen_os/bundles
chmod 755 /opt/graohen_os/bundles
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
- Using a local machine with ngrok tunnel

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

## ngrok Setup

### 1. Install ngrok

```bash
# Download ngrok
cd /tmp
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz

# Extract
tar -xzf ngrok-v3-stable-linux-amd64.tgz
mv ngrok /usr/local/bin/
chmod +x /usr/local/bin/ngrok

# Verify
ngrok version
```

### 2. Create ngrok Account and Get Authtoken

1. Sign up at https://dashboard.ngrok.com/signup
2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
3. Configure ngrok:

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

### 3. Create ngrok Configuration File

```bash
mkdir -p /etc/ngrok
cat > /etc/ngrok/ngrok.yml << 'EOF'
version: "2"
authtoken: YOUR_AUTHTOKEN_HERE
tunnels:
  grapheneflasher:
    addr: 17890
    proto: http
    bind_tls: true  # HTTPS tunnel
EOF
```

Replace `YOUR_AUTHTOKEN_HERE` with your actual authtoken.

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
WorkingDirectory=/opt/graohen_os/backend/py-service
Environment="PATH=/opt/graohen_os/backend/py-service/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/graohen_os/backend/py-service/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 17890
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

### 2. Create Systemd Service for ngrok

```bash
cat > /etc/systemd/system/ngrok.service << 'EOF'
[Unit]
Description=ngrok tunnel for GrapheneOS Flasher
After=network.target graphene-flasher.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/ngrok start --config /etc/ngrok/ngrok.yml grapheneflasher
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload and start
systemctl daemon-reload
systemctl enable ngrok
systemctl start ngrok

# Check status
systemctl status ngrok

# View logs
journalctl -u ngrok -f
```

### 3. Get ngrok URL

```bash
# Get the public URL from ngrok API
curl http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*"' | head -1

# Or check ngrok web interface
# Open: http://localhost:4040 in browser (if accessible)
```

The URL will be something like: `https://abc123def456.ngrok-free.app`

---

## Frontend Configuration

### 1. Update Frontend .env File

On your local development machine or frontend server, update the `.env` file:

```env
# Use the ngrok URL
VITE_API_BASE_URL=https://YOUR_NGROK_URL.ngrok-free.app
```

**Important**: Remove the trailing slash if present.

### 2. Rebuild Frontend

```bash
cd frontend/packages/desktop
npm install
npm run build
```

### 3. Test Connection

```bash
# Test health endpoint
curl https://YOUR_NGROK_URL.ngrok-free.app/health

# Should return:
# {"status":"healthy","service":"FlashDash API"}
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
cd /opt/graohen_os/backend/py-service
source venv/bin/activate
python -c "import uvicorn; print('OK')"
```

**Port already in use:**

```bash
# Find and kill process
lsof -ti:17890 | xargs kill -9

# Or change port in .env and service file
```

### ngrok Issues

**ngrok won't start:**

```bash
# Check authtoken
ngrok config check

# Test manually
ngrok http 17890

# Check if port 17890 is accessible
curl http://localhost:17890/health
```

**ngrok URL changes on restart:**

- Free tier: URL changes on each restart
- Solution: Use ngrok's reserved domains (paid feature) or update frontend .env when URL changes
- Or use ngrok's API to get the URL programmatically:

```bash
# Get current URL
curl http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4
```

### CORS Issues

If you see CORS errors in the frontend:

1. Check backend CORS configuration in `app/main.py`:
   ```python
   allow_origins=["*"]  # Should allow all for ngrok
   ```

2. Test CORS:
   ```bash
   curl -H "Origin: https://your-frontend-domain.com" \
        -H "Access-Control-Request-Method: GET" \
        -X OPTIONS \
        https://YOUR_NGROK_URL.ngrok-free.app/health
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
cd /opt/graohen_os/backend/py-service
source venv/bin/activate
python3 -c "from app.utils.tools import identify_device; print(identify_device('YOUR_DEVICE_SERIAL'))"
```

**Enable debug logging:**

Edit `/opt/graohen_os/backend/py-service/app/main.py`:

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
ufw allow 17890/tcp

# iptables
iptables -L -n | grep 17890
```

**Test local connection:**

```bash
# From server
curl http://localhost:17890/health

# From another machine on same network
curl http://DROPLET_IP:17890/health
```

---

## Security Considerations

### 1. ngrok Authentication

For production, enable ngrok authentication:

```bash
# In ngrok.yml
tunnels:
  grapheneflasher:
    addr: 17890
    proto: http
    bind_tls: true
    inspect: false  # Disable web interface
    # Add basic auth
    auth: "username:password"
```

### 2. Backend Security

- Change CORS `allow_origins` to specific domains in production
- Add authentication to API endpoints
- Use HTTPS (ngrok provides this automatically)
- Keep system updated: `apt update && apt upgrade`

### 3. Firewall Setup

```bash
# Install UFW
apt install ufw

# Allow SSH
ufw allow 22/tcp

# Allow ngrok (not needed, ngrok handles it)
# ufw allow 4040/tcp  # Only if accessing ngrok web UI

# Enable firewall
ufw enable
ufw status
```

---

## Monitoring

### View Service Logs

```bash
# Backend logs
journalctl -u graphene-flasher -f

# ngrok logs
journalctl -u ngrok -f

# Combined logs
journalctl -u graphene-flasher -u ngrok -f
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

# Check if ngrok is running
if ! pgrep -x ngrok > /dev/null; then
    echo "ngrok is down!"
    systemctl restart ngrok
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

# ngrok
systemctl status ngrok
systemctl restart ngrok
systemctl stop ngrok
systemctl start ngrok
```

### Get ngrok URL

```bash
curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*"' | head -1 | cut -d'"' -f4
```

### Test Backend

```bash
curl https://YOUR_NGROK_URL.ngrok-free.app/health
curl https://YOUR_NGROK_URL.ngrok-free.app/devices
curl https://YOUR_NGROK_URL.ngrok-free.app/tools/check
```

---

## Next Steps

1. **Get ngrok URL**: Use the command above to get your public URL
2. **Update frontend**: Set `VITE_API_BASE_URL` to your ngrok URL
3. **Test connection**: Verify frontend can connect to backend
4. **Connect device**: Ensure device is detected via `adb devices`
5. **Start flashing**: Test the full workflow

---

## Support

If you encounter issues:

1. Check logs: `journalctl -u graphene-flasher -n 100`
2. Verify device detection: `adb devices` and `fastboot devices`
3. Test endpoints: Use curl to test API endpoints
4. Check ngrok status: `systemctl status ngrok`

---

**Note**: For production use with a custom domain, consider:
- Using Digital Ocean Load Balancer
- Setting up a reverse proxy (nginx)
- Using Cloudflare Tunnel instead of ngrok
- Configuring proper SSL certificates


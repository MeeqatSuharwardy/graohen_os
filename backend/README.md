# GrapheneOS Installer - Unified Backend

A production-grade FastAPI backend that combines GrapheneOS device flashing capabilities with secure encrypted email and file storage services.

## Table of Contents

- [Project Structure](#project-structure)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Deployment on DigitalOcean](#deployment-on-digitalocean)
- [Accessing DigitalOcean](#accessing-digitalocean)

---

## Project Structure

```
backend/
├── py-service/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Unified FastAPI application entry point
│   │   ├── config.py               # Unified configuration (FastAPI + GrapheneOS)
│   │   │
│   │   ├── core/                   # Core application modules
│   │   │   ├── __init__.py
│   │   │   ├── database.py         # PostgreSQL async database connection
│   │   │   ├── logging.py          # Logging configuration
│   │   │   ├── secure_logging.py   # Secure logging with sensitive data filtering
│   │   │   ├── redis_client.py     # Redis client for caching/sessions
│   │   │   ├── security.py         # Password hashing, JWT tokens
│   │   │   ├── security_hardening.py  # Rate limiting, audit logging, brute-force protection
│   │   │   ├── encryption.py       # AES-256-GCM encryption engine
│   │   │   └── key_manager.py      # Passcode-based key derivation (Argon2id)
│   │   │
│   │   ├── middleware/             # FastAPI middleware
│   │   │   ├── __init__.py
│   │   │   └── security.py         # Rate limiting and security headers middleware
│   │   │
│   │   ├── models/                 # SQLAlchemy database models
│   │   │   ├── __init__.py
│   │   │   └── base.py             # Base model class
│   │   │
│   │   ├── services/               # Business logic services
│   │   │   ├── __init__.py
│   │   │   └── email_service.py    # Encrypted email service
│   │   │
│   │   ├── utils/                  # Utility functions
│   │   │   ├── __init__.py
│   │   │   ├── tools.py            # ADB/Fastboot command utilities
│   │   │   ├── bundles.py          # Bundle management utilities
│   │   │   ├── flash.py            # Flash job management
│   │   │   └── grapheneos/         # GrapheneOS-specific utilities
│   │   │       ├── __init__.py
│   │   │       ├── tools.py        # Device identification
│   │   │       ├── bundles.py      # Bundle download and verification
│   │   │       ├── flash.py        # Flash execution
│   │   │       ├── flasher.py      # Main flasher script
│   │   │       └── downloader.py   # Bundle downloader
│   │   │
│   │   ├── routes/                 # Legacy GrapheneOS routes
│   │   │   ├── __init__.py
│   │   │   ├── devices.py          # Device detection and management
│   │   │   ├── bundles.py          # Bundle indexing and verification
│   │   │   ├── flash.py            # Flash execution endpoints
│   │   │   ├── source.py           # Source code management
│   │   │   └── build.py            # Build management
│   │   │
│   │   └── api/                    # FastAPI v1 API routes
│   │       └── v1/
│   │           ├── __init__.py
│   │           ├── router.py       # Main API router
│   │           └── endpoints/
│   │               ├── __init__.py
│   │               ├── auth.py     # Authentication (register, login, refresh, logout)
│   │               ├── email.py    # Encrypted email endpoints
│   │               ├── drive.py    # Encrypted file storage endpoints
│   │               ├── public.py   # Public secure viewer endpoints
│   │               └── grapheneos/
│   │                   └── download.py  # Build download endpoints
│   │
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment variables template
│   └── env.example                 # Alternative env file
│
├── flasher.py                      # Standalone flasher script
├── downloader.py                   # Standalone downloader script
└── README.md                       # This file
```

---

## Features

### GrapheneOS Flashing
- Device detection (ADB/Fastboot)
- Bootloader unlock and flash
- Bundle download and verification
- Progress tracking and job management
- Support for all Pixel devices

### Secure Services
- **JWT Authentication**: Access and refresh tokens with rotation
- **Encrypted Email**: End-to-end encrypted email with passcode protection
- **Encrypted File Storage**: Secure file upload/download with signed URLs
- **Rate Limiting**: Redis-based rate limiting per IP/user
- **Audit Logging**: Comprehensive security event logging
- **Brute-Force Protection**: Automatic lockout after failed attempts
- **View-Once Content**: One-time viewing for sensitive content
- **Auto-Wipe**: Automatic content deletion after expiration

### Security Hardening
- Sensitive data sanitization in logs
- Token expiration enforcement
- Security headers (CSP, HSTS, XSS protection)
- Redis-based session management
- Password hashing with Argon2

---

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- ADB and Fastboot tools
- Virtual environment (recommended)

### Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd graohen_os/backend
   ```

2. **Create virtual environment**:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   cd py-service
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Copy environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations** (if using database):
   ```bash
   alembic upgrade head
   ```

---

## Configuration

Create a `.env` file in `py-service/` directory:

```bash
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

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/grapheneos_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Email Service
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# GrapheneOS / Device Flashing
ADB_PATH=/usr/local/bin/adb
FASTBOOT_PATH=/usr/local/bin/fastboot
GRAPHENE_BUNDLES_ROOT=~/.graphene-installer/bundles
SUPPORTED_CODENAMES=cheetah,panther,raven,oriole,husky,shiba,akita,felix,tangorpro,lynx,bluejay,barbet,redfin

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## API Endpoints

### GrapheneOS Flashing (Legacy Routes)

- `GET /devices/` - List connected devices
- `GET /devices/{device_id}/identify` - Identify device codename
- `POST /devices/{device_id}/reboot/bootloader` - Reboot to bootloader
- `GET /bundles/for/{codename}` - Get latest bundle for codename
- `POST /flash/unlock-and-flash` - Unlock bootloader and flash
- `GET /flash/jobs/{job_id}` - Get flash job status
- `GET /flash/jobs/{job_id}/stream` - Stream flash job logs (SSE)

### FastAPI v1 API Routes

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout

- `POST /api/v1/email/send` - Send encrypted email
- `GET /api/v1/email/{email_id}` - Get encrypted email
- `POST /api/v1/email/{email_id}/unlock` - Unlock passcode-protected email
- `DELETE /api/v1/email/{email_id}` - Delete email

- `POST /api/v1/drive/upload` - Upload encrypted file
- `GET /api/v1/drive/file/{file_id}` - Get file metadata
- `GET /api/v1/drive/file/{file_id}/download` - Download file
- `POST /api/v1/drive/file/{file_id}/unlock` - Unlock passcode-protected file
- `DELETE /api/v1/drive/file/{file_id}` - Delete file

- `GET /api/v1/download/check/{codename}` - Check build availability
- `POST /api/v1/download/start` - Start build download
- `GET /api/v1/download/status/{download_id}` - Get download progress

### Health & Tools

- `GET /health` - Health check
- `GET /tools/check` - Check ADB/Fastboot availability
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

---

## Development

### Running Locally

```bash
cd py-service
source ../.venv/bin/activate  # Activate virtual environment
python -m app.main
```

Or with uvicorn:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 17890 --reload
```

### Testing

```bash
# Run tests (if available)
pytest

# Check code formatting
black app/
isort app/

# Type checking
mypy app/
```

---

## Deployment on DigitalOcean

This guide covers deploying the unified backend on a DigitalOcean droplet.

### Prerequisites

1. **DigitalOcean Account**: Sign up at [https://www.digitalocean.com](https://www.digitalocean.com)
2. **SSH Key**: Have an SSH key pair ready
3. **Domain (Optional)**: A domain name for production

### Accessing DigitalOcean

1. **Sign Up / Log In**:
   - Visit [https://www.digitalocean.com](https://www.digitalocean.com)
   - Click "Sign Up" or "Log In"
   - Complete account verification (email, payment method)

2. **Dashboard Access**:
   - After logging in, you'll see the DigitalOcean Control Panel
   - The main dashboard shows your resources (droplets, databases, etc.)

3. **Navigation**:
   - **Droplets**: Virtual servers (VPS)
   - **Databases**: Managed PostgreSQL/Redis
   - **Networking**: Firewalls, Load Balancers
   - **Spaces**: Object storage (S3-compatible)

### Step 1: Create a Droplet

1. **Click "Create" → "Droplets"** in the DigitalOcean dashboard

2. **Choose Configuration**:
   - **Image**: Ubuntu 22.04 LTS (or latest LTS)
   - **Plan**: Basic plan, **2GB RAM / 1 vCPU** minimum (4GB recommended)
   - **Datacenter Region**: Choose closest to your users
   - **Authentication**: SSH keys (recommended) or password

3. **Additional Options**:
   - Enable **Monitoring**
   - Add **Backups** (optional, for production)

4. **Create Droplet**: Click "Create Droplet"

5. **Note the IP Address**: You'll need this for SSH access

### Step 2: Initial Server Setup

1. **SSH into Droplet**:
   ```bash
   ssh root@<droplet-ip-address>
   ```

2. **Update System**:
   ```bash
   apt update && apt upgrade -y
   ```

3. **Create Non-Root User** (recommended):
   ```bash
   adduser graphene
   usermod -aG sudo graphene
   su - graphene
   ```

### Step 3: Install Required Software

1. **Install Python 3.11+**:
   ```bash
   sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
   ```

2. **Install PostgreSQL**:
   ```bash
   sudo apt install -y postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

3. **Install Redis**:
   ```bash
   sudo apt install -y redis-server
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

4. **Install ADB and Fastboot**:
   ```bash
   # Install Android tools
   sudo apt install -y android-tools-adb android-tools-fastboot
   
   # Or download platform-tools
   wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
   unzip platform-tools-latest-linux.zip
   sudo mv platform-tools /opt/
   sudo ln -s /opt/platform-tools/adb /usr/local/bin/adb
   sudo ln -s /opt/platform-tools/fastboot /usr/local/bin/fastboot
   ```

5. **Install Git and Build Tools**:
   ```bash
   sudo apt install -y git build-essential
   ```

### Step 4: Setup Application

1. **Clone Repository** (or upload code):
   ```bash
   cd /opt
   sudo git clone <your-repository-url> graphene-installer
   sudo chown -R graphene:graphene graphene-installer
   cd graphene-installer/graohen_os/backend/py-service
   ```

2. **Create Virtual Environment**:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create Environment File**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with production values
   ```

5. **Setup Database**:
   ```bash
   # Create database and user
   sudo -u postgres psql
   ```
   ```sql
   CREATE DATABASE grapheneos_db;
   CREATE USER graphene_user WITH PASSWORD 'secure-password';
   GRANT ALL PRIVILEGES ON DATABASE grapheneos_db TO graphene_user;
   \q
   ```

6. **Run Migrations**:
   ```bash
   source .venv/bin/activate
   alembic upgrade head
   ```

### Step 5: Setup Systemd Service

1. **Create Service File**:
   ```bash
   sudo nano /etc/systemd/system/graphene-installer.service
   ```

2. **Add Service Configuration**:
   ```ini
   [Unit]
   Description=GrapheneOS Installer API
   After=network.target postgresql.service redis.service

   [Service]
   Type=simple
   User=graphene
   WorkingDirectory=/opt/graphene-installer/graohen_os/backend/py-service
   Environment="PATH=/opt/graphene-installer/graohen_os/backend/py-service/.venv/bin"
   ExecStart=/opt/graphene-installer/graohen_os/backend/py-service/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 17890
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and Start Service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable graphene-installer
   sudo systemctl start graphene-installer
   sudo systemctl status graphene-installer
   ```

### Step 6: Setup Firewall

```bash
# Allow SSH, HTTP, HTTPS, and API port
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 17890/tcp
sudo ufw enable
```

### Step 7: Setup Reverse Proxy (Optional but Recommended)

1. **Install Nginx**:
   ```bash
   sudo apt install -y nginx
   ```

2. **Create Nginx Config**:
   ```bash
   sudo nano /etc/nginx/sites-available/graphene-installer
   ```

3. **Add Configuration**:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:17890;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. **Enable Site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/graphene-installer /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

5. **Setup SSL with Let's Encrypt**:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

### Step 8: Setup ngrok (For Testing / Temporary Access)

If you need temporary external access without a domain:

1. **Install ngrok**:
   ```bash
   wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
   tar xvzf ngrok-v3-stable-linux-amd64.tgz
   sudo mv ngrok /usr/local/bin/
   ```

2. **Get ngrok Auth Token**:
   - Sign up at [https://ngrok.com](https://ngrok.com)
   - Get your auth token from the dashboard

3. **Configure ngrok**:
   ```bash
   ngrok config add-authtoken <your-token>
   ```

4. **Create ngrok Service** (optional):
   ```bash
   sudo nano /etc/systemd/system/ngrok.service
   ```
   ```ini
   [Unit]
   Description=ngrok tunnel
   After=network.target

   [Service]
   ExecStart=/usr/local/bin/ngrok http 17890
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl enable ngrok
   sudo systemctl start ngrok
   ```

5. **Get Public URL**:
   ```bash
   curl http://localhost:4040/api/tunnels | grep -o '"public_url":"[^"]*"' | head -1
   ```

### Step 9: Monitoring and Logs

1. **View Application Logs**:
   ```bash
   sudo journalctl -u graphene-installer -f
   ```

2. **View Nginx Logs**:
   ```bash
   sudo tail -f /var/log/nginx/access.log
   sudo tail -f /var/log/nginx/error.log
   ```

3. **Monitor Resources**:
   ```bash
   htop
   df -h  # Disk usage
   free -h  # Memory usage
   ```

### Troubleshooting

1. **Service Won't Start**:
   ```bash
   sudo journalctl -u graphene-installer -n 50
   # Check for errors in logs
   ```

2. **Database Connection Issues**:
   ```bash
   sudo -u postgres psql -c "SELECT version();"
   # Verify DATABASE_URL in .env matches actual database credentials
   ```

3. **Redis Connection Issues**:
   ```bash
   redis-cli ping
   # Should return "PONG"
   ```

4. **Port Already in Use**:
   ```bash
   sudo lsof -i :17890
   # Kill process if needed
   ```

5. **Device Detection Issues**:
   - Ensure USB devices are properly connected
   - Check udev rules for ADB/Fastboot
   - Verify user has permissions for USB devices

### Security Recommendations

1. **Change Default Passwords**: All passwords should be strong and unique
2. **Use SSH Keys**: Disable password authentication for SSH
3. **Enable Fail2Ban**: Protect against brute-force attacks
4. **Regular Updates**: Keep system and dependencies updated
5. **Firewall**: Only open necessary ports
6. **SSL/TLS**: Always use HTTPS in production
7. **Backup**: Regular backups of database and configuration

---

## Additional Resources

- **DigitalOcean Documentation**: [https://docs.digitalocean.com](https://docs.digitalocean.com)
- **FastAPI Documentation**: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **GrapheneOS Documentation**: [https://grapheneos.org](https://grapheneos.org)
- **PostgreSQL Documentation**: [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)
- **Redis Documentation**: [https://redis.io/documentation](https://redis.io/documentation)

---

## License

[Specify your license here]

---

## Support

For issues or questions, please open an issue in the repository or contact the development team.

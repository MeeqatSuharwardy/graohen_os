# VPS Backend Deployment Guide (Gunicorn)

Production deployment for FlashDash backend with Gunicorn. Includes storage (5GB free tier), ProtonMail-style encrypted email, and admin CMS APIs.

## Overview

- **Backend**: `freedomos.vulcantech.co` (API, email, drive, admin)
- **Email Domain**: `vulcantech.tech` (E2E encrypted, ProtonMail-style)
- **Storage**: 5GB free per user, admin can increase via CMS APIs
- **Security**: Rate limiting, Argon2id key derivation, AES-256-GCM encryption

---

## Environment Variables

Create `.env` in `backend/py-service/`:

```bash
# Server
PY_HOST=0.0.0.0
PY_PORT=8000
ENVIRONMENT=production

# Domains
FRONTEND_DOMAIN=freedomos.vulcantech.co
BACKEND_DOMAIN=freedomos.vulcantech.co
EMAIL_DOMAIN=vulcantech.tech
DRIVE_DOMAIN=freedomos.vulcantech.co
API_BASE_URL=https://freedomos.vulcantech.co
EXTERNAL_HTTPS_BASE_URL=https://vulcantech.tech
CORS_ORIGINS=*

# Security (change in production)
SECRET_KEY=your-long-random-secret-key-min-32-chars
ALLOWED_HOSTS=freedomos.vulcantech.co,vulcantech.tech,localhost,127.0.0.1

# Storage (Drive)
DEFAULT_STORAGE_QUOTA_BYTES=5368709120
ADMIN_EMAILS=admin@vulcantech.tech,admin2@example.com

# Redis
REDIS_URL=redis://localhost:6379/0

# Database (DigitalOcean Managed PostgreSQL)
DATABASE_URL=postgresql+asyncpg://doadmin:AVNS_4JvwOl3UBWtVfQ5aTaF@db-postgresql-nyc3-46529-do-user-315641620.j.db.ondigitalocean.com:25060/defaultdb?sslmode=require
DATABASE_CA_CERT=ca-certificate.crt

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

---

## Deployment Steps

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv redis-server postgresql nginx adb fastboot
```

### 2. Backend Setup

```bash
cd ~/graohen_os/backend/py-service
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Admin

Set `ADMIN_EMAILS` in `.env` (comma-separated). These emails can:
- View all users' storage usage
- Set storage quotas per user
- List and delete any drive file

### 4. Run with Gunicorn

```bash
cd ~/graohen_os/backend/py-service
source venv/bin/activate
export GUNICORN_BIND=127.0.0.1:8000
gunicorn app.main:app -c gunicorn.conf.py
```

### 5. Systemd Service

Create `/etc/systemd/system/flashdash.service`:

```ini
[Unit]
Description=FlashDash Backend
After=network.target redis-server.service postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/YOUR_USER/graohen_os/backend/py-service
Environment="PATH=/home/YOUR_USER/graohen_os/backend/py-service/venv/bin"
Environment="GUNICORN_BIND=127.0.0.1:8000"
Environment="ENVIRONMENT=production"
ExecStart=/home/YOUR_USER/graohen_os/backend/py-service/venv/bin/gunicorn app.main:app -c gunicorn.conf.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable flashdash
sudo systemctl start flashdash
```

### 6. Nginx

Create `/etc/nginx/sites-available/freedomos`:

```nginx
server {
    listen 80;
    server_name freedomos.vulcantech.co backend.vulcantech.tech;

    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

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
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. Cloudflare

- DNS: A record `freedomos` → YOUR_SERVER_IP (Proxied)
- SSL/TLS: Encryption mode **Full**

---

## GitHub Actions Deployment

Deploy automatically on push to `main` or trigger manually.

### 1. Add GitHub Secrets

In Repository → Settings → Secrets and variables → Actions, add:

| Secret | Description |
|--------|-------------|
| `VPS_HOST` | VPS IP or hostname (e.g. `123.45.67.89`) |
| `VPS_USER` | SSH user (e.g. `root` or `deploy`) |
| `SSH_PRIVATE_KEY` | Full SSH private key (paste entire key including `-----BEGIN ...-----`) |
| `VPS_PORT` | (Optional) SSH port, default `22` |

### 2. Create Deploy Key on VPS (Optional)

If you use a deploy key instead of your personal key:

```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-deploy" -f deploy_key -N ""

# Add deploy_key.pub to VPS ~/.ssh/authorized_keys
# Add deploy_key contents to GitHub secret SSH_PRIVATE_KEY
```

### 3. Workflow File

The workflow is at `.github/workflows/deploy.yml`. It:

- **Triggers**: Push to `main` when `backend/**` changes, or manual run
- **Deploys**: SSH into VPS, `git pull`, `pip install`, `systemctl restart flashdash`

### 4. Manual Deploy

Go to Actions → Deploy to VPS → Run workflow.

### 5. Prerequisites on VPS

- Git repo cloned at `~/graohen_os` (edit `deploy.yml` if using a different path)
- `origin` remote configured
- `flashdash` systemd service installed
- SSH key in `authorized_keys` for `VPS_USER`
- `sudo` without password for `systemctl restart flashdash` (or run as root)

```bash
# Allow sudo for systemctl without password (optional)
echo "deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart flashdash" | sudo tee /etc/sudoers.d/deploy
```

---

## Device-Bound Login (2-Min Key Rotation)

Encryption key downloads to device, rotates every 2 minutes. Server-synced. Same complex algorithm used for drive/email.

**Strength**: Multi-layer derivation (Argon2id + Blake2b + SHA3-256 chain + XOR mix). 256-bit keyspace, computationally infeasible to crack.

### Flow

1. **Register**: Returns `device_key_download` (encrypted blob). Save to device.
2. **Existing users**: `POST /api/v1/auth/device-key/download` with email, password, device_id → get blob.
3. **Login**:
   - `POST /api/v1/auth/login/challenge` → `{challenge, time_slot}`
   - Device: decrypt blob with password → get `device_seed`
   - Device: derive key using `secure_derivation.derive_device_time_key(seed, device_id, time_slot)`
   - Device: `proof = HMAC-SHA256(key, challenge)`
   - `POST /api/v1/auth/login/secure` with email, password, device_id, challenge, proof, time_slot

### Client implementation

Client must implement the same algorithm as `app.core.secure_derivation`. Do not expose or document the full derivation chain.

---

## API Reference

### Storage (Drive)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/v1/drive/storage` | User | Get current user's storage usage (5GB free) |
| `POST /api/v1/drive/upload` | User | Upload file (checks quota) |
| `GET /api/v1/drive/file/{id}` | User | Get file info |
| `DELETE /api/v1/drive/file/{id}` | User | Delete own file |

### Admin (CMS)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/v1/admin/stats` | Admin | System capacity stats |
| `GET /api/v1/admin/storage` | Admin | List all users' storage |
| `PUT /api/v1/admin/storage/{email}` | Admin | Set user quota (`quota_gb` or `quota_bytes`) |
| `GET /api/v1/admin/drive` | Admin | List all files (optional `?user_email=`) |
| `DELETE /api/v1/admin/drive/{file_id}` | Admin | Delete any file |

### Auth (Device-Bound)

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/register` | Register; returns `device_key_download` - save to device |
| `POST /api/v1/auth/device-key/download` | Get encrypted key for existing users |
| `POST /api/v1/auth/login/challenge` | Get challenge for secure login |
| `POST /api/v1/auth/login/secure` | Login with device proof |
| `POST /api/v1/auth/login` | Legacy login (password only, if no device seed) |

### Email (ProtonMail-style)

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/v1/email/send` | User | Send E2E encrypted email (30/hour limit, 500KB max) |
| `GET /api/v1/email/{id}` | User | Get email (authenticated mode) |
| `POST /api/v1/email/{id}/unlock` | Public | Unlock passcode-protected email |

---

## Security Features

- **Email**: AES-256-GCM, Argon2id key derivation, zero-knowledge (server never sees plaintext)
- **Storage**: 5GB free tier, admin-configurable quotas
- **Rate limiting**: 200 req/hour per IP (production), 30 emails/hour per user
- **Brute force**: 5 failed unlock attempts → 1 hour lockout

---

## Verify

```bash
curl https://freedomos.vulcantech.co/health
curl https://freedomos.vulcantech.co/api/v1/
```

---

## Admin Example

```bash
# Login and get token
TOKEN=$(curl -s -X POST https://freedomos.vulcantech.co/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vulcantech.tech","password":"yourpass"}' | jq -r '.access_token')

# List users storage
curl -H "Authorization: Bearer $TOKEN" https://freedomos.vulcantech.co/api/v1/admin/storage

# Set user quota to 10GB
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quota_gb":10}' \
  https://freedomos.vulcantech.co/api/v1/admin/storage/user@example.com
```

# FlashDash - Complete Platform

A comprehensive platform for GrapheneOS installation, encrypted email service, and secure file storage.

## Overview

FlashDash provides:
- **GrapheneOS Flashing**: Web-based and desktop tools for installing GrapheneOS on Pixel devices
- **Encrypted Email Service**: End-to-end encrypted email with support for custom email addresses (e.g., `howie@fxmail.ai`)
- **Secure Drive**: Encrypted file storage and sharing
- **RESTful API**: Complete API for all services

## Architecture

### Domains

- **frontend.fxmail.ai** - Main web application (React frontend)
- **backend.fxmail.ai** - API server (FastAPI backend)
- **fxmail.ai** - Email service (main domain for email addresses, e.g., howie@fxmail.ai)
- **drive.fxmail.ai** - Drive/file storage service

### Technology Stack

- **Backend**: Python 3.11, FastAPI, PostgreSQL, Redis
- **Frontend**: React, TypeScript, Vite
- **Infrastructure**: Docker, Nginx
- **Security**: End-to-end encryption, JWT authentication

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Ubuntu 20.04+ VPS (for production)
- Domain names configured (for production)

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd graohen_os

# Start services
docker-compose up -d

# Access services
# Frontend: http://localhost/
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Production Deployment

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete deployment instructions.

## Features

### GrapheneOS Flashing

- Web-based flasher (browser/WebUSB)
- Desktop Electron app
- Python CLI tool
- Support for all Pixel devices
- Automatic build management

### Email Service

- Create custom email addresses (e.g., `howie@fxmail.ai`)
- End-to-end encryption
- Passcode protection
- Self-destruct emails
- Expiring access links

### Drive Service

- Encrypted file uploads
- Secure file sharing
- Passcode protection
- Expiring links
- Large file support (up to 500MB)

## API Documentation

Complete API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs` (development)
- **API Reference**: See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

## Project Structure

```
graohen_os/
├── backend/
│   ├── py-service/          # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/      # API endpoints
│   │   │   ├── core/        # Core utilities
│   │   │   ├── services/    # Business logic
│   │   │   └── routes/      # Legacy routes
│   │   └── requirements.txt
│   └── flasher.py           # CLI flasher
├── frontend/
│   ├── packages/            # Shared packages
│   │   ├── web/            # Main web app
│   │   ├── desktop/        # Electron app
│   │   ├── flasher/        # Flashing engine
│   │   └── flasher-ui/     # UI components
│   └── apps/
│       └── web-flasher/     # Web flasher app
├── docker/
│   ├── nginx.conf          # Nginx main config
│   ├── nginx-site.conf     # Domain routing
│   └── start.sh           # Startup script
├── Dockerfile              # Multi-stage build
├── docker-compose.yml      # Docker orchestration
├── README.md              # This file
├── API_DOCUMENTATION.md   # Complete API reference
└── DEPLOYMENT_GUIDE.md    # Deployment instructions
```

## Configuration

### Environment Variables

Key environment variables (see `docker-compose.yml`):

- `FRONTEND_DOMAIN` - Frontend domain (default: `frontend.fxmail.ai`)
- `BACKEND_DOMAIN` - Backend domain (default: `backend.fxmail.ai`)
- `EMAIL_DOMAIN` - Email domain (default: `fxmail.ai`)
- `DRIVE_DOMAIN` - Drive domain (default: `drive.fxmail.ai`)
- `API_BASE_URL` - API base URL
- `EXTERNAL_HTTPS_BASE_URL` - External HTTPS base URL for email links
- `CORS_ORIGINS` - Allowed CORS origins
- `ALLOWED_HOSTS` - Allowed host headers

### Backend Configuration

Backend configuration is in `backend/py-service/app/config.py` and can be overridden via environment variables or `.env` file.

Key settings:
- `EMAIL_DOMAIN` - Email domain for generating addresses
- `EXTERNAL_HTTPS_BASE_URL` - Base URL for email links
- `SECRET_KEY` - JWT secret key (change in production!)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

## Services

### Email Service

Create encrypted emails with custom addresses:

```bash
# Register user
POST /api/v1/auth/register
{
  "email": "howie@fxmail.ai",
  "password": "secure-password"
}

# Send encrypted email
POST /api/v1/email/send
Authorization: Bearer <token>
{
  "to": ["recipient@example.com"],
  "subject": "Encrypted message",
  "body": "Message content",
  "passcode": "optional-passcode",
  "expires_in_hours": 168
}
```

### Drive Service

Upload and share encrypted files:

```bash
# Upload file
POST /api/v1/drive/upload
Authorization: Bearer <token>
FormData:
  - file: <file>
  - passcode: "optional-passcode"
  - expires_in_hours: 168

# Get file info
GET /api/v1/drive/file/{file_id}
Authorization: Bearer <token>
```

### GrapheneOS Flashing

Flash GrapheneOS to Pixel devices:

```bash
# List devices
GET /devices

# List bundles
GET /bundles/for/{codename}

# Start flash job
POST /flash/execute
{
  "device_serial": "ABC123XYZ",
  "bundle_path": "/path/to/bundle"
}
```

## Development

### Backend Development

```bash
cd backend/py-service
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
pnpm install
pnpm dev:web  # Main web app
pnpm dev:desktop  # Electron app
pnpm dev:web-flasher  # Web flasher
```

## Testing

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# List devices
curl http://localhost:8000/devices

# Test email service (requires auth)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@fxmail.ai","password":"test123456"}'
```

## Security

- **End-to-End Encryption**: All email and file content is encrypted
- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: Protection against brute force attacks
- **CORS**: Configurable CORS policies
- **HTTPS**: SSL/TLS encryption (production)

## Troubleshooting

### Common Issues

1. **Port already in use**: Change ports in `docker-compose.yml`
2. **Database connection errors**: Check `DATABASE_URL` in environment
3. **Redis connection errors**: Check `REDIS_URL` in environment
4. **CORS errors**: Verify `CORS_ORIGINS` includes your domain

### Logs

```bash
# Docker logs
docker-compose logs -f

# Backend logs
docker logs flashdash -f | grep backend

# Nginx logs
docker exec flashdash tail -f /var/log/nginx/error.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]

## Bundle Management

GrapheneOS builds should be placed in the `bundles/` directory following this structure:

```
bundles/
└── {codename}/              # Device codename (e.g., panther)
    └── {version}/           # Build version (e.g., 2025122500)
        ├── image.zip        # Factory image
        └── {codename}-install-{version}/  # Extracted install files
            ├── boot.img
            ├── bootloader-*.img
            ├── radio-*.img
            ├── super_*.img (1-14)
            └── ...
```

**See [BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md) for complete details.**

## Support

For issues and questions:
- **Documentation**: 
  - [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Complete API reference
  - [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Deployment instructions
  - [BUNDLE_STRUCTURE.md](./BUNDLE_STRUCTURE.md) - Bundle structure guide
- **Issues**: Open an issue on GitHub
- **Email**: [Your Support Email]

## Changelog

### Version 1.0.0
- Initial release
- GrapheneOS flashing support
- Encrypted email service
- Secure drive service
- Complete API documentation
- Docker deployment support

---

**Last Updated**: January 2025
**Version**: 1.0.0

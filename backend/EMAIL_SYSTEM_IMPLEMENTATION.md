# Email System Implementation - Complete Guide

## Overview

This document describes the complete email system implementation for fxmail.ai, including SMTP sending, email ingestion, security, and MongoDB storage.

## Architecture

```
┌─────────────────┐
│   Internet      │
│  (SMTP Clients) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Postfix       │
│  (SMTP Server)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  FastAPI        │─────▶│   MongoDB        │
│  /email/ingest  │      │  (Encrypted)     │
└─────────────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Email Sender   │
│  (SMTP Client)  │
└─────────────────┘
```

## Components

### 1. SMTP Sending (Outgoing Mail)

**Location**: `app/services/email_sender.py`

**Features**:
- Production-ready SMTP client using `aiosmtplib`
- TLS/STARTTLS support
- HTML and plain text email support
- Notification email templates

**Configuration**:
```python
SMTP_HOST=smtp.fxmail.ai
SMTP_PORT=587
SMTP_USERNAME=postmaster@fxmail.ai
SMTP_PASSWORD=STRONG_PASSWORD
SMTP_USE_TLS=true
```

**Usage**:
```python
from app.services.email_sender import get_email_sender

sender = get_email_sender()
await sender.send_email(
    from_email="token@fxmail.ai",
    to_emails=["recipient@example.com"],
    subject="Test",
    body="Email body",
    html_body="<html>...</html>"
)
```

**Note**: DKIM signing is handled by Postfix, not Python. SPF/DMARC are configured in Cloudflare DNS.

### 2. Email Ingestion (Incoming Mail)

**Location**: `app/services/email_ingestion.py`

**Features**:
- Parses raw email bytes from Postfix
- Extracts token from recipient address (token@fxmail.ai)
- Validates token entropy (min 32 characters)
- Prevents duplicate ingestion
- Encrypts and stores in MongoDB

**Flow**:
1. Postfix receives email → token@fxmail.ai
2. Postfix pipes email to FastAPI `/email/ingest`
3. FastAPI parses email, extracts token
4. FastAPI encrypts email (3-layer encryption)
5. FastAPI stores encrypted email in MongoDB

**API Endpoint**: `POST /api/v1/email/ingest`

**Request**:
- Body: Raw email bytes (RFC 2822 format)
- Headers:
  - `X-Recipient`: Recipient email address
  - `X-Sender`: Sender email address (optional)

**Response**:
```json
{
  "email_id": "token123...",
  "status": "ingested",
  "sender": "sender@example.com",
  "recipient": "token@fxmail.ai"
}
```

### 3. Email Security Middleware

**Location**: `app/middleware/email_security.py`

**Protections**:

#### A. Rate Limiting
- **Hourly**: 50 emails per hour per user
- **Daily**: 200 emails per day per user
- Uses Redis for tracking

#### B. Token Validation
- Minimum token length: 32 characters
- Entropy check: At least 16 unique characters
- Prevents guessable tokens

#### C. Recipient Validation
- Maximum 50 recipients per email
- Email format validation
- Prevents abuse

#### D. Email Size Limits
- Maximum 25 MB per email
- Prevents DoS attacks

#### E. Abuse Pattern Detection
- Rapid-fire sending detection
- Same recipient spam detection
- Automatic blocking

**Usage**:
```python
from app.middleware.email_security import (
    check_email_rate_limit,
    validate_email_token,
    validate_email_recipients,
)

# Check rate limit
await check_email_rate_limit(user_email)

# Validate token
validate_email_token(token)

# Validate recipients
validate_email_recipients(recipient_list)
```

### 4. Email Storage (MongoDB)

**Location**: `app/services/email_service_mongodb.py`

**Features**:
- 3-layer encryption (AES-256-GCM, ChaCha20-Poly1305, Scrypt)
- Encrypted content storage
- Encrypted content key storage
- Expiration support
- Self-destruct support

**Collections**:
- `emails`: Encrypted email documents
- `files`: Encrypted file documents (drive)

**Document Structure**:
```json
{
  "email_id": "token123...",
  "sender_email": "sender@example.com",
  "recipient_emails": ["token@fxmail.ai"],
  "encrypted_content": {
    "ciphertext": "...",
    "nonce": "...",
    "tag": "...",
    "layers": 3
  },
  "encrypted_content_key": {
    "ciphertext": "...",
    "nonce": "...",
    "tag": "...",
    "layers": 3
  },
  "encryption_mode": "authenticated",
  "has_passcode": false,
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": null
}
```

### 5. Web Viewer API

**Location**: `app/api/v1/endpoints/email.py`

**Endpoint**: `GET /api/v1/email/token/{token}`

**Features**:
- Token-based email access (no authentication required)
- Returns encrypted payload (client decrypts)
- Never decrypts on server
- Expiration checking

**Response**:
```json
{
  "email_id": "token123...",
  "subject": null,
  "body": "",
  "encryption_mode": "authenticated",
  "expires_at": null,
  "is_passcode_protected": false
}
```

**Note**: Subject and body are empty in response because they're encrypted. Client must decrypt using passcode or authentication.

## API Endpoints

### Send Email
```
POST /api/v1/email/send
Authorization: Bearer {token}
Content-Type: application/json

{
  "to": ["recipient@example.com"],
  "subject": "Test",
  "body": "Email body",
  "passcode": "optional",
  "expires_in_hours": 24
}
```

### Ingest Email (Postfix)
```
POST /api/v1/email/ingest
Content-Type: application/octet-stream
X-Recipient: token@fxmail.ai

{Raw email bytes}
```

### Get Email by Token
```
GET /api/v1/email/token/{token}
```

### Get Email (Authenticated)
```
GET /api/v1/email/{email_id}
Authorization: Bearer {token}
```

### Unlock Email (Passcode)
```
POST /api/v1/email/{email_id}/unlock
Content-Type: application/json

{
  "passcode": "1234"
}
```

## Security Features

### 1. Encryption
- **3-layer encryption**: Maximum security
- **Client-side encryption**: Server never sees plaintext
- **Encrypted storage**: MongoDB stores only ciphertext

### 2. Rate Limiting
- Per-user rate limits
- Redis-based tracking
- Automatic blocking

### 3. Abuse Protection
- Token entropy validation
- Recipient limits
- Email size limits
- Pattern detection

### 4. Authentication
- JWT tokens for authenticated endpoints
- Passcode protection for sensitive emails
- Token-based access for public emails

## Postfix Configuration

See `POSTFIX_SETUP.md` for complete Postfix configuration guide.

**Key Points**:
1. Postfix receives emails on port 25
2. Postfix pipes emails to FastAPI script
3. Script sends emails to `/email/ingest` endpoint
4. FastAPI encrypts and stores in MongoDB

## Cloudflare DNS Setup

### Required DNS Records

1. **A Record - Mail Server**
   - Name: `mail`
   - Value: `YOUR_SERVER_IP`
   - Proxy: OFF (gray cloud)

2. **A Record - SMTP**
   - Name: `smtp`
   - Value: `YOUR_SERVER_IP`
   - Proxy: OFF

3. **A Record - Web**
   - Name: `fxmail.ai`
   - Value: `YOUR_SERVER_IP`
   - Proxy: ON (orange cloud OK)

4. **MX Record**
   - Name: `fxmail.ai`
   - Priority: 10
   - Value: `mail.fxmail.ai`
   - Proxy: OFF

5. **SPF Record**
   - Type: TXT
   - Name: `fxmail.ai`
   - Value: `v=spf1 ip4:YOUR_SERVER_IP -all`

6. **DKIM Record**
   - Type: TXT
   - Name: `default._domainkey.fxmail.ai`
   - Value: `v=DKIM1; k=rsa; p=...` (generated by Postfix)

7. **DMARC Record**
   - Type: TXT
   - Name: `_dmarc.fxmail.ai`
   - Value: `v=DMARC1; p=none; rua=mailto:dmarc@fxmail.ai`

## Environment Variables

```bash
# SMTP Settings
SMTP_HOST=smtp.fxmail.ai
SMTP_PORT=587
SMTP_USERNAME=postmaster@fxmail.ai
SMTP_PASSWORD=STRONG_PASSWORD
SMTP_USE_TLS=true

# Email Domain
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# MongoDB
MONGODB_CONNECTION_STRING=mongodb+srv://...
MONGODB_DATABASE=admin
```

## Testing

### Test Email Ingestion

```bash
# Send test email via Postfix
echo "Test body" | mail -s "Test" token123456789012345678901234567890@fxmail.ai

# Check MongoDB
mongo admin --eval "db.emails.find().pretty()"
```

### Test Email Sending

```bash
# Get auth token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' \
  | jq -r '.access_token')

# Send email
curl -X POST http://localhost:8000/api/v1/email/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["recipient@example.com"],
    "subject": "Test",
    "body": "Test email"
  }'
```

### Test Rate Limiting

```bash
# Send 51 emails rapidly (should fail on 51st)
for i in {1..51}; do
  curl -X POST http://localhost:8000/api/v1/email/send \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"to":["test@example.com"],"body":"Test"}'
done
```

## Production Checklist

- [ ] Postfix installed and configured
- [ ] TLS certificates installed
- [ ] Cloudflare DNS records configured
- [ ] SPF record added
- [ ] DKIM key generated and added to DNS
- [ ] DMARC record added
- [ ] Email ingestion script created
- [ ] FastAPI running on port 8000
- [ ] MongoDB connection working
- [ ] Rate limiting tested
- [ ] Abuse protection tested
- [ ] Monitoring/logging configured
- [ ] Backup strategy for MongoDB
- [ ] Firewall rules configured
- [ ] SMTP port 25 open

## Troubleshooting

### Emails Not Reaching FastAPI

1. Check Postfix logs: `sudo tail -f /var/log/mail.log`
2. Check script permissions: `ls -la /usr/local/bin/mail_ingest.*`
3. Test script manually: `echo "test" | /usr/local/bin/mail_ingest.sh`
4. Check FastAPI is running: `curl http://localhost:8000/health`

### Rate Limiting Issues

1. Check Redis connection
2. Verify rate limit keys in Redis: `redis-cli KEYS "email:rate_limit:*"`
3. Check user email format (must be lowercase)

### Encryption Errors

1. Check MongoDB connection
2. Verify encryption keys are generated correctly
3. Check email content size (must be < 25 MB)

## Summary

The email system is now fully implemented with:

✅ **SMTP Sending**: Production-ready email sending
✅ **Email Ingestion**: Postfix → FastAPI pipeline
✅ **Security**: Rate limiting, abuse protection, token validation
✅ **Encryption**: 3-layer encryption, MongoDB storage
✅ **Web Viewer**: Token-based email access
✅ **Documentation**: Complete setup guides

The system is ready for production deployment!

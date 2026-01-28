# Postfix Setup Guide for Ubuntu - Step by Step

This guide provides step-by-step instructions to configure Postfix on Ubuntu to pipe incoming emails to FastAPI.

## Prerequisites

- Ubuntu 20.04+ (tested on 20.04, 22.04, 24.04)
- Postfix already installed (`sudo apt-get install postfix`)
- FastAPI backend running on `localhost:8000`
- Python 3.8+ installed
- Root or sudo access

## Overview

```
Internet → Postfix (SMTP) → Email Ingestion Script → FastAPI /email/ingest → MongoDB
```

**What we're doing:**
1. Configure Postfix to receive emails for `@fxmail.ai` domain
2. Create a script that pipes emails to FastAPI
3. Configure Postfix to use this script for all incoming emails
4. Test the setup

---

## Step 1: Verify Postfix Installation

```bash
# Check if Postfix is installed
sudo postfix status

# If not installed, install it
sudo apt-get update
sudo apt-get install -y postfix mailutils

# During installation, select "Internet Site"
# Enter your domain: fxmail.ai
```

**Expected output:**
```
postfix/postfix-script: the Postfix mail system is running: PID: 12345
```

---

## Step 2: Backup Original Configuration

```bash
# Backup original Postfix config
sudo cp /etc/postfix/main.cf /etc/postfix/main.cf.backup
sudo cp /etc/postfix/master.cf /etc/postfix/master.cf.backup
```

---

## Step 3: Configure Postfix Main Config

Edit `/etc/postfix/main.cf`:

```bash
sudo nano /etc/postfix/main.cf
```

**Add or modify these settings:**

```conf
# Basic settings
myhostname = mail.fxmail.ai
mydomain = fxmail.ai
myorigin = $mydomain
inet_interfaces = all
inet_protocols = ipv4

# Virtual alias domain (catch-all for token@fxmail.ai)
virtual_alias_domains = fxmail.ai
virtual_alias_maps = hash:/etc/postfix/virtual

# Transport map (pipe to FastAPI)
transport_maps = hash:/etc/postfix/transport

# Mailbox command (pipe to FastAPI script)
mailbox_command = /usr/local/bin/mail_ingest.py

# Security settings
smtpd_helo_required = yes
smtpd_recipient_restrictions = 
    permit_mynetworks,
    reject_unauth_destination,
    permit

# TLS settings (if you have certificates)
# smtpd_tls_cert_file = /etc/ssl/certs/fxmail.ai.crt
# smtpd_tls_key_file = /etc/ssl/private/fxmail.ai.key
# smtpd_tls_security_level = may
# smtpd_tls_auth_only = yes

# Message size limit (25MB)
message_size_limit = 26214400

# Queue settings
maximal_queue_lifetime = 7d
bounce_queue_lifetime = 7d
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

---

## Step 4: Create Virtual Alias Map

Create the virtual alias file:

```bash
sudo nano /etc/postfix/virtual
```

**Add this line:**

```
# Catch-all: all emails to @fxmail.ai go to FastAPI
@fxmail.ai    catchall
```

**Compile the virtual map:**

```bash
sudo postmap /etc/postfix/virtual
```

---

## Step 5: Create Transport Map

Create the transport file:

```bash
sudo nano /etc/postfix/transport
```

**Add this line:**

```
# Route all fxmail.ai emails to FastAPI pipe
fxmail.ai    fastapi:
```

**Compile the transport map:**

```bash
sudo postmap /etc/postfix/transport
```

---

## Step 6: Configure Master Config

Edit `/etc/postfix/master.cf`:

```bash
sudo nano /etc/postfix/master.cf
```

**Find the section with `smtp` and add this AFTER it (around line 100):**

```
# FastAPI email ingestion transport
fastapi    unix  -       n       n       -       -       pipe
  flags=F user=www-data argv=/usr/local/bin/mail_ingest.py
  environment=RECIPIENT=${recipient} SENDER=${sender} SIZE=${size}
```

**Important notes:**
- `user=www-data` - Change this to the user running FastAPI (or `nobody` for security)
- `flags=F` - Forward the original envelope sender
- The script will receive email via stdin

**Save and exit**

---

## Step 7: Create Email Ingestion Script

Create the Python script that pipes emails to FastAPI:

```bash
sudo nano /usr/local/bin/mail_ingest.py
```

**Paste this content:**

```python
#!/usr/bin/env python3
"""
Postfix email ingestion script for FastAPI

This script receives emails from Postfix via stdin and sends them to FastAPI.
"""

import sys
import os
import requests
import json

def main():
    # Read email from stdin (Postfix pipes it here)
    try:
        email_body = sys.stdin.buffer.read()
    except Exception as e:
        print(f"Error reading email: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get headers from environment (Postfix sets these)
    recipient = os.environ.get('RECIPIENT', '')
    sender = os.environ.get('SENDER', '')
    size = os.environ.get('SIZE', '0')
    
    # Validate recipient
    if not recipient:
        print("Error: RECIPIENT not set", file=sys.stderr)
        sys.exit(1)
    
    # FastAPI endpoint
    fastapi_url = 'http://localhost:8000/api/v1/email/ingest'
    
    # Send to FastAPI
    try:
        response = requests.post(
            fastapi_url,
            data=email_body,
            headers={
                'Content-Type': 'application/octet-stream',
                'X-Recipient': recipient,
                'X-Sender': sender,
                'X-Size': size,
            },
            timeout=30,
        )
        
        if response.status_code == 201:
            result = response.json()
            email_id = result.get('email_id', 'unknown')
            print(f"Email ingested successfully: {email_id[:16]}...", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"Error: HTTP {response.status_code} - {response.text}", file=sys.stderr)
            sys.exit(1)
            
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to FastAPI at http://localhost:8000", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Error: FastAPI request timed out", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error sending to FastAPI: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

**Make it executable:**

```bash
sudo chmod +x /usr/local/bin/mail_ingest.py
sudo chown www-data:www-data /usr/local/bin/mail_ingest.py
```

**Note:** Change `www-data` to the user running FastAPI if different.

---

## Step 8: Install Python Requests Library

The script needs the `requests` library:

```bash
# Install requests for Python 3
sudo apt-get install -y python3-requests

# Or use pip if available
sudo pip3 install requests
```

---

## Step 9: Test Postfix Configuration

```bash
# Check Postfix configuration for errors
sudo postfix check

# If there are errors, fix them before proceeding
```

**Expected output:**
```
(no output means success)
```

---

## Step 10: Reload Postfix

```bash
# Reload Postfix to apply changes
sudo postfix reload

# Or restart if reload doesn't work
sudo systemctl restart postfix

# Check status
sudo systemctl status postfix
```

**Expected output:**
```
● postfix.service - Postfix Mail Transport Agent
     Loaded: loaded
     Active: active (running)
```

---

## Step 11: Test Email Ingestion

### Test 1: Send Test Email Locally

```bash
# Send a test email
echo "Test email body" | mail -s "Test Subject" token123456789012345678901234567890@fxmail.ai

# Check Postfix logs
sudo tail -f /var/log/mail.log
```

**Expected log output:**
```
postfix/pipe: ...: to=<token123456789012345678901234567890@fxmail.ai>, ...
```

### Test 2: Check FastAPI Logs

```bash
# Check if FastAPI received the email
# Look for logs showing email ingestion
tail -f /path/to/fastapi/logs/app.log
```

### Test 3: Verify MongoDB Storage

```bash
# Connect to MongoDB
mongo admin

# Or if using MongoDB Atlas, use mongosh
mongosh "mongodb+srv://..."

# Find the email
db.emails.find({"email_id": "token123456789012345678901234567890"}).pretty()
```

---

## Step 12: Configure Firewall (If Applicable)

If you have a firewall, allow SMTP traffic:

```bash
# Allow SMTP (port 25)
sudo ufw allow 25/tcp

# Allow submission (port 587) if using
sudo ufw allow 587/tcp

# Check firewall status
sudo ufw status
```

---

## Step 13: Configure DNS (Cloudflare)

For production, configure DNS records in Cloudflare:

### A Records (Proxy OFF - Gray Cloud)
- `mail.fxmail.ai` → Your server IP
- `smtp.fxmail.ai` → Your server IP

### MX Record (Proxy OFF)
- Name: `fxmail.ai`
- Priority: `10`
- Value: `mail.fxmail.ai`

### SPF Record (TXT)
- Name: `fxmail.ai`
- Value: `v=spf1 ip4:YOUR_SERVER_IP -all`

### DKIM Record (TXT)
- Generate DKIM key in Postfix, then add to DNS
- Name: `default._domainkey.fxmail.ai`
- Value: `v=DKIM1; k=rsa; p=...`

### DMARC Record (TXT)
- Name: `_dmarc.fxmail.ai`
- Value: `v=DMARC1; p=none; rua=mailto:dmarc@fxmail.ai`

---

## Troubleshooting

### Problem: Emails Not Reaching FastAPI

**Check Postfix logs:**
```bash
sudo tail -f /var/log/mail.log | grep -i error
```

**Check script permissions:**
```bash
ls -la /usr/local/bin/mail_ingest.py
# Should show: -rwxr-xr-x 1 www-data www-data ...
```

**Test script manually:**
```bash
# Test with a sample email
echo "From: test@example.com
To: token@fxmail.ai
Subject: Test

Test body" | sudo -u www-data /usr/local/bin/mail_ingest.py
```

**Check FastAPI is running:**
```bash
curl http://localhost:8000/health
```

### Problem: Permission Denied

**Fix script ownership:**
```bash
sudo chown www-data:www-data /usr/local/bin/mail_ingest.py
sudo chmod +x /usr/local/bin/mail_ingest.py
```

**Check Postfix user:**
```bash
# In /etc/postfix/master.cf, ensure user matches FastAPI user
# Or use 'nobody' for better security
```

### Problem: FastAPI Connection Refused

**Check FastAPI is running:**
```bash
sudo systemctl status your-fastapi-service
# Or
ps aux | grep uvicorn
```

**Check FastAPI is listening on localhost:8000:**
```bash
sudo netstat -tlnp | grep 8000
# Should show: tcp 0 0 127.0.0.1:8000 ...
```

### Problem: Emails Going to Queue

**Check mail queue:**
```bash
sudo mailq
```

**Process queue:**
```bash
sudo postqueue -f
```

**Check queue logs:**
```bash
sudo tail -f /var/log/mail.log | grep queue
```

### Problem: DNS Not Resolving

**Test DNS:**
```bash
nslookup mail.fxmail.ai
dig mx fxmail.ai
```

**Wait for DNS propagation** (can take up to 48 hours)

---

## Verification Checklist

- [ ] Postfix installed and running
- [ ] `/etc/postfix/main.cf` configured
- [ ] `/etc/postfix/virtual` created and compiled
- [ ] `/etc/postfix/transport` created and compiled
- [ ] `/etc/postfix/master.cf` updated with fastapi transport
- [ ] `/usr/local/bin/mail_ingest.py` created and executable
- [ ] Python requests library installed
- [ ] Postfix configuration validated (`postfix check`)
- [ ] Postfix reloaded/restarted
- [ ] Test email sent successfully
- [ ] Email appears in MongoDB
- [ ] Firewall configured (if applicable)
- [ ] DNS records configured (for production)

---

## Production Recommendations

1. **Security:**
   - Use TLS certificates for SMTP
   - Configure SPF, DKIM, DMARC records
   - Set up fail2ban for SMTP protection
   - Use strong passwords for SMTP authentication

2. **Monitoring:**
   - Set up log rotation for `/var/log/mail.log`
   - Monitor Postfix queue size
   - Set up alerts for failed email ingestion
   - Monitor FastAPI logs

3. **Performance:**
   - Tune Postfix queue settings
   - Set appropriate message size limits
   - Configure connection limits

4. **Backup:**
   - Backup `/etc/postfix/` configuration
   - Backup MongoDB regularly
   - Document your DNS settings

---

## Quick Reference Commands

```bash
# Check Postfix status
sudo postfix status

# Check configuration
sudo postfix check

# Reload Postfix
sudo postfix reload

# Restart Postfix
sudo systemctl restart postfix

# View mail queue
sudo mailq

# Process queue
sudo postqueue -f

# View logs
sudo tail -f /var/log/mail.log

# Test email locally
echo "test" | mail -s "test" token@fxmail.ai

# Check script
sudo -u www-data /usr/local/bin/mail_ingest.py
```

---

## Support

If you encounter issues:

1. Check Postfix logs: `/var/log/mail.log`
2. Check FastAPI logs
3. Verify script permissions and ownership
4. Test script manually
5. Verify FastAPI is running and accessible

For more details, see `EMAIL_SYSTEM_IMPLEMENTATION.md`.

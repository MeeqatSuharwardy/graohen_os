# Email Domain & Mail Server Setup

This guide covers configuring your own mail server (Postfix) for **fxmail.ai** (or your domain) to send and receive emails from Gmail, Yahoo, and other providers—**without third-party services**.

---

## Overview

| Flow | Direction | Description |
|------|-----------|-------------|
| **Outbound** | Your server → Gmail/Yahoo | Send notification emails (link-only or link+passcode) |
| **Inbound** | Gmail/Yahoo → Your server | Receive emails sent to `token@fxmail.ai` |

---

## Part 1: DNS Records (Domain Side)

Configure these records at your domain registrar (e.g., Cloudflare, Namecheap, GoDaddy).

### A Records (Required)

```
fxmail.ai     A    <YOUR_SERVER_IP>
mail.fxmail.ai A   <YOUR_SERVER_IP>
smtp.fxmail.ai A   <YOUR_SERVER_IP>
```

### MX Record (Required for receiving)

```
fxmail.ai     MX   10 mail.fxmail.ai
```

This tells Gmail/Yahoo where to deliver emails sent to `*@fxmail.ai`.

### SPF Record (Reduce spam classification)

```
fxmail.ai     TXT   "v=spf1 mx a ip4:<YOUR_SERVER_IP> ~all"
```

### DKIM Record (Improve deliverability)

1. Generate DKIM keys (see Part 2 - Postfix setup)
2. Add TXT record:

```
selector._domainkey.fxmail.ai   TXT   "v=DKIM1; k=rsa; p=<YOUR_PUBLIC_KEY>"
```

Replace `selector` with your chosen name (e.g., `mail`) and paste the public key.

### DMARC Record (Optional - policy for failed auth)

```
_dmarc.fxmail.ai   TXT   "v=DMARC1; p=none; rua=mailto:admin@fxmail.ai"
```

---

## Part 2: Postfix Setup (VPS/Server)

### 1. Install Postfix

```bash
sudo apt update
sudo apt install postfix mailutils -y
# Choose "Internet Site" and set your domain when prompted
```

### 2. Configure Postfix for sending

Edit `/etc/postfix/main.cf`:

```
# Domain
myhostname = mail.fxmail.ai
mydomain = fxmail.ai
myorigin = $mydomain

# Network
inet_interfaces = all
inet_protocols = ipv4

# Relay (if using external SMTP for sending - or use local)
# relayhost = [smtp.gmail.com]:587  # Uncomment if relaying via Gmail
# smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
# smtp_sasl_auth_enable = yes
# smtp_use_tls = yes

# Receiving - virtual mailbox
virtual_mailbox_domains = fxmail.ai
virtual_mailbox_maps = hash:/etc/postfix/virtual_mailbox
virtual_alias_maps = hash:/etc/postfix/virtual_alias

# Mailbox command - pipe to FastAPI
mailbox_command = /usr/local/bin/fxmail-ingest-pipe
```

### 3. Virtual mailbox (catch-all for token@domain)

Create `/etc/postfix/virtual_mailbox`:

```
# Accept any address at your domain (token@fxmail.ai)
@fxmail.ai    OK
```

Create `/etc/postfix/virtual_alias` (or leave empty if using mailbox_command):

```
# Optional: route to a single mailbox
# @fxmail.ai    catchall@local
```

```bash
sudo postmap /etc/postfix/virtual_mailbox
sudo postmap /etc/postfix/virtual_alias
```

### 4. Pipe script - Postfix → FastAPI

Create `/usr/local/bin/fxmail-ingest-pipe`:

```bash
#!/bin/bash
# Pipe incoming email to FastAPI /email/ingest

# Read raw email from stdin
RAW_EMAIL=$(cat)

# Get recipient from Postfix env (set by master.cf)
RECIPIENT="${recipient:-$1}"

# Call FastAPI
curl -s -X POST "http://127.0.0.1:8000/api/v1/email/ingest" \
  -H "Content-Type: application/octet-stream" \
  -H "X-Recipient: ${RECIPIENT}" \
  --data-binary @- <<< "$RAW_EMAIL"
```

Make executable:

```bash
sudo chmod +x /usr/local/bin/fxmail-ingest-pipe
```

### 5. Configure Postfix master.cf for piping

Edit `/etc/postfix/master.cf`, add:

```
# Pipe to FastAPI for token@domain
fxmail.ai unix - n n - - pipe
  flags=Rq user=www-data argv=/usr/local/bin/fxmail-ingest-pipe ${recipient}
```

Or use a transport map. Simpler approach – use `mailbox_command` with a script that passes recipient.

For `mailbox_command`, Postfix sets `$HOME`, `$USER`, `$recipient`, etc. Create `/usr/local/bin/fxmail-ingest-pipe`:

```bash
#!/bin/bash
# Read from stdin, POST to FastAPI
RECIPIENT="$recipient"
curl -s -X POST "http://127.0.0.1:8000/api/v1/email/ingest" \
  -H "Content-Type: application/octet-stream" \
  -H "X-Recipient: $RECIPIENT" \
  --data-binary @-
```

### 6. Restart Postfix

```bash
sudo systemctl restart postfix
sudo systemctl status postfix
```

---

## Part 3: Backend Configuration

### .env (or environment)

```bash
# Email domain
EMAIL_DOMAIN=fxmail.ai
EXTERNAL_HTTPS_BASE_URL=https://fxmail.ai

# SMTP - for sending notifications (use same server or separate)
SMTP_HOST=mail.fxmail.ai   # or smtp.fxmail.ai
SMTP_PORT=587
SMTP_USERNAME=noreply@fxmail.ai
SMTP_PASSWORD=}+2kA&"SQ5jBoTr9/hxT|bXg[v}K^D1Ms`Vl(0cWX)5GXcc5
SMTP_USE_TLS=true
SMTP_FROM=noreply@fxmail.ai
```

---

## Part 4: Ingest Endpoint

The `/api/v1/email/ingest` endpoint accepts:

- **Method:** POST
- **Body:** Raw email bytes (from Postfix pipe)
- **Headers:** `X-Recipient: token@fxmail.ai` (optional, parsed from body if omitted)

It extracts the token from the recipient address, encrypts the content, and stores it in PostgreSQL.

---

## Part 5: Testing

### Test outbound (send notification to Gmail/Yahoo)

```bash
# Register and get token, then:
curl -X POST "https://your-api/api/v1/email/send" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": ["me@gmail.com"],
    "subject": "Test",
    "body": "Secret content",
    "notification_delivery": "link_only"
  }'
```

Check the recipient inbox for the notification with the secure link.

### Test inbound (receive from Gmail)

1. Create an email address via API (e.g., you get `abc123xyz@fxmail.ai`)
2. From Gmail, send an email TO `abc123xyz@fxmail.ai`
3. Check your ingest logs; the email should be stored
4. Visit `https://fxmail.ai/email/abc123xyz` and unlock with passcode `abc123xyz`

---

## Firewall

Ensure these ports are open:

- **25** – SMTP (inbound, for receiving)
- **587** – Submission (outbound, for sending)
- **80/443** – HTTP/HTTPS (API, web viewer)

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Emails not received | MX record, Postfix logs (`journalctl -u postfix -f`) |
| Spam folder | SPF, DKIM, DMARC, server reputation |
| Send fails | SMTP credentials, firewall, TLS |
| Ingest 404 | FastAPI running, correct URL in pipe script |

---

## Summary Checklist

- [ ] A records for domain, mail, smtp
- [ ] MX record pointing to mail server
- [ ] SPF TXT record
- [ ] DKIM keys and TXT record (optional but recommended)
- [ ] Postfix installed and configured
- [ ] Pipe script created and executable
- [ ] FastAPI running and reachable from Postfix
- [ ] .env has SMTP_* and EMAIL_DOMAIN set

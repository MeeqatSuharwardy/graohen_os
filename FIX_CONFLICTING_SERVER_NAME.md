# Fix Conflicting Server Name Error

## Problem

The error shows:
```
conflicting server name "freedomos.vulcantech.co" on 0.0.0.0:80, ignored
conflicting server name "freedomos.vulcantech.co" on 0.0.0.0:443, ignored
```

This means there are **multiple nginx configuration files** defining the same `server_name`, and nginx is ignoring the duplicate.

## Solution: Find and Remove Duplicates

### Step 1: Find All Configurations with freedomos.vulcantech.co

```bash
# Search for all occurrences
sudo grep -r "freedomos.vulcantech.co" /etc/nginx/sites-enabled/
sudo grep -r "freedomos.vulcantech.co" /etc/nginx/sites-available/
```

### Step 2: List All Enabled Sites

```bash
ls -la /etc/nginx/sites-enabled/
```

### Step 3: Check Each File

```bash
# Check each enabled site
for file in /etc/nginx/sites-enabled/*; do
    echo "=== $file ==="
    sudo grep -A 5 "server_name.*freedomos" "$file" || echo "No freedomos config"
    echo ""
done
```

### Step 4: Remove Duplicates

Keep only ONE configuration file with `freedomos.vulcantech.co`. Remove or comment out the others.

**Common locations:**
- `/etc/nginx/sites-enabled/default` - might have freedomos config
- `/etc/nginx/sites-enabled/freedomos` - your new config
- `/etc/nginx/sites-enabled/000-default` - default site
- Other custom config files

### Step 5: Fix the Configuration

**Option A: Remove from default site**

```bash
# Check default site
sudo cat /etc/nginx/sites-enabled/default

# If it has freedomos.vulcantech.co, remove those server blocks
sudo nano /etc/nginx/sites-enabled/default
# Or disable default site entirely:
sudo rm /etc/nginx/sites-enabled/default
```

**Option B: Keep only freedomos config**

```bash
# Disable all other sites temporarily
cd /etc/nginx/sites-enabled/
sudo mv default default.bak 2>/dev/null
sudo mv 000-default 000-default.bak 2>/dev/null

# Keep only freedomos
ls -la
# Should only see freedomos symlink
```

### Step 6: Test and Reload

```bash
# Test configuration
sudo nginx -t

# If test passes, reload
sudo systemctl reload nginx

# Test domain
curl https://freedomos.vulcantech.co/health
```

---

## Quick Fix Script

Run this script to automatically find and fix duplicates:

```bash
#!/bin/bash
echo "Finding all freedomos.vulcantech.co configurations..."

# Find all files with freedomos config
FILES=$(sudo grep -rl "freedomos.vulcantech.co" /etc/nginx/sites-enabled/ 2>/dev/null)

if [ -z "$FILES" ]; then
    echo "No freedomos config found in sites-enabled"
    exit 1
fi

echo "Found in these files:"
echo "$FILES"
echo ""

# Check if freedomos site exists
if [ -L "/etc/nginx/sites-enabled/freedomos" ]; then
    echo "✅ freedomos config exists"
    KEEP_FILE="/etc/nginx/sites-enabled/freedomos"
else
    echo "⚠️  freedomos config not found, creating..."
    # Create it if missing
    sudo tee /etc/nginx/sites-available/freedomos > /dev/null << 'EOF'
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;
    
    # SSL certs commented for Cloudflare
    # ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:81;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
    sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos
    KEEP_FILE="/etc/nginx/sites-enabled/freedomos"
fi

# Remove freedomos config from other files
for file in $FILES; do
    if [ "$file" != "$KEEP_FILE" ]; then
        echo "Removing freedomos config from: $file"
        # Backup file
        sudo cp "$file" "${file}.backup"
        # Remove server blocks with freedomos
        sudo sed -i '/server_name.*freedomos/,/^}/d' "$file"
    fi
done

# Disable default site if it exists and conflicts
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo "Disabling default site..."
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test and reload
echo ""
echo "Testing nginx configuration..."
if sudo nginx -t; then
    echo "✅ Configuration valid"
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded"
    echo ""
    echo "Test: curl https://freedomos.vulcantech.co/health"
else
    echo "❌ Configuration has errors"
    exit 1
fi
```

---

## Manual Fix Steps

**1. Find duplicates:**
```bash
sudo grep -r "server_name.*freedomos" /etc/nginx/sites-enabled/
```

**2. Check each file:**
```bash
sudo cat /etc/nginx/sites-enabled/default | grep -A 10 freedomos
sudo cat /etc/nginx/sites-enabled/freedomos | grep -A 10 freedomos
```

**3. Remove freedomos from default site:**
```bash
sudo nano /etc/nginx/sites-enabled/default
# Remove or comment out any server blocks with freedomos.vulcantech.co
```

**4. Or disable default site:**
```bash
sudo rm /etc/nginx/sites-enabled/default
```

**5. Ensure only freedomos config exists:**
```bash
ls -la /etc/nginx/sites-enabled/
# Should only see freedomos (and maybe other non-conflicting sites)
```

**6. Test and reload:**
```bash
sudo nginx -t
sudo systemctl reload nginx
curl https://freedomos.vulcantech.co/health
```

---

## Most Common Cause

The **default nginx site** (`/etc/nginx/sites-enabled/default`) likely has a server block for `freedomos.vulcantech.co`. 

**Quick fix:**
```bash
# Disable default site
sudo rm /etc/nginx/sites-enabled/default

# Ensure freedomos config is enabled
sudo ln -sf /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/freedomos

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

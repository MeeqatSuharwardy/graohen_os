# Fix Port 80 Conflict Error

## Problem
Port 80 is already in use by another service, preventing Docker from binding to it.

## Solution Options

### Option 1: Find and Stop the Service Using Port 80 (Recommended)

**Step 1: Check what's using port 80**

```bash
# Check what process is using port 80
sudo lsof -i :80
# or
sudo netstat -tlnp | grep :80
# or
sudo ss -tlnp | grep :80
```

**Step 2: Stop the conflicting service**

Common services that use port 80:
- **Nginx** (system service)
- **Apache** (httpd)
- **Another Docker container**

**If it's Nginx:**
```bash
sudo systemctl stop nginx
sudo systemctl disable nginx  # Prevent it from starting on boot
```

**If it's Apache:**
```bash
sudo systemctl stop apache2
sudo systemctl disable apache2
```

**If it's another Docker container:**
```bash
# List running containers
docker ps

# Stop the conflicting container
docker stop <container_name_or_id>
```

**Step 3: Verify port 80 is free**

```bash
sudo lsof -i :80
# Should return nothing if port is free
```

**Step 4: Start your container**

```bash
cd ~/graohen_os
docker-compose up -d
```

---

### Option 2: Change Docker Port Mapping (Alternative)

If you can't stop the service using port 80, you can map Docker to a different port:

**Update docker-compose.yml:**

```yaml
ports:
  - "8080:80"  # Map host port 8080 to container port 80
  - "443:443"
  - "8000:8000"
```

Then access your frontend at `http://YOUR_VPS_IP:8080` instead of port 80.

**Or use a different port for HTTP:**

```yaml
ports:
  - "3000:80"  # Use port 3000 instead
  - "443:443"
  - "8000:8000"
```

---

### Option 3: Use Nginx as Reverse Proxy (Advanced)

If you want to keep system nginx running, configure it as a reverse proxy:

**1. Stop Docker container:**
```bash
docker-compose down
```

**2. Configure system nginx:**

```bash
sudo nano /etc/nginx/sites-available/freedomos
```

Add:
```nginx
server {
    listen 80;
    server_name freedomos.vulcantech.co;

    location / {
        proxy_pass http://127.0.0.1:8080;  # Forward to Docker container
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**3. Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/freedomos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**4. Update docker-compose.yml to use port 8080:**
```yaml
ports:
  - "8080:80"  # Internal port mapping
```

**5. Start Docker:**
```bash
docker-compose up -d
```

---

## Quick Fix Script

Run this script to automatically find and stop the service using port 80:

```bash
#!/bin/bash
echo "Checking what's using port 80..."

# Find process using port 80
PID=$(sudo lsof -t -i:80)

if [ -z "$PID" ]; then
    echo "Port 80 is free!"
    exit 0
fi

echo "Port 80 is in use by PID: $PID"
echo "Process details:"
ps -p $PID -o pid,ppid,cmd

# Check if it's nginx
if systemctl is-active --quiet nginx; then
    echo "Stopping nginx..."
    sudo systemctl stop nginx
    sudo systemctl disable nginx
    echo "✅ Nginx stopped"
elif systemctl is-active --quiet apache2; then
    echo "Stopping apache2..."
    sudo systemctl stop apache2
    sudo systemctl disable apache2
    echo "✅ Apache stopped"
else
    echo "⚠️  Unknown service. Please stop it manually:"
    echo "sudo kill $PID"
    exit 1
fi

echo "Verifying port 80 is free..."
sleep 2
if sudo lsof -t -i:80; then
    echo "❌ Port 80 still in use"
else
    echo "✅ Port 80 is now free"
    echo "You can now run: docker-compose up -d"
fi
```

---

## Most Common Solution

**99% of the time, it's system nginx:**

```bash
# Stop system nginx
sudo systemctl stop nginx
sudo systemctl disable nginx

# Verify port is free
sudo lsof -i :80

# Start Docker container
cd ~/graohen_os
docker-compose up -d
```

---

## Verify After Fix

```bash
# Check container is running
docker ps

# Check port 80 is bound to Docker
sudo lsof -i :80 | grep docker

# Test the service
curl http://localhost/health
curl http://freedomos.vulcantech.co/health
```

---

## Prevention

To prevent this in the future:

1. **Disable system nginx/apache** if you're using Docker:
   ```bash
   sudo systemctl disable nginx
   sudo systemctl disable apache2
   ```

2. **Check before starting Docker:**
   ```bash
   sudo lsof -i :80
   ```

3. **Use Docker's port mapping** if you need both services running.

# Redis Setup for Backend

## Problem

Registration endpoint fails with:
```
ConnectionError: Error 111 connecting to localhost:6379. 111.
```

This means Redis is not running on the server.

## Solution

### Step 1: Check if Redis is Installed

```bash
redis-cli --version
```

If not installed:
```bash
sudo apt update
sudo apt install -y redis-server
```

### Step 2: Start Redis Service

```bash
# Start Redis
sudo systemctl start redis-server

# Enable Redis to start automatically on boot
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server
```

**Expected output**: Should show `active (running)`

### Step 3: Verify Redis is Working

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG

# Check Redis is listening on port 6379
sudo netstat -tlnp | grep 6379
# Should show: tcp 0 0 127.0.0.1:6379 ...
```

### Step 4: Restart Backend Service

```bash
# Restart backend to reconnect to Redis
sudo systemctl restart flashdash-backend

# Check backend status
sudo systemctl status flashdash-backend

# Check backend logs
sudo journalctl -u flashdash-backend -n 50 --no-pager
```

### Step 5: Test Registration

```bash
# Test registration endpoint
curl -X POST https://freedomos.vulcantech.co/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@fxmail.ai", "password": "testpass123", "full_name": "Test User"}'
```

## Redis Configuration

### Check Redis Config

```bash
# View Redis config
sudo nano /etc/redis/redis.conf
```

**Important settings:**
- `bind 127.0.0.1` - Only listen on localhost (secure)
- `port 6379` - Default Redis port
- `protected-mode yes` - Enable protection mode

### Redis Service Management

```bash
# Start Redis
sudo systemctl start redis-server

# Stop Redis
sudo systemctl stop redis-server

# Restart Redis
sudo systemctl restart redis-server

# Check status
sudo systemctl status redis-server

# View logs
sudo journalctl -u redis-server -f
```

## Troubleshooting

### Redis Won't Start

```bash
# Check Redis logs
sudo journalctl -u redis-server -n 50

# Check if port 6379 is already in use
sudo lsof -i :6379

# Test Redis config
redis-server /etc/redis/redis.conf --test-memory 1
```

### Connection Still Failing

1. **Verify Redis is running:**
   ```bash
   sudo systemctl status redis-server
   ```

2. **Check Redis is listening:**
   ```bash
   sudo netstat -tlnp | grep 6379
   ```

3. **Test connection manually:**
   ```bash
   redis-cli -h 127.0.0.1 -p 6379 ping
   ```

4. **Check backend .env file:**
   ```bash
   cat /root/graohen_os/backend/py-service/.env | grep REDIS
   ```
   
   Should have:
   ```
   REDIS_URL=redis://localhost:6379/0
   ```

### Firewall Issues

If Redis needs to be accessible from outside (not recommended for production):

```bash
# Allow Redis port (only if needed)
sudo ufw allow 6379/tcp

# But better: Keep Redis on localhost only
# Edit /etc/redis/redis.conf
# Set: bind 127.0.0.1
```

## Quick Fix Commands

```bash
# Complete fix sequence
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo systemctl restart flashdash-backend
sudo systemctl status redis-server
sudo systemctl status flashdash-backend
```

## Verification

After fixing, test:

```bash
# 1. Redis is running
redis-cli ping
# Should return: PONG

# 2. Backend can connect
curl https://freedomos.vulcantech.co/health
# Should return: {"status":"healthy",...}

# 3. Registration works
curl -X POST https://freedomos.vulcantech.co/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@fxmail.ai", "password": "testpass123", "full_name": "Test"}'
# Should return: {"access_token":"...","refresh_token":"..."}
```

## Summary

**Issue**: Redis service not running  
**Fix**: Start Redis service  
**Commands**:
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
sudo systemctl restart flashdash-backend
```

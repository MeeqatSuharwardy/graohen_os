# Fixing Cloudflare Error 521 - Web Server is Down

## Problem
Cloudflare error 521 means Cloudflare can reach your server but the origin web server is refusing the connection or not responding.

## Solutions

### 1. Check if Ports are Open

On your VPS, check if ports 80 and 443 are open:

```bash
# Check if ports are listening
sudo netstat -tlnp | grep -E ':(80|443)'

# Or use ss
sudo ss -tlnp | grep -E ':(80|443)'

# Check Docker ports
docker ps | grep flashdash
```

### 2. Check Firewall (UFW)

```bash
# Check firewall status
sudo ufw status

# Allow ports 80 and 443
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# If using iptables
sudo iptables -L -n | grep -E '(80|443)'
```

### 3. Check Cloudflare Proxy Settings

In Cloudflare dashboard:
1. Go to DNS settings
2. Make sure the A record for `frontend.fxmail.ai` has the **orange cloud** (proxied) enabled
3. The IP should point to your VPS IP address
4. SSL/TLS mode should be set to **"Full"** or **"Full (strict)"**

### 4. Verify Docker Container is Running

```bash
# Check container status
docker ps

# Check if container is listening on port 80
docker exec flashdash netstat -tlnp | grep :80

# Check container logs
docker logs flashdash -f
```

### 5. Test Direct Access

```bash
# From your VPS, test if the server responds
curl -I http://localhost
curl -I http://localhost:8000/health

# Test from outside (replace with your VPS IP)
curl -I http://YOUR_VPS_IP
```

### 6. Check Nginx Configuration

```bash
# Test nginx config inside container
docker exec flashdash nginx -t

# Check nginx error logs
docker exec flashdash tail -f /var/log/nginx/error.log

# Check nginx access logs
docker exec flashdash tail -f /var/log/nginx/access.log
```

### 7. Verify Domain Points to Correct IP

```bash
# Check what IP your domain resolves to
dig frontend.fxmail.ai +short

# Should match your VPS IP
curl ifconfig.me  # Get your VPS IP
```

### 8. Restart Docker Container

```bash
# Restart the container
docker-compose restart

# Or rebuild and restart
docker-compose down
docker-compose up -d --build
```

### 9. Check Cloudflare SSL/TLS Settings

1. Go to Cloudflare Dashboard → SSL/TLS
2. Set SSL/TLS encryption mode to **"Full"** (not "Flexible")
3. This ensures Cloudflare connects to your origin via HTTPS

### 10. Common Issues and Fixes

**Issue: Port 80 not accessible**
```bash
# Check if nginx is running inside container
docker exec flashdash ps aux | grep nginx

# Restart nginx inside container
docker exec flashdash nginx -s reload
```

**Issue: Backend health check failing**
```bash
# Check backend logs
docker logs flashdash | grep -i backend

# Test backend directly
docker exec flashdash curl http://localhost:8000/health
```

**Issue: Firewall blocking connections**
```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload

# Check firewall rules
sudo ufw status numbered
```

## Quick Diagnostic Commands

Run these on your VPS to diagnose:

```bash
# 1. Check container status
docker ps -a

# 2. Check if ports are exposed
docker port flashdash

# 3. Check if nginx is running
docker exec flashdash ps aux | grep nginx

# 4. Check if backend is running
docker exec flashdash ps aux | grep uvicorn

# 5. Test local access
curl -I http://localhost
curl http://localhost:8000/health

# 6. Check firewall
sudo ufw status

# 7. Check listening ports
sudo netstat -tlnp | grep -E ':(80|443|8000)'

# 8. Check Cloudflare DNS
dig frontend.fxmail.ai +short
```

## Expected Results

After fixing, you should see:
- ✅ Container running: `docker ps` shows `flashdash` as `Up`
- ✅ Port 80 listening: `netstat` shows `:80` in LISTEN state
- ✅ Nginx running: `docker exec flashdash ps aux | grep nginx` shows process
- ✅ Backend responding: `curl http://localhost:8000/health` returns 200
- ✅ Cloudflare shows "Full" SSL mode
- ✅ Domain DNS points to correct IP

## If Still Not Working

1. **Check Cloudflare logs**: Go to Cloudflare Dashboard → Analytics → Web Traffic
2. **Check server logs**: `docker logs flashdash -f`
3. **Test without Cloudflare**: Access directly via IP to see if server works
4. **Check VPS provider firewall**: Some providers (DigitalOcean, AWS) have additional firewalls

## Contact Support

If none of the above works, provide:
- Output of `docker ps`
- Output of `docker logs flashdash` (last 50 lines)
- Output of `sudo ufw status`
- Output of `netstat -tlnp | grep -E ':(80|443)'`
- Cloudflare SSL/TLS mode setting

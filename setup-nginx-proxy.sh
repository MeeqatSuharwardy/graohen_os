#!/bin/bash
# Script to set up nginx reverse proxy for freedomos.vulcantech.co
# This proxies requests to Docker container on port 81

set -e

echo "=========================================="
echo "Setting up Nginx Reverse Proxy"
echo "for freedomos.vulcantech.co -> port 81"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Nginx is not installed. Installing..."
    apt-get update
    apt-get install -y nginx
fi

# Check if SSL certificates exist
SSL_CERT="/etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem"
SSL_KEY="/etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem"

if [ ! -f "$SSL_CERT" ]; then
    echo "⚠️  Warning: SSL certificates not found at $SSL_CERT"
    echo "You have two options:"
    echo "1. Use Cloudflare SSL only (comment out SSL cert lines in config)"
    echo "2. Get Let's Encrypt certificate: sudo certbot certonly --standalone -d freedomos.vulcantech.co"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    USE_CLOUDFLARE_SSL=true
else
    USE_CLOUDFLARE_SSL=false
    echo "✅ SSL certificates found"
fi

# Copy nginx configuration
CONFIG_FILE="/etc/nginx/sites-available/freedomos"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/nginx-freedomos.conf" ]; then
    cp "$SCRIPT_DIR/nginx-freedomos.conf" "$CONFIG_FILE"
    echo "✅ Configuration file copied to $CONFIG_FILE"
else
    echo "❌ nginx-freedomos.conf not found in current directory"
    echo "Creating basic configuration..."
    cat > "$CONFIG_FILE" << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name freedomos.vulcantech.co;
    return 301 https://$server_name$request_uri;
}

# HTTPS server - proxies to Docker container on port 81
server {
    listen 443 ssl http2;
    server_name freedomos.vulcantech.co;

    # SSL certificates (update if needed)
    ssl_certificate /etc/letsencrypt/live/freedomos.vulcantech.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/freedomos.vulcantech.co/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # CORS headers
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;

    if ($request_method = OPTIONS) {
        return 204;
    }

    location / {
        proxy_pass http://127.0.0.1:81;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF
fi

# If using Cloudflare SSL only, comment out SSL cert lines
if [ "$USE_CLOUDFLARE_SSL" = true ]; then
    echo "⚠️  Commenting out SSL certificate lines (using Cloudflare SSL only)"
    sed -i 's/^    ssl_certificate/#    ssl_certificate/g' "$CONFIG_FILE"
    sed -i 's/^    ssl_certificate_key/#    ssl_certificate_key/g' "$CONFIG_FILE"
fi

# Enable site
if [ ! -L "/etc/nginx/sites-enabled/freedomos" ]; then
    ln -s "$CONFIG_FILE" /etc/nginx/sites-enabled/freedomos
    echo "✅ Site enabled"
else
    echo "✅ Site already enabled"
fi

# Test nginx configuration
echo "Testing nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    exit 1
fi

# Reload nginx
echo "Reloading nginx..."
systemctl reload nginx

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Test the setup:"
echo "  curl https://freedomos.vulcantech.co/health"
echo ""
echo "If you need to get SSL certificates:"
echo "  sudo certbot certonly --standalone -d freedomos.vulcantech.co"
echo "  sudo systemctl reload nginx"
echo ""

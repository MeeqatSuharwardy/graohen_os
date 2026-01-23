#!/bin/bash
# Fix CORS duplicate headers in Nginx configuration
# Run this script on your VPS as root

set -e

NGINX_CONFIG="/etc/nginx/sites-available/freedomos"
BACKUP_FILE="/etc/nginx/sites-available/freedomos.backup.$(date +%Y%m%d_%H%M%S)"

echo "=========================================="
echo "Fixing CORS Headers in Nginx"
echo "=========================================="
echo ""

# Check if config file exists
if [ ! -f "$NGINX_CONFIG" ]; then
    echo "❌ Error: Nginx config file not found: $NGINX_CONFIG"
    exit 1
fi

# Backup current config
echo "📦 Creating backup: $BACKUP_FILE"
cp "$NGINX_CONFIG" "$BACKUP_FILE"
echo "✅ Backup created"
echo ""

# Remove CORS headers using sed
echo "🔧 Removing CORS headers from Nginx config..."
sed -i '/add_header Access-Control-Allow-Origin/d' "$NGINX_CONFIG"
sed -i '/add_header Access-Control-Allow-Methods/d' "$NGINX_CONFIG"
sed -i '/add_header Access-Control-Allow-Headers/d' "$NGINX_CONFIG"
sed -i '/add_header Access-Control-Allow-Credentials/d' "$NGINX_CONFIG"
sed -i '/if ($request_method = OPTIONS)/,/^[[:space:]]*}/d' "$NGINX_CONFIG"

echo "✅ CORS headers removed"
echo ""

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration is valid"
    echo ""
    
    # Reload Nginx
    echo "🔄 Reloading Nginx..."
    systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
    echo ""
    
    echo "=========================================="
    echo "✅ CORS Fix Complete!"
    echo "=========================================="
    echo ""
    echo "Backend will now handle all CORS headers."
    echo "Local frontend (localhost:5174) should work now."
    echo ""
    echo "Backup saved at: $BACKUP_FILE"
else
    echo "❌ Error: Nginx configuration test failed"
    echo "Restoring backup..."
    cp "$BACKUP_FILE" "$NGINX_CONFIG"
    echo "Backup restored. Please check the configuration manually."
    exit 1
fi

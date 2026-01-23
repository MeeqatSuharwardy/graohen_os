#!/bin/bash

# Fix 413 Request Entity Too Large Error in Nginx
# Adds client_max_body_size directive to allow large APK uploads

set -e

NGINX_CONFIG="/etc/nginx/sites-available/freedomos"
BACKUP_FILE="/etc/nginx/sites-available/freedomos.backup.$(date +%Y%m%d_%H%M%S)"
MAX_SIZE="500M"

echo "🔧 Fixing 413 Request Entity Too Large Error"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Error: Please run as root (use sudo)"
    exit 1
fi

# Check if nginx config exists
if [ ! -f "$NGINX_CONFIG" ]; then
    echo "❌ Error: Nginx config file not found: $NGINX_CONFIG"
    echo "   Please check the path and try again"
    exit 1
fi

# Backup config
echo "📦 Creating backup: $BACKUP_FILE"
cp "$NGINX_CONFIG" "$BACKUP_FILE"
echo "✅ Backup created"

# Check if client_max_body_size already exists
if grep -q "client_max_body_size" "$NGINX_CONFIG"; then
    echo "⚠️  Warning: client_max_body_size already exists in config"
    echo "   Current setting:"
    grep "client_max_body_size" "$NGINX_CONFIG" | head -1
    echo ""
    read -p "Do you want to update it to ${MAX_SIZE}? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted. No changes made."
        exit 0
    fi
    # Update existing setting
    sed -i "s/client_max_body_size.*/client_max_body_size ${MAX_SIZE};/" "$NGINX_CONFIG"
    echo "✅ Updated existing client_max_body_size to ${MAX_SIZE}"
else
    # Add client_max_body_size after server_name line
    echo "➕ Adding client_max_body_size ${MAX_SIZE} directive..."
    
    # Find the server block and add after server_name
    if grep -q "server_name.*freedomos.vulcantech.co" "$NGINX_CONFIG"; then
        # Add after server_name line in HTTPS server block
        sed -i '/server_name.*freedomos.vulcantech.co/a\    # Allow large file uploads (for APKs)\n    client_max_body_size '"${MAX_SIZE}"';' "$NGINX_CONFIG"
        echo "✅ Added client_max_body_size ${MAX_SIZE} to HTTPS server block"
    else
        # Fallback: add after first server_name found
        sed -i '/server_name/a\    client_max_body_size '"${MAX_SIZE}"';' "$NGINX_CONFIG"
        echo "✅ Added client_max_body_size ${MAX_SIZE} to server block"
    fi
fi

# Also add timeout settings for large uploads if not present
if ! grep -q "proxy_read_timeout.*300" "$NGINX_CONFIG"; then
    echo "➕ Adding timeout settings for large uploads..."
    # Add after proxy_pass line in location block
    sed -i '/proxy_pass.*127.0.0.1:8000/a\        # Timeouts for large uploads\n        proxy_read_timeout 300s;\n        proxy_connect_timeout 300s;\n        proxy_send_timeout 300s;' "$NGINX_CONFIG"
    echo "✅ Added timeout settings"
fi

# Test nginx configuration
echo ""
echo "🧪 Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration is valid"
    echo ""
    
    # Reload nginx
    echo "🔄 Reloading Nginx..."
    if systemctl reload nginx; then
        echo "✅ Nginx reloaded successfully"
        echo ""
        echo "🎉 Fix applied successfully!"
        echo ""
        echo "Summary:"
        echo "  - client_max_body_size set to ${MAX_SIZE}"
        echo "  - Timeout settings added for large uploads"
        echo "  - Nginx reloaded"
        echo ""
        echo "You can now upload APK files up to ${MAX_SIZE} in size."
        echo ""
        echo "To verify, check the config:"
        echo "  grep client_max_body_size $NGINX_CONFIG"
    else
        echo "❌ Error: Failed to reload Nginx"
        echo "   Restoring backup..."
        cp "$BACKUP_FILE" "$NGINX_CONFIG"
        echo "   Backup restored. Please check the configuration manually."
        exit 1
    fi
else
    echo "❌ Error: Nginx configuration test failed"
    echo "   Restoring backup..."
    cp "$BACKUP_FILE" "$NGINX_CONFIG"
    echo "   Backup restored. Please check the configuration manually."
    exit 1
fi

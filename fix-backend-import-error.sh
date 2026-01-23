#!/bin/bash
# Fix backend import error by clearing Python cache and restarting service

echo "=== Fixing Backend Import Error ==="
echo ""

# Navigate to backend directory
cd /root/graohen_os/backend/py-service || exit 1

echo "1. Clearing Python cache files..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
echo "✅ Cache cleared"

echo ""
echo "2. Checking for circular imports..."
python3 -c "
import sys
sys.path.insert(0, '/root/graohen_os/backend/py-service')
try:
    from app.utils.bundles import index_bundles
    print('✅ app.utils.bundles imports successfully')
except Exception as e:
    print(f'❌ Error importing app.utils.bundles: {e}')
    sys.exit(1)

try:
    from app.routes import bundles
    print('✅ app.routes.bundles imports successfully')
except Exception as e:
    print(f'❌ Error importing app.routes.bundles: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Import check failed. Checking file contents..."
    echo ""
    echo "Checking app/utils/bundles.py line 9:"
    sed -n '9p' app/utils/bundles.py
    echo ""
    echo "Checking app/routes/bundles.py imports:"
    head -20 app/routes/bundles.py | grep -E "^from|^import"
    exit 1
fi

echo ""
echo "3. Restarting backend service..."
systemctl restart flashdash-backend.service

echo ""
echo "4. Checking service status..."
sleep 2
systemctl status flashdash-backend.service --no-pager -l

echo ""
echo "=== Fix Complete ==="
echo ""
echo "If the service still fails, check logs with:"
echo "  journalctl -u flashdash-backend.service -n 50 --no-pager"

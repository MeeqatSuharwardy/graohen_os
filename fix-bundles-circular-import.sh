#!/bin/bash
# Fix circular import in app/utils/bundles.py

echo "=== Fixing Circular Import in bundles.py ==="
echo ""

BUNDLES_FILE="/root/graohen_os/backend/py-service/app/utils/bundles.py"

if [ ! -f "$BUNDLES_FILE" ]; then
    echo "❌ File not found: $BUNDLES_FILE"
    exit 1
fi

echo "1. Checking for circular import..."
if grep -q "from ..utils.bundles import" "$BUNDLES_FILE"; then
    echo "❌ Found circular import!"
    echo ""
    echo "Line with issue:"
    grep -n "from ..utils.bundles import" "$BUNDLES_FILE"
    echo ""
    
    echo "2. Fixing circular import..."
    # Remove the problematic line
    sed -i '/from ..utils.bundles import/d' "$BUNDLES_FILE"
    echo "✅ Removed circular import line"
else
    echo "✅ No circular import found"
fi

echo ""
echo "3. Verifying file structure..."
echo "First 15 lines of bundles.py:"
head -15 "$BUNDLES_FILE"

echo ""
echo "4. Checking for other issues..."
if grep -q "from.*bundles.*import" "$BUNDLES_FILE"; then
    echo "⚠️  Found other bundle imports:"
    grep -n "from.*bundles.*import" "$BUNDLES_FILE"
fi

echo ""
echo "5. Clearing cache..."
cd /root/graohen_os/backend/py-service
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
echo "✅ Cache cleared"

echo ""
echo "6. Testing import..."
python3 -c "
import sys
sys.path.insert(0, '/root/graohen_os/backend/py-service')
try:
    from app.utils.bundles import index_bundles
    print('✅ app.utils.bundles imports successfully')
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "7. Restarting service..."
    systemctl restart flashdash-backend.service
    sleep 2
    
    echo ""
    echo "8. Checking service status..."
    systemctl status flashdash-backend.service --no-pager -l | head -20
else
    echo ""
    echo "❌ Import test failed. Please check the file manually."
    exit 1
fi

echo ""
echo "=== Fix Complete ==="

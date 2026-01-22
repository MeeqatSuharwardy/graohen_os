#!/bin/bash
# Quick test script for Docker deployment

set -e

echo "=========================================="
echo "FlashDash Docker Quick Test"
echo "=========================================="
echo ""

# Check if container is running
if ! docker ps | grep -q flashdash; then
    echo "❌ Container is not running!"
    echo ""
    echo "Start it with: docker-compose up -d"
    exit 1
fi

echo "✓ Container is running"
echo ""

# Test endpoints
echo "Testing endpoints..."
echo "----------------------------------------"

ENDPOINTS=(
    "http://localhost:8000/health:Backend Health"
    "http://localhost:8000/:Backend Root"
    "http://localhost/:Frontend"
    "http://localhost/flash:Web Flasher"
    "http://localhost/api/health:API Proxy"
)

for endpoint_info in "${ENDPOINTS[@]}"; do
    IFS=':' read -r url name <<< "$endpoint_info"
    echo -n "Testing $name... "
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo "✓ OK"
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        echo "✗ Failed (HTTP $HTTP_CODE)"
    fi
done

echo ""
echo "=========================================="
echo "Quick test complete!"
echo "=========================================="
echo ""
echo "For detailed verification, run: ./docker/verify.sh"

#!/bin/bash
# Complete Local Setup Test Script

set -e

echo "=========================================="
echo "Complete Local Setup Verification"
echo "=========================================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# 1. Check Backend Port
echo "1. Checking backend port 8000..."
if lsof -i :8000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Port 8000 is in use${NC}"
else
    echo -e "${RED}✗ Port 8000 is not in use - backend not running${NC}"
    echo "  Start with: cd backend/py-service && source venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    ERRORS=$((ERRORS + 1))
fi

# 2. Test Health Endpoint
echo ""
echo "2. Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health 2>&1)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Health endpoint OK (HTTP $HTTP_CODE)${NC}"
    echo "  Response: $BODY"
else
    echo -e "${RED}✗ Health endpoint failed (HTTP $HTTP_CODE)${NC}"
    ERRORS=$((ERRORS + 1))
fi

# 3. Test Devices Endpoint (with timeout)
echo ""
echo "3. Testing devices endpoint (10s timeout)..."
DEVICES_RESPONSE=$(curl -s -m 10 -w "\n%{http_code}" http://localhost:8000/devices 2>&1)
DEVICES_HTTP_CODE=$(echo "$DEVICES_RESPONSE" | tail -1)
DEVICES_BODY=$(echo "$DEVICES_RESPONSE" | sed '$d')

if [ "$DEVICES_HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Devices endpoint OK (HTTP $DEVICES_HTTP_CODE)${NC}"
    DEVICE_COUNT=$(echo "$DEVICES_BODY" | grep -o '"serial"' | wc -l | tr -d ' ')
    echo "  Found $DEVICE_COUNT device(s)"
else
    echo -e "${RED}✗ Devices endpoint failed (HTTP $DEVICES_HTTP_CODE)${NC}"
    if [ -z "$DEVICES_BODY" ]; then
        echo "  Empty response - endpoint may be hanging"
    else
        echo "  Response: $DEVICES_BODY"
    fi
    ERRORS=$((ERRORS + 1))
fi

# 4. Check Frontend .env
echo ""
echo "4. Checking frontend configuration..."
if [ -f "frontend/packages/desktop/.env" ]; then
    if grep -q "VITE_API_BASE_URL=http://localhost:8000" frontend/packages/desktop/.env; then
        echo -e "${GREEN}✓ Frontend .env configured correctly${NC}"
    else
        echo -e "${YELLOW}⚠ Frontend .env exists but may need update${NC}"
        echo "  Current: $(grep VITE_API_BASE_URL frontend/packages/desktop/.env || echo 'not found')"
        echo "  Should be: VITE_API_BASE_URL=http://localhost:8000"
    fi
else
    echo -e "${YELLOW}⚠ Frontend .env file not found${NC}"
    echo "  Creating..."
    echo "VITE_API_BASE_URL=http://localhost:8000" > frontend/packages/desktop/.env
    echo -e "${GREEN}✓ Created frontend/packages/desktop/.env${NC}"
fi

# 5. Check CORS Headers
echo ""
echo "5. Testing CORS headers..."
CORS_HEADERS=$(curl -s -H "Origin: http://localhost:5174" -H "Access-Control-Request-Method: GET" -X OPTIONS http://localhost:8000/devices -I 2>&1 | grep -i "access-control" || echo "")

if echo "$CORS_HEADERS" | grep -qi "access-control-allow-origin"; then
    echo -e "${GREEN}✓ CORS headers present${NC}"
    echo "$CORS_HEADERS" | head -3
else
    echo -e "${YELLOW}⚠ CORS headers not found (may need backend restart)${NC}"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start Electron app: pnpm run dev"
    echo "  2. Check Electron console for API calls"
    echo "  3. Should see 'Service Running' badge"
else
    echo -e "${RED}✗ Found $ERRORS issue(s)${NC}"
    echo ""
    echo "Fix issues above, then restart backend:"
    echo "  cd backend/py-service"
    echo "  source venv/bin/activate"
    echo "  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
fi
echo "=========================================="

#!/bin/bash
# Production Verification Script
# Verifies all services are configured correctly for freedomos.vulcantech.co

set -e

echo "=========================================="
echo "Production Configuration Verification"
echo "Domain: freedomos.vulcantech.co"
echo "=========================================="

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Check docker-compose.yml
echo "1. Checking docker-compose.yml..."
if grep -q "freedomos.vulcantech.co" docker-compose.yml; then
    echo -e "${GREEN}✓ docker-compose.yml configured for freedomos.vulcantech.co${NC}"
else
    echo -e "${RED}✗ docker-compose.yml not configured correctly${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check for localhost references (should be minimal)
LOCALHOST_COUNT=$(grep -c "localhost" docker-compose.yml || echo "0")
if [ "$LOCALHOST_COUNT" -lt 3 ]; then
    echo -e "${GREEN}✓ docker-compose.yml has minimal localhost references${NC}"
else
    echo -e "${YELLOW}⚠ docker-compose.yml has $LOCALHOST_COUNT localhost references${NC}"
fi

# Check nginx configuration
echo "2. Checking nginx configuration..."
if grep -q "freedomos.vulcantech.co" docker/nginx-site.conf; then
    echo -e "${GREEN}✓ nginx-site.conf configured for freedomos.vulcantech.co${NC}"
else
    echo -e "${RED}✗ nginx-site.conf not configured correctly${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check backend config
echo "3. Checking backend configuration..."
if grep -q "freedomos.vulcantech.co" backend/py-service/app/config.py; then
    echo -e "${GREEN}✓ Backend config includes freedomos.vulcantech.co${NC}"
else
    echo -e "${YELLOW}⚠ Backend config may need updating${NC}"
fi

# Check Dockerfile
echo "4. Checking Dockerfile..."
if grep -q "freedomos.vulcantech.co" Dockerfile; then
    echo -e "${GREEN}✓ Dockerfile configured for freedomos.vulcantech.co${NC}"
else
    echo -e "${RED}✗ Dockerfile not configured correctly${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check environment variables
echo "5. Checking environment variables..."
if docker ps | grep -q flashdash; then
    echo "Container is running, checking environment..."
    ENV_CHECK=$(docker exec flashdash env | grep -E "(API_BASE_URL|BACKEND_DOMAIN|VITE_API_BASE_URL)" || echo "")
    if echo "$ENV_CHECK" | grep -q "freedomos.vulcantech.co"; then
        echo -e "${GREEN}✓ Container environment variables configured correctly${NC}"
        echo "$ENV_CHECK" | grep -E "(API|DOMAIN|VITE)"
    else
        echo -e "${YELLOW}⚠ Container environment may need verification${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Container not running (will check after deployment)${NC}"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All configuration checks passed!${NC}"
    echo "Ready for production deployment on freedomos.vulcantech.co"
else
    echo -e "${RED}✗ Found $ERRORS configuration issue(s)${NC}"
    echo "Please review and fix before deployment"
fi
echo "=========================================="

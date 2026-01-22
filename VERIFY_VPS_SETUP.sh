#!/bin/bash
# Verification script for VPS setup
# Run this on the VPS to verify everything is configured correctly

set -e

echo "=========================================="
echo "VPS Setup Verification"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Check Docker
echo "1. Checking Docker..."
if docker ps &> /dev/null; then
    echo -e "${GREEN}✓ Docker is installed and running${NC}"
else
    echo -e "${RED}✗ Docker is not running${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Docker Compose
echo "2. Checking Docker Compose..."
if docker-compose version &> /dev/null; then
    echo -e "${GREEN}✓ Docker Compose is installed${NC}"
else
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Container
echo "3. Checking Docker container..."
if docker ps | grep -q flashdash; then
    echo -e "${GREEN}✓ Container 'flashdash' is running${NC}"
    docker ps | grep flashdash
else
    echo -e "${RED}✗ Container 'flashdash' is not running${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Port 81
echo "4. Checking port 81..."
if curl -f -s http://localhost:81/health &> /dev/null; then
    echo -e "${GREEN}✓ Port 81 is accessible${NC}"
    curl -s http://localhost:81/health | head -1
else
    echo -e "${YELLOW}⚠ Port 81 not responding (container may still be starting)${NC}"
fi

# Check Port 8000
echo "5. Checking port 8000 (backend)..."
if curl -f -s http://localhost:8000/health &> /dev/null; then
    echo -e "${GREEN}✓ Backend API is responding${NC}"
    curl -s http://localhost:8000/health
else
    echo -e "${RED}✗ Backend API is not responding${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check Nginx
echo "6. Checking Nginx..."
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
else
    echo -e "${YELLOW}⚠ Nginx is not running (may not be needed if using Docker nginx)${NC}"
fi

# Check Nginx Configuration
echo "7. Checking Nginx configuration..."
if [ -f /etc/nginx/sites-available/freedomos ]; then
    echo -e "${GREEN}✓ Nginx config file exists${NC}"
    if nginx -t &> /dev/null; then
        echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    else
        echo -e "${RED}✗ Nginx configuration has errors${NC}"
        nginx -t
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠ Nginx config file not found${NC}"
fi

# Check Firewall
echo "8. Checking firewall..."
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        echo -e "${GREEN}✓ Firewall is active${NC}"
        ufw status | grep -E "(80|443|81|8000)" || echo "  (Ports may be allowed)"
    else
        echo -e "${YELLOW}⚠ Firewall is not active${NC}"
    fi
fi

# Check Domain DNS (if accessible)
echo "9. Checking domain DNS..."
if dig +short freedomos.vulcantech.co | grep -q "138.197.24.229"; then
    echo -e "${GREEN}✓ Domain DNS points to server IP${NC}"
else
    echo -e "${YELLOW}⚠ Domain DNS may not be configured yet${NC}"
    echo "  Expected IP: 138.197.24.229"
    echo "  Current IP: $(dig +short freedomos.vulcantech.co || echo 'Not resolved')"
fi

# Check Container Logs for Errors
echo "10. Checking container logs for errors..."
RECENT_ERRORS=$(docker logs flashdash --tail 100 2>&1 | grep -i "error\|failed\|exception" | wc -l)
if [ "$RECENT_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✓ No recent errors in container logs${NC}"
else
    echo -e "${YELLOW}⚠ Found $RECENT_ERRORS potential errors in logs${NC}"
    echo "  Run 'docker logs flashdash --tail 50' to see details"
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
else
    echo -e "${RED}✗ Found $ERRORS issue(s)${NC}"
fi
echo "=========================================="
echo ""
echo "Quick test commands:"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:81/health"
echo "  curl https://freedomos.vulcantech.co/health"
echo ""
echo "View logs:"
echo "  docker-compose logs -f"
echo "  docker logs flashdash -f"
echo ""

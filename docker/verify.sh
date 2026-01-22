#!/bin/bash
# Comprehensive Docker deployment verification script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print status
print_status() {
    local status=$1
    local message=$2
    case $status in
        "pass")
            echo -e "${GREEN}✓${NC} $message"
            ((PASSED++))
            ;;
        "fail")
            echo -e "${RED}✗${NC} $message"
            ((FAILED++))
            ;;
        "warn")
            echo -e "${YELLOW}⚠${NC} $message"
            ((WARNINGS++))
            ;;
        "info")
            echo -e "${BLUE}ℹ${NC} $message"
            ;;
    esac
}

echo "=========================================="
echo "FlashDash Docker Deployment Verification"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_status "fail" "Docker is not installed"
    exit 1
fi
print_status "info" "Docker is installed"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_status "fail" "Docker Compose is not available"
    exit 1
fi
print_status "info" "Docker Compose is available"

# Check if container exists
if ! docker ps -a | grep -q flashdash; then
    print_status "fail" "Container 'flashdash' does not exist"
    echo ""
    echo "To create the container, run:"
    echo "  docker-compose up -d --build"
    exit 1
fi
print_status "info" "Container 'flashdash' exists"

# Check if container is running
if ! docker ps | grep -q flashdash; then
    print_status "fail" "Container is not running"
    echo ""
    echo "Container status:"
    docker ps -a | grep flashdash
    echo ""
    echo "To start the container, run:"
    echo "  docker-compose up -d"
    exit 1
fi
print_status "pass" "Container is running"

# Get container status
CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' flashdash 2>/dev/null)
HEALTH_STATUS=$(docker inspect -f '{{.State.Health.Status}}' flashdash 2>/dev/null 2>/dev/null || echo "no-healthcheck")

if [ "$CONTAINER_STATUS" = "running" ]; then
    print_status "pass" "Container status: $CONTAINER_STATUS"
else
    print_status "fail" "Container status: $CONTAINER_STATUS"
fi

if [ "$HEALTH_STATUS" != "no-healthcheck" ]; then
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        print_status "pass" "Container health: $HEALTH_STATUS"
    else
        print_status "warn" "Container health: $HEALTH_STATUS"
    fi
fi

echo ""
echo "Checking services..."
echo "----------------------------------------"

# Check backend health endpoint
echo -n "Backend health endpoint... "
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    RESPONSE=$(curl -s http://localhost:8000/health)
    print_status "pass" "Backend is healthy"
    echo "  Response: $RESPONSE"
else
    print_status "fail" "Backend health check failed"
    echo "  Trying to get error details..."
    curl -v http://localhost:8000/health 2>&1 | tail -5
fi

# Check backend root endpoint
echo -n "Backend root endpoint... "
if curl -f -s http://localhost:8000/ > /dev/null 2>&1; then
    print_status "pass" "Backend root is accessible"
else
    print_status "fail" "Backend root is not accessible"
fi

# Check frontend
echo -n "Frontend (main web app)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
if [ "$HTTP_CODE" = "200" ]; then
    print_status "pass" "Frontend is accessible (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "404" ]; then
    print_status "warn" "Frontend returned 404 (files may not be built)"
else
    print_status "fail" "Frontend returned HTTP $HTTP_CODE"
fi

# Check web flasher
echo -n "Web flasher (/flash)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/flash)
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    print_status "pass" "Web flasher is accessible (HTTP $HTTP_CODE)"
elif [ "$HTTP_CODE" = "404" ]; then
    print_status "warn" "Web flasher returned 404 (files may not be built)"
else
    print_status "fail" "Web flasher returned HTTP $HTTP_CODE"
fi

# Check API proxy
echo -n "API proxy (/api/health)... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health)
if [ "$HTTP_CODE" = "200" ]; then
    print_status "pass" "API proxy is working (HTTP $HTTP_CODE)"
else
    print_status "warn" "API proxy returned HTTP $HTTP_CODE"
fi

# Check devices endpoint
echo -n "Devices endpoint... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/devices)
if [ "$HTTP_CODE" = "200" ]; then
    print_status "pass" "Devices endpoint is working"
else
    print_status "warn" "Devices endpoint returned HTTP $HTTP_CODE (OK if no devices connected)"
fi

# Check tools endpoint
echo -n "Tools check endpoint... "
if curl -f -s http://localhost:8000/tools/check > /dev/null 2>&1; then
    TOOLS=$(curl -s http://localhost:8000/tools/check)
    print_status "pass" "Tools check endpoint is working"
    echo "  Response: $TOOLS"
else
    print_status "warn" "Tools check endpoint failed"
fi

echo ""
echo "Checking container logs..."
echo "----------------------------------------"

# Check for errors in logs
ERROR_COUNT=$(docker logs flashdash 2>&1 | grep -i "error\|failed\|exception" | wc -l || echo "0")
if [ "$ERROR_COUNT" -gt 0 ]; then
    print_status "warn" "Found $ERROR_COUNT potential errors in logs"
    echo "  Recent errors:"
    docker logs flashdash 2>&1 | grep -i "error\|failed\|exception" | tail -3 | sed 's/^/    /'
else
    print_status "pass" "No errors found in recent logs"
fi

# Check container resource usage
echo ""
echo "Container resource usage..."
echo "----------------------------------------"
docker stats flashdash --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null || print_status "warn" "Could not get resource stats"

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
    echo ""
    echo "Access points:"
    echo "  - Frontend: http://localhost/"
    echo "  - Web Flasher: http://localhost/flash"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please review the errors above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check container logs: docker logs flashdash"
    echo "  2. Restart container: docker-compose restart"
    echo "  3. Rebuild container: docker-compose up -d --build"
    echo ""
    exit 1
fi

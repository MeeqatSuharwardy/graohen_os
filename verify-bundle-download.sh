#!/bin/bash
# Quick verification script to test bundle download functionality
# Run this on your server to verify the bundle is downloadable

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BUNDLE_PATH="/root/graohen_os/bundles/panther/2026011300"
CODENAME="panther"
VERSION="2026011300"
API_BASE="${1:-http://localhost:8000}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Bundle Download Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ERRORS=0

# Check 1: Bundle folder exists
echo -e "${BLUE}[1]${NC} Checking bundle folder exists..."
if [ -d "$BUNDLE_PATH" ]; then
    echo -e "${GREEN}✓${NC} Bundle folder exists: $BUNDLE_PATH"
else
    echo -e "${RED}✗${NC} Bundle folder not found: $BUNDLE_PATH"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: image.zip exists
echo -e "${BLUE}[2]${NC} Checking image.zip exists..."
if [ -f "$BUNDLE_PATH/image.zip" ]; then
    SIZE=$(du -h "$BUNDLE_PATH/image.zip" | cut -f1)
    echo -e "${GREEN}✓${NC} image.zip exists (size: $SIZE)"
else
    echo -e "${RED}✗${NC} image.zip not found in bundle folder"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Backend is running
echo -e "${BLUE}[3]${NC} Checking backend is running..."
if curl -s -f "$API_BASE/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is running at $API_BASE"
else
    echo -e "${RED}✗${NC} Backend not responding at $API_BASE"
    echo -e "${YELLOW}  Make sure backend is running and accessible${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Bundle is discoverable
echo -e "${BLUE}[4]${NC} Checking bundle is discoverable..."
BUNDLE_INFO=$(curl -s "$API_BASE/bundles/for/$CODENAME" 2>/dev/null || echo "")
if echo "$BUNDLE_INFO" | grep -q "$VERSION"; then
    echo -e "${GREEN}✓${NC} Bundle is discoverable (version: $VERSION)"
    echo "$BUNDLE_INFO" | jq '.' 2>/dev/null || echo "$BUNDLE_INFO"
else
    echo -e "${YELLOW}⚠${NC} Bundle not found via API, attempting to index..."
    INDEX_RESULT=$(curl -s -X POST "$API_BASE/bundles/index" 2>/dev/null || echo "")
    sleep 1
    BUNDLE_INFO=$(curl -s "$API_BASE/bundles/for/$CODENAME" 2>/dev/null || echo "")
    if echo "$BUNDLE_INFO" | grep -q "$VERSION"; then
        echo -e "${GREEN}✓${NC} Bundle discovered after indexing"
    else
        echo -e "${RED}✗${NC} Bundle still not found after indexing"
        echo -e "${YELLOW}  Response: $BUNDLE_INFO${NC}"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: List files endpoint
echo -e "${BLUE}[5]${NC} Testing list files endpoint..."
LIST_RESULT=$(curl -s "$API_BASE/bundles/releases/$CODENAME/$VERSION/list" 2>/dev/null || echo "")
if echo "$LIST_RESULT" | grep -q "files"; then
    FILE_COUNT=$(echo "$LIST_RESULT" | jq '.total_files' 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓${NC} List endpoint works (found $FILE_COUNT files)"
else
    echo -e "${RED}✗${NC} List endpoint failed"
    echo -e "${YELLOW}  Response: $LIST_RESULT${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Download endpoint
echo -e "${BLUE}[6]${NC} Testing download endpoint..."
DOWNLOAD_HEADERS=$(curl -s -I "$API_BASE/bundles/releases/$CODENAME/$VERSION/download" 2>/dev/null || echo "")
if echo "$DOWNLOAD_HEADERS" | grep -q "200 OK\|Content-Type.*zip"; then
    CONTENT_LENGTH=$(echo "$DOWNLOAD_HEADERS" | grep -i "content-length" | cut -d' ' -f2 | tr -d '\r' || echo "unknown")
    echo -e "${GREEN}✓${NC} Download endpoint works"
    echo -e "  Content-Length: $CONTENT_LENGTH bytes"
else
    HTTP_CODE=$(echo "$DOWNLOAD_HEADERS" | head -n1 | cut -d' ' -f2 || echo "unknown")
    echo -e "${RED}✗${NC} Download endpoint failed (HTTP $HTTP_CODE)"
    echo -e "${YELLOW}  Headers: $DOWNLOAD_HEADERS${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: File download endpoint
echo -e "${BLUE}[7]${NC} Testing file download endpoint..."
FILE_HEADERS=$(curl -s -I "$API_BASE/bundles/releases/$CODENAME/$VERSION/file/metadata.json" 2>/dev/null || echo "")
if echo "$FILE_HEADERS" | grep -q "200 OK"; then
    echo -e "${GREEN}✓${NC} File download endpoint works"
else
    HTTP_CODE=$(echo "$FILE_HEADERS" | head -n1 | cut -d' ' -f2 || echo "unknown")
    echo -e "${RED}✗${NC} File download endpoint failed (HTTP $HTTP_CODE)"
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo -e "${GREEN}Bundle is ready for download!${NC}"
    echo ""
    echo "Download URLs:"
    echo -e "  ${BLUE}Complete bundle:${NC}"
    echo "    $API_BASE/bundles/releases/$CODENAME/$VERSION/download"
    echo ""
    echo -e "  ${BLUE}Individual files:${NC}"
    echo "    $API_BASE/bundles/releases/$CODENAME/$VERSION/file/{filename}"
    echo ""
    echo -e "  ${BLUE}List files:${NC}"
    echo "    $API_BASE/bundles/releases/$CODENAME/$VERSION/list"
else
    echo -e "${RED}✗ Found $ERRORS issue(s)${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Ensure bundle folder exists: $BUNDLE_PATH"
    echo "2. Ensure image.zip exists in bundle folder"
    echo "3. Check backend logs for errors"
    echo "4. Verify GRAPHENE_BUNDLES_ROOT config (or let it auto-detect)"
    echo "5. Ensure backend has read permissions on /root/graohen_os/bundles/"
fi
echo -e "${BLUE}========================================${NC}"

exit $ERRORS

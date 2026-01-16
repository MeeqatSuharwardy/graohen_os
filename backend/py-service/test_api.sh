#!/bin/bash

# API Testing Script for GrapheneOS Backend
# This script tests all major API endpoints and security layers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:17890}"
API_BASE="${BASE_URL}/api/v1"

echo -e "${GREEN}=== GrapheneOS API Test Suite ===${NC}\n"

# Test 1: Health Check
echo -e "${YELLOW}[1/10] Testing Health Endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "Response: $BODY"
else
    echo -e "${RED}✗ Health check failed (HTTP $HTTP_CODE)${NC}"
    exit 1
fi
echo ""

# Test 2: Root Endpoint
echo -e "${YELLOW}[2/10] Testing Root Endpoint...${NC}"
ROOT_RESPONSE=$(curl -s -w "\n%{http_code}" "${BASE_URL}/")
HTTP_CODE=$(echo "$ROOT_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ Root endpoint accessible${NC}"
else
    echo -e "${RED}✗ Root endpoint failed (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Test 3: API Root
echo -e "${YELLOW}[3/10] Testing API Root...${NC}"
API_ROOT_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_BASE}/")
HTTP_CODE=$(echo "$API_ROOT_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ API root accessible${NC}"
else
    echo -e "${RED}✗ API root failed (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Test 4: User Registration
echo -e "${YELLOW}[4/10] Testing User Registration...${NC}"
TEST_EMAIL="test_$(date +%s)@example.com"
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"${TEST_EMAIL}\",
        \"password\": \"SecurePass123!\",
        \"full_name\": \"Test User\"
    }")
HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "201" ]; then
    echo -e "${GREEN}✓ User registration successful${NC}"
    ACCESS_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    REFRESH_TOKEN=$(echo "$BODY" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)
    echo "Access Token: ${ACCESS_TOKEN:0:20}..."
else
    echo -e "${RED}✗ User registration failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
    ACCESS_TOKEN=""
fi
echo ""

# Test 5: User Login
echo -e "${YELLOW}[5/10] Testing User Login...${NC}"
LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"${TEST_EMAIL}\",
        \"password\": \"SecurePass123!\"
    }")
HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ User login successful${NC}"
    if [ -z "$ACCESS_TOKEN" ]; then
        ACCESS_TOKEN=$(echo "$BODY" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    fi
else
    echo -e "${RED}✗ User login failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 6: Protected Endpoint (with auth)
if [ -n "$ACCESS_TOKEN" ]; then
    echo -e "${YELLOW}[6/10] Testing Protected Endpoint (Auth Required)...${NC}"
    PROTECTED_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/example" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}")
    HTTP_CODE=$(echo "$PROTECTED_RESPONSE" | tail -n1)
    if [ "$HTTP_CODE" == "200" ]; then
        echo -e "${GREEN}✓ Protected endpoint accessible with auth${NC}"
    else
        echo -e "${RED}✗ Protected endpoint failed (HTTP $HTTP_CODE)${NC}"
    fi
else
    echo -e "${YELLOW}[6/10] Skipping protected endpoint test (no access token)${NC}"
fi
echo ""

# Test 7: Unauthorized Access
echo -e "${YELLOW}[7/10] Testing Unauthorized Access Protection...${NC}"
UNAUTH_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${API_BASE}/example")
HTTP_CODE=$(echo "$UNAUTH_RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
    echo -e "${GREEN}✓ Unauthorized access properly blocked (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}✗ Security issue: Unauthorized access not blocked (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Test 8: Rate Limiting
echo -e "${YELLOW}[8/10] Testing Rate Limiting...${NC}"
RATE_LIMIT_COUNT=0
for i in {1..6}; do
    RATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"nonexistent@example.com\",
            \"password\": \"wrongpassword\"
        }")
    HTTP_CODE=$(echo "$RATE_RESPONSE" | tail -n1)
    if [ "$HTTP_CODE" == "429" ]; then
        RATE_LIMIT_COUNT=$((RATE_LIMIT_COUNT + 1))
        break
    fi
    sleep 0.5
done

if [ "$RATE_LIMIT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Rate limiting working (HTTP 429 after multiple attempts)${NC}"
else
    echo -e "${YELLOW}⚠ Rate limiting may not be triggered (test with more requests)${NC}"
fi
echo ""

# Test 9: CORS Headers
echo -e "${YELLOW}[9/10] Testing CORS Configuration...${NC}"
CORS_RESPONSE=$(curl -s -I -X OPTIONS "${API_BASE}/auth/login" \
    -H "Origin: https://example.com" \
    -H "Access-Control-Request-Method: POST")
if echo "$CORS_RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo -e "${GREEN}✓ CORS headers present${NC}"
else
    echo -e "${YELLOW}⚠ CORS headers not found${NC}"
fi
echo ""

# Test 10: Security Headers
echo -e "${YELLOW}[10/10] Testing Security Headers...${NC}"
SECURITY_RESPONSE=$(curl -s -I "${BASE_URL}/health")
SECURITY_HEADERS=0

if echo "$SECURITY_RESPONSE" | grep -qi "X-Frame-Options"; then
    SECURITY_HEADERS=$((SECURITY_HEADERS + 1))
fi
if echo "$SECURITY_RESPONSE" | grep -qi "X-Content-Type-Options"; then
    SECURITY_HEADERS=$((SECURITY_HEADERS + 1))
fi
if echo "$SECURITY_RESPONSE" | grep -qi "X-XSS-Protection"; then
    SECURITY_HEADERS=$((SECURITY_HEADERS + 1))
fi

if [ "$SECURITY_HEADERS" -ge 2 ]; then
    echo -e "${GREEN}✓ Security headers present ($SECURITY_HEADERS/3)${NC}"
else
    echo -e "${YELLOW}⚠ Some security headers missing ($SECURITY_HEADERS/3)${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}=== Test Summary ===${NC}"
echo "Base URL: $BASE_URL"
echo "API Base: $API_BASE"
echo ""
echo -e "${GREEN}All tests completed!${NC}"
echo ""
echo "To test email service:"
echo "  curl -X POST ${API_BASE}/email/send \\"
echo "    -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"to\":[\"test@example.com\"],\"body\":\"Test email\"}'"
echo ""
echo "To test drive service:"
echo "  curl -X POST ${API_BASE}/drive/upload \\"
echo "    -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "    -F 'file=@/path/to/file.txt'"


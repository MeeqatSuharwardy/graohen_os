#!/bin/bash

# Comprehensive API Test Suite
# Tests all endpoints including Auth, Email, Drive, and Security

BASE_URL="http://127.0.0.1:17890"
API_BASE="${BASE_URL}/api/v1"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_code=$5
    local headers=$6
    
    echo -e "${BLUE}Testing: ${name}${NC}"
    
    if [ "$method" == "GET" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -H "$headers" "${endpoint}")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X "$method" -H "$headers" -H "Content-Type: application/json" -d "$data" "${endpoint}")
    fi
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" == "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $HTTP_CODE)"
        echo "Response: $(echo "$BODY" | head -c 200)..."
        PASSED=$((PASSED + 1))
        echo "$BODY"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_code, got $HTTP_CODE)"
        echo "Response: $BODY"
        FAILED=$((FAILED + 1))
        return 1
    fi
    echo ""
}

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Comprehensive API Test Suite${NC}"
echo -e "${YELLOW}========================================${NC}\n"

# Test 1: Health Check
echo -e "\n${YELLOW}[1] Health & Root Endpoints${NC}"
test_endpoint "Health Check" "GET" "${BASE_URL}/health" "" "200" ""
test_endpoint "Root Endpoint" "GET" "${BASE_URL}/" "" "200" ""
test_endpoint "API Root" "GET" "${API_BASE}/" "" "200" ""

# Test 2: Authentication - Registration
echo -e "\n${YELLOW}[2] Authentication - Registration${NC}"
TEST_EMAIL="test_$(date +%s)@example.com"
REGISTER_DATA="{\"email\":\"${TEST_EMAIL}\",\"password\":\"SecurePass123!\",\"full_name\":\"Test User\"}"
REGISTER_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/register" \
    -H "Content-Type: application/json" \
    -d "$REGISTER_DATA")

ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
REFRESH_TOKEN=$(echo "$REGISTER_RESPONSE" | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)

if [ -n "$ACCESS_TOKEN" ]; then
    echo -e "${GREEN}✓ Registration successful${NC}"
    echo "Access Token: ${ACCESS_TOKEN:0:30}..."
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Registration failed${NC}"
    echo "Response: $REGISTER_RESPONSE"
    FAILED=$((FAILED + 1))
fi

# Test 3: Authentication - Login
echo -e "\n${YELLOW}[3] Authentication - Login${NC}"
LOGIN_DATA="{\"email\":\"${TEST_EMAIL}\",\"password\":\"SecurePass123!\"}"
LOGIN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_DATA")

LOGIN_ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
if [ -n "$LOGIN_ACCESS_TOKEN" ]; then
    echo -e "${GREEN}✓ Login successful${NC}"
    ACCESS_TOKEN="$LOGIN_ACCESS_TOKEN"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    FAILED=$((FAILED + 1))
fi

# Test 4: Protected Endpoints
if [ -n "$ACCESS_TOKEN" ]; then
    echo -e "\n${YELLOW}[4] Protected Endpoints${NC}"
    AUTH_HEADER="Authorization: Bearer ${ACCESS_TOKEN}"
    
    test_endpoint "Example Endpoint (Protected)" "GET" "${API_BASE}/example" "" "200" "$AUTH_HEADER"
    
    # Test 5: Email Service
    echo -e "\n${YELLOW}[5] Email Service${NC}"
    EMAIL_SEND_DATA="{\"to\":[\"recipient@example.com\"],\"subject\":\"Test Email\",\"body\":\"This is a test encrypted email\",\"expires_in_hours\":24}"
    EMAIL_SEND_RESPONSE=$(curl -s -X POST "${API_BASE}/email/send" \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d "$EMAIL_SEND_DATA")
    
    EMAIL_ID=$(echo "$EMAIL_SEND_RESPONSE" | grep -o '"email_id":"[^"]*' | cut -d'"' -f4)
    if [ -n "$EMAIL_ID" ]; then
        echo -e "${GREEN}✓ Email send successful${NC}"
        echo "Email ID: ${EMAIL_ID:0:30}..."
        PASSED=$((PASSED + 1))
        
        # Try to get email
        test_endpoint "Get Email" "GET" "${API_BASE}/email/${EMAIL_ID}" "" "200" "$AUTH_HEADER"
    else
        echo -e "${RED}✗ Email send failed${NC}"
        echo "Response: $EMAIL_SEND_RESPONSE"
        FAILED=$((FAILED + 1))
    fi
    
    # Test 6: Drive Service
    echo -e "\n${YELLOW}[6] Drive Service${NC}"
    # Create a test file
    echo "This is a test file for drive upload" > /tmp/test_upload.txt
    
    DRIVE_UPLOAD_RESPONSE=$(curl -s -X POST "${API_BASE}/drive/upload" \
        -H "$AUTH_HEADER" \
        -F "file=@/tmp/test_upload.txt" \
        -F "expires_in_hours=168")
    
    FILE_ID=$(echo "$DRIVE_UPLOAD_RESPONSE" | grep -o '"file_id":"[^"]*' | cut -d'"' -f4)
    if [ -n "$FILE_ID" ]; then
        echo -e "${GREEN}✓ File upload successful${NC}"
        echo "File ID: ${FILE_ID:0:30}..."
        PASSED=$((PASSED + 1))
        
        # Get file info
        test_endpoint "Get File Info" "GET" "${API_BASE}/drive/file/${FILE_ID}" "" "200" "$AUTH_HEADER"
    else
        echo -e "${RED}✗ File upload failed${NC}"
        echo "Response: $DRIVE_UPLOAD_RESPONSE"
        FAILED=$((FAILED + 1))
    fi
    
    # Test 7: Token Refresh
    echo -e "\n${YELLOW}[7] Token Refresh${NC}"
    if [ -n "$REFRESH_TOKEN" ]; then
        REFRESH_DATA="{\"refresh_token\":\"${REFRESH_TOKEN}\"}"
        REFRESH_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/refresh" \
            -H "Content-Type: application/json" \
            -d "$REFRESH_DATA")
        
        NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        if [ -n "$NEW_ACCESS_TOKEN" ]; then
            echo -e "${GREEN}✓ Token refresh successful${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}✗ Token refresh failed${NC}"
            echo "Response: $REFRESH_RESPONSE"
            FAILED=$((FAILED + 1))
        fi
    fi
    
    # Test 8: Logout
    echo -e "\n${YELLOW}[8] Logout${NC}"
    LOGOUT_DATA="{\"all_devices\":false}"
    test_endpoint "Logout" "POST" "${API_BASE}/auth/logout" "$LOGOUT_DATA" "200" "$AUTH_HEADER"
fi

# Test 9: Security - Unauthorized Access
echo -e "\n${YELLOW}[9] Security - Unauthorized Access${NC}"
test_endpoint "Protected Endpoint Without Auth" "GET" "${API_BASE}/example" "" "401" ""
test_endpoint "Email Send Without Auth" "POST" "${API_BASE}/email/send" "{\"to\":[\"test@example.com\"],\"body\":\"test\"}" "401" ""

# Test 10: Security - Rate Limiting
echo -e "\n${YELLOW}[10] Security - Rate Limiting${NC}"
echo "Making multiple rapid login attempts..."
RATE_LIMIT_TRIGGERED=0
for i in {1..6}; do
    RATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${API_BASE}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"nonexistent@example.com\",\"password\":\"wrong\"}")
    HTTP_CODE=$(echo "$RATE_RESPONSE" | tail -n1)
    if [ "$HTTP_CODE" == "429" ]; then
        RATE_LIMIT_TRIGGERED=1
        echo -e "${GREEN}✓ Rate limiting triggered (HTTP 429)${NC}"
        PASSED=$((PASSED + 1))
        break
    fi
    sleep 0.3
done

if [ "$RATE_LIMIT_TRIGGERED" == "0" ]; then
    echo -e "${YELLOW}⚠ Rate limiting not triggered (may need more requests)${NC}"
fi

# Test 11: CORS Headers
echo -e "\n${YELLOW}[11] CORS Configuration${NC}"
CORS_RESPONSE=$(curl -s -I -X OPTIONS "${API_BASE}/auth/login" \
    -H "Origin: https://example.com" \
    -H "Access-Control-Request-Method: POST")

if echo "$CORS_RESPONSE" | grep -qi "Access-Control-Allow-Origin"; then
    echo -e "${GREEN}✓ CORS headers present${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ CORS headers not found${NC}"
fi

# Test 12: Security Headers
echo -e "\n${YELLOW}[12] Security Headers${NC}"
SECURITY_RESPONSE=$(curl -s -I "${BASE_URL}/health")
HEADER_COUNT=0

if echo "$SECURITY_RESPONSE" | grep -qi "X-Frame-Options"; then HEADER_COUNT=$((HEADER_COUNT + 1)); fi
if echo "$SECURITY_RESPONSE" | grep -qi "X-Content-Type-Options"; then HEADER_COUNT=$((HEADER_COUNT + 1)); fi
if echo "$SECURITY_RESPONSE" | grep -qi "X-XSS-Protection"; then HEADER_COUNT=$((HEADER_COUNT + 1)); fi

if [ "$HEADER_COUNT" -ge 2 ]; then
    echo -e "${GREEN}✓ Security headers present ($HEADER_COUNT/3)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ Some security headers missing ($HEADER_COUNT/3)${NC}"
fi

# Test 13: Public Endpoints
echo -e "\n${YELLOW}[13] Public Endpoints${NC}"
test_endpoint "Public Endpoint" "GET" "${API_BASE}/public/view/test123" "" "200" ""

# Test 14: GrapheneOS Endpoints
echo -e "\n${YELLOW}[14] GrapheneOS Endpoints${NC}"
test_endpoint "Check Build Availability" "GET" "${API_BASE}/grapheneos/download/check/panther" "" "200" ""

# Summary
echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Test Summary${NC}"
echo -e "${YELLOW}========================================${NC}"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "Total: $((PASSED + FAILED))"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review above.${NC}"
    exit 1
fi


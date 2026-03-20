#!/bin/bash
# Test all APIs: auth (register, login), email, drive
# Usage: ./test_all_apis.sh [BASE_URL]
# Default: http://127.0.0.1:8000

BASE_URL="${1:-http://127.0.0.1:8000}"
API="${BASE_URL}/api/v1"
TEST_EMAIL="test_$(date +%s)@example.com"
TEST_PASS="TestPass123!"
DEVICE_ID="device-$(date +%s)"

echo "=== API Tests: $BASE_URL ==="
echo "Test email: $TEST_EMAIL"
echo ""

# Health check
echo "1. Health check"
curl -s "$BASE_URL/health" | head -1
echo -e "\n"

# API root
echo "2. API root"
curl -s "$API/" | python3 -m json.tool 2>/dev/null || curl -s "$API/"
echo -e "\n"

# Register
echo "3. Register"
REG_RESP=$(curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\",\"device_id\":\"$DEVICE_ID\"}")
echo "$REG_RESP" | python3 -m json.tool 2>/dev/null || echo "$REG_RESP"
TOKEN=$(echo "$REG_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)
echo "Token: ${TOKEN:0:20}..."
echo ""

# Login (legacy)
echo "4. Login (legacy)"
LOGIN_RESP=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASS\"}")
echo "$LOGIN_RESP" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESP"
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)
echo ""

# Drive: storage
echo "5. Drive - Get storage"
curl -s -H "Authorization: Bearer $TOKEN" "$API/drive/storage" | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $TOKEN" "$API/drive/storage"
echo -e "\n"

# Drive: upload (create temp file)
echo "6. Drive - Upload file"
echo "test content" > /tmp/test_upload_$$.txt
UPLOAD_RESP=$(curl -s -X POST "$API/drive/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_upload_$$.txt" \
  -F "filename=test.txt" \
  -F "passcode_protected=false" 2>/dev/null || echo '{"detail":"error"}')
rm -f /tmp/test_upload_$$.txt
echo "$UPLOAD_RESP" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESP"
FILE_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_id',''))" 2>/dev/null)
echo ""

# Drive: list files
echo "7. Drive - List files"
curl -s -H "Authorization: Bearer $TOKEN" "$API/drive/files" | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $TOKEN" "$API/drive/files"
echo -e "\n"

# Email: send
echo "8. Email - Send"
EMAIL_RESP=$(curl -s -X POST "$API/email/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"to\":\"$TEST_EMAIL\",\"subject\":\"Test\",\"body\":\"Hello\",\"encryption_mode\":\"authenticated\"}")
echo "$EMAIL_RESP" | python3 -m json.tool 2>/dev/null || echo "$EMAIL_RESP"
echo ""

# Email: inbox
echo "9. Email - Inbox"
curl -s -H "Authorization: Bearer $TOKEN" "$API/email/inbox" | python3 -m json.tool 2>/dev/null || curl -s -H "Authorization: Bearer $TOKEN" "$API/email/inbox"
echo -e "\n"

# Login challenge (device-bound)
echo "10. Auth - Login challenge"
curl -s -X POST "$API/auth/login/challenge" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"device_id\":\"$DEVICE_ID\"}" | python3 -m json.tool 2>/dev/null
echo ""

echo "=== Tests complete ==="

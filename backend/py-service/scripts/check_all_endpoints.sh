#!/bin/bash
# Check all API endpoints on server
# Usage: ./scripts/check_all_endpoints.sh [BASE_URL]
BASE="${1:-https://freedomos.vulcantech.co}"
API="$BASE/api/v1"

run() {
  local method=$1 path=$2 extra=$3
  local url="$API$path"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -X "$method" $extra "$url" 2>/dev/null)
  printf "%-6s %-50s %s\n" "$method" "$path" "$code"
}

echo "=== Checking endpoints on $BASE ==="
echo ""

TOKEN=$(curl -s -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"epcheck_'$(date +%s)'@example.com","password":"TestPass123!","device_id":"ep-1"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "Token: ${TOKEN:0:25}... (len=${#TOKEN})"
echo ""

echo "--- Auth ---"
run POST /auth/register "-H 'Content-Type: application/json' -d '{\"email\":\"x@y.com\",\"password\":\"TestPass123!\",\"device_id\":\"d1\"}'"
run POST /auth/login "-H 'Content-Type: application/json' -d '{\"email\":\"x@y.com\",\"password\":\"TestPass123!\"}'"
run POST /auth/login/challenge "-H 'Content-Type: application/json' -d '{\"email\":\"x@y.com\",\"device_id\":\"d1\"}'"
run POST /auth/refresh "-H 'Content-Type: application/json' -d '{\"refresh_token\":\"x\"}'"
run POST /auth/logout "-H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{}'"
run POST /auth/device-key/download "-H 'Content-Type: application/json' -d '{\"email\":\"x@y.com\",\"password\":\"x\",\"device_id\":\"d1\"}'"
run GET /auth/device/key-info/d1
run POST /auth/device/register-key "-H 'Content-Type: application/json' -d '{\"device_id\":\"d1\",\"key_blob\":\"x\"}'"
echo ""

echo "--- Email ---"
run POST /email/send "-H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"to\":[\"a@b.com\"],\"subject\":\"T\",\"body\":\"B\",\"notification_delivery\":\"link_only\"}'"
run GET /email/inbox "-H \"Authorization: Bearer $TOKEN\""
run GET /email/sent "-H \"Authorization: Bearer $TOKEN\""
run GET /email/drafts "-H \"Authorization: Bearer $TOKEN\""
run GET /email/token/abc123xyz
run POST /email/ingest "-H 'Content-Type: application/octet-stream' -d ''"
run POST /email/drafts "-H 'Content-Type: application/json' -H \"Authorization: Bearer $TOKEN\" -d '{\"to\":[\"a@b.com\"],\"body\":\"B\"}'"
echo ""

echo "--- Drive ---"
run GET /drive/storage "-H \"Authorization: Bearer $TOKEN\""
run GET /drive/files "-H \"Authorization: Bearer $TOKEN\""
run GET /drive/storage/quota "-H \"Authorization: Bearer $TOKEN\""
run GET /drive/file/nonexistent-id "-H \"Authorization: Bearer $TOKEN\""
run DELETE /drive/file/nonexistent-id "-H \"Authorization: Bearer $TOKEN\""
echo ""

echo "--- Public ---"
run GET /public/view/testtoken
run POST /public/unlock/testtoken "-H 'Content-Type: application/json' -d '{\"passcode\":\"1234\"}'"
run GET /public/data/testtoken
run GET /public/session/testtoken
echo ""

echo "--- Example ---"
run GET /example
echo ""

echo "--- GrapheneOS ---"
run GET /grapheneos/check/cheetah
run POST /grapheneos/start "-H 'Content-Type: application/json' -d '{\"codename\":\"cheetah\"}'"
run GET /grapheneos/status/nonexistent
echo ""

echo "--- Admin ---"
run GET /admin/stats "-H \"Authorization: Bearer $TOKEN\""
run GET /admin/storage "-H \"Authorization: Bearer $TOKEN\""
run GET /admin/drive "-H \"Authorization: Bearer $TOKEN\""
echo ""

echo "=== Done ==="
echo "2xx=OK, 401=Auth required, 404=Not found, 422=Validation error"

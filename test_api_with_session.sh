#!/bin/bash

# Test if devices endpoint works with session cookies

set -e

# Load .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "Testing FireBoard API with Session Cookies"
echo "==========================================="
echo ""

# Step 1: Login and capture cookies
echo "Step 1: Login and capture session..."
COOKIE_JAR=$(mktemp)

curl -c "$COOKIE_JAR" -s https://fireboard.io/api/rest-auth/login/ \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  -d "{\"username\":\"$FIREBOARD_EMAIL\",\"password\":\"$FIREBOARD_PASSWORD\"}" > /dev/null

echo "✅ Session cookies captured"
echo ""

# Extract token
TOKEN=$(curl -s https://fireboard.io/api/rest-auth/login/ \
  -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$FIREBOARD_EMAIL\",\"password\":\"$FIREBOARD_PASSWORD\"}" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['key'])")

echo "Step 2: Try devices endpoint WITH cookies..."
echo "--------------------------------------------"

RESPONSE=$(curl -b "$COOKIE_JAR" -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Accept: application/json" \
  "https://fireboard.io/api/v1/devices.json")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')

echo "Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" == "200" ]; then
    echo "✅ SUCCESS WITH SESSION COOKIES!"
    echo "$BODY" | python3 -m json.tool
else
    echo "❌ Still blocked even with session cookies"
    echo "${BODY:0:300}"
fi

# Cleanup
rm -f "$COOKIE_JAR"


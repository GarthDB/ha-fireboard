#!/bin/bash

# FireBoard API Test with curl
# This bypasses Python and tests the raw API

set -e

echo "====================================="
echo "FireBoard API Test with curl"
echo "====================================="
echo ""

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading credentials from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Get credentials from args or env vars
if [ -n "$1" ] && [ -n "$2" ]; then
    EMAIL="$1"
    PASSWORD="$2"
elif [ -n "$FIREBOARD_EMAIL" ] && [ -n "$FIREBOARD_PASSWORD" ]; then
    EMAIL="$FIREBOARD_EMAIL"
    PASSWORD="$FIREBOARD_PASSWORD"
else
    echo "Error: No credentials provided!"
    echo ""
    echo "Usage Option 1 - Command line:"
    echo "  ./test_api_curl.sh 'your@email.com' 'your!password'"
    echo ""
    echo "Usage Option 2 - .env file:"
    echo "  1. Copy .env.example to .env"
    echo "  2. Edit .env with your credentials"
    echo "  3. Run: ./test_api_curl.sh"
    exit 1
fi

echo "Step 1: Authentication"
echo "----------------------"

# Authenticate
AUTH_RESPONSE=$(curl -s https://fireboard.io/api/rest-auth/login/ \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: HomeAssistant-FireBoard' \
  -d "{\"username\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

echo "Auth Response: $AUTH_RESPONSE"

# Extract token
TOKEN=$(echo $AUTH_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['key'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo "❌ Authentication failed!"
    exit 1
fi

echo "✅ Token: ${TOKEN:0:20}..."
echo ""

echo "Step 2: Get Devices"
echo "-------------------"

# Try different device endpoints
ENDPOINTS=(
    "https://fireboard.io/api/v1/devices"
    "https://fireboard.io/api/v1/devices.json"
    "https://fireboard.io/api/v1/devices/"
    "https://fireboard.io/api/rest-auth/user/"
)

for ENDPOINT in "${ENDPOINTS[@]}"; do
    echo "Trying: $ENDPOINT"
    RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -H "Authorization: Token $TOKEN" \
        -H "Content-Type: application/json" \
        -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
        "$ENDPOINT")
    
    HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed -e 's/HTTP_STATUS\:.*//g')
    
    echo "Status: $HTTP_STATUS"
    
    if [ "$HTTP_STATUS" == "200" ]; then
        echo "✅ SUCCESS!"
        echo "Response:"
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
        echo ""
        echo "====================================="
        echo "Found working endpoint: $ENDPOINT"
        echo "====================================="
        exit 0
    else
        echo "❌ Failed (showing first 200 chars of response)"
        echo "${BODY:0:200}..."
        echo ""
    fi
done

echo "❌ None of the endpoints worked"
exit 1


#!/bin/bash
# Validate Notion API Access
# Tests if Notion token and database access are configured correctly

set -euo pipefail

NOTION_TOKEN="${NOTION_TOKEN:-}"
DATABASE_ID="${1:-}"
NOTION_API="https://api.notion.com/v1"
NOTION_VERSION="2022-06-28"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "  Notion API Access Validator"
echo "========================================="
echo ""

# Check if token is set
if [[ -z "$NOTION_TOKEN" ]]; then
    echo -e "${RED}ERROR: NOTION_TOKEN is not set${NC}"
    echo ""
    echo "Set your token:"
    echo "  export NOTION_TOKEN=secret_xxx"
    echo ""
    echo "Or pass to script:"
    echo "  NOTION_TOKEN=secret_xxx $0"
    exit 1
fi

echo "✓ NOTION_TOKEN is set"
echo ""

# Check dependencies
echo "Checking dependencies..."
for cmd in curl jq; do
    if command -v "$cmd" &>/dev/null; then
        echo "  ✓ $cmd found"
    else
        echo -e "  ${RED}✗ $cmd not found${NC}"
        echo "    Install with: sudo apt-get install $cmd"
        exit 1
    fi
done
echo ""

# Test 1: Validate token by getting current user
echo "Test 1: Validating Notion token..."
response=$(curl -s \
    -H "Authorization: Bearer ${NOTION_TOKEN}" \
    -H "Notion-Version: ${NOTION_VERSION}" \
    "${NOTION_API}/users/me")

if echo "$response" | jq -e '.object == "error"' &>/dev/null; then
    echo -e "${RED}✗ Token validation failed${NC}"
    echo "Error:"
    echo "$response" | jq -r '.message'
    exit 1
else
    user_name=$(echo "$response" | jq -r '.name // "Unknown"')
    echo -e "${GREEN}✓ Token is valid${NC}"
    echo "  User: $user_name"
fi
echo ""

# Test 2: List databases (if no specific database provided)
if [[ -z "$DATABASE_ID" ]]; then
    echo "Test 2: Searching for databases..."
    response=$(curl -s -X POST \
        -H "Authorization: Bearer ${NOTION_TOKEN}" \
        -H "Notion-Version: ${NOTION_VERSION}" \
        -H "Content-Type: application/json" \
        -d '{"filter": {"value": "database", "property": "object"}}' \
        "${NOTION_API}/search")

    if echo "$response" | jq -e '.object == "error"' &>/dev/null; then
        echo -e "${YELLOW}⚠ Could not search databases${NC}"
        echo "Error:"
        echo "$response" | jq -r '.message'
    else
        db_count=$(echo "$response" | jq '.results | length')
        echo -e "${GREEN}✓ Found $db_count accessible database(s)${NC}"

        if [[ $db_count -gt 0 ]]; then
            echo ""
            echo "Available databases:"
            echo "$response" | jq -r '.results[] | "  • " + (.id // "no-id") + " - " + (.title[0].plain_text // "Untitled")'
            echo ""
            echo "To test a specific database:"
            echo "  $0 <database-id>"
        fi
    fi
else
    # Test 3: Query specific database
    echo "Test 2: Querying database ${DATABASE_ID}..."
    response=$(curl -s -X POST \
        -H "Authorization: Bearer ${NOTION_TOKEN}" \
        -H "Notion-Version: ${NOTION_VERSION}" \
        -H "Content-Type: application/json" \
        -d '{"page_size": 1}' \
        "${NOTION_API}/databases/${DATABASE_ID}/query")

    if echo "$response" | jq -e '.object == "error"' &>/dev/null; then
        echo -e "${RED}✗ Database query failed${NC}"
        echo "Error:"
        echo "$response" | jq -r '.message'
        echo ""
        echo "Common issues:"
        echo "  1. Database not shared with integration"
        echo "  2. Invalid database ID"
        echo "  3. Integration doesn't have read permission"
        exit 1
    else
        entry_count=$(echo "$response" | jq '.results | length')
        echo -e "${GREEN}✓ Database is accessible${NC}"
        echo "  Retrieved: $entry_count page(s) (limited to 1 for test)"

        # Check for required columns
        echo ""
        echo "Test 3: Checking database schema..."

        if [[ $entry_count -gt 0 ]]; then
            properties=$(echo "$response" | jq -r '.results[0].properties | keys[]')

            has_name=false
            has_ip=false
            has_mac=false

            while IFS= read -r prop; do
                case "$prop" in
                    "Name") has_name=true ;;
                    "IP") has_ip=true ;;
                    "MAC") has_mac=true ;;
                esac
            done <<< "$properties"

            if $has_name; then
                echo "  ✓ Name column found"
            else
                echo -e "  ${RED}✗ Name column NOT found (required)${NC}"
            fi

            if $has_ip; then
                echo "  ✓ IP column found"
            else
                echo -e "  ${YELLOW}⚠ IP column NOT found (required for DNS/DHCP)${NC}"
            fi

            if $has_mac; then
                echo "  ✓ MAC column found"
            else
                echo -e "  ${YELLOW}⚠ MAC column NOT found (optional, needed for DHCP)${NC}"
            fi

            echo ""
            echo "All columns found:"
            echo "$properties" | sed 's/^/  • /'

            if ! $has_name || ! $has_ip; then
                echo ""
                echo -e "${YELLOW}Warning: Database may not work with notion-dnsmasq.sh${NC}"
                echo "Required columns: Name (title), IP (text)"
                echo "Optional columns: MAC (text)"
            fi
        else
            echo -e "${YELLOW}⚠ Database is empty, cannot check schema${NC}"
            echo "  Add at least one entry to validate schema"
        fi
    fi
fi

echo ""
echo "========================================="
echo "  Validation Summary"
echo "========================================="
echo -e "${GREEN}✓ All tests passed!${NC}"
echo ""
echo "You can now run:"
echo "  ./converters/notion-dnsmasq.sh --dry-run"
echo ""
if [[ -n "$DATABASE_ID" ]]; then
    echo "Using database: $DATABASE_ID"
else
    echo "Set DATABASE_ID in notion-dnsmasq.sh or pass --database <id>"
fi

#!/bin/bash
# deploy-nginx-config.sh
# Regenerate and deploy nginx reverse proxy config from Notion

set -euo pipefail

SERVICES_DB="${SERVICES_DB:-}"  # Set in environment or systemd unit
NGINX_CONF="/etc/nginx/conf.d/services.conf"
SCRIPT_DIR="/opt/notion2config/converters"

# Ensure required vars are set
if [[ -z "${NOTION_TOKEN:-}" ]]; then
  echo "ERROR: NOTION_TOKEN not set" >&2
  exit 1
fi

if [[ -z "$SERVICES_DB" ]]; then
  echo "ERROR: SERVICES_DB not set" >&2
  exit 1
fi

# Generate new config
"${SCRIPT_DIR}/notion-nginx.sh" \
  --database "$SERVICES_DB" \
  --output "$NGINX_CONF"

# Config is already tested and reloaded by the script
echo "✓ nginx configuration deployed"

#!/bin/bash
# auto-update-prometheus.sh
# Automatically regenerate Prometheus targets from Notion

set -euo pipefail

COMPUTE_DB="30b3d6434d24819dbc06e0046b140c30"
TARGETS_PATH="/etc/prometheus/targets/notion-hosts.yml"
SCRIPT_DIR="/opt/notion2config/converters"

# Ensure NOTION_TOKEN is set
if [[ -z "${NOTION_TOKEN:-}" ]]; then
  echo "ERROR: NOTION_TOKEN not set" >&2
  exit 1
fi

# Generate new targets
"${SCRIPT_DIR}/notion-prometheus.sh" \
  --database "$COMPUTE_DB" \
  --output "$TARGETS_PATH"

# Prometheus will auto-reload the file (file_sd_configs)
echo "✓ Prometheus targets updated (auto-reload enabled)"

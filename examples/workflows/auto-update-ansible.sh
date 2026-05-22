#!/bin/bash
# auto-update-ansible.sh
# Automatically regenerate Ansible inventory from Notion

set -euo pipefail

COMPUTE_DB="30b3d6434d24819dbc06e0046b140c30"
INVENTORY_PATH="/etc/ansible/inventory.ini"
SCRIPT_DIR="/opt/notion2config/converters"

# Ensure NOTION_TOKEN is set
if [[ -z "${NOTION_TOKEN:-}" ]]; then
  echo "ERROR: NOTION_TOKEN not set" >&2
  exit 1
fi

# Generate new inventory
"${SCRIPT_DIR}/notion-ansible.sh" \
  --database "$COMPUTE_DB" \
  --output "$INVENTORY_PATH"

# Validate inventory
if command -v ansible-inventory &>/dev/null; then
  ansible-inventory -i "$INVENTORY_PATH" --list >/dev/null && \
    echo "✓ Ansible inventory validated"
fi

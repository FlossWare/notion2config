#!/usr/bin/env bash
# notion-prometheus.sh
# Pulls the Compute database from Notion and generates a Prometheus file service
# discovery config in YAML format for scraping node_exporter on infrastructure hosts.
#
# Requirements:
#   - curl
#   - jq (>= 1.6)
#   - A Notion integration token with read access to the Compute database
#
# Usage:
#   NOTION_TOKEN=secret_xxx ./notion-prometheus.sh
#   NOTION_TOKEN=secret_xxx ./notion-prometheus.sh --output prometheus-targets.yml
#   NOTION_TOKEN=secret_xxx ./notion-prometheus.sh --dry-run

set -euo pipefail

# Temp files for large database handling
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# ── Configuration ─────────────────────────────────────────────────────────────

NOTION_TOKEN="${NOTION_TOKEN:-}"
DATABASE_ID="30b3d6434d24819dbc06e0046b140c30"   # Compute database
NOTION_API="https://api.notion.com/v1"
NOTION_VERSION="2022-06-28"

OUTPUT_FILE=""
DRY_RUN=false
FILTER_TYPE=""
FILTER_LOCATION=""
FILTER_STATUS=""
EXPORTER_PORT="9100"  # Default node_exporter port

# ── Argument parsing ──────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output|-o)
      OUTPUT_FILE="$2"; shift 2 ;;
    --dry-run|-n)
      DRY_RUN=true; shift ;;
    --token|-t)
      NOTION_TOKEN="$2"; shift 2 ;;
    --database|-d)
      DATABASE_ID="$2"; shift 2 ;;
    --port|-p)
      EXPORTER_PORT="$2"; shift 2 ;;
    --filter-type)
      FILTER_TYPE="$2"; shift 2 ;;
    --filter-location)
      FILTER_LOCATION="$2"; shift 2 ;;
    --filter-status)
      FILTER_STATUS="$2"; shift 2 ;;
    --help|-h)
      grep '^#' "$0" | head -20 | sed 's/^# \?//'
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# ── Preflight checks ──────────────────────────────────────────────────────────

if [[ -z "$NOTION_TOKEN" ]]; then
  echo "ERROR: NOTION_TOKEN is not set." >&2
  echo "       Export it or pass --token secret_xxx" >&2
  exit 1
fi

for cmd in curl jq; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is required but not found in PATH." >&2
    exit 1
  fi
done

# ── Notion helpers ────────────────────────────────────────────────────────────

notion_query() {
  local db_id="$1"
  local cursor="${2:-}"
  local body

  if [[ -n "$cursor" ]]; then
    body=$(jq -n --arg c "$cursor" '{"start_cursor": $c, "page_size": 100}')
  else
    body='{"page_size": 100}'
  fi

  curl -s -X POST \
    "${NOTION_API}/databases/${db_id}/query" \
    -H "Authorization: Bearer ${NOTION_TOKEN}" \
    -H "Notion-Version: ${NOTION_VERSION}" \
    -H "Content-Type: application/json" \
    -d "$body"
}

# ── Fetch all pages (handles pagination) ──────────────────────────────────────

echo "→ Querying Notion Compute database..." >&2

echo "[]" > "$TEMP_DIR/all_results.json"
cursor=""

while true; do
  notion_query "$DATABASE_ID" "$cursor" > "$TEMP_DIR/response.json"

  # Check for API errors
  if jq -e '.object == "error"' "$TEMP_DIR/response.json" &>/dev/null; then
    echo "ERROR: Notion API returned an error:" >&2
    jq -r '.message' "$TEMP_DIR/response.json" >&2
    exit 1
  fi

  # Append results
  jq '.results' "$TEMP_DIR/response.json" > "$TEMP_DIR/page_results.json"
  jq -s '.[0] + .[1]' "$TEMP_DIR/all_results.json" "$TEMP_DIR/page_results.json" > "$TEMP_DIR/merged.json"
  mv "$TEMP_DIR/merged.json" "$TEMP_DIR/all_results.json"

  has_more=$(jq -r '.has_more' "$TEMP_DIR/response.json")
  [[ "$has_more" == "true" ]] || break
  cursor=$(jq -r '.next_cursor' "$TEMP_DIR/response.json")
done

total=$(jq 'length' "$TEMP_DIR/all_results.json")
echo "→ Found ${total} entries." >&2

# ── Extract and filter fields ─────────────────────────────────────────────────

# Build filter expression
filter_expr="select(.name != \"\" and .ip != \"\")"
if [[ -n "$FILTER_TYPE" ]]; then
  filter_expr="$filter_expr | select(.type == \"$FILTER_TYPE\")"
fi
if [[ -n "$FILTER_LOCATION" ]]; then
  filter_expr="$filter_expr | select(.location == \"$FILTER_LOCATION\")"
fi
if [[ -n "$FILTER_STATUS" ]]; then
  filter_expr="$filter_expr | select(.status == \"$FILTER_STATUS\")"
fi

# Extract fields with filtering
jq --arg filter "$filter_expr" '[
  .[] |
  {
    name:     (.properties.Name.title[0].plain_text // "" | ascii_downcase | gsub(" "; "-")),
    ip:       (.properties.IP.rich_text[0].plain_text // ""),
    type:     (.properties.Type.select.name // "unknown"),
    location: (.properties.Location.select.name // "unknown"),
    os:       (.properties.OS.select.name // "unknown"),
    status:   (.properties.Status.select.name // "")
  } |
  '"$filter_expr"'
] | sort_by(.type, .name)' "$TEMP_DIR/all_results.json" > "$TEMP_DIR/hosts.json"

filtered_total=$(jq 'length' "$TEMP_DIR/hosts.json")
if [[ "$filtered_total" -lt "$total" ]]; then
  echo "→ Filtered to ${filtered_total} entries." >&2
fi

# ── Generate Prometheus targets ───────────────────────────────────────────────

generate_targets() {
  local ts
  ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  cat <<EOF
# prometheus-targets.yml — auto-generated by notion-prometheus.sh
# Source : Notion Compute database (${DATABASE_ID})
# Generated: ${ts}
# DO NOT EDIT BY HAND — regenerate with notion-prometheus.sh
#
# Configure in prometheus.yml:
#   scrape_configs:
#     - job_name: 'infrastructure'
#       file_sd_configs:
#         - files:
#           - '/etc/prometheus/targets/*.yml'
#       relabel_configs:
#         - source_labels: [__address__]
#           target_label: instance
#           regex: '([^:]+):\d+'
#           replacement: '\$1'

EOF

  # Group hosts by type and create target groups
  local types
  types=$(jq -r '[.[].type] | unique | .[]' "$TEMP_DIR/hosts.json")

  for type in $types; do
    # Get all hosts of this type
    local targets
    targets=$(jq -r --arg t "$type" --arg p "$EXPORTER_PORT" '
      [.[] | select(.type == $t) | .ip + ":" + $p] | join("\",\n    - \"")
    ' "$TEMP_DIR/hosts.json")

    # Get a sample host for labels (they all share same type)
    local location os
    location=$(jq -r --arg t "$type" '[.[] | select(.type == $t)][0].location' "$TEMP_DIR/hosts.json")
    os=$(jq -r --arg t "$type" '[.[] | select(.type == $t)][0].os' "$TEMP_DIR/hosts.json")

    cat <<EOF
- targets:
    - "${targets}"
  labels:
    job: node_exporter
    type: ${type}
    location: ${location}
    os: ${os}

EOF
  done
}

# ── Output ────────────────────────────────────────────────────────────────────

config=$(generate_targets)

if $DRY_RUN; then
  echo "=== DRY RUN — would write: ===" >&2
  echo "$config"
elif [[ -n "$OUTPUT_FILE" ]]; then
  # Backup existing file if present
  if [[ -f "$OUTPUT_FILE" ]]; then
    cp "$OUTPUT_FILE" "${OUTPUT_FILE}.bak"
    echo "→ Backed up existing file to ${OUTPUT_FILE}.bak" >&2
  fi
  echo "$config" > "$OUTPUT_FILE"
  echo "→ Written to ${OUTPUT_FILE}" >&2
  # Check if Prometheus is running
  if command -v systemctl &>/dev/null && systemctl is-active --quiet prometheus 2>/dev/null; then
    echo "→ Prometheus is running. It will auto-reload the target file." >&2
  fi
else
  echo "$config"
fi

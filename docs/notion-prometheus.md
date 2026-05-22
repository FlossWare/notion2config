# notion-prometheus.sh - Detailed Documentation

Generate Prometheus file service discovery targets from Notion Compute database.

## Overview

Creates YAML file for Prometheus file_sd_configs with targets grouped by Type. Automatically discovers node_exporter instances on infrastructure hosts.

## Usage

```bash
notion-prometheus.sh [--output FILE] [--port PORT] [--dry-run] [--token TOKEN] [--database ID] [--help]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output FILE` | Write to FILE | stdout |
| `-p, --port PORT` | Exporter port | 9100 (node_exporter) |
| `-n, --dry-run` | Preview only | false |
| `-t, --token TOKEN` | Notion token | `$NOTION_TOKEN` |
| `-d, --database ID` | Database ID | hardcoded |
| `-h, --help` | Show help | - |

## Examples

```bash
# Generate targets for node_exporter (port 9100)
./notion-prometheus.sh -o /etc/prometheus/targets/notion-hosts.yml

# Custom exporter port
./notion-prometheus.sh --port 9256 -o postgres-exporters.yml
```

## Database Requirements

**Required:**
- **Name** (Title): Hostname (for reference)
- **IP** (Text): Target IP

**Optional (added as labels):**
- **Type**: Added as `type` label
- **Location**: Added as `location` label
- **OS**: Added as `os` label

## Output Format

```yaml
# prometheus-targets.yml — auto-generated

- targets:
    - "192.168.1.10:9100"
    - "192.168.1.11:9100"
  labels:
    job: node_exporter
    type: web
    location: datacenter-1
    os: Ubuntu

- targets:
    - "192.168.1.20:9100"
  labels:
    job: node_exporter
    type: database
    location: datacenter-1
    os: Ubuntu
```

## Prometheus Configuration

In `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'infrastructure'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.yml'
        refresh_interval: 5m
    
    relabel_configs:
      # Use hostname instead of IP:port for instance label
      - source_labels: [__address__]
        target_label: instance
        regex: '([^:]+):\d+'
        replacement: '$1'
```

## Behavior

- **Auto-reload:** Prometheus reloads file_sd targets automatically
- **Grouping:** Targets grouped by Type for efficient scraping
- **Labels:** Type, Location, OS available for filtering/alerting

## Integration

### Multiple Exporters

Generate separate files per exporter type:

```bash
# Node exporter
./notion-prometheus.sh -p 9100 -o targets/node.yml

# Postgres exporter  
./notion-prometheus.sh -p 9187 -o targets/postgres.yml
```

### PromQL Queries

Use labels for filtering:

```promql
# All web servers CPU usage
node_cpu_seconds_total{type="web"}

# Specific location
up{location="datacenter-1"}

# Filter by OS
node_memory_Active_bytes{os="Ubuntu"}
```

### Alerting

```yaml
- alert: HostDown
  expr: up{job="node_exporter"} == 0
  labels:
    severity: critical
  annotations:
    summary: "Host {{ $labels.instance }} ({{ $labels.type }}) is down"
    location: "{{ $labels.location }}"
```

## Troubleshooting

**Targets not appearing:**
- Check file path in prometheus.yml matches output
- Verify refresh_interval allows time for reload
- Check Prometheus logs for file read errors

**"invalid YAML":**
- Use `promtool check config` to validate
- Ensure proper YAML formatting

**Wrong ports:**
- Use `--port` flag for custom exporter ports
- Different exporters need separate target files

## Filtering Options (v2.0+)

Create targeted scrape configs:

```bash
# Only monitor web servers
./notion-prometheus.sh --filter-type web -o web-targets.yml

# Only specific datacenter
./notion-prometheus.sh --filter-location datacenter-1

# Production hosts only
./notion-prometheus.sh --filter-status Active -o prod-targets.yml
```

## Large Database Support

- Handles unlimited infrastructure entries
- Uses temp files to prevent memory issues
- Efficient grouping for large fleets

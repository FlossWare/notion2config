# notion-hosts.sh - Detailed Documentation

Generate /etc/hosts file from Notion Compute database.

## Overview

Queries Notion Compute database and generates /etc/hosts file with IP-to-hostname mappings. Useful for maintaining consistent host resolution across infrastructure.

## Usage

```bash
notion-hosts.sh [--output FILE] [--dry-run] [--token TOKEN] [--database ID] [--help]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output FILE` | Write to FILE | stdout |
| `-n, --dry-run` | Preview only | false |
| `-t, --token TOKEN` | Notion token | `$NOTION_TOKEN` |
| `-d, --database ID` | Database ID | hardcoded |
| `-h, --help` | Show help | - |

## Examples

```bash
# Preview
./notion-hosts.sh --dry-run

# Generate to temp file
./notion-hosts.sh -o /tmp/hosts

# Deploy (manual copy required)
./notion-hosts.sh -o /tmp/hosts
sudo cp /tmp/hosts /etc/hosts
```

## Database Requirements

**Required:**
- **Name** (Title): Hostname
- **IP** (Text): IPv4 address

**Optional:** All other columns (ignored)

## Output Format

```
# /etc/hosts — auto-generated
# Source: Notion Compute database
# Generated: TIMESTAMP

# Localhost entries
127.0.0.1       localhost
::1             localhost ip6-localhost

# Compute inventory
192.168.1.10    web-01
192.168.1.11    web-02
```

## Behavior

- **Sorting:** By IP address (numeric)
- **Localhost:** Always included at top
- **IPv6:** Localhost IPv6 entries included
- **No reload:** Manual copy to /etc/hosts required

## Integration

### Automated Deployment

```bash
#!/bin/bash
./notion-hosts.sh -o /tmp/hosts
if diff -q /tmp/hosts /etc/hosts >/dev/null; then
  echo "No changes"
else
  sudo cp /tmp/hosts /etc/hosts
  echo "Updated /etc/hosts"
fi
```

### Git Tracking

```bash
./notion-hosts.sh -o /etc/hosts.notion
cd /etc && git diff hosts.notion
```

## Troubleshooting

**Permission denied:**
- /etc/hosts requires root write access
- Generate to /tmp first, then `sudo cp`

**IPv6 not needed:**
- Edit script to remove ::1 section

**Duplicate IPs:**
- Notion may have multiple hosts with same IP
- Last one wins in /etc/hosts

## Filtering Options (v2.0+)

Generate targeted host files:

```bash
# Only web servers
./notion-hosts.sh --filter-type web -o /tmp/web-hosts

# Only production hosts
./notion-hosts.sh --filter-status Active -o /tmp/prod-hosts

# Specific location
./notion-hosts.sh --filter-location datacenter-1
```

## Large Database Support

- Uses temp files for unlimited database size
- Successfully tested with 100+ entries
- No "Argument list too long" errors

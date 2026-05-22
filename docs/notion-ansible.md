# notion-ansible.sh - Detailed Documentation

Generate Ansible inventory (INI format) from Notion Compute database.

## Overview

`notion-ansible.sh` queries the Notion Compute database and generates an Ansible inventory file with:

1. **Host groups** - Based on the Type column (e.g., [web], [database])
2. **Host variables** - ansible_host, ansible_mac, ansible_os_family, location
3. **Common variables** - [all:vars] section for defaults

This enables managing Ansible inventory in Notion and automatically generating inventory files for deployment automation.

## Usage

### Basic Syntax

```bash
notion-ansible.sh [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output FILE`, `-o FILE` | Write output to FILE | stdout |
| `--dry-run`, `-n` | Preview output without writing | false |
| `--token TOKEN`, `-t TOKEN` | Notion integration token | `$NOTION_TOKEN` |
| `--database ID`, `-d ID` | Notion database ID | hardcoded Compute DB |
| `--filter-type TYPE` | Filter by Type column | none |
| `--filter-location LOC` | Filter by Location column | none |
| `--filter-status STATUS` | Filter by Status column | none |
| `--help`, `-h` | Show help message | - |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NOTION_TOKEN` | Notion integration token | Yes |

## Examples

### Preview Output

```bash
export NOTION_TOKEN=secret_xxx
./notion-ansible.sh --dry-run
```

### Generate to File

```bash
./notion-ansible.sh --output inventory.ini
```

### Direct to Production

```bash
./notion-ansible.sh -o /etc/ansible/inventory.ini
```

### Use Filtering

```bash
# Only web servers
./notion-ansible.sh --filter-type web --dry-run

# Only datacenter-1 hosts
./notion-ansible.sh --filter-location datacenter-1 -o dc1-inventory.ini

# Combine filters
./notion-ansible.sh --filter-type web --filter-location datacenter-1
```

### Test Inventory

```bash
ansible-inventory -i inventory.ini --list
ansible all -i inventory.ini -m ping
```

## Database Requirements

### Required Columns

| Column | Type | Purpose | Example |
|--------|------|---------|---------|
| **Name** | Title | Hostname | `web-01` |
| **IP** | Text | ansible_host value | `192.168.1.10` |

### Optional Columns (Recommended)

| Column | Type | Maps To | Example |
|--------|------|---------|---------|
| **MAC** | Text | ansible_mac | `aa:bb:cc:dd:ee:01` |
| **Type** | Select | Group name | `web` → `[web]` |
| **Location** | Select | location var | `datacenter-1` |
| **OS** | Select | ansible_os_family | `Ubuntu` |

## Output Format

### INI Structure

```ini
# Ansible inventory — auto-generated
# Source: Notion Compute database (ID)
# Generated: TIMESTAMP

[GROUP_NAME]
host-1 ansible_host=IP [ansible_mac=MAC] [ansible_os_family=OS] [location=LOC]
host-2 ansible_host=IP ...

[ANOTHER_GROUP]
host-3 ansible_host=IP ...

[all:vars]
# ansible_user=admin
# ansible_ssh_private_key_file=~/.ssh/id_rsa
```

### Grouping Logic

- **Type column → Group name:** Type="web" becomes `[web]`
- **Normalization:** Lowercase, non-alphanumeric → underscore
- **Ungrouped:** Hosts without Type go to `[ungrouped]`
- **Sorting:** Alphabetical within each group

## Behavior

### Pagination
- Handles large databases (100 entries per API call)
- Automatically follows next_cursor

### File Operations
- Creates backup (.bak) before overwriting
- No service reload (manual `ansible-inventory --graph` to verify)

### Error Handling
- Validates NOTION_TOKEN is set
- Checks for curl and jq availability
- Reports Notion API errors with messages
- Skips entries without Name or IP

## Integration Examples

### Use with ansible-playbook

```bash
# Generate inventory
./notion-ansible.sh -o inventory.ini

# Run playbook
ansible-playbook -i inventory.ini deploy.yml
```

### Dynamic Inventory Wrapper

```bash
#!/bin/bash
# ansible-notion-inventory.sh
# Dynamic inventory script for Ansible

./notion-ansible.sh
```

Make executable and use:
```bash
ansible-playbook -i ansible-notion-inventory.sh playbook.yml
```

### Automated Updates (cron)

```bash
# /etc/cron.d/ansible-inventory
0 * * * * user NOTION_TOKEN=xxx /opt/notion2config/converters/notion-ansible.sh -o /etc/ansible/inventory.ini
```

### Systemd Timer

See `examples/workflows/systemd-timers/` for complete example.

## Troubleshooting

### "Group name contains invalid characters"

**Cause:** Type column has special characters

**Solution:** Use alphanumeric + underscore only, or script normalizes automatically

### "Host appears in multiple groups"

**Cause:** Each host should have one Type value

**Solution:** Use Ansible group inheritance in playbooks instead

### "ansible_host not set"

**Cause:** IP column is empty in Notion

**Solution:** Fill IP column for all hosts

## Security

### Least Privilege
- Integration needs read-only access to Compute database
- Run as non-root user where possible

### Credentials
- Store NOTION_TOKEN in environment file (`/etc/ansible/notion.env`)
- Set file permissions: `chmod 600 /etc/ansible/notion.env`
- Load with: `source /etc/ansible/notion.env`

### Sensitive Data
- Avoid storing passwords/keys in Notion
- Use Ansible Vault for secrets
- Inventory should contain connection info only

## Advanced Usage

### Multiple Environments

Create separate databases or use Status column:

```bash
# Production
./notion-ansible.sh --database PROD_DB_ID -o prod-inventory.ini

# Staging
./notion-ansible.sh --database STAGING_DB_ID -o staging-inventory.ini
```

### Custom Variables

Extend the script to read additional Notion columns as Ansible variables.

### Group Nesting

Ansible supports group nesting in INI format. Enhance script to support parent groups.

## Performance

- **Small (<100 hosts):** <2 seconds
- **Medium (100-500 hosts):** 5-10 seconds (multiple pages)
- **Large (>500 hosts):** 15-30 seconds
- **Very Large (1000+ hosts):** Uses temp files to avoid memory limits

**Optimizations:**
- Temp file storage prevents "Argument list too long" errors
- Supports unlimited database size
- Pagination handles large result sets automatically

Notion API rate limits: ~3 requests/second

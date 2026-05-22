# Database Schemas Reference

notion2config uses two Notion databases with different schemas optimized for different purposes.

## Compute Database

**Purpose:** Track infrastructure hosts (physical servers, VMs, network devices)

**Used by:** dnsmasq, Ansible, /etc/hosts, Terraform, Prometheus

### Required Columns

| Column | Type | Property Path | Description | Example |
|--------|------|---------------|-------------|---------|
| **Name** | Title | `.properties.Name.title[0].plain_text` | Hostname | `server-01` |
| **IP** | Text | `.properties.IP.rich_text[0].plain_text` | IPv4 address | `192.168.1.100` |
| **MAC** | Text | `.properties.MAC.rich_text[0].plain_text` | MAC address (optional for some tools) | `aa:bb:cc:dd:ee:ff` |

### Optional Columns (for organization)

| Column | Type | Property Path | Description | Used By |
|--------|------|---------------|-------------|---------|
| **Type** | Select | `.properties.Type.select.name` | Host type/role | Ansible (grouping), Prometheus (labels) |
| **Location** | Select | `.properties.Location.select.name` | Physical/cloud location | Ansible (vars), Prometheus (labels) |
| **OS** | Select | `.properties.OS.select.name` | Operating system | Ansible (vars), Prometheus (labels) |
| Status | Select | - | Operational status | - |
| Notes | Text | - | Additional information | - |
| Owner | Person | - | Responsible person | - |
| Tags | Multi-select | - | Categorization | - |

### Data Processing Rules

**Name normalization:**
- Convert to lowercase
- Replace spaces with hyphens
- Used as hostname across all tools

**MAC normalization:**
- Accept formats: `AA:BB:CC:DD:EE:FF`, `aa-bb-cc-dd-ee-ff`, `aabbccddeeff`
- Normalize to lowercase colon-separated format
- Strip non-hexadecimal characters

**IP validation:**
- Used as-is (no validation by default)
- Assumed to be valid IPv4

**Filtering:**
- Entries without Name are skipped
- Tool-specific filtering (e.g., dnsmasq skips entries without IP/MAC)

### Example Data

| Name | IP | MAC | Type | Location | OS |
|------|-----|-----|------|----------|-----|
| web-01 | 192.168.1.10 | aa:bb:cc:dd:ee:01 | web | datacenter-1 | Ubuntu |
| web-02 | 192.168.1.11 | aa:bb:cc:dd:ee:02 | web | datacenter-1 | Ubuntu |
| db-01 | 192.168.1.20 | aa:bb:cc:dd:ee:03 | database | datacenter-1 | Ubuntu |
| monitor-01 | 192.168.1.30 | aa:bb:cc:dd:ee:05 | monitoring | datacenter-1 | Ubuntu |
| cloud-server | 203.0.113.100 | | cloud | aws-us-east-1 | Ubuntu |

## Services Database

**Purpose:** Track applications and services (web apps, containers, APIs)

**Used by:** nginx, Docker Compose

### Required Columns

| Column | Type | Property Path | Description | Example | Used By |
|--------|------|---------------|-------------|---------|---------|
| **Name** | Title | `.properties.Name.title[0].plain_text` | Service identifier | `grafana` | Both |
| **Domain** | Text | `.properties.Domain.rich_text[0].plain_text` | Public domain | `grafana.example.com` | nginx |
| **Backend** | Text | `.properties.Backend.rich_text[0].plain_text` | Backend URL | `http://192.168.1.50:3000` | nginx |
| **Port** | Number | `.properties.Port.number` | External port | `443` | nginx |
| **Image** | Text | `.properties.Image.rich_text[0].plain_text` | Docker image | `grafana/grafana:latest` | Docker Compose |
| **Ports** | Text | `.properties.Ports.rich_text[0].plain_text` | Port mappings | `3000:3000,3001:3001` | Docker Compose |
| **Volumes** | Text | `.properties.Volumes.rich_text[0].plain_text` | Volume mounts | `/data:/var/lib/grafana` | Docker Compose |
| **Environment** | Text | `.properties.Environment.rich_text[0].plain_text` | Env vars | `KEY=value,KEY2=value2` | Docker Compose |

### Optional Columns

| Column | Type | Property Path | Description | Used By |
|--------|------|---------------|-------------|---------|
| **SSL** | Checkbox | `.properties.SSL.checkbox` | Enable HTTPS | nginx (SSL config) |
| **Network** | Text | `.properties.Network.rich_text[0].plain_text` | Docker network | Docker Compose |
| Type | Select | - | Service type | - |
| Status | Select | - | Active/Inactive | - |
| Owner | Person | - | Service owner | - |
| Notes | Text | - | Additional info | - |

### Data Format Specifications

**Ports (Docker Compose):**
- Format: `HOST:CONTAINER[,HOST:CONTAINER,...]`
- Example: `80:80,443:443`

**Volumes (Docker Compose):**
- Format: `HOST_PATH:CONTAINER_PATH[:OPTIONS][,...]`
- Example: `/data:/var/lib/data,/logs:/var/log:ro`

**Environment (Docker Compose):**
- Format: `KEY=VALUE[,KEY=VALUE,...]`
- Example: `NODE_ENV=production,PORT=3000`

**Backend (nginx):**
- Format: `PROTOCOL://HOST:PORT`
- Example: `http://192.168.1.100:8080`

### Example Data

| Name | Domain | Backend | Port | SSL | Image | Ports | Volumes | Environment |
|------|--------|---------|------|-----|-------|-------|---------|-------------|
| grafana | grafana.example.com | http://192.168.1.50:3000 | 443 | ✓ | grafana/grafana:latest | 3000:3000 | /data/grafana:/var/lib/grafana | GF_ADMIN_PASSWORD=secret |
| postgres | | | | | postgres:15-alpine | 5432:5432 | /data/postgres:/var/lib/postgresql/data | POSTGRES_PASSWORD=dbpass |
| api | api.example.com | http://192.168.1.60:8080 | 80 | | | | | |

## Database ID Configuration

Each converter accepts the database ID via:
1. Command-line: `--database <id>`
2. Hardcoded default (edit script)
3. Environment variable (future enhancement)

### Finding Your Database ID

From the Notion database URL:
```
https://notion.so/workspace/30b3d6434d24819dbc06e0046b140c30?v=...
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                          This is your database ID (32 chars)
```

## API Property Access Patterns

All converters use consistent jq patterns to extract Notion properties:

**Title properties:**
```jq
.properties.Name.title[0].plain_text // ""
```

**Rich text properties:**
```jq
.properties.IP.rich_text[0].plain_text // ""
```

**Select properties:**
```jq
.properties.Type.select.name // "default-value"
```

**Number properties:**
```jq
.properties.Port.number // 80
```

**Checkbox properties:**
```jq
.properties.SSL.checkbox // false
```

## Schema Migration

### Adding Optional Columns

Optional columns can be added to existing databases without breaking converters:
- Converters use `// ""` or `// false` defaults
- Missing columns return empty values
- No script changes needed

### Removing Columns

Required columns cannot be removed without breaking converters. Update scripts to handle missing columns if needed.

### Renaming Columns

Column names are case-sensitive. Renaming requires updating the converter script's property paths.

## Best Practices

1. **Consistent naming:** Use kebab-case for hostnames (`web-01` not `Web 01`)
2. **Validate data:** Use Notion formulas to validate IP formats
3. **Use selects:** Type, Location, OS should be Select (not Text) for consistency
4. **Document conventions:** Add a "README" page in Notion explaining column purposes
5. **Regular backups:** Export database periodically
6. **Access control:** Limit integration to read-only permissions

## Template Creation

Quick database duplication:
1. Open Notion database
2. Click "•••" → "Duplicate"
3. Rename to match purpose (Compute vs Services)
4. Share with integration
5. Populate with initial data
6. Test with `--dry-run`

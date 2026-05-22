# notion2config

**System Configs from Notion Databases**

Generate infrastructure configuration files from Notion databases. Keep your inventory in Notion and automatically generate configs for dnsmasq, Ansible, nginx, and more.

> *Infrastructure as data, configs as code.*

## Overview

Stop maintaining infrastructure configuration in multiple places. Keep your single source of truth in Notion (network devices, servers, containers, services) and automatically generate system configuration files.

### Why Notion?

- 📊 **Centralized inventory** - Single source of truth for all infrastructure
- 👥 **Team collaboration** - Non-technical members can update
- 🔗 **Rich data model** - Relations, formulas, rollups, tags
- 📝 **Change tracking** - Built-in history and comments
- 🔌 **API access** - Automated config generation

### Current Tools

- ✅ **dnsmasq** - DHCP and DNS configuration
- 🚧 **Ansible** - Inventory generation (planned)
- 🚧 **nginx** - Reverse proxy configs (planned)
- 🚧 **/etc/hosts** - Host files (planned)
- 🚧 **Docker Compose** - Container definitions (planned)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/FlossWare/notion2config.git
cd notion2config

# Set your Notion integration token
export NOTION_TOKEN=secret_xxx

# Validate access
./tests/validate-notion-access.sh <database-id>

# Generate dnsmasq config (dry run)
./converters/notion-dnsmasq.sh --dry-run

# Generate to file
./converters/notion-dnsmasq.sh -o /tmp/dnsmasq-hosts.conf
```

## Tools

### notion-dnsmasq.sh

Generates dnsmasq configuration from a Notion database containing network device inventory.

**Features:**
- 🔍 Queries Notion database (handles pagination)
- 🌐 Generates `dhcp-host` entries for static DHCP leases
- 📇 Generates `address` entries for DNS A records
- 💾 Backs up existing configs before overwriting
- 🔄 Auto-reloads dnsmasq service (systemd)
- 👁️ Dry-run mode for testing

**Usage:**
```bash
# Preview output
./converters/notion-dnsmasq.sh --dry-run

# Generate config file
./converters/notion-dnsmasq.sh --output /etc/dnsmasq.d/hosts.conf

# Use custom database
./converters/notion-dnsmasq.sh --database <db-id> -o hosts.conf
```

See [docs/notion-dnsmasq.md](docs/notion-dnsmasq.md) for detailed documentation.

## Requirements

### General

- **Notion API access** - Integration token with database read permissions
- **curl** - HTTP requests
- **jq** - JSON parsing (>= 1.6)

### Tool-Specific

- **dnsmasq** - For dnsmasq config generation

### Installation

**Debian/Ubuntu:**
```bash
sudo apt-get install curl jq dnsmasq
```

**FreeBSD:**
```bash
sudo pkg install curl jq dnsmasq
```

**macOS:**
```bash
brew install curl jq
```

## Notion Setup

### 1. Create Integration

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Name it (e.g., "Infrastructure Automation")
4. Copy the "Internal Integration Token" (starts with `secret_`)

### 2. Share Database

1. Open your Notion database
2. Click "•••" → "Add connections"
3. Select your integration
4. Grant access

### 3. Get Database ID

From the database URL:
```
https://notion.so/myworkspace/30b3d6434d24819dbc06e0046b140c30?v=...
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                              This is your database ID
```

## Database Schema

### Compute Database (for dnsmasq)

**Required columns:**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| **Name** | Title | Hostname | `server-01` |
| **IP** | Text | IP address | `192.168.1.100` |
| **MAC** | Text | MAC address (optional) | `aa:bb:cc:dd:ee:ff` |

**Optional columns** (for organization):

| Column | Type | Description |
|--------|------|-------------|
| Location | Select | Physical location |
| Type | Select | Device type |
| OS | Select | Operating system |
| Notes | Text | Additional info |

See [examples/compute-database-template.md](examples/compute-database-template.md) for complete template.

## Project Structure

```
notion2config/
├── README.md                       # This file
├── converters/
│   ├── notion-dnsmasq.sh          # dnsmasq config generator
│   ├── notion-ansible.sh          # Ansible inventory (planned)
│   ├── notion-hosts.sh            # /etc/hosts generator (planned)
│   └── notion-nginx.sh            # nginx config generator (planned)
├── examples/
│   ├── compute-database-template.md
│   ├── dnsmasq-output.conf
│   └── workflows/
│       └── auto-update-dnsmasq.sh (planned)
├── docs/
│   ├── notion-setup.md (planned)
│   ├── notion-dnsmasq.md
│   └── database-schemas.md (planned)
└── tests/
    └── validate-notion-access.sh
```

## Usage Examples

### Basic Workflow

```bash
# 1. Set up environment
export NOTION_TOKEN=secret_xxx

# 2. Test access (dry run)
./converters/notion-dnsmasq.sh --dry-run

# 3. Generate config
./converters/notion-dnsmasq.sh -o /tmp/dnsmasq-hosts.conf

# 4. Review output
cat /tmp/dnsmasq-hosts.conf

# 5. Deploy (requires sudo)
sudo ./converters/notion-dnsmasq.sh -o /etc/dnsmasq.d/hosts.conf
```

### Automated Updates

Create a cron job to sync configuration:

```bash
# /etc/cron.d/notion2config
# Update dnsmasq config from Notion every hour
0 * * * * root NOTION_TOKEN=secret_xxx /opt/notion2config/converters/notion-dnsmasq.sh -o /etc/dnsmasq.d/hosts.conf 2>&1 | logger -t notion2config
```

Or use systemd timer (see examples/workflows/).

## Security Best Practices

### Protect Your Notion Token

**Don't:**
- ❌ Hardcode tokens in scripts
- ❌ Commit tokens to git
- ❌ Share tokens in logs

**Do:**
- ✅ Use environment variables
- ✅ Store in secure credential manager
- ✅ Rotate tokens regularly
- ✅ Use read-only integration permissions

### Secure Token Storage

```bash
# Store token in systemd environment file
echo "NOTION_TOKEN=secret_xxx" | sudo tee /etc/notion2config/token.env
sudo chmod 600 /etc/notion2config/token.env

# Use with systemd service
[Service]
EnvironmentFile=/etc/notion2config/token.env
ExecStart=/opt/notion2config/converters/notion-dnsmasq.sh -o /etc/dnsmasq.d/hosts.conf
```

## FreeBSD Support

All scripts work on FreeBSD:

```bash
# Install dependencies
sudo pkg install curl jq dnsmasq

# Use FreeBSD paths
./converters/notion-dnsmasq.sh -o /usr/local/etc/dnsmasq.d/hosts.conf

# Reload dnsmasq on FreeBSD
sudo service dnsmasq reload
```

## Troubleshooting

### "Notion API returned an error"

**Possible causes:**
- Invalid token
- Database not shared with integration
- Missing read permission

**Solution:**
```bash
# Test API access
curl -H "Authorization: Bearer $NOTION_TOKEN" \
     -H "Notion-Version: 2022-06-28" \
     https://api.notion.com/v1/users/me
```

### "command not found: jq"

Install jq:
```bash
# Debian/Ubuntu
sudo apt-get install jq

# FreeBSD
sudo pkg install jq

# macOS
brew install jq
```

### "dnsmasq reload failed"

Check dnsmasq syntax:
```bash
dnsmasq --test
```

## Roadmap

### Short Term
- [ ] Ansible inventory generator
- [ ] /etc/hosts generator
- [ ] Validation tests
- [ ] CI/CD examples

### Medium Term
- [ ] nginx reverse proxy configs
- [ ] Docker Compose generator
- [ ] Terraform variables
- [ ] Prometheus service discovery

### Long Term
- [ ] Web UI for configuration
- [ ] Multi-database support
- [ ] Template system
- [ ] Real-time sync via webhooks

## Contributing

Contributions welcome! Ideas for new converters:

- **Ansible inventory** - Generate inventory from Notion
- **nginx configs** - Reverse proxy from services database
- **Docker Compose** - Container definitions
- **Terraform vars** - Generate tfvars from Notion
- **Prometheus targets** - Service discovery
- **HAProxy** - Load balancer configs
- **Kubernetes** - Resource definitions

See existing tools in `converters/` as reference implementations.

## Examples

### Generated dnsmasq Config

From a Notion database with 8 devices:

```
# dnsmasq.conf — auto-generated by notion-dnsmasq.sh
# Source : Notion Compute database (30b3d6434d24819dbc06e0046b140c30)
# Generated: 2026-05-21T15:30:00Z

# ── Static DHCP leases ────────────────────────────────────────────
dhcp-host=aa:bb:cc:dd:ee:01,server-01,192.168.1.100
dhcp-host=aa:bb:cc:dd:ee:02,server-02,192.168.1.101
...

# ── DNS address records ───────────────────────────────────────────
address=/server-01/192.168.1.100
address=/server-02/192.168.1.101
address=/cloud-server/203.0.113.100
...
```

See [examples/dnsmasq-output.conf](examples/dnsmasq-output.conf) for complete example.

## License

This project is provided as-is for educational and practical use.

## Resources

- [Notion API Documentation](https://developers.notion.com/)
- [dnsmasq Documentation](http://www.thekelleys.org.uk/dnsmasq/doc.html)
- [Notion Database Properties](https://developers.notion.com/reference/property-object)

## Author

**Scot P. Floess**
- GitHub: [@sfloess](https://github.com/sfloess)

## Version

Current version: 1.0.0

## Changelog

### 1.0.0 (2026-05-21)
- Initial release
- notion-dnsmasq.sh - Generate dnsmasq configs from Notion
- Notion API integration with pagination
- Auto-reload functionality
- Validation tools
- Complete documentation
- FreeBSD support

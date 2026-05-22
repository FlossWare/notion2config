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

### Available Tools

**Infrastructure Tools** (Compute Database):
- ✅ **dnsmasq** - DHCP and DNS configuration
- ✅ **Ansible** - Inventory generation (INI format)
- ✅ **/etc/hosts** - Host file generation
- ✅ **Terraform** - tfvars generation
- ✅ **Prometheus** - Service discovery targets

**Application Tools** (Services Database):
- ✅ **nginx** - Reverse proxy configuration
- ✅ **Docker Compose** - Container orchestration

## Quick Start

```bash
# Clone the repository
git clone https://github.com/FlossWare/notion2config.git
cd notion2config

# Set your Notion integration token
export NOTION_TOKEN=secret_xxx

# Validate access to Compute database
./tests/validate-notion-access.sh <compute-database-id>

# Try any converter (dry run mode):
./converters/notion-dnsmasq.sh --dry-run
./converters/notion-ansible.sh --dry-run
./converters/notion-hosts.sh --dry-run
./converters/notion-terraform.sh --dry-run
./converters/notion-prometheus.sh --dry-run

# For Services database tools, specify database ID:
./converters/notion-nginx.sh --database <services-db-id> --dry-run
./converters/notion-docker-compose.sh --database <services-db-id> --dry-run

# Generate to file
./converters/notion-ansible.sh -o inventory.ini
./converters/notion-terraform.sh -o terraform.tfvars
```

## Databases

notion2config uses two Notion databases for different purposes:

### Compute Database
**Purpose:** Infrastructure hosts (servers, VMs, network devices)  
**Columns:** Name, IP, MAC, Type, Location, OS  
**Used by:** dnsmasq, Ansible, /etc/hosts, Terraform, Prometheus  
**Template:** See [examples/compute-database-template.md](examples/compute-database-template.md)

### Services Database
**Purpose:** Applications and services (web apps, containers, APIs)  
**Columns:** Name, Domain, Backend, Port, SSL, Image, Ports, Volumes, Environment  
**Used by:** nginx, Docker Compose  
**Template:** See [examples/services-database-template.md](examples/services-database-template.md)

See [docs/database-schemas.md](docs/database-schemas.md) for complete schema documentation.

## Tools

### Infrastructure Tools (Compute Database)

#### notion-dnsmasq.sh
Generates dnsmasq DHCP and DNS configuration.
- Static DHCP leases (`dhcp-host`)
- DNS A records (`address`)
- Auto-reloads dnsmasq service

[Docs](docs/notion-dnsmasq.md) | [Example Output](examples/dnsmasq-output.conf)

#### notion-ansible.sh
Generates Ansible inventory in INI format.
- Groups hosts by Type
- Includes ansible_host, ansible_mac, ansible_os_family variables
- Ready for ansible-playbook

[Docs](docs/notion-ansible.md) | [Example Output](examples/ansible-inventory.ini)

#### notion-hosts.sh
Generates /etc/hosts file.
- IP to hostname mappings
- Includes localhost entries
- Sorted by IP address

[Docs](docs/notion-hosts.md) | [Example Output](examples/hosts-output.txt)

#### notion-terraform.sh
Generates Terraform tfvars file.
- HCL format
- compute_hosts map with all attributes
- Reference in .tf files

[Docs](docs/notion-terraform.md) | [Example Output](examples/terraform.tfvars)

#### notion-prometheus.sh
Generates Prometheus file service discovery targets.
- YAML format for file_sd_configs
- Grouped by Type with labels
- Auto-discovered by Prometheus

[Docs](docs/notion-prometheus.md) | [Example Output](examples/prometheus-targets.yml)

### Application Tools (Services Database)

#### notion-nginx.sh
Generates nginx reverse proxy configuration.
- Server blocks per service
- SSL/TLS support with auto HTTP→HTTPS redirect
- Config validation before reload

[Docs](docs/notion-nginx.md) | [Example Output](examples/nginx-services.conf)

**Usage:**
```bash
./converters/notion-nginx.sh --database <services-db-id> -o /etc/nginx/conf.d/services.conf
```

#### notion-docker-compose.sh
Generates docker-compose.yml.
- Docker Compose v3.8 format
- Supports ports, volumes, environment, networks
- Config validation

[Docs](docs/notion-docker-compose.md) | [Example Output](examples/docker-compose.yml)

**Usage:**
```bash
./converters/notion-docker-compose.sh --database <services-db-id> -o docker-compose.yml
```

## Requirements

### General

- **Notion API access** - Integration token with database read permissions
- **curl** - HTTP requests
- **jq** - JSON parsing (>= 1.6)

### Tool-Specific (optional)

- **dnsmasq** - For dnsmasq config generation and testing
- **ansible** - For Ansible inventory validation
- **nginx** - For nginx config testing
- **docker** or **docker-compose** - For Docker Compose validation
- **terraform** - For tfvars validation
- **prometheus** or **promtool** - For Prometheus config validation

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

## Common Features

All converters share these capabilities:

- **🔍 Pagination** - Handles large databases (100+ entries)
- **💾 Backups** - Creates .bak files before overwriting
- **👁️ Dry-run** - Preview output with `--dry-run`
- **🔄 Service reload** - Auto-reloads services when applicable
- **⚙️ Flexible** - Override database ID with `--database`
- **🛡️ Error handling** - Validates Notion API responses
- **📊 Logging** - Progress output to stderr

## Project Structure

```
notion2config/
├── README.md
├── converters/
│   ├── notion-dnsmasq.sh          # dnsmasq DHCP/DNS config
│   ├── notion-ansible.sh          # Ansible inventory
│   ├── notion-hosts.sh            # /etc/hosts file
│   ├── notion-terraform.sh        # Terraform tfvars
│   ├── notion-prometheus.sh       # Prometheus targets
│   ├── notion-nginx.sh            # nginx reverse proxy
│   └── notion-docker-compose.sh   # Docker Compose
├── examples/
│   ├── compute-database-template.md
│   ├── services-database-template.md
│   ├── dnsmasq-output.conf
│   ├── ansible-inventory.ini
│   ├── hosts-output.txt
│   ├── terraform.tfvars
│   ├── prometheus-targets.yml
│   ├── nginx-services.conf
│   ├── docker-compose.yml
│   └── workflows/
│       ├── auto-update-ansible.sh
│       ├── auto-update-prometheus.sh
│       ├── deploy-nginx-config.sh
│       └── systemd-timers/
│           ├── notion2config-ansible.service
│           ├── notion2config-ansible.timer
│           └── README.md
├── docs/
│   ├── notion-dnsmasq.md
│   ├── notion-ansible.md
│   ├── notion-hosts.md
│   ├── notion-terraform.md
│   ├── notion-prometheus.md
│   ├── notion-nginx.md
│   ├── notion-docker-compose.md
│   └── database-schemas.md
└── tests/
    └── validate-notion-access.sh
```

## Usage Examples

### Basic Workflow (Infrastructure)

```bash
# 1. Set up environment
export NOTION_TOKEN=secret_xxx
export COMPUTE_DB=30b3d6434d24819dbc06e0046b140c30  # Your Compute database ID

# 2. Test access (dry run)
./converters/notion-dnsmasq.sh --dry-run
./converters/notion-ansible.sh --dry-run

# 3. Generate all infrastructure configs
./converters/notion-dnsmasq.sh -o /tmp/dnsmasq-hosts.conf
./converters/notion-ansible.sh -o /tmp/inventory.ini
./converters/notion-hosts.sh -o /tmp/hosts
./converters/notion-terraform.sh -o /tmp/terraform.tfvars
./converters/notion-prometheus.sh -o /tmp/prometheus-targets.yml

# 4. Review and deploy
ansible-inventory -i /tmp/inventory.ini --list
terraform plan -var-file=/tmp/terraform.tfvars
sudo cp /tmp/dnsmasq-hosts.conf /etc/dnsmasq.d/hosts.conf
```

### Basic Workflow (Services)

```bash
# 1. Set up environment
export NOTION_TOKEN=secret_xxx
export SERVICES_DB=your-services-database-id

# 2. Test (dry run)
./converters/notion-nginx.sh --database $SERVICES_DB --dry-run
./converters/notion-docker-compose.sh --database $SERVICES_DB --dry-run

# 3. Generate configs
./converters/notion-nginx.sh -d $SERVICES_DB -o /tmp/nginx-services.conf
./converters/notion-docker-compose.sh -d $SERVICES_DB -o /tmp/docker-compose.yml

# 4. Deploy
sudo cp /tmp/nginx-services.conf /etc/nginx/conf.d/services.conf
sudo nginx -t && sudo systemctl reload nginx

docker-compose -f /tmp/docker-compose.yml up -d
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

### Completed (v2.0.0)
- [x] Ansible inventory generator
- [x] /etc/hosts generator
- [x] nginx reverse proxy configs
- [x] Docker Compose generator
- [x] Terraform variables generator
- [x] Prometheus service discovery
- [x] Comprehensive documentation
- [x] Example outputs and templates
- [x] Workflow automation examples

### Short Term
- [ ] Validation test suite
- [ ] CI/CD GitHub Actions workflows
- [ ] Additional database templates (HAProxy, Kubernetes)
- [ ] Web UI for configuration preview

### Medium Term
- [ ] Multi-database aggregation
- [ ] Template customization system
- [ ] Webhook-based auto-updates
- [ ] Monitoring/metrics integration

### Long Term
- [ ] GUI configuration builder
- [ ] Plugin system for custom converters
- [ ] Real-time collaboration features
- [ ] Change approval workflows

## Contributing

Contributions welcome! See existing tools in `converters/` as reference implementations.

### Converter Development Pattern

All converters follow this structure:
1. Bash script using curl + jq
2. Notion API pagination support
3. Command-line args: `--output`, `--dry-run`, `--token`, `--database`
4. Three output modes: stdout, file, dry-run
5. Backup before overwrite (.bak)
6. Service reload (if applicable)
7. Comprehensive documentation in `docs/`
8. Example output in `examples/`

### Ideas for New Converters

- **HAProxy** - Load balancer configs
- **Kubernetes** - Resource manifests (Deployments, Services)
- **Consul** - Service catalog registration
- **systemd-networkd** - Network interface configs
- **PowerDNS** - Zone files
- **Zabbix** - Host monitoring configs
- **pfSense/OPNsense** - Firewall rules (XML)

### Pull Request Guidelines

- Follow existing bash style and patterns
- Include documentation (follow `docs/notion-*.md` structure)
- Include example output
- Test with `--dry-run` mode
- Support pagination for large databases
- Handle missing/optional columns gracefully

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

Current version: **2.0.0**

## Changelog

### 2.0.0 (2026-05-22)
- **Major release:** All planned converters implemented
- Added notion-ansible.sh - Generate Ansible inventory (INI format)
- Added notion-hosts.sh - Generate /etc/hosts files
- Added notion-terraform.sh - Generate Terraform tfvars (HCL format)
- Added notion-prometheus.sh - Generate Prometheus service discovery targets
- Added notion-nginx.sh - Generate nginx reverse proxy configurations
- Added notion-docker-compose.sh - Generate Docker Compose files
- Introduced Services database schema for application-level configs
- Comprehensive documentation for all 7 converters
- Example outputs for all tools
- Workflow automation examples (cron, systemd timers)
- Database schema reference documentation
- Services database template

### 1.0.0 (2026-05-21)
- Initial release
- notion-dnsmasq.sh - Generate dnsmasq configs from Notion
- Notion API integration with pagination
- Auto-reload functionality
- Validation tools
- Compute database template
- FreeBSD support

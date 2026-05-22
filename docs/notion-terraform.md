# notion-terraform.sh - Detailed Documentation

Generate Terraform variables file (HCL) from Notion Compute database.

## Overview

Exports Notion Compute database as Terraform tfvars file with a `compute_hosts` map containing all host attributes. Reference in your .tf files for infrastructure as code.

## Usage

```bash
notion-terraform.sh [--output FILE] [--dry-run] [--token TOKEN] [--database ID] [--help]
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
# Generate tfvars
./notion-terraform.sh -o terraform.tfvars

# Use in Terraform
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Database Requirements

**Required:**
- **Name** (Title): Host identifier
- **IP** (Text): IP address

**Optional (exported if present):**
- MAC, Type, Location, OS

## Output Format

```hcl
# terraform.tfvars — auto-generated

compute_hosts = {
  "web-01" = {
    ip       = "192.168.1.10"
    mac      = "aa:bb:cc:dd:ee:01"
    type     = "web"
    location = "datacenter-1"
    os       = "Ubuntu"
  }
  "db-01" = {
    ip       = "192.168.1.20"
    mac      = "aa:bb:cc:dd:ee:03"
    type     = "database"
    location = "datacenter-1"
    os       = "Ubuntu"
  }
}
```

## Terraform Integration

### Define Variable

In your `variables.tf`:

```hcl
variable "compute_hosts" {
  type = map(object({
    ip       = string
    mac      = string
    type     = string
    location = string
    os       = string
  }))
  description = "Compute hosts from Notion"
}
```

### Use in Resources

```hcl
# Create DNS records for all hosts
resource "cloudflare_record" "hosts" {
  for_each = var.compute_hosts
  
  zone_id = var.zone_id
  name    = each.key
  value   = each.value.ip
  type    = "A"
}

# Filter by type
locals {
  web_servers = {
    for k, v in var.compute_hosts : k => v
    if v.type == "web"
  }
}
```

## Troubleshooting

**"variable not declared":**
- Add variable definition to variables.tf

**"empty string not allowed":**
- Optional fields may be empty
- Use `try()` or `coalesce()` functions

**"syntax error":**
- Validate with `terraform fmt terraform.tfvars`

## Filtering Options (v2.0+)

Generate tfvars for subsets of infrastructure:

```bash
# Only web tier
./notion-terraform.sh --filter-type web -o web-hosts.tfvars

# Only specific location
./notion-terraform.sh --filter-location aws-us-east-1 -o aws-hosts.tfvars

# Production only
./notion-terraform.sh --filter-status Active
```

## Large Database Support

- Uses temp files to handle unlimited entries
- Tested with 100+ host definitions
- Efficient memory usage for large infrastructures

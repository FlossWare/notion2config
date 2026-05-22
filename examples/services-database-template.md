# Notion Services Database Template

This template describes the **Services database** schema for generating nginx reverse proxy configs and Docker Compose files from Notion.

Unlike the Compute database (which tracks infrastructure hosts), the Services database tracks **applications and services** running on that infrastructure.

## Quick Setup

1. Create a new database in Notion named "Services"
2. Add the columns described below
3. Share the database with your Notion integration
4. Populate with your service definitions
5. Run the converters:
   ```bash
   NOTION_TOKEN=xxx ./converters/notion-nginx.sh --database <services-db-id>
   NOTION_TOKEN=xxx ./converters/notion-docker-compose.sh --database <services-db-id>
   ```

## Required Columns

These columns are required for the converters to work:

| Column | Type | Description | Example | Used By |
|--------|------|-------------|---------|---------|
| **Name** | Title | Service identifier | `grafana` | Both |
| **Domain** | Text | Public domain name | `grafana.example.com` | nginx |
| **Backend** | Text | Backend URL to proxy | `http://192.168.1.50:3000` | nginx |
| **Port** | Number | External port | `443` | nginx |
| **Image** | Text | Docker image | `grafana/grafana:latest` | Docker Compose |
| **Ports** | Text | Port mappings (comma-separated) | `3000:3000,3001:3001` | Docker Compose |
| **Volumes** | Text | Volume mounts (comma-separated) | `/data:/var/lib/grafana` | Docker Compose |
| **Environment** | Text | Environment variables (comma-separated) | `GF_ADMIN_PASSWORD=secret` | Docker Compose |

## Optional Columns

These columns help with organization but aren't used by converters:

| Column | Type | Description |
|--------|------|-------------|
| **SSL** | Checkbox | Enable HTTPS (nginx only) |
| **Network** | Text | Docker network name |
| **Type** | Select | Service type (web, database, cache, etc.) |
| **Status** | Select | Active, Inactive, Staging |
| **Owner** | Person | Service owner/maintainer |
| **Notes** | Text | Additional information |
| **Tags** | Multi-select | Categorization tags |

## Example Data

Here's sample data for common services:

| Name | Domain | Backend | Port | SSL | Image | Ports | Volumes | Environment | Type |
|------|--------|---------|------|-----|-------|-------|---------|-------------|------|
| grafana | grafana.example.com | http://192.168.1.50:3000 | 443 | ✓ | grafana/grafana:latest | 3000:3000 | /data/grafana:/var/lib/grafana | GF_SECURITY_ADMIN_PASSWORD=admin123 | monitoring |
| prometheus | prometheus.example.com | http://192.168.1.51:9090 | 443 | ✓ | prom/prometheus:latest | 9090:9090 | /data/prometheus:/prometheus,/etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml | | monitoring |
| postgres | db.example.com | http://192.168.1.52:5432 | 5432 |  | postgres:15-alpine | 5432:5432 | /data/postgres:/var/lib/postgresql/data | POSTGRES_PASSWORD=dbpass,POSTGRES_DB=myapp | database |
| nginx | www.example.com | http://192.168.1.53:80 | 443 | ✓ | nginx:alpine | 80:80,443:443 | /etc/nginx/conf.d:/etc/nginx/conf.d | | web |
| redis | | | | | redis:7-alpine | 6379:6379 | /data/redis:/data | | cache |

## Field Format Specifications

### Ports (Docker Compose)
Format: `HOST_PORT:CONTAINER_PORT`
- Single port: `3000:3000`
- Multiple ports: `80:80,443:443,8080:8080`
- UDP ports: `53:53/udp`

### Volumes (Docker Compose)
Format: `HOST_PATH:CONTAINER_PATH[:OPTIONS]`
- Named volume: `postgres-data:/var/lib/postgresql/data`
- Bind mount: `/host/path:/container/path`
- Read-only: `/host/path:/container/path:ro`
- Multiple: `/path1:/mount1,/path2:/mount2`

### Environment (Docker Compose)
Format: `KEY=VALUE`
- Single var: `NODE_ENV=production`
- Multiple vars: `DB_HOST=localhost,DB_PORT=5432,DB_NAME=myapp`
- Secrets: Store sensitive values in separate secret management

### Backend (nginx)
Format: `PROTOCOL://HOST:PORT`
- HTTP: `http://192.168.1.100:8080`
- HTTPS: `https://backend.internal:443`
- Unix socket: `unix:/var/run/app.sock`

## Generated Output Examples

### nginx Reverse Proxy

From the Grafana entry above:

```nginx
# grafana
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name grafana.example.com;
    
    ssl_certificate /etc/ssl/certs/grafana.crt;
    ssl_certificate_key /etc/ssl/private/grafana.key;
    
    location / {
        proxy_pass http://192.168.1.50:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# grafana HTTP redirect
server {
    listen 80;
    listen [::]:80;
    server_name grafana.example.com;
    return 301 https://$server_name$request_uri;
}
```

### Docker Compose

From the Postgres entry above:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: postgres
    ports:
      - "5432:5432"
    volumes:
      - /data/postgres:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=dbpass
      - POSTGRES_DB=myapp
    restart: unless-stopped
```

## Usage Tips

### Organizing Services

**By Type:**
- Use the Type select column to categorize (web, api, database, cache, monitoring)
- Makes it easier to find and filter services

**By Environment:**
- Create separate databases for prod/staging/dev
- Or use a Status/Environment select column to filter

**By Team:**
- Use the Owner person column
- Helps with responsibility and notifications

### SSL Certificates

When SSL checkbox is enabled:
- Ensure certificates exist at `/etc/ssl/certs/<service-name>.crt`
- Ensure private keys exist at `/etc/ssl/private/<service-name>.key`
- Use Let's Encrypt, cert-manager, or manual cert deployment

### Docker Networks

For services that need to communicate:
1. Add Network column value: `myapp-network`
2. All services with same network can communicate
3. Use service name as hostname (e.g., `http://postgres:5432`)

### Environment Variables

**Don't store secrets directly:**
- Use placeholder values in Notion
- Override with `.env` file: `docker-compose --env-file .env up`
- Use Docker secrets or HashiCorp Vault for production

**Common patterns:**
```
# Database connection
DB_HOST=postgres,DB_PORT=5432,DB_NAME=myapp

# Application config
NODE_ENV=production,LOG_LEVEL=info,PORT=3000

# Feature flags
ENABLE_METRICS=true,ENABLE_CACHE=true
```

## Automation

### Regenerate on Changes

Use a cron job or systemd timer to auto-update configs:

```bash
#!/bin/bash
# /opt/scripts/update-services.sh

SERVICES_DB="your-services-database-id"

# Update nginx config
NOTION_TOKEN=xxx ./notion-nginx.sh \
  --database "$SERVICES_DB" \
  --output /etc/nginx/conf.d/services.conf

# Update docker-compose
NOTION_TOKEN=xxx ./notion-docker-compose.sh \
  --database "$SERVICES_DB" \
  --output /opt/docker/docker-compose.yml

cd /opt/docker && docker-compose up -d
```

### Git Tracking

Track generated configs in git for change history:

```bash
cd /etc/nginx/conf.d
git add services.conf
git commit -m "Update nginx config from Notion ($(date))"
```

## Migration from Existing Configs

### From nginx configs

For each existing `server {}` block:
1. Create a Services row
2. Set Name to a unique identifier
3. Set Domain from `server_name`
4. Set Backend from `proxy_pass`
5. Set SSL checkbox if listening on 443

### From docker-compose.yml

For each service:
1. Create a Services row
2. Set Name to service name
3. Set Image to `image:` value
4. Set Ports to `ports:` (comma-separated)
5. Set Volumes to `volumes:` (comma-separated)
6. Set Environment to `environment:` (comma-separated KEY=value)

## Troubleshooting

### nginx Converter

**"SSL certificate not found"**
- Ensure `/etc/ssl/certs/<service>.crt` exists
- Or uncheck SSL checkbox for plain HTTP

**"Backend unreachable"**
- Verify backend URL is correct
- Check firewall rules
- Test: `curl http://backend-ip:port`

### Docker Compose Converter

**"Invalid port mapping"**
- Format must be `HOST:CONTAINER`
- Multiple ports: comma-separated, no spaces

**"Volume mount failed"**
- Ensure host path exists
- Check permissions
- Use absolute paths

**"Environment variable not set"**
- Format: `KEY=value` (no quotes unless value has special chars)
- Separate multiple vars with commas

## Advanced Examples

### Multi-Backend Load Balancing (nginx)

In Backend column: `http://backend-pool` (upstream must be defined separately)

### Docker Compose with Dependencies

Add a Dependencies column (Text) with comma-separated service names, then modify the converter to add `depends_on:`.

### Health Checks

Add HealthCheck column (Text): `/health,30s` (path,interval)

## Schema Summary

**Minimum viable schema:**
```
Name (Title) + Image (Text) = Docker Compose ✓
Name (Title) + Domain (Text) + Backend (Text) = nginx ✓
```

**Recommended schema:**
All required columns + SSL + Type + Status + Notes

**Full schema:**
All columns listed above for maximum flexibility

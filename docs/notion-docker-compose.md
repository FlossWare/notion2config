# notion-docker-compose.sh - Detailed Documentation

Generate docker-compose.yml from Notion Services database.

## Overview

Creates Docker Compose v3.8 configuration from Services database. Supports containers with ports, volumes, environment variables, and custom networks.

## Usage

```bash
notion-docker-compose.sh --database ID [--output FILE] [--dry-run] [--token TOKEN] [--help]
```

### Options

| Option | Description | Default | Required |
|--------|-------------|---------|----------|
| `-d, --database ID` | Services database ID | - | **Yes** |
| `-o, --output FILE` | Write to FILE | stdout | No |
| `-n, --dry-run` | Preview only | false | No |
| `-t, --token TOKEN` | Notion token | `$NOTION_TOKEN` | No |
| `-h, --help` | Show help | - | No |

## Examples

```bash
# Preview
./notion-docker-compose.sh --database SERVICE_DB_ID --dry-run

# Generate file
./notion-docker-compose.sh -d SERVICE_DB_ID -o docker-compose.yml

# Validate and deploy
./notion-docker-compose.sh -d SERVICE_DB_ID -o docker-compose.yml
docker-compose -f docker-compose.yml config  # Validate
docker-compose up -d  # Deploy
```

## Database Requirements

Create a **Services database** (not Compute database).

### Required Columns

| Column | Type | Purpose | Example |
|--------|------|---------|---------|
| **Name** | Title | Service/container name | `grafana` |
| **Image** | Text | Docker image | `grafana/grafana:latest` |

### Optional Columns

| Column | Type | Format | Example |
|--------|------|--------|---------|
| **Ports** | Text | `HOST:CONTAINER[,...]` | `3000:3000,3001:3001` |
| **Volumes** | Text | `HOST:CONTAINER[:ro][,...]` | `/data:/var/lib/data,/logs:/var/log:ro` |
| **Environment** | Text | `KEY=value[,...]` | `NODE_ENV=prod,PORT=3000` |
| **Network** | Text | Network name | `backend` |

## Output Format

```yaml
# docker-compose.yml — auto-generated
version: '3.8'

services:
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - /data/grafana:/var/lib/grafana
    environment:
      - GF_ADMIN_PASSWORD=secret
    networks:
      - monitoring
    restart: unless-stopped

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
    networks:
      - backend
    restart: unless-stopped

networks:
  backend:
    driver: bridge
  monitoring:
    driver: bridge
```

## Field Format Specifications

### Ports

Format: `HOST_PORT:CONTAINER_PORT[/PROTOCOL]`

Examples:
- `3000:3000` - Map host port 3000 to container port 3000
- `80:80,443:443` - Multiple ports (comma-separated)
- `53:53/udp` - UDP port
- `8080-8090:8080-8090` - Port range

### Volumes

Format: `SOURCE:DESTINATION[:OPTIONS]`

Examples:
- `/host/path:/container/path` - Bind mount
- `/data:/var/lib/data:ro` - Read-only
- `named-volume:/data` - Named volume
- `/path1:/mount1,/path2:/mount2` - Multiple volumes

### Environment

Format: `KEY=VALUE`

Examples:
- `NODE_ENV=production` - Single variable
- `DB_HOST=postgres,DB_PORT=5432` - Multiple (comma-separated)
- `SECRET_KEY=abc123` - Strings (no quotes needed)

**Security Warning:** Don't store secrets in Notion. Use Docker secrets or .env files:

```bash
# Create .env file
cat > .env <<EOF
DB_PASSWORD=real_password
API_KEY=real_api_key
EOF

# Override with .env
docker-compose --env-file .env up -d
```

### Network

Single network name:
- `backend`
- `frontend`
- `monitoring`

For multiple networks, extend the script or edit generated file.

## Behavior

### Config Validation
- Automatically validates with `docker-compose config`
- Reports syntax errors
- Only if docker/docker-compose available

### File Backup
- Creates `.bak` before overwriting
- Rollback: `mv docker-compose.yml.bak docker-compose.yml`

### Container Naming
- container_name = service name from Notion
- Prevents name conflicts

### Restart Policy
- Always sets `restart: unless-stopped`
- Override in file if needed

## Integration

### Deployment

```bash
# Generate config
./notion-docker-compose.sh -d "$DB" -o docker-compose.yml

# Deploy
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

### Updates

```bash
# Regenerate
./notion-docker-compose.sh -d "$DB" -o docker-compose.yml

# Pull new images
docker-compose pull

# Recreate changed services
docker-compose up -d
```

### Multiple Environments

```bash
# Production
./notion-docker-compose.sh -d PROD_DB -o prod-compose.yml
docker-compose -f prod-compose.yml up -d

# Staging
./notion-docker-compose.sh -d STAGE_DB -o stage-compose.yml
docker-compose -f stage-compose.yml up -d
```

## Troubleshooting

### "Invalid port mapping"

**Problem:** Port format incorrect

**Solution:** Use `HOST:CONTAINER` format, comma-separated for multiple

### "Volume mount failed"

**Causes:**
- Host path doesn't exist
- Permission denied
- SELinux blocking (if enabled)

**Solutions:**
```bash
# Create directory
mkdir -p /data/app

# Fix permissions
chown -R 1000:1000 /data/app

# SELinux
chcon -Rt svirt_sandbox_file_t /data/app
```

### "Network not found"

**Problem:** Network doesn't exist

**Solution:** Script auto-creates networks referenced by services

### "Container name already in use"

**Problem:** Container with same name already running

**Solutions:**
```bash
# Stop old container
docker stop <container_name>
docker rm <container_name>

# Or rename in Notion
```

## Advanced Usage

### Depends_on

Add Dependencies column in Notion:
```
Format: service1,service2
```

Extend script to generate:
```yaml
depends_on:
  - service1
  - service2
```

### Health Checks

Add HealthCheck column:
```
Format: /health,30s,3
# Path, interval, retries
```

### Build Instead of Image

Add Dockerfile column for custom builds.

### Resource Limits

Add Memory/CPU columns:
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

## Security

### Secrets Management
- **Never** store passwords in Notion
- Use Docker secrets (Swarm mode)
- Or .env file (gitignored)
- Or external secret store (Vault, etc.)

### Network Isolation
- Use networks to isolate services
- Frontend network for web services
- Backend network for databases
- No direct external access to backend

### Least Privilege
- Run containers as non-root user
- Read-only root filesystem where possible
- Drop capabilities

### Image Security
- Use specific tags (not `latest`)
- Scan images: `docker scan <image>`
- Use official images or build from scratch
- Update regularly

## Docker Compose v2 vs v3

Script generates v3.8 format. Compatible with:
- docker-compose (v1.x standalone tool)
- docker compose (v2.x plugin)

For Swarm mode (docker stack deploy), some features differ. Adjust as needed.

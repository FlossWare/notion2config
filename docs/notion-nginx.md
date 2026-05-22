# notion-nginx.sh - Detailed Documentation

Generate nginx reverse proxy configuration from Notion Services database.

## Overview

Creates nginx server blocks for reverse proxying services. Supports SSL/TLS termination, HTTP-to-HTTPS redirects, and automatic config testing before reload.

## Usage

```bash
notion-nginx.sh --database ID [--output FILE] [--dry-run] [--token TOKEN] [--help]
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
# Preview configuration
./notion-nginx.sh --database SERVICE_DB_ID --dry-run

# Generate to file
./notion-nginx.sh -d SERVICE_DB_ID -o /etc/nginx/conf.d/services.conf

# Test and reload
./notion-nginx.sh -d SERVICE_DB_ID -o /etc/nginx/conf.d/services.conf
# Script automatically runs nginx -t and systemctl reload nginx
```

## Database Requirements

Create a **Services database** (not Compute database).

### Required Columns

| Column | Type | Purpose | Example |
|--------|------|---------|---------|
| **Name** | Title | Service identifier | `grafana` |
| **Domain** | Text | Public domain | `grafana.example.com` |
| **Backend** | Text | Upstream URL | `http://192.168.1.50:3000` |

### Optional Columns

| Column | Type | Purpose | Default |
|--------|------|---------|---------|
| **Port** | Number | Listen port (non-SSL) | 80 |
| **SSL** | Checkbox | Enable HTTPS | false |

## Output Format

### Without SSL

```nginx
# service-name
server {
    listen 80;
    listen [::]:80;
    server_name domain.example.com;

    location / {
        proxy_pass http://backend:port;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### With SSL

```nginx
# service-name
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name domain.example.com;
    
    ssl_certificate /etc/ssl/certs/service-name.crt;
    ssl_certificate_key /etc/ssl/private/service-name.key;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:...;

    location / {
        proxy_pass http://backend:port;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP redirect
server {
    listen 80;
    listen [::]:80;
    server_name domain.example.com;
    return 301 https://$server_name$request_uri;
}
```

## SSL Certificate Requirements

When SSL checkbox is enabled:
- Certificate: `/etc/ssl/certs/<service-name>.crt`
- Private key: `/etc/ssl/private/<service-name>.key`

### Using Let's Encrypt

```bash
# Generate certificates
certbot certonly --standalone -d grafana.example.com

# Link to expected location
ln -s /etc/letsencrypt/live/grafana.example.com/fullchain.pem /etc/ssl/certs/grafana.crt
ln -s /etc/letsencrypt/live/grafana.example.com/privkey.pem /etc/ssl/private/grafana.key
```

## Behavior

### Config Testing
- Automatically runs `nginx -t` before reload
- Only reloads if test passes
- Reports errors if test fails

### Service Reload
- Detects systemd nginx service
- Graceful reload (no downtime)
- Only if output to file (not dry-run or stdout)

### File Backup
- Creates `.bak` before overwriting
- Preserves previous config for rollback

## Integration

### Main nginx.conf

Include generated config:

```nginx
http {
    # Main config
    include /etc/nginx/conf.d/*.conf;
}
```

### Automated Updates

```bash
#!/bin/bash
# /opt/scripts/update-nginx.sh
SERVICES_DB="your-services-db-id"

./notion-nginx.sh -d "$SERVICES_DB" -o /etc/nginx/conf.d/services.conf

# Already reloaded by script if test passed
```

### Pre-Deployment Validation

```bash
# Generate to temp, test, then deploy
./notion-nginx.sh -d "$DB" -o /tmp/services.conf
nginx -t -c /tmp/nginx-test.conf
if [ $? -eq 0 ]; then
  sudo cp /tmp/services.conf /etc/nginx/conf.d/
  sudo systemctl reload nginx
fi
```

## Troubleshooting

### "SSL certificate not found"

**Problem:** `/etc/ssl/certs/<name>.crt` doesn't exist

**Solutions:**
- Generate certificates with certbot/acme.sh
- Or uncheck SSL in Notion
- Or use wildcard cert

### "nginx: test failed"

**Problem:** Invalid nginx syntax

**Check:**
- Backend URL format: `http://host:port`
- Domain name valid
- No duplicate server_name directives

### "Backend unreachable"

**Not an nginx config issue** - verify separately:

```bash
curl http://backend-host:port
```

### "Permission denied reloading nginx"

Run script with sudo or add to sudoers:

```bash
user ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
```

## Advanced Usage

### Custom Proxy Headers

Edit script to add:

```nginx
proxy_set_header X-Custom-Header value;
```

### WebSocket Support

Add to location block:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Rate Limiting

Add limit zones in main nginx.conf, reference in server blocks.

### Multiple Backends (Load Balancing)

Requires upstream blocks - extend script or add manually to main config.

## Security

### SSL Best Practices
- Use TLS 1.2+ only (script default)
- Rotate certificates before expiry
- Enable HSTS (add manually):
  ```nginx
  add_header Strict-Transport-Security "max-age=31536000" always;
  ```

### Access Control
- Integration needs read-only access to Services database
- Protect `/etc/ssl/private/` directory (mode 700)

### Sensitive Data
- Don't store backend credentials in Notion
- Use nginx auth_basic or external auth

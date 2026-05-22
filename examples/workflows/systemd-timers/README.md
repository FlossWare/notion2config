# Systemd Timer Examples

Automate notion2config updates with systemd timers.

## Installation

1. **Create token environment file:**
   ```bash
   sudo mkdir -p /etc/notion2config
   echo "NOTION_TOKEN=secret_xxx" | sudo tee /etc/notion2config/token.env
   echo "SERVICES_DB=your-services-db-id" | sudo tee -a /etc/notion2config/token.env
   sudo chmod 600 /etc/notion2config/token.env
   ```

2. **Copy automation scripts:**
   ```bash
   sudo mkdir -p /opt/notion2config
   sudo cp -r /path/to/notion2config /opt/
   ```

3. **Install systemd units:**
   ```bash
   sudo cp *.service *.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

4. **Enable and start timer:**
   ```bash
   sudo systemctl enable notion2config-ansible.timer
   sudo systemctl start notion2config-ansible.timer
   ```

## Available Timers

- **notion2config-ansible** - Updates Ansible inventory hourly
- Create similar units for other converters (prometheus, nginx, etc.)

## Verify Timer Status

```bash
systemctl list-timers | grep notion2config
journalctl -u notion2config-ansible.service
```

## Customization

Edit timer intervals in `.timer` files:
- `OnUnitActiveSec=1h` - Every hour
- `OnUnitActiveSec=15m` - Every 15 minutes
- `OnCalendar=hourly` - Alternative calendar-based syntax

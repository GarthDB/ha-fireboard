# FireBoard Integration - Development Environment Setup

This guide shows you how to set up a Docker-based Home Assistant development environment for testing the FireBoard integration safely, without affecting your production Raspberry Pi installation.

## Why Docker for Development?

✅ **Safe**: Test without risking your production Home Assistant  
✅ **Fast**: Quick to restart and reset  
✅ **Isolated**: Changes don't affect your real HA  
✅ **Easy**: Simple setup and teardown  
✅ **Live Reload**: Changes to integration code are immediately available  

## Prerequisites

- Docker Desktop installed on your Mac
- Docker Compose (included with Docker Desktop)
- Your FireBoard account credentials

## Quick Start

### 1. Start Development Environment

```bash
cd /Users/garthdb/Projects/ha-fireboard

# Start Home Assistant in Docker
docker-compose up -d

# Watch the logs
docker-compose logs -f homeassistant
```

**First startup takes 2-3 minutes** while Home Assistant initializes.

### 2. Access Home Assistant

1. Open browser to: http://localhost:8123
2. Complete onboarding:
   - Create your user account
   - Name: "Dev Environment"
   - Location: Your location
   - Skip analytics

### 3. Install FireBoard Integration

The integration is automatically mounted in the container!

1. Go to **Settings → Devices & Services**
2. Click **"+ Add Integration"**
3. Search for **"FireBoard"**
4. Enter your FireBoard credentials
5. Test with your real devices!

## Development Workflow

### Making Changes to the Integration

```bash
# 1. Edit integration code
vim custom_components/fireboard/api_client.py

# 2. Restart Home Assistant to reload
docker-compose restart homeassistant

# 3. Watch logs for errors
docker-compose logs -f homeassistant
```

### Viewing Logs

```bash
# All logs
docker-compose logs -f homeassistant

# Only FireBoard integration logs
docker-compose logs -f homeassistant | grep fireboard

# Last 100 lines
docker-compose logs --tail=100 homeassistant
```

### Debugging

Enable debug logging (already configured in `dev-config/configuration.yaml`):

```yaml
logger:
  default: info
  logs:
    custom_components.fireboard: debug
```

### Reset Environment

If you need to start fresh:

```bash
# Stop and remove everything
docker-compose down

# Remove all data (fresh start)
rm -rf dev-config/.storage dev-config/home-assistant.log* dev-config/home-assistant_v2.db*

# Start again
docker-compose up -d
```

## Testing Process

### Phase 1: API Connection Test

Before starting Docker, test the API directly:

```bash
# Install dependencies
pip3 install aiohttp

# Test API endpoints
python3 test_api_connection.py
```

This validates:
- Authentication works
- Endpoints are correct
- Device discovery works
- Data structures match

### Phase 2: Integration Testing

With Home Assistant running in Docker:

1. **Install Integration**:
   - Add integration through UI
   - Enter credentials
   - Verify configuration succeeds

2. **Verify Devices**:
   - Check all devices discovered
   - Verify device information correct

3. **Test Sensors**:
   - Temperature sensors show values
   - Battery sensors present (wireless devices)
   - Binary sensors working

4. **Test Updates**:
   - Sensors update every 40 seconds
   - Changes reflect in UI
   - No rate limit errors

5. **Test Error Handling**:
   - Try invalid credentials
   - Turn off a device
   - Check connectivity status

### Phase 3: Dashboard Testing

Create test dashboard:

```yaml
type: entities
title: FireBoard Test
entities:
  - sensor.backyard_smoker_probe_1
  - sensor.fireboard_spark_battery
  - binary_sensor.backyard_smoker_connectivity
```

### Phase 4: Automation Testing

Create test automation:

```yaml
automation:
  - alias: "Test FireBoard Temp Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.backyard_smoker_probe_1
        above: 250
    action:
      - service: persistent_notification.create
        data:
          message: "Grill is hot!"
```

## Common Tasks

### Check Integration Status

```bash
# Shell into container
docker exec -it ha-fireboard-dev /bin/bash

# Inside container:
ls -la /config/custom_components/fireboard/
cat /config/home-assistant.log | grep fireboard
```

### Update Home Assistant Version

```bash
# Pull latest stable
docker-compose pull

# Recreate container
docker-compose up -d
```

### Export Configuration

```bash
# Backup your test configuration
cp -r dev-config dev-config-backup

# Or specific files
cp dev-config/configuration.yaml dev-config-backup/
```

## Troubleshooting

### Integration Not Appearing

**Problem**: Can't find FireBoard in Add Integration

**Solution**:
1. Check integration is mounted:
   ```bash
   docker exec ha-fireboard-dev ls -la /config/custom_components/fireboard/
   ```
2. Restart container:
   ```bash
   docker-compose restart homeassistant
   ```
3. Clear browser cache
4. Check logs for Python errors

### Container Won't Start

**Problem**: Docker container fails to start

**Solution**:
```bash
# Check logs
docker-compose logs homeassistant

# Check if port 8123 is in use
lsof -i :8123

# Remove and restart
docker-compose down
docker-compose up -d
```

### Logs Show Errors

**Problem**: Errors in Home Assistant logs

**Solution**:
1. Check the error message carefully
2. Verify integration code syntax
3. Check API responses in debug logs
4. Restart container after fixing

### Can't Connect to FireBoard API

**Problem**: API authentication failing

**Solution**:
1. Verify credentials at https://fireboard.io
2. Check internet connectivity from container:
   ```bash
   docker exec ha-fireboard-dev curl -I https://fireboard.io
   ```
3. Check for firewall/proxy issues

## Advantages Over Production Testing

| Aspect | Docker Dev | Production Pi |
|--------|------------|---------------|
| **Safety** | Isolated, can't break production | Risk to production |
| **Speed** | Instant restart (~2 sec) | Slow restart (~30 sec) |
| **Logs** | Easy to tail and filter | Harder to access |
| **Reset** | Delete folder, done | Risky |
| **Debugging** | Full debug mode enabled | May affect performance |
| **Iteration** | Fast edit-test cycle | Slow deployment |

## When to Test on Production Pi

After Docker testing is successful:

1. ✅ All API tests pass
2. ✅ Integration installs correctly
3. ✅ Devices discovered
4. ✅ Sensors working
5. ✅ No errors in logs
6. ✅ Automations tested

**Then** deploy to your Raspberry Pi for final validation with your actual Home Assistant setup.

## Docker vs Pi Commands

### Docker Environment
```bash
# Start
docker-compose up -d

# Logs
docker-compose logs -f homeassistant

# Restart
docker-compose restart homeassistant

# Stop
docker-compose down

# Shell access
docker exec -it ha-fireboard-dev /bin/bash
```

### Production Pi
```bash
# Restart
ssh pi@homeassistant.local "ha core restart"

# Logs
ssh pi@homeassistant.local "tail -f /config/home-assistant.log"

# Copy integration
scp -r custom_components/fireboard pi@homeassistant.local:/config/custom_components/
```

## File Structure

```
ha-fireboard/
├── docker-compose.yml           # Docker configuration
├── dev-config/                  # Home Assistant config (dev)
│   ├── configuration.yaml       # HA configuration
│   ├── automations.yaml         # Test automations
│   ├── .storage/               # HA storage (created)
│   └── custom_components/       # Symlinked in Docker
├── custom_components/
│   └── fireboard/              # Your integration (mounted)
└── test_api_connection.py      # API test script
```

## Pro Tips

1. **Keep Docker Running**: Leave it running during development for fast iteration

2. **Watch Logs**: Keep a terminal with logs open:
   ```bash
   docker-compose logs -f homeassistant | grep -E "(fireboard|ERROR)"
   ```

3. **Quick Restart**: Use restart instead of down/up:
   ```bash
   docker-compose restart homeassistant
   ```

4. **Backup**: Copy `dev-config/.storage` before major changes

5. **Clean State**: For clean tests, remove `.storage` between runs

## Next Steps

Once testing is successful in Docker:

1. **Document Results**: Create `TESTING_RESULTS.md`
2. **Fix Issues**: Address any problems found
3. **Deploy to Pi**: Install on production for final validation
4. **Create Release**: Tag v0.1.0
5. **Submit to HACS**: Share with the community!

## Resources

- [Home Assistant Docker Docs](https://www.home-assistant.io/installation/linux#docker-compose)
- [Custom Component Development](https://developers.home-assistant.io/docs/creating_component_index)
- [Integration Quality Scale](https://www.home-assistant.io/docs/quality_scale/)

---

**Happy Testing!** 🚀

This approach gives you the best of both worlds: safe, fast development iteration plus final validation on your real Home Assistant.


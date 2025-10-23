# Home Assistant FireBoard Integration

[![CI](https://github.com/GarthDB/ha-fireboard/workflows/CI/badge.svg)](https://github.com/GarthDB/ha-fireboard/actions)
[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern Home Assistant integration for FireBoard wireless thermometers using direct cloud API communication.

> **Status**: ✅ Ready for Testing

## Why This Integration?

While there is an existing [fireboard2mqtt integration](https://github.com/gordlea/fireboard2mqtt), this implementation provides several key improvements:

### **Simpler Setup**
- **No MQTT Broker Required**: Direct API integration vs. MQTT middleware
- **UI Configuration**: Easy setup through Home Assistant UI
- **Auto-Discovery**: Automatically discovers all devices and channels

### **Modern Architecture**
- **Native Python**: Built with Home Assistant best practices
- **Config Flow**: Proper integration setup wizard with validation
- **Modern Patterns**: Uses current Home Assistant integration standards

### **Enhanced Features**
- **Real-time Updates**: Live temperature data from FireBoard Cloud
- **Multiple Device Support**: Manage all your FireBoard devices in one integration
- **Battery Monitoring**: Track battery levels on wireless devices
- **Connectivity Status**: Know when devices go offline

### **Development Quality**
- **Extensive Testing**: Comprehensive test coverage (>80%)
- **Active Maintenance**: Regular updates and bug fixes
- **Code Quality**: Modern Python patterns, type hints, comprehensive linting
- **Documentation**: Detailed setup guides and examples

## Features

- **Temperature Monitoring**: Real-time temperature readings from all channels
- **Multiple Devices**: Support for FireBoard 2 Pro, Spark, and other models
- **Battery Monitoring**: Track battery levels on wireless devices
- **Cloud Connectivity**: Uses official FireBoard Cloud API
- **HACS Compatible**: Easy installation through Home Assistant Community Store

## Supported Devices

- **FireBoard 2 Pro**: 6-channel WiFi thermometer
- **FireBoard Spark**: Portable instant-read thermometer with leave-in probe
- **Other FireBoard Models**: Any device compatible with FireBoard Cloud

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click "+ Explore & Download Repositories"
4. Search for "FireBoard"
5. Click "Download"
6. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract to `custom_components/fireboard/` in your Home Assistant config
3. Restart Home Assistant
4. Add the integration through the UI

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "FireBoard"
4. Enter your FireBoard account credentials:
   - **Email**: Your FireBoard account email
   - **Password**: Your FireBoard account password
   - **Polling Interval**: How often to update data (default: 40 seconds)

**Note**: The minimum polling interval is 40 seconds to respect FireBoard's API rate limit of 200 calls per hour.

## Entities

### Temperature Sensors
- One sensor per temperature channel (typically 6 per device)
- Device class: `temperature`
- Unit: Fahrenheit (°F)
- Attributes:
  - `channel`: Channel number (1-6)
  - `label`: Custom channel label from FireBoard app
  - `target_temp`: Target temperature if set

### Battery Sensors
- Battery level percentage for wireless devices
- Device class: `battery`
- Unit: Percent (%)

### Binary Sensors
- **Connectivity**: Device online/offline status
- **Battery Low**: Alert when battery below 20%

## Dashboard Examples

### Simple Temperature Card

```yaml
type: entities
title: FireBoard Temperatures
entities:
  - entity: sensor.backyard_smoker_probe_1
    name: Grill Temp
  - entity: sensor.backyard_smoker_probe_2
    name: Brisket
  - entity: sensor.backyard_smoker_probe_3
    name: Pork Shoulder
```

### Temperature Gauge

```yaml
type: gauge
entity: sensor.backyard_smoker_probe_1
name: Grill Temperature
min: 0
max: 500
severity:
  green: 225
  yellow: 200
  red: 150
needle: true
```

### Complete FireBoard Dashboard

```yaml
type: vertical-stack
cards:
  # Device Status
  - type: horizontal-stack
    cards:
      - type: entity
        entity: binary_sensor.backyard_smoker_connectivity
        name: Status
      - type: entity
        entity: sensor.fireboard_spark_battery
        name: Battery

  # Temperature Grid
  - type: grid
    columns: 2
    square: false
    cards:
      - type: gauge
        entity: sensor.backyard_smoker_probe_1
        name: Probe 1
        min: 0
        max: 500
        needle: true
      - type: gauge
        entity: sensor.backyard_smoker_probe_2
        name: Probe 2
        min: 0
        max: 300
        needle: true
```

## Automation Examples

### Temperature Alert

```yaml
automation:
  - alias: "FireBoard: Brisket Done"
    trigger:
      - platform: numeric_state
        entity_id: sensor.backyard_smoker_probe_2
        above: 203
    action:
      - service: notify.notify
        data:
          title: "🔥 Brisket is Done!"
          message: >
            Probe 2 has reached {{ states('sensor.backyard_smoker_probe_2') }}°F
```

### Low Battery Notification

```yaml
automation:
  - alias: "FireBoard: Low Battery Warning"
    trigger:
      - platform: state
        entity_id: binary_sensor.fireboard_spark_battery_low
        to: "on"
    action:
      - service: notify.notify
        data:
          title: "🔋 FireBoard Battery Low"
          message: >
            FireBoard Spark battery is at {{ states('sensor.fireboard_spark_battery') }}%
```

### Device Offline Alert

```yaml
automation:
  - alias: "FireBoard: Device Offline"
    trigger:
      - platform: state
        entity_id: binary_sensor.backyard_smoker_connectivity
        to: "off"
        for:
          minutes: 5
    action:
      - service: notify.notify
        data:
          title: "⚠️ FireBoard Offline"
          message: "Backyard Smoker has been offline for 5 minutes"
```

## Troubleshooting

### Authentication Errors

**Problem**: "Invalid email or password"

**Solution**:
- Verify your credentials at https://fireboard.io
- Ensure you're using the email address associated with your FireBoard account
- Check for any typos in the password

### Rate Limit Errors

**Problem**: "Rate limit exceeded"

**Solution**:
- Increase the polling interval in the integration configuration
- Default is 40 seconds (90 calls/hour)
- FireBoard allows 200 API calls per hour
- If you have multiple Home Assistant instances, they share the same limit

### Devices Not Showing Up

**Problem**: No devices or sensors created

**Solution**:
- Ensure your devices are online in the FireBoard app
- Check that devices are properly associated with your account
- Restart Home Assistant after adding the integration
- Check the Home Assistant logs for errors

### Connection Issues

**Problem**: "Cannot connect to FireBoard API"

**Solution**:
- Check your internet connection
- Verify FireBoard Cloud is operational: https://status.fireboard.io
- Check Home Assistant logs for detailed error messages
- Try removing and re-adding the integration

## Comparison with fireboard2mqtt

| Feature | ha-fireboard | fireboard2mqtt |
|---------|-------------|----------------|
| **Setup Complexity** | Simple (UI config) | Complex (MQTT broker + addon) |
| **Dependencies** | None | MQTT broker required |
| **Configuration** | UI | YAML + Environment variables |
| **Language** | Python | Rust |
| **Integration Type** | Native HA | MQTT |
| **Auto-Discovery** | Yes | Yes (via MQTT) |
| **Multiple Devices** | Yes | Yes |
| **Battery Monitoring** | Yes | Yes |

## Development

### Prerequisites

- Python 3.9+
- Home Assistant 2023.1.0+
- FireBoard account with devices for testing

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/GarthDB/ha-fireboard.git
cd ha-fireboard

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ --cov=custom_components/fireboard

# Run linting
black custom_components/fireboard tests/
isort custom_components/fireboard tests/
flake8 custom_components/fireboard tests/

# Run all checks
make check-all  # If using Makefile
```

### Project Structure

```
ha-fireboard/
├── custom_components/
│   └── fireboard/
│       ├── __init__.py          # Integration setup
│       ├── api_client.py        # FireBoard API client
│       ├── config_flow.py       # UI configuration
│       ├── const.py             # Constants
│       ├── coordinator.py       # Data coordinator
│       ├── entity.py            # Base entity
│       ├── sensor.py            # Temperature sensors
│       ├── binary_sensor.py     # Status sensors
│       ├── manifest.json        # Integration metadata
│       └── strings.json         # UI strings
├── tests/                       # Test suite
├── .github/workflows/           # CI/CD
└── docs/                        # Documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Ensure code is formatted (`black`, `isort`)
7. Submit a pull request

## Support

- **Issues**: [GitHub Issues](https://github.com/garthdb/ha-fireboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/garthdb/ha-fireboard/discussions)
- **Home Assistant Community**: [Community Forum](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on the [fireboard2mqtt](https://github.com/gordlea/fireboard2mqtt) project
- Built for the Home Assistant community
- Uses the official FireBoard Cloud API

## Changelog

### v0.1.0 (Initial Release)
- Direct FireBoard Cloud API integration
- UI-based configuration
- Temperature sensor support
- Battery monitoring
- Connectivity status
- HACS compatibility
- Comprehensive test coverage

---

**Maintained by**: [@GarthDB](https://github.com/GarthDB)  
**License**: MIT


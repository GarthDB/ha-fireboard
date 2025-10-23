# Development Guide

## Getting Started

### Prerequisites

- Python 3.9 or later
- Home Assistant 2023.1.0 or later
- Git
- FireBoard account with devices for testing

### Setup

1. Clone the repository:
```bash
git clone https://github.com/GarthDB/ha-fireboard.git
cd ha-fireboard
```

2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Install pre-commit hooks (optional but recommended):
```bash
pre-commit install
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/fireboard --cov-report=html

# Run specific test file
pytest tests/test_api_client.py

# Run specific test
pytest tests/test_api_client.py::test_authenticate_success

# View coverage report
open htmlcov/index.html
```

### Code Quality

```bash
# Format code with black
black custom_components/fireboard tests/

# Sort imports with isort
isort custom_components/fireboard tests/

# Lint with flake8
flake8 custom_components/fireboard tests/

# Type checking with mypy
mypy custom_components/fireboard/

# Security check with bandit
bandit -r custom_components/fireboard/

# Check for unused code with vulture
vulture custom_components/fireboard/ --min-confidence 80
```

### Testing with Home Assistant

#### Method 1: Copy to Home Assistant config

```bash
# Create symbolic link to your Home Assistant config
ln -s $(pwd)/custom_components/fireboard ~/.homeassistant/custom_components/fireboard

# Restart Home Assistant
```

#### Method 2: Development Container

Use the included `.devcontainer` configuration with VS Code:

1. Open project in VS Code
2. Install "Remote - Containers" extension
3. Click "Reopen in Container"
4. Home Assistant will be available at http://localhost:8123

### Local CI Testing

Test GitHub Actions workflows locally before pushing:

```bash
# Install act (if not already installed)
brew install act

# Run all CI jobs
act

# Run specific jobs
act -j test     # Run tests
act -j hassfest # Run Home Assistant validation
```

## Project Structure

```
ha-fireboard/
├── custom_components/fireboard/  # Integration code
│   ├── __init__.py              # Entry point
│   ├── api_client.py            # API client
│   ├── config_flow.py           # Configuration flow
│   ├── const.py                 # Constants
│   ├── coordinator.py           # Data coordinator
│   ├── entity.py                # Base entity
│   ├── sensor.py                # Sensor platform
│   ├── binary_sensor.py         # Binary sensor platform
│   ├── manifest.json            # Integration metadata
│   └── strings.json             # Translations
├── tests/                        # Test suite
│   ├── conftest.py              # Test fixtures
│   ├── test_*.py                # Test files
│   └── fixtures/                # Test data
├── .github/                      # GitHub configuration
│   ├── workflows/               # CI/CD workflows
│   └── ISSUE_TEMPLATE/          # Issue templates
├── docs/                         # Documentation
├── requirements-dev.txt          # Development dependencies
├── requirements-test.txt         # Test dependencies
├── pyproject.toml               # Project configuration
└── README.md                    # Main documentation
```

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 88 characters (Black default)
- Use f-strings for formatting
- Prefer async/await over callbacks

### Naming Conventions

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### Documentation

- Docstrings for all public classes and methods
- Google-style docstrings
- Include examples in docstrings where helpful
- Keep comments concise and meaningful

Example:
```python
async def get_temperatures(self, device_uuid: str) -> dict[str, Any]:
    """Get current temperatures for a device.

    Args:
        device_uuid: Device UUID

    Returns:
        Temperature data dictionary

    Raises:
        FireBoardApiClientError: If request fails

    Example:
        >>> temps = await client.get_temperatures("device-123")
        >>> print(temps['channels'][0]['current_temp'])
        225.5
    """
```

### Error Handling

- Use custom exceptions for specific error cases
- Always provide helpful error messages
- Log errors appropriately:
  - `_LOGGER.debug()` for detailed information
  - `_LOGGER.info()` for important events
  - `_LOGGER.warning()` for recoverable issues
  - `_LOGGER.error()` for errors

### Testing

- Aim for >80% code coverage
- Write unit tests for all new functionality
- Use mocks for external dependencies
- Test error cases and edge cases
- Use descriptive test names

Test naming convention:
```python
def test_<what>_<condition>_<expected_result>():
    """Test that <what> <condition> results in <expected_result>."""
```

## API Client Guidelines

### Authentication

- Store token securely
- Handle token expiration gracefully
- Retry with new token on 401

### Rate Limiting

- Respect API rate limits (200 calls/hour)
- Default polling interval: 40 seconds
- Provide clear error messages when rate limited
- Allow users to configure polling interval

### Error Handling

- Distinguish between:
  - Authentication errors (401)
  - Rate limit errors (429)
  - Communication errors (network issues)
  - API errors (4xx, 5xx)

## Home Assistant Integration Guidelines

### Config Flow

- Validate user input
- Provide clear error messages
- Show what will be added (devices found)
- Support reconfiguration
- Handle already configured gracefully

### Coordinator

- Use `DataUpdateCoordinator` for polling
- Handle API errors gracefully
- Mark devices offline on errors
- Provide meaningful update failures

### Entities

- Extend `CoordinatorEntity` for efficiency
- Provide proper device info
- Use appropriate device classes
- Include meaningful attributes
- Handle unavailable states

### Platforms

Currently supported:
- `sensor`: Temperature sensors, battery level
- `binary_sensor`: Connectivity, battery low

Future platforms:
- `switch`: Power control (if API supports)
- `number`: Target temperature adjustment

## Debugging

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.fireboard: debug
```

### Common Issues

**Import Errors**
- Ensure all dependencies are installed
- Check Python version compatibility
- Verify file paths

**API Errors**
- Check network connectivity
- Verify credentials
- Check API rate limits
- Review API response format

**Entity Not Updating**
- Check coordinator update interval
- Verify device is online
- Check for API errors in logs

## Release Process

1. Update version in `manifest.json`
2. Update `CHANGELOG.md`
3. Commit changes: `git commit -m "Release vX.Y.Z"`
4. Create tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. Push: `git push && git push --tags`
6. GitHub Actions will create release automatically
7. Update HACS repository (if listed)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Getting Help

- Check existing [Issues](https://github.com/GarthDB/ha-fireboard/issues)
- Join [Discussions](https://github.com/GarthDB/ha-fireboard/discussions)
- Ask on [Home Assistant Community](https://community.home-assistant.io/)


"""Test fixtures for FireBoard integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock Home Assistant imports for CI testing
try:
    from homeassistant.core import HomeAssistant
except ImportError:
    # Use our mock Home Assistant module
    import sys

    from .mock_homeassistant import homeassistant, voluptuous

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = homeassistant.core
    sys.modules["homeassistant.config_entries"] = homeassistant.config_entries
    sys.modules["homeassistant.data_entry_flow"] = homeassistant.data_entry_flow
    sys.modules["homeassistant.exceptions"] = homeassistant.exceptions
    sys.modules["homeassistant.const"] = homeassistant.const
    sys.modules["homeassistant.helpers"] = homeassistant.helpers
    sys.modules["homeassistant.helpers.entity"] = homeassistant.helpers.entity
    sys.modules["homeassistant.helpers.update_coordinator"] = (
        homeassistant.helpers.update_coordinator
    )
    sys.modules["homeassistant.components.binary_sensor"] = (
        homeassistant.components.binary_sensor
    )
    sys.modules["homeassistant.components.sensor"] = homeassistant.components.sensor
    sys.modules["voluptuous"] = voluptuous

    from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.fireboard.const import (
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)


@pytest.fixture
async def hass() -> HomeAssistant:
    """Return a Home Assistant instance."""
    import asyncio

    # Create a new event loop for this test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    hass_instance = HomeAssistant("")
    hass_instance.config_entries = MagicMock()
    hass_instance.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass_instance.config_entries.async_forward_entry_setups = AsyncMock(
        return_value=None
    )
    hass_instance.entity_registry = MagicMock()
    hass_instance.device_registry = MagicMock()

    # Mock the config entries flow
    hass_instance.config_entries.flow = MagicMock()
    hass_instance.config_entries.flow.async_init = AsyncMock()

    # Start the Home Assistant instance
    await hass_instance.async_start()

    yield hass_instance

    # Clean up
    await hass_instance.async_stop()
    loop.close()


@pytest.fixture
def mock_config_entry_data():
    """Return mock config entry data."""
    return {
        CONF_EMAIL: "test@example.com",
        CONF_PASSWORD: "test_password",
        CONF_POLLING_INTERVAL: DEFAULT_POLLING_INTERVAL,
    }


@pytest.fixture
def mock_device_data():
    """Return mock device data."""
    return {
        "uuid": "test-device-uuid-123",
        "title": "Test FireBoard",
        "hardware_id": "FireBoard 2 Pro",
        "model": "FB2",
        "software_version": "1.0.0",
        "has_battery": True,
        "battery_level": 85,
    }


@pytest.fixture
def mock_temperature_data():
    """Return mock temperature data."""
    return {
        "channels": [
            {
                "channel": 1,
                "label": "Probe 1",
                "current_temp": 225.5,
                "target_temp": 225.0,
            },
            {
                "channel": 2,
                "label": "Probe 2",
                "current_temp": 165.0,
                "target_temp": 165.0,
            },
            {
                "channel": 3,
                "label": "Probe 3",
                "current_temp": None,
                "target_temp": None,
            },
        ]
    }


@pytest.fixture
def mock_api_client():
    """Return a mock FireBoard API client."""
    client = AsyncMock()
    client._token = "test-token-123"
    client.authenticate = AsyncMock(return_value=True)
    client.get_devices = AsyncMock(return_value=[])
    client.get_device = AsyncMock(return_value={})
    client.get_sessions = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_coordinator_data(mock_device_data, mock_temperature_data):
    """Return mock coordinator data."""
    return {
        "test-device-uuid-123": {
            "device_info": mock_device_data,
            "temperatures": mock_temperature_data,
            "online": True,
        }
    }

"""Test fixtures for FireBoard integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.fireboard.const import (
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
)


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
    client.get_temperatures = AsyncMock(return_value={})
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


# Note: Don't use autouse=True as it affects simple unit tests
# that don't need Home Assistant fixtures
@pytest.fixture
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for Home Assistant tests."""
    yield


"""Tests for FireBoard integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fireboard.const import DOMAIN

pytestmark = pytest.mark.usefixtures("auto_enable_custom_integrations")


async def test_setup_entry(hass, mock_config_entry_data, mock_coordinator_data):
    """Test setting up a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    config_entry.add_to_hass(hass)
    
    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.get_devices = AsyncMock(return_value=[])
        mock_client.auth_token = "test-token"
        mock_client_class.return_value = mock_client
        
        with patch(
            "custom_components.fireboard.mqtt_client.FireBoardMQTTClient"
        ) as mock_mqtt:
            mock_mqtt_instance = AsyncMock()
            mock_mqtt_instance.connect = AsyncMock(return_value=True)
            mock_mqtt.return_value = mock_mqtt_instance

            from custom_components.fireboard import async_setup_entry

            result = await async_setup_entry(hass, config_entry)

            assert result is True
            assert DOMAIN in hass.data
            assert config_entry.entry_id in hass.data[DOMAIN]


async def test_unload_entry(hass, mock_config_entry_data, mock_coordinator_data):
    """Test unloading a config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    # Setup first
    with patch(
        "custom_components.fireboard.FireBoardDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.data = mock_coordinator_data
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        # Store coordinator
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][config_entry.entry_id] = mock_coordinator

        with patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ):
            from custom_components.fireboard import async_unload_entry

            result = await async_unload_entry(hass, config_entry)

            assert result is True
            assert config_entry.entry_id not in hass.data[DOMAIN]


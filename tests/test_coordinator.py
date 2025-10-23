"""Tests for FireBoard data update coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator


async def test_coordinator_update_success(
    hass, mock_config_entry_data, mock_device_data, mock_temperature_data
):
    """Test successful coordinator update."""
    config_entry = ConfigEntry(
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_temperatures = AsyncMock(return_value=mock_temperature_data)
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)

        # Manually set the client to our mock
        coordinator.client = mock_client

        await coordinator.async_refresh()

        assert coordinator.last_update_success
        assert mock_device_data["uuid"] in coordinator.data
        assert coordinator.data[mock_device_data["uuid"]]["online"] is True


async def test_coordinator_authentication(hass, mock_config_entry_data):
    """Test coordinator authenticates when token is missing."""
    config_entry = ConfigEntry(
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = None  # No token initially
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.get_devices = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator.async_refresh()

        # Verify authenticate was called
        mock_client.authenticate.assert_called_once()


async def test_coordinator_rate_limit_error(hass, mock_config_entry_data):
    """Test coordinator handles rate limit errors."""
    from homeassistant.config_entries import ConfigEntry

    from custom_components.fireboard.api_client import FireBoardApiClientRateLimitError

    config_entry = ConfigEntry(
        version=1,
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.get_devices = AsyncMock(
            side_effect=FireBoardApiClientRateLimitError("Rate limited")
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        with pytest.raises(UpdateFailed):
            await coordinator.async_refresh()


async def test_coordinator_communication_error(hass, mock_config_entry_data):
    """Test coordinator handles communication errors."""
    from homeassistant.config_entries import ConfigEntry

    from custom_components.fireboard.api_client import (
        FireBoardApiClientCommunicationError,
    )

    config_entry = ConfigEntry(
        version=1,
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.get_devices = AsyncMock(
            side_effect=FireBoardApiClientCommunicationError("Connection error")
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        with pytest.raises(UpdateFailed):
            await coordinator.async_refresh()


async def test_coordinator_device_offline(
    hass, mock_config_entry_data, mock_device_data, mock_temperature_data
):
    """Test coordinator marks device offline on temperature fetch error."""
    config_entry = ConfigEntry(
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_temperatures = AsyncMock(side_effect=Exception("Temp error"))
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator.async_refresh()

        # Device should be marked offline but still in data
        assert mock_device_data["uuid"] in coordinator.data
        assert coordinator.data[mock_device_data["uuid"]]["online"] is False

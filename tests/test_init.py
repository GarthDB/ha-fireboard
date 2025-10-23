"""Tests for FireBoard integration initialization."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.fireboard.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_entry(hass, mock_config_entry_data, mock_coordinator_data):
    """Test setting up a config entry."""
    config_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.FireBoardDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.data = mock_coordinator_data
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        with patch(
            "custom_components.fireboard.async_forward_entry_setups",
            return_value=True,
        ):
            from custom_components.fireboard import async_setup_entry

            result = await async_setup_entry(hass, config_entry)

            assert result is True
            assert DOMAIN in hass.data
            assert config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry(hass, mock_config_entry_data, mock_coordinator_data):
    """Test unloading a config entry."""
    config_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
        source="user",
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


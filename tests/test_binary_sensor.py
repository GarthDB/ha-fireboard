"""Tests for FireBoard binary sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.fireboard.const import DOMAIN


@pytest.mark.asyncio
async def test_connectivity_sensor(hass, mock_coordinator_data, mock_config_entry_data):
    """Test connectivity sensor."""
    from custom_components.fireboard.binary_sensor import FireBoardConnectivitySensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardConnectivitySensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.is_on is True
        assert sensor.available is True


@pytest.mark.asyncio
async def test_connectivity_sensor_offline(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test connectivity sensor when device is offline."""
    from custom_components.fireboard.binary_sensor import FireBoardConnectivitySensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    # Mark device as offline
    mock_coordinator_data["test-device-uuid-123"]["online"] = False

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardConnectivitySensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.is_on is False
        assert sensor.available is True  # Connectivity sensor is always available


@pytest.mark.asyncio
async def test_battery_low_sensor(hass, mock_coordinator_data, mock_config_entry_data):
    """Test battery low sensor."""
    from custom_components.fireboard.binary_sensor import FireBoardBatteryLowSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardBatteryLowSensor(
            coordinator,
            "test-device-uuid-123",
        )

        # Battery at 85% should not be low
        assert sensor.is_on is False


@pytest.mark.asyncio
async def test_battery_low_sensor_low_battery(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test battery low sensor when battery is low."""
    from custom_components.fireboard.binary_sensor import FireBoardBatteryLowSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    # Set battery to low level
    mock_coordinator_data["test-device-uuid-123"]["device_info"]["battery_level"] = 15

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardBatteryLowSensor(
            coordinator,
            "test-device-uuid-123",
        )

        # Battery at 15% should be low
        assert sensor.is_on is True


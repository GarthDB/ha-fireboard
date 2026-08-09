"""Tests for FireBoard binary sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry

from custom_components.fireboard.const import DOMAIN


async def test_connectivity_sensor(hass, mock_coordinator_data, mock_config_entry_data):
    """Test connectivity sensor."""
    from custom_components.fireboard.binary_sensor import FireBoardConnectivitySensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardConnectivitySensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.is_on is True
        assert sensor.available is True


async def test_connectivity_sensor_offline(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test connectivity sensor when device is offline."""
    from custom_components.fireboard.binary_sensor import FireBoardConnectivitySensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    # Mark device as offline
    mock_coordinator_data["test-device-uuid-123"]["online"] = False

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardConnectivitySensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.is_on is False
        assert sensor.available is True  # Connectivity sensor is always available


async def test_battery_low_sensor(hass, mock_coordinator_data, mock_config_entry_data):
    """Test battery low sensor."""
    from custom_components.fireboard.binary_sensor import FireBoardBatteryLowSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardBatteryLowSensor(
            coordinator,
            "test-device-uuid-123",
        )

        # Battery at 85% should not be low
        assert sensor.is_on is False


async def test_battery_low_sensor_low_battery(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test battery low sensor when battery is low."""
    from custom_components.fireboard.binary_sensor import FireBoardBatteryLowSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    # Set battery to a low level (15%)
    mock_coordinator_data["test-device-uuid-123"]["device_info"][
        "last_battery_reading"
    ] = 0.15

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardBatteryLowSensor(
            coordinator,
            "test-device-uuid-123",
        )

        # Battery at 15% should be low
        assert sensor.is_on is True


async def test_battery_low_sensor_invalid_battery_level(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test battery low sensor treats an unparseable reading as not-low."""
    from custom_components.fireboard.binary_sensor import FireBoardBatteryLowSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"][
        "last_battery_reading"
    ] = "not-a-number"

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardBatteryLowSensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.is_on is False


async def test_binary_sensor_setup_entry_creates_connectivity_and_battery_sensors(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test async_setup_entry creates the expected binary sensor entities.

    A connectivity sensor for every device, plus a battery-low sensor only
    for devices that have a battery.
    """
    from custom_components.fireboard.binary_sensor import (
        FireBoardBatteryLowSensor,
        FireBoardConnectivitySensor,
        async_setup_entry,
    )

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator = AsyncMock()
    mock_coordinator.data = mock_coordinator_data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = mock_coordinator

    entities = []

    def add_entities(new_entities):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, add_entities)

    connectivity = [e for e in entities if isinstance(e, FireBoardConnectivitySensor)]
    battery_low = [e for e in entities if isinstance(e, FireBoardBatteryLowSensor)]
    assert len(connectivity) == 1
    assert len(battery_low) == 1  # mock_device_data has last_battery_reading set


async def test_drive_lid_paused_sensor_when_paused(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the lid-paused sensor is on when drive_status reports it."""
    from custom_components.fireboard.binary_sensor import FireBoardDriveLidPausedSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["drive_status"] = {
        "mode": "Auto",
        "power_mode": "Heating",
        "lid_paused": True,
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardDriveLidPausedSensor(coordinator, "test-device-uuid-123")

        assert sensor.is_on is True


async def test_drive_lid_paused_sensor_without_status(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the lid-paused sensor defaults to off before drive_status is known."""
    from custom_components.fireboard.binary_sensor import FireBoardDriveLidPausedSensor
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardDriveLidPausedSensor(coordinator, "test-device-uuid-123")

        assert sensor.is_on is False


async def test_binary_sensor_setup_creates_lid_paused_when_drivelog_present(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the lid-paused binary sensor is only created for Drive-equipped devices."""
    from custom_components.fireboard.binary_sensor import (
        FireBoardDriveLidPausedSensor,
        async_setup_entry,
    )

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "setpoint": 225.0,
        "driveper": 0.0,
    }

    mock_coordinator = AsyncMock()
    mock_coordinator.data = mock_coordinator_data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = mock_coordinator

    entities = []

    def add_entities(new_entities):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, add_entities)

    lid_paused = [e for e in entities if isinstance(e, FireBoardDriveLidPausedSensor)]
    assert len(lid_paused) == 1

"""Tests for FireBoard sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature

from custom_components.fireboard.const import DOMAIN


async def test_temperature_sensor_setup(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test temperature sensor setup."""
    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardDataUpdateCoordinator"
    ) as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.data = mock_coordinator_data
        mock_coordinator.last_update_success = True
        mock_coordinator_class.return_value = mock_coordinator

        # Store coordinator in hass data
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][config_entry.entry_id] = mock_coordinator

        # Setup sensor platform
        from custom_components.fireboard.sensor import async_setup_entry

        entities = []

        def add_entities(new_entities):
            entities.extend(new_entities)

        await async_setup_entry(hass, config_entry, add_entities)

        # Should create sensors for channels plus battery sensor
        assert len(entities) > 0

        # Check temperature sensors
        temp_sensors = [e for e in entities if "temp" in e.unique_id]
        assert len(temp_sensors) == 3  # 3 channels in mock data

        # A session sensor is always created, one per device
        session_sensors = [e for e in entities if e.unique_id.endswith("_session")]
        assert len(session_sensors) == 1

        # No Drive sensors, since mock_device_data has no last_drivelog
        drive_sensors = [e for e in entities if "_drive_" in e.unique_id]
        assert len(drive_sensors) == 0


async def test_sensor_setup_creates_drive_sensors_when_drivelog_present(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test Drive sensors are only created for devices with a last_drivelog."""
    from custom_components.fireboard.sensor import async_setup_entry

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "setpoint": 225.0,
        "driveper": 0.42,
    }

    mock_coordinator = AsyncMock()
    mock_coordinator.data = mock_coordinator_data
    mock_coordinator.last_update_success = True
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = mock_coordinator

    entities = []

    def add_entities(new_entities):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, add_entities)

    drive_sensors = [e for e in entities if "_drive_" in e.unique_id]
    assert len(drive_sensors) == 4  # setpoint, fan, mode, battery voltage


async def test_temperature_sensor_value(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test temperature sensor value."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardTemperatureSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardTemperatureSensor(
            coordinator,
            "test-device-uuid-123",
            1,
        )

        assert sensor.native_value == 225.5
        assert sensor.native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT
        assert sensor.extra_state_attributes["channel"] == 1
        assert sensor.extra_state_attributes["label"] == "Probe 1"
        assert sensor.extra_state_attributes["target_temp"] == 225.0


async def test_temperature_sensor_uses_celsius_when_degreetype_is_1(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the sensor reports Celsius when FireBoard's degreetype says so.

    Regression test: the account/device's configured unit was previously
    ignored and every temperature sensor was hardcoded to Fahrenheit, which
    mislabeled Celsius readings (e.g. a 140 setpoint showing as "140 F"
    instead of the correct "140 C").
    """
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardTemperatureSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["temperatures"]["channels"][0][
        "degreetype"
    ] = 1

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardTemperatureSensor(
            coordinator,
            "test-device-uuid-123",
            1,
        )

        assert sensor.native_value == 225.5
        assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS


async def test_temperature_sensor_unavailable(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test temperature sensor when device is offline."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardTemperatureSensor

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

        sensor = FireBoardTemperatureSensor(
            coordinator,
            "test-device-uuid-123",
            1,
        )

        assert sensor.available is False


async def test_battery_sensor(hass, mock_coordinator_data, mock_config_entry_data):
    """Test battery sensor."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardBatterySensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardBatterySensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.native_value == 85
        assert sensor.native_unit_of_measurement == "%"


async def test_temperature_sensor_invalid_value_returns_none(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test an unparseable current_temp is treated as no reading, not a crash."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardTemperatureSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["temperatures"]["channels"][0][
        "current_temp"
    ] = "not-a-number"

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardTemperatureSensor(
            coordinator,
            "test-device-uuid-123",
            1,
        )

        assert sensor.native_value is None


async def test_temperature_sensor_no_reading_yet(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test a channel with no current_temp reports no value or extra attrs."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardTemperatureSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        # Channel 3 in mock_temperature_data has current_temp=None, target_temp=None
        sensor = FireBoardTemperatureSensor(
            coordinator,
            "test-device-uuid-123",
            3,
        )

        assert sensor.native_value is None
        assert "target_temp" not in sensor.extra_state_attributes


async def test_battery_sensor_invalid_value_returns_none(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test an unparseable battery reading is treated as no reading, not a crash."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardBatterySensor

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

        sensor = FireBoardBatterySensor(
            coordinator,
            "test-device-uuid-123",
        )

        assert sensor.native_value is None


async def test_drive_setpoint_and_fan_sensors(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test Drive sensors read setpoint/fan values from device_info.last_drivelog."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import (
        FireBoardDriveFanSensor,
        FireBoardDriveSetpointSensor,
    )

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "setpoint": 225.0,
        "driveper": 0.42,
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        setpoint_sensor = FireBoardDriveSetpointSensor(
            coordinator, "test-device-uuid-123"
        )
        fan_sensor = FireBoardDriveFanSensor(coordinator, "test-device-uuid-123")

        assert setpoint_sensor.native_value == 225.0
        assert (
            setpoint_sensor.native_unit_of_measurement == UnitOfTemperature.FAHRENHEIT
        )
        assert fan_sensor.native_value == 42


async def test_drive_setpoint_uses_celsius_when_degreetype_is_1(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the Drive setpoint reports Celsius when FireBoard's degreetype says so.

    Regression test: this previously always showed as Fahrenheit even when
    the account was configured for Celsius (e.g. a 140 setpoint showing as
    "140 F" instead of the correct "140 C").
    """
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardDriveSetpointSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "setpoint": 140.0,
        "driveper": 0.0,
        "degreetype": 1,
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        setpoint_sensor = FireBoardDriveSetpointSensor(
            coordinator, "test-device-uuid-123"
        )

        assert setpoint_sensor.native_value == 140.0
        assert setpoint_sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS


async def test_drive_sensors_invalid_values_return_none(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test unparseable Drive readings are treated as no reading, not a crash."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import (
        FireBoardDriveFanSensor,
        FireBoardDriveSetpointSensor,
    )

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "setpoint": "not-a-number",
        "driveper": "not-a-number",
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        setpoint_sensor = FireBoardDriveSetpointSensor(
            coordinator, "test-device-uuid-123"
        )
        fan_sensor = FireBoardDriveFanSensor(coordinator, "test-device-uuid-123")

        assert setpoint_sensor.native_value is None
        assert fan_sensor.native_value is None


async def test_drive_sensors_return_none_without_a_drivelog(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test Drive sensors don't crash when the device has no last_drivelog."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import (
        FireBoardDriveFanSensor,
        FireBoardDriveSetpointSensor,
    )

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        setpoint_sensor = FireBoardDriveSetpointSensor(
            coordinator, "test-device-uuid-123"
        )
        fan_sensor = FireBoardDriveFanSensor(coordinator, "test-device-uuid-123")

        assert setpoint_sensor.native_value is None
        assert fan_sensor.native_value is None


async def test_drive_mode_sensor_with_status(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the Drive mode sensor surfaces the human-readable mode string."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardDriveModeSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["drive_status"] = {
        "mode": "Auto",
        "power_mode": "Heating",
        "lid_paused": False,
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardDriveModeSensor(coordinator, "test-device-uuid-123")

        assert sensor.native_value == "Auto"
        assert sensor.extra_state_attributes == {"power_mode": "Heating"}


async def test_drive_mode_sensor_without_status(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the Drive mode sensor falls back to "Unknown" before first fetch."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardDriveModeSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardDriveModeSensor(coordinator, "test-device-uuid-123")

        assert sensor.native_value == "Unknown"
        assert sensor.extra_state_attributes == {}


async def test_drive_battery_voltage_sensor(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the Drive battery voltage sensor reads vbatt from last_drivelog."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardDriveBatterySensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "vbatt": 4.220333999999995,
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardDriveBatterySensor(coordinator, "test-device-uuid-123")

        assert sensor.native_value == 4.22
        assert sensor.native_unit_of_measurement == "V"


async def test_drive_battery_voltage_sensor_invalid_value_returns_none(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test an unparseable vbatt is treated as no reading, not a crash."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardDriveBatterySensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["device_info"]["last_drivelog"] = {
        "vbatt": "not-a-number",
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardDriveBatterySensor(coordinator, "test-device-uuid-123")

        assert sensor.native_value is None


async def test_session_sensor_with_active_session(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the session sensor surfaces title and attributes of an active session."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardSessionSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    mock_coordinator_data["test-device-uuid-123"]["session"] = {
        "id": 42,
        "title": "Sun Aug 9 Session",
        "start_time": "2026-08-09T12:37:58Z",
        "end_time": None,
        "duration": "50 minutes",
        "description": "Auto-created session",
    }

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardSessionSensor(coordinator, "test-device-uuid-123")

        assert sensor.native_value == "Sun Aug 9 Session"
        assert sensor.extra_state_attributes["session_id"] == 42
        assert sensor.extra_state_attributes["start_time"] == "2026-08-09T12:37:58Z"
        assert sensor.extra_state_attributes["active"] is True
        assert sensor.extra_state_attributes["description"] == "Auto-created session"


async def test_session_sensor_without_a_session(
    hass, mock_coordinator_data, mock_config_entry_data
):
    """Test the session sensor falls back cleanly when no session is known."""
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator
    from custom_components.fireboard.sensor import FireBoardSessionSensor

    config_entry = ConfigEntry(
        domain=DOMAIN,
        title="Test",
        data=mock_config_entry_data,
    )

    with patch("custom_components.fireboard.coordinator.FireBoardApiClient"):
        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.data = mock_coordinator_data
        coordinator.last_update_success = True

        sensor = FireBoardSessionSensor(coordinator, "test-device-uuid-123")

        assert sensor.native_value == "No Session"
        assert sensor.extra_state_attributes == {}

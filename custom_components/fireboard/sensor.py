"""Sensor platform for FireBoard integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_SESSION_ID, ATTR_SESSION_START, DOMAIN
from .coordinator import FireBoardDataUpdateCoordinator
from .entity import FireBoardEntity

_LOGGER = logging.getLogger(__name__)


def _unit_from_degreetype(degreetype: Any) -> str:
    """Map FireBoard's "degreetype" field to a Home Assistant temperature unit.

    FireBoard reports temperatures in whatever unit the account is actually
    configured for (visible per-reading as "degreetype": 1 = Celsius,
    2 = Fahrenheit) -- it must not be assumed to always be Fahrenheit.
    Defaults to Fahrenheit, FireBoard's own default, if degreetype is
    missing.
    """
    if degreetype == 1:
        return UnitOfTemperature.CELSIUS
    return UnitOfTemperature.FAHRENHEIT


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FireBoard sensor entities."""
    coordinator: FireBoardDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities: list[SensorEntity] = []

    # Create sensors for each device and channel
    for device_uuid, device_data in coordinator.data.items():
        device_info = device_data.get("device_info", {})

        # Get channels from device info (REST API provides channel configuration)
        channels = device_info.get("channels", [])

        for channel in channels:
            channel_number = channel.get("channel")
            if channel_number is not None:
                # Temperature sensor for this channel
                entities.append(
                    FireBoardTemperatureSensor(
                        coordinator,
                        device_uuid,
                        channel_number,
                    )
                )

        # Add device-level sensors
        # Battery level sensor (if the device reports a battery reading).
        # Note: FireBoard's devices.json has no "has_battery" field -- every
        # device we've observed reports "last_battery_reading" directly.
        if device_info.get("last_battery_reading") is not None:
            entities.append(
                FireBoardBatterySensor(
                    coordinator,
                    device_uuid,
                )
            )

        # FireBoard Drive (fan controller) sensors, if this device has one
        # attached. devices.json embeds "last_drivelog" directly whenever a
        # Drive has ever reported for the device.
        if device_info.get("last_drivelog"):
            entities.append(FireBoardDriveSetpointSensor(coordinator, device_uuid))
            entities.append(FireBoardDriveFanSensor(coordinator, device_uuid))
            entities.append(FireBoardDriveModeSensor(coordinator, device_uuid))
            entities.append(FireBoardDriveBatterySensor(coordinator, device_uuid))

        # Current/most recent cook session for this device.
        entities.append(FireBoardSessionSensor(coordinator, device_uuid))

    async_add_entities(entities)


class FireBoardTemperatureSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
        channel_number: int,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, device_uuid, channel_number)

        # Get channel info for naming from device configuration
        device_info = self._device_data.get("device_info", {})
        channels = device_info.get("channels", [])
        channel_label = f"Channel {channel_number}"

        for channel in channels:
            if channel.get("channel") == channel_number:
                channel_label = channel.get("channel_label", channel_label)
                break

        # Set unique ID
        self._attr_unique_id = f"{device_uuid}_temp_{channel_number}"

        # Set name
        self._attr_name = f"{self._device_title} {channel_label}"

    def _get_channel_info(self) -> dict[str, Any]:
        """Get channel information from coordinator data."""
        # Get channel configuration from device_info (REST API)
        device_info = self._device_data.get("device_info", {})
        channels = device_info.get("channels", [])

        channel_info = {}
        for channel in channels:
            if channel.get("channel") == self._channel_number:
                channel_info = {
                    "label": channel.get(
                        "channel_label", f"Channel {self._channel_number}"
                    ),
                    "channel": channel.get("channel"),
                }
                break

        # Merge with temperature data from MQTT if available
        temp_channels = self._temperatures.get("channels", [])
        for temp_channel in temp_channels:
            if temp_channel.get("channel") == self._channel_number:
                channel_info.update(temp_channel)
                break

        return channel_info

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit this channel's readings are actually reported in."""
        return _unit_from_degreetype(self._get_channel_info().get("degreetype"))

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        channel_info = self._get_channel_info()
        temp = channel_info.get("current_temp")

        if temp is not None:
            try:
                return float(temp)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid temperature value for %s: %s",
                    self._attr_name,
                    temp,
                )
                return None

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        channel_info = self._get_channel_info()

        attributes = {}

        # Add target temperature if set
        target_temp = channel_info.get("target_temp")
        if target_temp is not None:
            attributes["target_temp"] = target_temp

        # Add channel label
        label = channel_info.get("label")
        if label:
            attributes["label"] = label

        # Add channel number
        attributes["channel"] = self._channel_number

        return attributes


class FireBoardBatterySensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard battery level sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, device_uuid)

        # Set unique ID
        self._attr_unique_id = f"{device_uuid}_battery"

        # Set name
        self._attr_name = f"{self._device_title} Battery"

    @property
    def native_value(self) -> int | None:
        """Return the battery level.

        FireBoard reports "last_battery_reading" as a 0.0-1.0 ratio rather
        than a 0-100 percentage.
        """
        device_info = self._device_data.get("device_info", {})
        battery_reading = device_info.get("last_battery_reading")

        if battery_reading is not None:
            try:
                return round(float(battery_reading) * 100)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid battery reading for %s: %s",
                    self._attr_name,
                    battery_reading,
                )
                return None

        return None


class FireBoardDriveSetpointSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard Drive's target temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the Drive setpoint sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_drive_setpoint"
        self._attr_name = f"{self._device_title} Drive Setpoint"

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit the Drive setpoint is actually reported in."""
        drivelog = self._device_data.get("device_info", {}).get("last_drivelog") or {}
        return _unit_from_degreetype(drivelog.get("degreetype"))

    @property
    def native_value(self) -> float | None:
        """Return the Drive's target temperature."""
        drivelog = self._device_data.get("device_info", {}).get("last_drivelog") or {}
        setpoint = drivelog.get("setpoint")

        if setpoint is not None:
            try:
                return float(setpoint)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid Drive setpoint for %s: %s", self._attr_name, setpoint
                )
                return None

        return None


class FireBoardDriveFanSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard Drive's fan output."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the Drive fan sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_drive_fan"
        self._attr_name = f"{self._device_title} Drive Fan"

    @property
    def native_value(self) -> int | None:
        """Return the Drive's fan output percentage.

        FireBoard reports "driveper" as a 0.0-1.0 ratio rather than a
        0-100 percentage.
        """
        drivelog = self._device_data.get("device_info", {}).get("last_drivelog") or {}
        drive_percent = drivelog.get("driveper")

        if drive_percent is not None:
            try:
                return round(float(drive_percent) * 100)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid Drive fan reading for %s: %s",
                    self._attr_name,
                    drive_percent,
                )
                return None

        return None


class FireBoardSessionSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard cook session."""

    _attr_icon = "mdi:notebook-outline"

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the session sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_session"
        self._attr_name = f"{self._device_title} Session"

    @property
    def native_value(self) -> str:
        """Return the session title, or a placeholder if none is known."""
        session = self._device_data.get("session")
        if not session:
            return "No Session"
        return session.get("title") or "No Session"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional session details."""
        session = self._device_data.get("session")
        if not session:
            return {}

        attributes = {
            ATTR_SESSION_ID: session.get("id"),
            ATTR_SESSION_START: session.get("start_time"),
            "end_time": session.get("end_time"),
            "duration": session.get("duration"),
            "active": session.get("end_time") is None,
        }
        description = session.get("description")
        if description:
            attributes["description"] = description

        return attributes


class FireBoardDriveModeSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard Drive's operating mode (Auto/Manual/Off).

    Sourced from session detail rather than devices.json, since only session
    detail reports FireBoard's own human-readable mode string -- devices.json
    only exposes this as an undocumented raw integer with no published
    mapping. Only refreshed on the (throttled) session-polling cycle, so this
    can lag briefly behind an actual mode change made in the FireBoard app.
    """

    _attr_icon = "mdi:fan"

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the Drive mode sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_drive_mode"
        self._attr_name = f"{self._device_title} Drive Mode"

    @property
    def native_value(self) -> str:
        """Return the Drive's mode, or "Unknown" if not yet fetched."""
        drive_status = self._device_data.get("drive_status")
        mode = drive_status.get("mode") if drive_status else None
        return mode or "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the raw power_mode value alongside the mode."""
        drive_status = self._device_data.get("drive_status")
        if not drive_status or drive_status.get("power_mode") is None:
            return {}
        return {"power_mode": drive_status["power_mode"]}


class FireBoardDriveBatterySensor(FireBoardEntity, SensorEntity):
    """Representation of the FireBoard Drive unit's own battery voltage.

    Distinct from the main device's battery percentage (last_battery_reading)
    -- the Drive fan controller has its own separate battery.
    """

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the Drive battery voltage sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_drive_battery_voltage"
        self._attr_name = f"{self._device_title} Drive Battery Voltage"

    @property
    def native_value(self) -> float | None:
        """Return the Drive's battery voltage."""
        drivelog = self._device_data.get("device_info", {}).get("last_drivelog") or {}
        vbatt = drivelog.get("vbatt")

        if vbatt is not None:
            try:
                return round(float(vbatt), 2)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid Drive battery voltage for %s: %s", self._attr_name, vbatt
                )
                return None

        return None

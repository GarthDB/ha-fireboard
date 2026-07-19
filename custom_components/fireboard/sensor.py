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
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FireBoardDataUpdateCoordinator
from .entity import FireBoardEntity

_LOGGER = logging.getLogger(__name__)


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
        # Battery level sensor (if device has battery)
        if device_info.get("has_battery", False):
            entities.append(
                FireBoardBatterySensor(
                    coordinator,
                    device_uuid,
                )
            )

        # Auger/drive percentage sensor. Always created, like the probe
        # sensors: whether last_drivelog is present depends on whether
        # Drive is actively holding a setpoint right now, not on whether
        # the device supports Drive at all, so gating entity *creation*
        # on it (rather than just availability/native_value) means the
        # entity can get permanently skipped if HA happens to restart
        # while the grill is off/idle.
        entities.append(
            FireBoardAugerSensor(
                coordinator,
                device_uuid,
            )
        )

    async_add_entities(entities)


class FireBoardTemperatureSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

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
                        "channel_label",
                        f"Channel {self._channel_number}"
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
        """Return the battery level."""
        device_info = self._device_data.get("device_info", {})
        battery_level = device_info.get("battery_level")

        if battery_level is not None:
            try:
                return int(battery_level)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid battery level for %s: %s",
                    self._attr_name,
                    battery_level,
                )
                return None

        return None


class FireBoardAugerSensor(FireBoardEntity, SensorEntity):
    """Representation of a FireBoard Drive auger duty-cycle sensor.

    FireBoard Drive-equipped grills (e.g. Yoder/YS series) report a
    `last_drivelog.driveper` fraction — the percentage of time the
    auger motor is currently running to hold the setpoint. This is
    pure REST data (device_info), unrelated to the temperatures/MQTT
    path, so it works regardless of MQTT connectivity.
    """

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:screw-lag"

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the auger sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_auger_drive_percent"
        self._attr_name = f"{self._device_title} Auger Drive"

    def _get_drivelog(self) -> dict[str, Any]:
        """Return the latest drivelog block from device_info."""
        device_info = self._device_data.get("device_info", {})
        return device_info.get("last_drivelog") or {}

    @property
    def native_value(self) -> float | None:
        """Return the auger duty cycle as a percentage."""
        driveper = self._get_drivelog().get("driveper")

        if driveper is not None:
            try:
                return round(float(driveper) * 100, 1)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid driveper value for %s: %s",
                    self._attr_name,
                    driveper,
                )
                return None

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional drive state attributes."""
        drivelog = self._get_drivelog()
        attributes = {}

        if drivelog.get("setpoint") is not None:
            attributes["setpoint"] = drivelog.get("setpoint")

        if drivelog.get("powermode") is not None:
            attributes["power_mode"] = drivelog.get("powermode")

        if drivelog.get("created") is not None:
            attributes["updated"] = drivelog.get("created")

        return attributes

    # No `available` override: like the probe sensors, this stays
    # available whenever the device itself is online (FireBoardEntity's
    # default). Absence of an active drivelog just means native_value
    # returns None ("unknown"), not that the entity is unavailable.

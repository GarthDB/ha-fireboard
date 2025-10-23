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
from homeassistant.const import UnitOfTemperature
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
        temperatures = device_data.get("temperatures", {})

        # Get channels from temperature data
        channels = temperatures.get("channels", [])

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

        # Get channel info for naming
        channel_info = self._get_channel_info()
        channel_label = channel_info.get("label") or f"Channel {channel_number}"

        # Set unique ID
        self._attr_unique_id = f"{device_uuid}_temp_{channel_number}"

        # Set name
        self._attr_name = f"{self._device_title} {channel_label}"

    def _get_channel_info(self) -> dict[str, Any]:
        """Get channel information from coordinator data."""
        channels = self._temperatures.get("channels", [])
        for channel in channels:
            if channel.get("channel") == self._channel_number:
                return channel
        return {}

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


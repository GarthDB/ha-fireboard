"""Binary sensor platform for FireBoard integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up FireBoard binary sensor entities."""
    coordinator: FireBoardDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    entities: list[BinarySensorEntity] = []

    # Create binary sensors for each device
    for device_uuid, device_data in coordinator.data.items():
        device_info = device_data.get("device_info", {})

        # Device connectivity sensor
        entities.append(
            FireBoardConnectivitySensor(
                coordinator,
                device_uuid,
            )
        )

        # Battery low sensor (if the device reports a battery reading).
        # Note: FireBoard's devices.json has no "has_battery" field -- every
        # device we've observed reports "last_battery_reading" directly.
        if device_info.get("last_battery_reading") is not None:
            entities.append(
                FireBoardBatteryLowSensor(
                    coordinator,
                    device_uuid,
                )
            )

        # Drive lid-paused sensor, if this device has a Drive attached.
        if device_info.get("last_drivelog"):
            entities.append(
                FireBoardDriveLidPausedSensor(
                    coordinator,
                    device_uuid,
                )
            )

    async_add_entities(entities)


class FireBoardConnectivitySensor(FireBoardEntity, BinarySensorEntity):
    """Representation of a FireBoard connectivity sensor."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the connectivity sensor."""
        super().__init__(coordinator, device_uuid)

        # Set unique ID
        self._attr_unique_id = f"{device_uuid}_connectivity"

        # Set name
        self._attr_name = f"{self._device_title} Connectivity"

    @property
    def is_on(self) -> bool:
        """Return true if device is connected."""
        return self._device_data.get("online", False)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Connectivity sensor is always available if coordinator has data
        return self.coordinator.last_update_success


class FireBoardBatteryLowSensor(FireBoardEntity, BinarySensorEntity):
    """Representation of a FireBoard battery low sensor."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the battery low sensor."""
        super().__init__(coordinator, device_uuid)

        # Set unique ID
        self._attr_unique_id = f"{device_uuid}_battery_low"

        # Set name
        self._attr_name = f"{self._device_title} Battery Low"

    @property
    def is_on(self) -> bool:
        """Return true if battery is low.

        FireBoard reports "last_battery_reading" as a 0.0-1.0 ratio rather
        than a 0-100 percentage.
        """
        device_info = self._device_data.get("device_info", {})
        battery_reading = device_info.get("last_battery_reading")

        if battery_reading is not None:
            try:
                # Consider battery low if below 20%
                return float(battery_reading) * 100 < 20
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Invalid battery reading for %s: %s",
                    self._attr_name,
                    battery_reading,
                )
                return False

        return False


class FireBoardDriveLidPausedSensor(FireBoardEntity, BinarySensorEntity):
    """Representation of whether FireBoard Drive has paused for an open lid.

    Sourced from session detail rather than devices.json, since only session
    detail exposes "lidpaused" as a direct field. Only refreshed on the
    (throttled) session-polling cycle, so this can lag briefly behind the
    lid actually opening/closing.
    """

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
    ) -> None:
        """Initialize the Drive lid-paused sensor."""
        super().__init__(coordinator, device_uuid)

        self._attr_unique_id = f"{device_uuid}_drive_lid_paused"
        self._attr_name = f"{self._device_title} Drive Lid Paused"

    @property
    def is_on(self) -> bool:
        """Return true if the Drive fan is currently paused for an open lid."""
        drive_status = self._device_data.get("drive_status")
        return bool(drive_status and drive_status.get("lid_paused"))

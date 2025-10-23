"""Base entity for FireBoard integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FireBoardDataUpdateCoordinator


class FireBoardEntity(CoordinatorEntity[FireBoardDataUpdateCoordinator]):
    """Base entity for FireBoard devices."""

    def __init__(
        self,
        coordinator: FireBoardDataUpdateCoordinator,
        device_uuid: str,
        channel_number: int | None = None,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: Data update coordinator
            device_uuid: Device UUID
            channel_number: Optional channel number for temperature entities

        """
        super().__init__(coordinator)
        self._device_uuid = device_uuid
        self._channel_number = channel_number

        # Get device info from coordinator data
        device_data = self.coordinator.data.get(device_uuid, {})
        device_info = device_data.get("device_info", {})

        self._device_title = device_info.get("title", "FireBoard")
        self._device_model = device_info.get("hardware_id", "Unknown")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        device_data = self.coordinator.data.get(self._device_uuid, {})
        device_info = device_data.get("device_info", {})

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_uuid)},
            name=self._device_title,
            manufacturer="FireBoard",
            model=self._device_model,
            sw_version=device_info.get("software_version"),
            configuration_url="https://fireboard.io",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if coordinator has recent data
        # and the device is marked as online
        if not self.coordinator.last_update_success:
            return False

        device_data = self.coordinator.data.get(self._device_uuid, {})
        return device_data.get("online", False)

    @property
    def _device_data(self) -> dict[str, Any]:
        """Return device data from coordinator."""
        return self.coordinator.data.get(self._device_uuid, {})

    @property
    def _temperatures(self) -> dict[str, Any]:
        """Return temperature data for this device."""
        return self._device_data.get("temperatures", {})

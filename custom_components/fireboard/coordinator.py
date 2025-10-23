"""Data update coordinator for FireBoard integration with MQTT support."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import (
    FireBoardApiClient,
    FireBoardApiClientCommunicationError,
    FireBoardApiClientRateLimitError,
)
from .const import DOMAIN
from .mqtt_client import FireBoardMQTTClient

_LOGGER = logging.getLogger(__name__)

# Refresh device list every 5 minutes (MQTT handles real-time temps)
DEVICE_REFRESH_INTERVAL = timedelta(minutes=5)


class FireBoardDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from FireBoard API and MQTT."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self.mqtt_client: FireBoardMQTTClient | None = None
        self._subscribed_devices: set[str] = set()

        # Create API client
        session = async_get_clientsession(hass)
        self.client = FireBoardApiClient(
            email=config_entry.data[CONF_EMAIL],
            password=config_entry.data[CONF_PASSWORD],
            session=session,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Only need to refresh device list periodically
            # MQTT handles real-time temperature updates
            update_interval=DEVICE_REFRESH_INTERVAL,
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator with MQTT."""
        try:
            # Authenticate first
            await self.client.authenticate()

            # Set up MQTT client for real-time updates
            if self.client.auth_token:
                self.mqtt_client = FireBoardMQTTClient(
                    auth_token=self.client.auth_token,
                    on_message_callback=self._handle_mqtt_message,
                )

                # Connect to MQTT broker
                await self.hass.async_add_executor_job(self.mqtt_client.connect)

                _LOGGER.info("MQTT client connected successfully")
            else:
                _LOGGER.warning("No auth token available for MQTT connection")

        except Exception as err:
            _LOGGER.error("Failed to set up MQTT connection: %s", err)
            # Don't fail setup, we can fall back to polling

    def _handle_mqtt_message(
        self, device_uuid: str, message_data: dict[str, Any]
    ) -> None:
        """Handle incoming MQTT message with temperature data.

        Args:
            device_uuid: The device UUID
            message_data: The message payload containing temperature data

        """
        _LOGGER.debug("MQTT message for device %s: %s", device_uuid, message_data)

        # Update the coordinator's data with the new temperature info
        if self.data and device_uuid in self.data:
            # Update temperatures from MQTT message
            self.data[device_uuid]["temperatures"] = message_data
            self.data[device_uuid]["online"] = True

            # Trigger update to sensors
            self.async_set_updated_data(self.data)
        else:
            _LOGGER.debug("Received data for unknown device: %s", device_uuid)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update device list via REST API.

        MQTT handles real-time temperature updates, so this just refreshes
        the device list and configuration periodically.

        Returns:
            Dictionary containing all device data

        Raises:
            UpdateFailed: If update fails

        """
        try:
            # Ensure we're authenticated
            if not self.client.auth_token:
                await self.client.authenticate()

                # Set up MQTT if not already connected
                if not self.mqtt_client and self.client.auth_token:
                    await self._async_setup()

            # Get all devices from REST API
            devices = await self.client.get_devices()

            # Build data structure with device info
            device_data = {}

            for device in devices:
                device_uuid = device.get("uuid")
                if not device_uuid:
                    continue

                # Keep existing temperature data if we have it (from MQTT)
                existing_temps = {}
                if self.data and device_uuid in self.data:
                    existing_temps = self.data[device_uuid].get("temperatures", {})

                # Extract channel information and latest temps from device data
                channels = device.get("channels", [])
                latest_temps = device.get("latest_temps", [])

                device_data[device_uuid] = {
                    "device_info": device,
                    "channels": channels,
                    "latest_temps": latest_temps,
                    "temperatures": existing_temps,  # Keep MQTT temps
                    "online": True,
                }

                # Subscribe to MQTT for this device
                if self.mqtt_client and device_uuid not in self._subscribed_devices:
                    await self.hass.async_add_executor_job(
                        self.mqtt_client.subscribe_device, device_uuid
                    )
                    self._subscribed_devices.add(device_uuid)
                    _LOGGER.debug("Subscribed to MQTT for device %s", device_uuid)

                _LOGGER.debug(
                    "Updated data for device %s",
                    device.get("title", device_uuid),
                )

            return device_data

        except FireBoardApiClientRateLimitError as err:
            _LOGGER.error("Rate limit exceeded: %s", err)
            raise UpdateFailed(f"Rate limit exceeded: {err}") from err
        except FireBoardApiClientCommunicationError as err:
            _LOGGER.error("Communication error: %s", err)
            raise UpdateFailed(f"Communication error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self.mqtt_client:
            await self.hass.async_add_executor_job(self.mqtt_client.disconnect)
            _LOGGER.info("MQTT client disconnected")

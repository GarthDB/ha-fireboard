"""Data update coordinator for FireBoard integration."""

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
from .const import CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FireBoardDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the FireBoard API."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry

        # Create API client
        session = async_get_clientsession(hass)
        self.client = FireBoardApiClient(
            email=config_entry.data[CONF_EMAIL],
            password=config_entry.data[CONF_PASSWORD],
            session=session,
        )

        # Get polling interval from config
        polling_interval = config_entry.data.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library.

        Returns:
            Dictionary containing all device data

        Raises:
            UpdateFailed: If update fails

        """
        try:
            # Ensure we're authenticated
            if not self.client._token:
                await self.client.authenticate()

            # Get all devices
            devices = await self.client.get_devices()

            # Build a data structure with device info and temperatures
            device_data = {}

            for device in devices:
                device_uuid = device.get("uuid")
                if not device_uuid:
                    continue

                try:
                    # Get temperature data for this device
                    temps = await self.client.get_temperatures(device_uuid)

                    # Combine device info with temperature data
                    device_data[device_uuid] = {
                        "device_info": device,
                        "temperatures": temps,
                        "online": True,
                    }

                    _LOGGER.debug(
                        "Updated data for device %s: %s",
                        device.get("title", device_uuid),
                        device_data[device_uuid],
                    )

                except Exception as err:
                    _LOGGER.warning(
                        "Error fetching temperatures for device %s: %s",
                        device_uuid,
                        err,
                    )
                    # Mark device as offline but keep device info
                    device_data[device_uuid] = {
                        "device_info": device,
                        "temperatures": {},
                        "online": False,
                    }

            return device_data

        except FireBoardApiClientRateLimitError as err:
            _LOGGER.error(
                "Rate limit exceeded. Consider increasing polling interval: %s", err
            )
            raise UpdateFailed(
                f"Rate limit exceeded: {err}. Please increase polling interval."
            ) from err
        except FireBoardApiClientCommunicationError as err:
            _LOGGER.error("Communication error: %s", err)
            raise UpdateFailed(f"Communication error: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err


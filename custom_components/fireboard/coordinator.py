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
from .const import CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL, DOMAIN
from .mqtt_client import FireBoardMQTTClient

_LOGGER = logging.getLogger(__name__)

# sessions.json returns every session for the account in one call (not
# filterable per-device), so it's cheap relative to devices.json, but every
# extra call still eats into FireBoard's 17-calls-per-5-minutes limit. Poll
# it on a slower cadence than temperature data, which changes far more
# slowly than temperatures do.
SESSION_POLL_EVERY_N_REFRESHES = 3


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
        self._refresh_count = 0

        # Create API client
        session = async_get_clientsession(hass)
        self.client = FireBoardApiClient(
            email=config_entry.data[CONF_EMAIL],
            password=config_entry.data[CONF_PASSWORD],
            session=session,
        )

        polling_interval = config_entry.data.get(
            CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Only need to refresh device list periodically
            # MQTT handles real-time temperature updates
            update_interval=timedelta(seconds=polling_interval),
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator with MQTT."""
        try:
            # Authenticate first
            await self.client.authenticate()

            # Set up MQTT client for real-time updates
            if self.client.auth_token and self.client.session_cookies:
                self.mqtt_client = FireBoardMQTTClient(
                    auth_token=self.client.auth_token,
                    session_cookies=self.client.session_cookies,
                    on_message_callback=self._handle_mqtt_message,
                )

                # Connect to MQTT broker
                await self.hass.async_add_executor_job(self.mqtt_client.connect)

                _LOGGER.info("MQTT client connected successfully")
            else:
                _LOGGER.warning("No auth token or session cookies available for MQTT")

        except Exception as err:
            _LOGGER.warning(
                "MQTT connection unavailable, will use REST API polling: %s", err
            )
            # Don't fail setup, we can fall back to polling
            self.mqtt_client = None

    def _handle_mqtt_message(
        self, device_uuid: str, message_data: dict[str, Any]
    ) -> None:
        """Handle incoming MQTT message with temperature data.

        Args:
            device_uuid: The device UUID
            message_data: The message payload containing temperature data
                         Format: {"temp": 67, "channel": 1, "p": true,
                                 "date": "...", "degreetype": 2}

        """
        _LOGGER.debug("MQTT message for device %s: %s", device_uuid, message_data)

        # Update the coordinator's data with the new temperature info
        if self.data and device_uuid in self.data:
            # Initialize temperatures dict if not exists
            if "temperatures" not in self.data[device_uuid]:
                self.data[device_uuid]["temperatures"] = {"channels": []}

            # Update or add channel temperature
            channel_num = message_data.get("channel")
            if channel_num:
                channels = self.data[device_uuid]["temperatures"].get("channels", [])

                # Find and update existing channel or add new one
                found = False
                for ch in channels:
                    if ch.get("channel") == channel_num:
                        ch["current_temp"] = message_data.get("temp")
                        ch["probe_present"] = message_data.get("p", False)
                        ch["last_update"] = message_data.get("date")
                        ch["degreetype"] = message_data.get("degreetype")
                        found = True
                        break

                if not found:
                    channels.append(
                        {
                            "channel": channel_num,
                            "current_temp": message_data.get("temp"),
                            "probe_present": message_data.get("p", False),
                            "last_update": message_data.get("date"),
                            "degreetype": message_data.get("degreetype"),
                        }
                    )

                self.data[device_uuid]["temperatures"]["channels"] = channels
                self.data[device_uuid]["online"] = True

                # Trigger update to sensors
                self.async_set_updated_data(self.data)
        else:
            _LOGGER.debug("Received data for unknown device: %s", device_uuid)

    @staticmethod
    def _pick_current_session(
        sessions: list[dict[str, Any]], device_uuid: str
    ) -> dict[str, Any] | None:
        """Pick the most relevant session for a device.

        Prefers a session that's still ongoing (end_time is None); falls
        back to the most recently started session for that device.
        """
        device_sessions = [
            session
            for session in sessions
            if device_uuid in (session.get("device_ids") or [])
        ]
        if not device_sessions:
            return None

        ongoing = [s for s in device_sessions if s.get("end_time") is None]
        if ongoing:
            return max(ongoing, key=lambda s: s.get("start_time") or "")

        return max(device_sessions, key=lambda s: s.get("start_time") or "")

    @staticmethod
    def _extract_drive_status(
        session_detail: dict[str, Any], device_uuid: str
    ) -> dict[str, Any] | None:
        """Pull a device's Drive mode/lid-paused state out of session detail.

        Unlike devices.json's embedded last_drivelog (raw, undocumented
        integer modetype/powermode), a session's detail endpoint reports
        these as FireBoard's own human-readable strings (e.g. "Off"), which
        is what makes exposing a reliable Drive Mode sensor possible at all.
        """
        for device in session_detail.get("devices", []):
            if device.get("uuid") != device_uuid:
                continue
            drivelog = device.get("last_drivelog")
            if not drivelog:
                return None
            return {
                "mode": drivelog.get("modetype"),
                "power_mode": drivelog.get("powermode"),
                "lid_paused": drivelog.get("lidpaused"),
            }
        return None

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

            # Sessions change far more slowly than temperatures, so only
            # refetch them periodically to conserve API budget; a failure
            # here shouldn't fail the whole update, since temperature data
            # is the priority.
            should_poll_sessions = (
                self._refresh_count % SESSION_POLL_EVERY_N_REFRESHES == 0
            )
            sessions: list[dict[str, Any]] = []
            if should_poll_sessions:
                try:
                    sessions = await self.client.get_sessions()
                except (
                    FireBoardApiClientRateLimitError,
                    FireBoardApiClientCommunicationError,
                ) as err:
                    _LOGGER.warning("Could not refresh sessions this cycle: %s", err)
                    should_poll_sessions = False
            self._refresh_count += 1

            # Session detail (needed for human-readable Drive mode/lid-paused
            # state) is its own API call per session. Devices sharing a
            # session are deduplicated via this cache, but on top of that,
            # cap detail fetches to at most one *new* session per refresh --
            # with several devices each on a different session, fetching all
            # of their details in one cycle could burst several extra calls
            # at once, which risks the 17-calls-per-5-minutes limit. Any
            # session not reached this cycle just keeps its previous
            # drive_status and gets picked up on a later cycle.
            session_detail_cache: dict[int, dict[str, Any]] = {}
            session_detail_fetches_remaining = 1

            # Build data structure with device info
            device_data = {}

            for device in devices:
                device_uuid = device.get("uuid")
                if not device_uuid:
                    continue

                if should_poll_sessions:
                    session = self._pick_current_session(sessions, device_uuid)
                    session_id = session.get("id") if session else None

                    if (
                        session_id is not None
                        and session_id not in session_detail_cache
                    ):
                        if session_detail_fetches_remaining > 0:
                            try:
                                session_detail_cache[session_id] = (
                                    await self.client.get_session(session_id)
                                )
                            except (
                                FireBoardApiClientRateLimitError,
                                FireBoardApiClientCommunicationError,
                            ) as err:
                                _LOGGER.warning(
                                    "Could not fetch session %s detail: %s",
                                    session_id,
                                    err,
                                )
                                session_detail_cache[session_id] = {}
                            session_detail_fetches_remaining -= 1
                        else:
                            session_detail_cache[session_id] = None

                    detail = (
                        session_detail_cache.get(session_id)
                        if session_id is not None
                        else None
                    )
                    if detail:
                        drive_status = self._extract_drive_status(detail, device_uuid)
                    else:
                        # No session, or this cycle's fetch budget was
                        # already spent on another device's session.
                        drive_status = (
                            self.data.get(device_uuid, {}).get("drive_status")
                            if self.data
                            else None
                        )
                else:
                    session = (
                        self.data.get(device_uuid, {}).get("session")
                        if self.data
                        else None
                    )
                    drive_status = (
                        self.data.get(device_uuid, {}).get("drive_status")
                        if self.data
                        else None
                    )

                # Extract channel information and latest temps from device data
                channels = device.get("channels", [])
                latest_temps = device.get("latest_temps", [])

                # devices.json already embeds each channel's current_temp /
                # last_templog (FireBoard docs: "< 60 seconds old"), so seed
                # temperature data from REST on every poll rather than relying
                # solely on MQTT pushes -- MQTT is undocumented/reverse
                # engineered and can silently stop working, in which case
                # sensors must not be left permanently without a value.
                rest_channels = []
                for channel in channels:
                    channel_num = channel.get("channel")
                    if channel_num is None:
                        continue
                    last_templog = channel.get("last_templog") or {}
                    current_temp = channel.get("current_temp", last_templog.get("temp"))
                    rest_channels.append(
                        {
                            "channel": channel_num,
                            "current_temp": current_temp,
                            "probe_present": current_temp is not None,
                            "last_update": last_templog.get("created"),
                            # 1 = Celsius, 2 = Fahrenheit -- this reflects the
                            # unit the account/device is actually configured
                            # for, and must not be assumed to always be °F.
                            "degreetype": channel.get(
                                "degreetype", last_templog.get("degreetype")
                            ),
                        }
                    )

                device_data[device_uuid] = {
                    "device_info": device,
                    "channels": channels,
                    "latest_temps": latest_temps,
                    "temperatures": {"channels": rest_channels},
                    "session": session,
                    "drive_status": drive_status,
                    "online": True,
                }

                # Subscribe to MQTT for this device
                if self.mqtt_client and device_uuid not in self._subscribed_devices:
                    # Get list of channel numbers
                    channel_numbers = [
                        ch.get("channel") for ch in channels if ch.get("channel")
                    ]

                    if channel_numbers:
                        await self.hass.async_add_executor_job(
                            self.mqtt_client.subscribe_device,
                            device_uuid,
                            channel_numbers,
                        )
                        self._subscribed_devices.add(device_uuid)
                        _LOGGER.debug(
                            "Subscribed to MQTT for device %s (channels: %s)",
                            device_uuid,
                            channel_numbers,
                        )

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

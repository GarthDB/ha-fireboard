"""FireBoard MQTT client for real-time temperature updates."""

from __future__ import annotations

import json
import logging
import ssl
from typing import Any, Callable

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


class FireBoardMQTTClient:
    """FireBoard MQTT client for WebSocket connection."""

    def __init__(
        self,
        auth_token: str,
        session_cookies: dict[str, str],
        on_message_callback: Callable[[str, dict[str, Any]], None],
    ) -> None:
        """Initialize the MQTT client.

        Args:
            auth_token: FireBoard authentication token
            session_cookies: Session cookies (sessionid and csrftoken)
            on_message_callback: Callback function for received messages
                                 Takes (device_uuid, message_data) as arguments

        """
        self._auth_token = auth_token
        self._session_cookies = session_cookies
        self._on_message_callback = on_message_callback
        self._client: mqtt.Client | None = None
        self._connected = False
        self._subscribed_topics: set[str] = set()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict[str, Any],
        rc: int,
    ) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            _LOGGER.info("Connected to FireBoard MQTT broker")
            self._connected = True
            # Resubscribe to all topics on reconnect
            for topic in self._subscribed_topics:
                client.subscribe(topic)
                _LOGGER.debug("Resubscribed to topic: %s", topic)
        else:
            _LOGGER.error("Failed to connect to MQTT broker: %s", rc)
            self._connected = False

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
    ) -> None:
        """Handle MQTT disconnection."""
        _LOGGER.warning("Disconnected from FireBoard MQTT broker: %s", rc)
        self._connected = False

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """Handle incoming MQTT message."""
        try:
            # Parse the topic to extract device UUID and message type
            # Topic format: {device_uuid}/templog{channel} or {device_uuid}/drivelog
            topic_parts = msg.topic.split("/")
            if len(topic_parts) >= 2:
                device_uuid = topic_parts[0]
                message_type = topic_parts[1]  # templog1, templog2, drivelog, etc.
            else:
                _LOGGER.warning("Invalid topic format: %s", msg.topic)
                return

            # Parse message payload (JSON format)
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                _LOGGER.warning("Failed to decode MQTT message: %s", msg.payload)
                return

            _LOGGER.debug(
                "Received MQTT message for device %s (%s): %s",
                device_uuid,
                message_type,
                payload,
            )

            # Call the callback with device UUID and payload
            if self._on_message_callback:
                self._on_message_callback(device_uuid, payload)

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error processing MQTT message: %s", err)

    def connect(self) -> None:
        """Connect to FireBoard MQTT broker over WebSocket."""
        try:
            # Create MQTT client with WebSocket transport
            # Use callback API version 1 for better WebSocket compatibility
            self._client = mqtt.Client(
                client_id=f"fireboard_ha_{self._auth_token[:8]}",
                transport="websockets",
                protocol=mqtt.MQTTv31,  # Use MQTTv31 (not v311) to match mqttv3.1
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
            )

            # Set callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            # Build cookie header from session cookies
            cookie_header = "; ".join(
                [f"{key}={value}" for key, value in self._session_cookies.items()]
            )

            # Configure WebSocket with cookies and proper protocol
            self._client.ws_set_options(
                path="/ws",
                headers={
                    "Origin": "https://fireboard.io",
                    "Cookie": cookie_header,
                },
            )

            # Enable TLS for wss://
            self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

            # Connect to FireBoard MQTT broker
            _LOGGER.info("Connecting to FireBoard MQTT broker with cookies...")
            _LOGGER.debug("Cookie header: %s", cookie_header[:50] + "...")
            self._client.connect("fireboard.io", 443, keepalive=60)

            # Start the network loop in a background thread
            self._client.loop_start()

            _LOGGER.info("MQTT client started successfully")

        except Exception as err:
            _LOGGER.error("Failed to connect to MQTT broker: %s", err)
            raise

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self._client:
            _LOGGER.info("Disconnecting from FireBoard MQTT broker...")
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False

    def subscribe_device(self, device_uuid: str, channels: list[int]) -> None:
        """Subscribe to temperature updates for a specific device.

        Args:
            device_uuid: The device UUID to subscribe to
            channels: List of channel numbers to subscribe to

        """
        if not self._client:
            _LOGGER.error("Cannot subscribe: MQTT client not connected")
            return

        # Subscribe to each channel's temperature topic
        # Topic format: {device_uuid}/templog{channel}
        for channel in channels:
            topic = f"{device_uuid}/templog{channel}"
            self._subscribed_topics.add(topic)

            if self._connected:
                result, _ = self._client.subscribe(topic)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    _LOGGER.info(
                        "Subscribed to device %s channel %d", device_uuid, channel
                    )
                else:
                    _LOGGER.error(
                        "Failed to subscribe to device %s channel %d",
                        device_uuid,
                        channel,
                    )
            else:
                _LOGGER.debug(
                    "Device %s channel %d will be subscribed on connection",
                    device_uuid,
                    channel,
                )

        # Also subscribe to drive log if needed
        drive_topic = f"{device_uuid}/drivelog"
        self._subscribed_topics.add(drive_topic)
        if self._connected:
            self._client.subscribe(drive_topic)

    def unsubscribe_device(self, device_uuid: str) -> None:
        """Unsubscribe from a device's updates.

        Args:
            device_uuid: The device UUID to unsubscribe from

        """
        if not self._client:
            return

        # Topics are stored as {device_uuid}/templog{channel} and
        # {device_uuid}/drivelog (see subscribe_device), so match by prefix
        # rather than the wildcard form the broker was never subscribed to.
        prefix = f"{device_uuid}/"
        topics = [t for t in self._subscribed_topics if t.startswith(prefix)]

        for topic in topics:
            self._subscribed_topics.discard(topic)
            if self._connected:
                self._client.unsubscribe(topic)

        if topics:
            _LOGGER.info(
                "Unsubscribed from device %s (%d topics)", device_uuid, len(topics)
            )

    @property
    def is_connected(self) -> bool:
        """Return True if connected to MQTT broker."""
        return self._connected

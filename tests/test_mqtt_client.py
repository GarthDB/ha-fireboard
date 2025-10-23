"""Tests for FireBoard MQTT client."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from custom_components.fireboard.mqtt_client import FireBoardMQTTClient


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    with patch("custom_components.fireboard.mqtt_client.mqtt.Client") as mock:
        yield mock


@pytest.fixture
def callback_mock():
    """Create a callback mock."""
    return Mock()


def test_mqtt_client_initialization(callback_mock):
    """Test MQTT client initialization."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    assert client._auth_token == "test-token"
    assert client._on_message_callback == callback_mock
    assert client._connected is False
    assert len(client._subscribed_topics) == 0


def test_mqtt_connect(mock_mqtt_client, callback_mock):
    """Test MQTT connection."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client.connect()

    # Verify client was created
    mock_mqtt_client.assert_called_once()

    # Verify callbacks were set
    assert mqtt_instance.on_connect is not None
    assert mqtt_instance.on_disconnect is not None
    assert mqtt_instance.on_message is not None

    # Verify WebSocket options were set
    mqtt_instance.ws_set_options.assert_called_once()

    # Verify TLS was enabled
    mqtt_instance.tls_set.assert_called_once()

    # Verify connection was attempted
    mqtt_instance.connect.assert_called_once_with("fireboard.io", 443, keepalive=60)

    # Verify loop was started
    mqtt_instance.loop_start.assert_called_once()


def test_mqtt_disconnect(mock_mqtt_client, callback_mock):
    """Test MQTT disconnection."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client.connect()
    client.disconnect()

    # Verify disconnect was called
    mqtt_instance.loop_stop.assert_called_once()
    mqtt_instance.disconnect.assert_called_once()
    assert client._connected is False


def test_mqtt_on_connect_success(callback_mock):
    """Test successful MQTT connection callback."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    mqtt_client_mock = MagicMock()
    client._on_connect(mqtt_client_mock, None, {}, 0)

    assert client._connected is True


def test_mqtt_on_connect_failure(callback_mock):
    """Test failed MQTT connection callback."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    mqtt_client_mock = MagicMock()
    client._on_connect(mqtt_client_mock, None, {}, 1)

    assert client._connected is False


def test_mqtt_on_disconnect(callback_mock):
    """Test MQTT disconnection callback."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client._connected = True
    mqtt_client_mock = MagicMock()

    client._on_disconnect(mqtt_client_mock, None, 0)

    assert client._connected is False


def test_mqtt_on_message_valid_json(callback_mock):
    """Test handling valid MQTT message."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    # Create mock MQTT message
    msg = MagicMock()
    msg.topic = "fireboard/test-device-uuid/temps"
    msg.payload = b'{"channel_1": 250.5, "channel_2": 195.0}'

    client._on_message(None, None, msg)

    # Verify callback was called with parsed data
    callback_mock.assert_called_once_with(
        "test-device-uuid",
        {"channel_1": 250.5, "channel_2": 195.0},
    )


def test_mqtt_on_message_invalid_json(callback_mock):
    """Test handling invalid MQTT message."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    # Create mock MQTT message with invalid JSON
    msg = MagicMock()
    msg.topic = "fireboard/test-device-uuid/temps"
    msg.payload = b"invalid-json{{"

    client._on_message(None, None, msg)

    # Verify callback was NOT called
    callback_mock.assert_not_called()


def test_subscribe_device(mock_mqtt_client, callback_mock):
    """Test subscribing to device topics."""
    mqtt_instance = MagicMock()
    mqtt_instance.subscribe.return_value = (0, 1)  # MQTT_ERR_SUCCESS
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client.connect()
    client._connected = True  # Simulate successful connection

    device_uuid = "test-device-123"
    client.subscribe_device(device_uuid)

    # Verify subscription
    expected_topic = f"fireboard/{device_uuid}/#"
    mqtt_instance.subscribe.assert_called_once_with(expected_topic)
    assert expected_topic in client._subscribed_topics


def test_subscribe_device_not_connected(mock_mqtt_client, callback_mock):
    """Test subscribing when not connected queues the subscription."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client.connect()
    # Don't set _connected to True

    device_uuid = "test-device-123"
    client.subscribe_device(device_uuid)

    # Topic should be queued but not subscribed yet
    expected_topic = f"fireboard/{device_uuid}/#"
    assert expected_topic in client._subscribed_topics
    mqtt_instance.subscribe.assert_not_called()


def test_unsubscribe_device(mock_mqtt_client, callback_mock):
    """Test unsubscribing from device topics."""
    mqtt_instance = MagicMock()
    mqtt_instance.subscribe.return_value = (0, 1)
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client.connect()
    client._connected = True

    device_uuid = "test-device-123"
    client.subscribe_device(device_uuid)
    client.unsubscribe_device(device_uuid)

    # Verify unsubscription
    expected_topic = f"fireboard/{device_uuid}/#"
    mqtt_instance.unsubscribe.assert_called_once_with(expected_topic)
    assert expected_topic not in client._subscribed_topics


def test_is_connected_property(callback_mock):
    """Test is_connected property."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    assert client.is_connected is False

    client._connected = True
    assert client.is_connected is True

    client._connected = False
    assert client.is_connected is False


def test_mqtt_resubscribe_on_reconnect(mock_mqtt_client, callback_mock):
    """Test that topics are resubscribed after reconnection."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        on_message_callback=callback_mock,
    )

    client.connect()

    # Add some subscribed topics
    client._subscribed_topics.add("fireboard/device-1/#")
    client._subscribed_topics.add("fireboard/device-2/#")

    # Simulate connection callback
    client._on_connect(mqtt_instance, None, {}, 0)

    # Verify both topics were resubscribed
    assert mqtt_instance.subscribe.call_count == 2
    calls = mqtt_instance.subscribe.call_args_list
    assert call("fireboard/device-1/#") in calls
    assert call("fireboard/device-2/#") in calls

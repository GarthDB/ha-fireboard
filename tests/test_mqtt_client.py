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


@pytest.fixture
def session_cookies():
    """Create sample session cookies."""
    return {"sessionid": "test-session", "csrftoken": "test-csrf"}


def test_mqtt_client_initialization(callback_mock, session_cookies):
    """Test MQTT client initialization."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    assert client._auth_token == "test-token"
    assert client._session_cookies == session_cookies
    assert client._on_message_callback == callback_mock
    assert client._connected is False
    assert len(client._subscribed_topics) == 0


def test_mqtt_connect(mock_mqtt_client, callback_mock, session_cookies):
    """Test MQTT connection."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
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


def test_mqtt_disconnect(mock_mqtt_client, callback_mock, session_cookies):
    """Test MQTT disconnection."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    client.connect()
    client.disconnect()

    # Verify disconnect was called
    mqtt_instance.loop_stop.assert_called_once()
    mqtt_instance.disconnect.assert_called_once()
    assert client._connected is False


def test_mqtt_on_connect_success(callback_mock, session_cookies):
    """Test successful MQTT connection callback."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    mqtt_client_mock = MagicMock()
    client._on_connect(mqtt_client_mock, None, {}, 0)

    assert client._connected is True


def test_mqtt_on_connect_failure(callback_mock, session_cookies):
    """Test failed MQTT connection callback."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    mqtt_client_mock = MagicMock()
    client._on_connect(mqtt_client_mock, None, {}, 1)

    assert client._connected is False


def test_mqtt_on_disconnect(callback_mock, session_cookies):
    """Test MQTT disconnection callback."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    client._connected = True
    mqtt_client_mock = MagicMock()

    client._on_disconnect(mqtt_client_mock, None, 0)

    assert client._connected is False


def test_mqtt_on_message_valid_json(callback_mock, session_cookies):
    """Test handling valid MQTT message."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    # Create mock MQTT message. Topic format: {device_uuid}/templog{channel}
    msg = MagicMock()
    msg.topic = "test-device-uuid/templog1"
    msg.payload = b'{"temp": 67, "channel": 1, "p": true}'

    client._on_message(None, None, msg)

    # Verify callback was called with parsed data
    callback_mock.assert_called_once_with(
        "test-device-uuid",
        {"temp": 67, "channel": 1, "p": True},
    )


def test_mqtt_on_message_invalid_topic_format(callback_mock, session_cookies):
    """Test a topic with no '/' is logged and ignored rather than crashing."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    msg = MagicMock()
    msg.topic = "no-slash-in-this-topic"
    msg.payload = b"{}"

    client._on_message(None, None, msg)

    callback_mock.assert_not_called()


def test_mqtt_on_message_invalid_json(callback_mock, session_cookies):
    """Test handling invalid MQTT message."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    # Create mock MQTT message with invalid JSON
    msg = MagicMock()
    msg.topic = "test-device-uuid/templog1"
    msg.payload = b"invalid-json{{"

    client._on_message(None, None, msg)

    # Verify callback was NOT called
    callback_mock.assert_not_called()


def test_subscribe_device(mock_mqtt_client, callback_mock, session_cookies):
    """Test subscribing to device topics."""
    mqtt_instance = MagicMock()
    mqtt_instance.subscribe.return_value = (0, 1)  # MQTT_ERR_SUCCESS
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    client.connect()
    client._connected = True  # Simulate successful connection

    device_uuid = "test-device-123"
    client.subscribe_device(device_uuid, channels=[1, 2])

    # Verify per-channel and drive log subscriptions
    expected_topics = {
        f"{device_uuid}/templog1",
        f"{device_uuid}/templog2",
        f"{device_uuid}/drivelog",
    }
    assert expected_topics == client._subscribed_topics
    subscribed = {c.args[0] for c in mqtt_instance.subscribe.call_args_list}
    assert expected_topics == subscribed


def test_subscribe_device_not_connected(
    mock_mqtt_client, callback_mock, session_cookies
):
    """Test subscribing when not connected queues the subscription."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    client.connect()
    # Don't set _connected to True

    device_uuid = "test-device-123"
    client.subscribe_device(device_uuid, channels=[1])

    # Topics should be queued but not subscribed yet
    assert f"{device_uuid}/templog1" in client._subscribed_topics
    assert f"{device_uuid}/drivelog" in client._subscribed_topics
    mqtt_instance.subscribe.assert_not_called()


def test_unsubscribe_device(mock_mqtt_client, callback_mock, session_cookies):
    """Test unsubscribing from device topics."""
    mqtt_instance = MagicMock()
    mqtt_instance.subscribe.return_value = (0, 1)
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    client.connect()
    client._connected = True

    device_uuid = "test-device-123"
    other_uuid = "other-device-456"
    client.subscribe_device(device_uuid, channels=[1, 2])
    client.subscribe_device(other_uuid, channels=[1])

    client.unsubscribe_device(device_uuid)

    # Verify only the target device's topics were unsubscribed
    unsubscribed = {c.args[0] for c in mqtt_instance.unsubscribe.call_args_list}
    assert unsubscribed == {
        f"{device_uuid}/templog1",
        f"{device_uuid}/templog2",
        f"{device_uuid}/drivelog",
    }
    assert not any(t.startswith(f"{device_uuid}/") for t in client._subscribed_topics)
    # The other device's subscriptions must be left intact
    assert f"{other_uuid}/templog1" in client._subscribed_topics
    assert f"{other_uuid}/drivelog" in client._subscribed_topics


def test_is_connected_property(callback_mock, session_cookies):
    """Test is_connected property."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    assert client.is_connected is False

    client._connected = True
    assert client.is_connected is True

    client._connected = False
    assert client.is_connected is False


def test_mqtt_resubscribe_on_reconnect(
    mock_mqtt_client, callback_mock, session_cookies
):
    """Test that topics are resubscribed after reconnection."""
    mqtt_instance = MagicMock()
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    client.connect()

    # Add some subscribed topics
    client._subscribed_topics.add("device-1/templog1")
    client._subscribed_topics.add("device-2/templog1")

    # Simulate connection callback
    client._on_connect(mqtt_instance, None, {}, 0)

    # Verify both topics were resubscribed
    assert mqtt_instance.subscribe.call_count == 2
    calls = mqtt_instance.subscribe.call_args_list
    assert call("device-1/templog1") in calls
    assert call("device-2/templog1") in calls


def test_subscribe_device_without_connecting_first(callback_mock, session_cookies):
    """Test subscribe_device is a no-op (logged, not raised) before connect()."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    # connect() was never called, so self._client is still None
    client.subscribe_device("test-device-123", channels=[1])

    assert client._subscribed_topics == set()


def test_subscribe_device_logs_broker_failure(
    mock_mqtt_client, callback_mock, session_cookies
):
    """Test a non-success subscribe() return code is logged, not raised."""
    mqtt_instance = MagicMock()
    mqtt_instance.subscribe.return_value = (1, None)  # non-zero = failure
    mock_mqtt_client.return_value = mqtt_instance

    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )
    client.connect()
    client._connected = True

    # Must not raise even though the broker reports failure.
    client.subscribe_device("test-device-123", channels=[1])

    assert "test-device-123/templog1" in client._subscribed_topics


def test_unsubscribe_device_without_connecting_first(callback_mock, session_cookies):
    """Test unsubscribe_device is a no-op before connect()."""
    client = FireBoardMQTTClient(
        auth_token="test-token",
        session_cookies=session_cookies,
        on_message_callback=callback_mock,
    )

    # Must not raise even though self._client is still None
    client.unsubscribe_device("test-device-123")

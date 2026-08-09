"""Tests for FireBoard data update coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator


async def test_coordinator_update_success(
    hass, mock_config_entry_data, mock_device_data, mock_temperature_data
):
    """Test successful coordinator update.

    Patches FireBoardMQTTClient (as imported into coordinator.py's own
    namespace) so async_refresh()'s first-run _async_setup() doesn't open a
    real network connection to fireboard.io.
    """
    config_entry = ConfigEntry(
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
    )

    with (
        patch(
            "custom_components.fireboard.coordinator.FireBoardApiClient"
        ) as mock_client_class,
        patch(
            "custom_components.fireboard.coordinator.FireBoardMQTTClient"
        ) as mock_mqtt_class,
    ):
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.auth_token = "test-token"
        mock_client.session_cookies = {"sessionid": "test-session"}
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client_class.return_value = mock_client
        # FireBoardMQTTClient's own methods (connect, subscribe_device, ...) are
        # synchronous and run via hass.async_add_executor_job, so use MagicMock
        # rather than AsyncMock to match their real (non-coroutine) call signature.
        mock_mqtt_class.return_value = MagicMock()

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)

        # Manually set the client to our mock
        coordinator.client = mock_client

        await coordinator.async_refresh()

        assert coordinator.last_update_success
        assert mock_device_data["uuid"] in coordinator.data
        assert coordinator.data[mock_device_data["uuid"]]["online"] is True


async def test_coordinator_authentication(hass, mock_config_entry_data):
    """Test _async_update_data re-authenticates when no token is cached yet.

    Calls _async_update_data() directly rather than async_refresh(), since
    _async_setup() (invoked by the base class on first refresh) would also
    unconditionally authenticate and mask what this test is checking.
    """
    config_entry = ConfigEntry(
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = None  # No token cached yet
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.get_devices = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator._async_update_data()

        # Verify authenticate was called since auth_token was missing
        mock_client.authenticate.assert_called_once()


async def test_coordinator_rate_limit_error(hass, mock_config_entry_data):
    """Test coordinator surfaces rate limit errors from _async_update_data.

    Note: real HA's DataUpdateCoordinator.async_refresh() catches UpdateFailed
    and turns it into last_update_success=False rather than propagating it, so
    this exercises our own _async_update_data() override directly rather than
    the base class's refresh cycle.
    """
    from homeassistant.config_entries import ConfigEntry

    from custom_components.fireboard.api_client import FireBoardApiClientRateLimitError

    config_entry = ConfigEntry(
        version=1,
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(
            side_effect=FireBoardApiClientRateLimitError("Rate limited")
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_communication_error(hass, mock_config_entry_data):
    """Test coordinator surfaces communication errors from _async_update_data."""
    from homeassistant.config_entries import ConfigEntry

    from custom_components.fireboard.api_client import (
        FireBoardApiClientCommunicationError,
    )

    config_entry = ConfigEntry(
        version=1,
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
        source="user",
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(
            side_effect=FireBoardApiClientCommunicationError("Connection error")
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_async_update_data_populates_temperatures_from_rest(
    hass, mock_config_entry_data, mock_device_data
):
    """Test temperature data is seeded directly from the REST devices.json response.

    Live testing against the real FireBoard API showed devices.json already
    embeds each channel's current_temp/last_templog (docs: "< 60 seconds
    old"), and that the undocumented MQTT push feature can fail outright
    (WebSocket handshake rejected). So _async_update_data must populate
    temperatures from REST on every poll rather than depending on MQTT ever
    having delivered a message -- otherwise sensors never get a value at all
    when MQTT is unavailable.
    """
    device = {
        **mock_device_data,
        "channels": [
            {"channel": 1, "channel_label": "Probe 1"},  # no reading yet
            {
                "channel": 2,
                "channel_label": "Probe 2",
                "current_temp": 137.0,
                "last_templog": {
                    "channel": 2,
                    "temp": 137.0,
                    "created": "2026-08-09T13:15:04Z",
                    "degreetype": 1,
                },
            },
        ],
    }
    config_entry = ConfigEntry(
        domain="fireboard",
        title="Test",
        data=mock_config_entry_data,
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client._token = "test-token"
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[device])
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        result = await coordinator._async_update_data()

        temp_channels = result[device["uuid"]]["temperatures"]["channels"]
        channel_1 = next(c for c in temp_channels if c["channel"] == 1)
        channel_2 = next(c for c in temp_channels if c["channel"] == 2)

        assert channel_1["current_temp"] is None
        assert channel_1["probe_present"] is False
        assert channel_2["current_temp"] == 137.0
        assert channel_2["probe_present"] is True
        assert channel_2["last_update"] == "2026-08-09T13:15:04Z"
        assert result[device["uuid"]]["online"] is True


async def test_async_setup_connects_mqtt_when_credentials_available(
    hass, mock_config_entry_data
):
    """Test _async_setup connects MQTT when credentials are available.

    Authenticates and connects the MQTT client when the API client has both
    an auth token and session cookies available.
    """
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with (
        patch(
            "custom_components.fireboard.coordinator.FireBoardApiClient"
        ) as mock_client_class,
        patch(
            "custom_components.fireboard.coordinator.FireBoardMQTTClient"
        ) as mock_mqtt_class,
    ):
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.auth_token = "test-token"
        mock_client.session_cookies = {"sessionid": "test-session"}
        mock_client_class.return_value = mock_client

        mock_mqtt_instance = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_instance

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator._async_setup()

        mock_client.authenticate.assert_called_once()
        mock_mqtt_class.assert_called_once_with(
            auth_token="test-token",
            session_cookies={"sessionid": "test-session"},
            on_message_callback=coordinator._handle_mqtt_message,
        )
        mock_mqtt_instance.connect.assert_called_once()
        assert coordinator.mqtt_client is mock_mqtt_instance


async def test_async_setup_skips_mqtt_without_credentials(hass, mock_config_entry_data):
    """Test _async_setup leaves mqtt_client unset without credentials.

    There's no auth token or session cookies to connect with in this case.
    """
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.auth_token = None
        mock_client.session_cookies = {}
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator._async_setup()

        assert coordinator.mqtt_client is None


async def test_async_setup_falls_back_to_polling_on_error(hass, mock_config_entry_data):
    """Test _async_setup swallows setup errors instead of failing outright.

    E.g. an auth failure shouldn't fail coordinator setup entirely, since
    REST polling can still work.
    """
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(side_effect=RuntimeError("network down"))
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client
        coordinator.mqtt_client = "sentinel-should-be-cleared"

        await coordinator._async_setup()  # must not raise

        assert coordinator.mqtt_client is None


async def test_handle_mqtt_message_updates_existing_channel(
    hass, mock_config_entry_data, mock_device_data, mock_temperature_data
):
    """Test an MQTT push for a known channel updates that channel in place."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )
    coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
    coordinator.data = {
        mock_device_data["uuid"]: {
            "temperatures": mock_temperature_data,
            "online": False,
        }
    }

    coordinator._handle_mqtt_message(
        mock_device_data["uuid"],
        {"channel": 1, "temp": 300.0, "p": True, "date": "2024-01-01T00:00:00Z"},
    )

    channels = coordinator.data[mock_device_data["uuid"]]["temperatures"]["channels"]
    channel_1 = next(ch for ch in channels if ch["channel"] == 1)
    assert channel_1["current_temp"] == 300.0
    assert channel_1["probe_present"] is True
    assert coordinator.data[mock_device_data["uuid"]]["online"] is True


async def test_handle_mqtt_message_adds_new_channel(
    hass, mock_config_entry_data, mock_device_data
):
    """Test an MQTT push for a device with no temperature data yet creates it."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )
    coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
    coordinator.data = {mock_device_data["uuid"]: {}}

    coordinator._handle_mqtt_message(
        mock_device_data["uuid"],
        {"channel": 5, "temp": 120.0, "p": False, "date": "2024-01-01T00:00:00Z"},
    )

    channels = coordinator.data[mock_device_data["uuid"]]["temperatures"]["channels"]
    assert len(channels) == 1
    assert channels[0]["channel"] == 5
    assert channels[0]["current_temp"] == 120.0
    assert channels[0]["probe_present"] is False


async def test_handle_mqtt_message_ignores_unknown_device(hass, mock_config_entry_data):
    """Test an MQTT push for a device not tracked by the coordinator is a no-op."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )
    coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
    coordinator.data = {"some-other-device": {}}

    # Must not raise even though "unknown-device" isn't in coordinator.data
    coordinator._handle_mqtt_message("unknown-device", {"channel": 1, "temp": 100.0})

    assert "unknown-device" not in coordinator.data


async def test_async_update_data_wraps_unexpected_errors(hass, mock_config_entry_data):
    """Test an unexpected error from get_devices is still wrapped in UpdateFailed.

    A raw, non-FireBoard exception must not propagate as-is.
    """
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(side_effect=RuntimeError("boom"))
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_async_shutdown_disconnects_mqtt_client(hass, mock_config_entry_data):
    """Test async_shutdown disconnects an active MQTT client via the executor."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )
    coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
    coordinator.mqtt_client = MagicMock()

    await coordinator.async_shutdown()

    coordinator.mqtt_client.disconnect.assert_called_once()


async def test_async_shutdown_without_mqtt_client(hass, mock_config_entry_data):
    """Test async_shutdown is a no-op when MQTT was never connected."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )
    coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
    coordinator.mqtt_client = None

    await coordinator.async_shutdown()  # must not raise


async def test_first_refresh_failure_raises_config_entry_not_ready(
    hass, mock_config_entry_data
):
    """Test a failed first update surfaces as ConfigEntryNotReady.

    This is what tells Home Assistant to retry integration setup later
    instead of treating the config entry as permanently broken.
    """
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with (
        patch(
            "custom_components.fireboard.coordinator.FireBoardApiClient"
        ) as mock_client_class,
        patch(
            "custom_components.fireboard.coordinator.FireBoardMQTTClient"
        ) as mock_mqtt_class,
    ):
        mock_client = AsyncMock()
        mock_client.authenticate = AsyncMock(return_value=True)
        mock_client.auth_token = "test-token"
        mock_client.session_cookies = {"sessionid": "test-session"}
        mock_client.get_devices = AsyncMock(side_effect=RuntimeError("boom"))
        mock_client_class.return_value = mock_client
        mock_mqtt_class.return_value = MagicMock()

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        with pytest.raises(ConfigEntryNotReady):
            await coordinator.async_config_entry_first_refresh()


def test_pick_current_session_prefers_ongoing_session():
    """Test an ongoing session (end_time=None) wins over a finished one."""
    sessions = [
        {
            "id": 1,
            "device_ids": ["device-1"],
            "start_time": "2026-08-01T00:00:00Z",
            "end_time": "2026-08-01T05:00:00Z",
        },
        {
            "id": 2,
            "device_ids": ["device-1"],
            "start_time": "2026-08-09T12:00:00Z",
            "end_time": None,
        },
    ]

    result = FireBoardDataUpdateCoordinator._pick_current_session(sessions, "device-1")

    assert result["id"] == 2


def test_pick_current_session_falls_back_to_most_recent_finished():
    """Test the most recently started session wins when none are ongoing."""
    sessions = [
        {
            "id": 1,
            "device_ids": ["device-1"],
            "start_time": "2026-08-01T00:00:00Z",
            "end_time": "2026-08-01T05:00:00Z",
        },
        {
            "id": 2,
            "device_ids": ["device-1"],
            "start_time": "2026-08-05T00:00:00Z",
            "end_time": "2026-08-05T05:00:00Z",
        },
    ]

    result = FireBoardDataUpdateCoordinator._pick_current_session(sessions, "device-1")

    assert result["id"] == 2


def test_pick_current_session_returns_none_without_a_match():
    """Test a device with no matching sessions gets None, not an error."""
    sessions = [{"id": 1, "device_ids": ["some-other-device"], "end_time": None}]

    result = FireBoardDataUpdateCoordinator._pick_current_session(sessions, "device-1")

    assert result is None


async def test_async_update_data_fetches_sessions_on_first_refresh(
    hass, mock_config_entry_data, mock_device_data
):
    """Test the very first refresh always fetches sessions."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_sessions = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "title": "Sun Cook",
                    "device_ids": [mock_device_data["uuid"]],
                    "start_time": "2026-08-09T12:00:00Z",
                    "end_time": None,
                }
            ]
        )
        mock_client.get_session = AsyncMock(return_value={})
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        result = await coordinator._async_update_data()

        mock_client.get_sessions.assert_called_once()
        assert result[mock_device_data["uuid"]]["session"]["id"] == 1


async def test_async_update_data_skips_sessions_between_polls(
    hass, mock_config_entry_data, mock_device_data
):
    """Test sessions are only refetched every SESSION_POLL_EVERY_N_REFRESHES.

    Carries forward the previously known session on the skipped polls rather
    than dropping it, since sessions change far more slowly than temperature.
    """
    from custom_components.fireboard.coordinator import (
        SESSION_POLL_EVERY_N_REFRESHES,
    )

    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )
    known_session = {
        "id": 1,
        "title": "Sun Cook",
        "device_ids": [mock_device_data["uuid"]],
        "start_time": "2026-08-09T12:00:00Z",
        "end_time": None,
    }

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_sessions = AsyncMock(return_value=[known_session])
        mock_client.get_session = AsyncMock(return_value={})
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        assert SESSION_POLL_EVERY_N_REFRESHES > 1, "test assumes throttling is on"

        # First refresh: fetches sessions.
        coordinator.data = await coordinator._async_update_data()
        assert mock_client.get_sessions.call_count == 1

        # Next refresh: should be skipped, but the session must persist.
        coordinator.data = await coordinator._async_update_data()
        assert mock_client.get_sessions.call_count == 1
        assert coordinator.data[mock_device_data["uuid"]]["session"]["id"] == 1


async def test_async_update_data_session_fetch_failure_is_non_fatal(
    hass, mock_config_entry_data, mock_device_data
):
    """Test a rate-limited/failed session fetch doesn't fail the whole update."""
    from custom_components.fireboard.api_client import FireBoardApiClientRateLimitError

    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_sessions = AsyncMock(
            side_effect=FireBoardApiClientRateLimitError("rate limited")
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        result = await coordinator._async_update_data()

        assert mock_device_data["uuid"] in result
        assert result[mock_device_data["uuid"]]["session"] is None


async def test_async_update_data_session_detail_fetch_failure_is_non_fatal(
    hass, mock_config_entry_data, mock_device_data
):
    """Test a failed session *detail* fetch doesn't fail the whole update."""
    from custom_components.fireboard.api_client import FireBoardApiClientRateLimitError

    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_sessions = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "device_ids": [mock_device_data["uuid"]],
                    "start_time": "2026-08-09T12:00:00Z",
                    "end_time": None,
                }
            ]
        )
        mock_client.get_session = AsyncMock(
            side_effect=FireBoardApiClientRateLimitError("rate limited")
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        result = await coordinator._async_update_data()

        assert mock_device_data["uuid"] in result
        assert result[mock_device_data["uuid"]]["session"]["id"] == 1
        assert result[mock_device_data["uuid"]]["drive_status"] is None


def test_extract_drive_status_returns_mode_and_lid_paused():
    """Test drive status is pulled from the matching device's last_drivelog."""
    session_detail = {
        "devices": [
            {
                "uuid": "device-1",
                "last_drivelog": {
                    "modetype": "Auto",
                    "powermode": "Heating",
                    "lidpaused": True,
                },
            }
        ]
    }

    result = FireBoardDataUpdateCoordinator._extract_drive_status(
        session_detail, "device-1"
    )

    assert result == {
        "mode": "Auto",
        "power_mode": "Heating",
        "lid_paused": True,
    }


def test_extract_drive_status_no_matching_device():
    """Test a device not present in session detail yields None, not an error."""
    session_detail = {"devices": [{"uuid": "some-other-device", "last_drivelog": {}}]}

    result = FireBoardDataUpdateCoordinator._extract_drive_status(
        session_detail, "device-1"
    )

    assert result is None


def test_extract_drive_status_device_without_drivelog():
    """Test a matching device with no last_drivelog yields None."""
    session_detail = {"devices": [{"uuid": "device-1", "last_drivelog": None}]}

    result = FireBoardDataUpdateCoordinator._extract_drive_status(
        session_detail, "device-1"
    )

    assert result is None


async def test_async_update_data_fetches_drive_status_via_session_detail(
    hass, mock_config_entry_data, mock_device_data
):
    """Test _async_update_data fetches session detail and populates drive_status."""
    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[mock_device_data])
        mock_client.get_sessions = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "device_ids": [mock_device_data["uuid"]],
                    "start_time": "2026-08-09T12:00:00Z",
                    "end_time": None,
                }
            ]
        )
        mock_client.get_session = AsyncMock(
            return_value={
                "devices": [
                    {
                        "uuid": mock_device_data["uuid"],
                        "last_drivelog": {
                            "modetype": "Off",
                            "powermode": "N/A",
                            "lidpaused": False,
                        },
                    }
                ]
            }
        )
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        result = await coordinator._async_update_data()

        mock_client.get_session.assert_called_once_with(1)
        assert result[mock_device_data["uuid"]]["drive_status"] == {
            "mode": "Off",
            "power_mode": "N/A",
            "lid_paused": False,
        }


async def test_async_update_data_caps_session_detail_fetches_per_refresh(
    hass, mock_config_entry_data
):
    """Test at most one *new* session detail is fetched per refresh cycle.

    With several devices each on a different session, fetching every
    session's detail in the same cycle could burst multiple extra API calls
    at once. Devices whose session isn't reached this cycle should just fall
    back to their previously known drive_status instead.
    """
    device_a = {"uuid": "device-a", "title": "A", "channels": []}
    device_b = {"uuid": "device-b", "title": "B", "channels": []}

    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[device_a, device_b])
        mock_client.get_sessions = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "device_ids": ["device-a"],
                    "start_time": "2026-08-09T12:00:00Z",
                    "end_time": None,
                },
                {
                    "id": 2,
                    "device_ids": ["device-b"],
                    "start_time": "2026-08-09T12:00:00Z",
                    "end_time": None,
                },
            ]
        )
        mock_client.get_session = AsyncMock(return_value={"devices": []})
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator._async_update_data()

        # Two devices, two distinct sessions -- only one detail call allowed.
        assert mock_client.get_session.call_count == 1


async def test_async_update_data_reuses_cached_session_detail_across_devices(
    hass, mock_config_entry_data
):
    """Test devices sharing one session only trigger a single detail fetch."""
    device_a = {"uuid": "device-a", "title": "A", "channels": []}
    device_b = {"uuid": "device-b", "title": "B", "channels": []}

    config_entry = ConfigEntry(
        domain="fireboard", title="Test", data=mock_config_entry_data
    )

    with patch(
        "custom_components.fireboard.coordinator.FireBoardApiClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client.auth_token = "test-token"
        mock_client.get_devices = AsyncMock(return_value=[device_a, device_b])
        mock_client.get_sessions = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "device_ids": ["device-a", "device-b"],
                    "start_time": "2026-08-09T12:00:00Z",
                    "end_time": None,
                }
            ]
        )
        mock_client.get_session = AsyncMock(return_value={"devices": []})
        mock_client_class.return_value = mock_client

        coordinator = FireBoardDataUpdateCoordinator(hass, config_entry)
        coordinator.client = mock_client

        await coordinator._async_update_data()

        mock_client.get_session.assert_called_once_with(1)

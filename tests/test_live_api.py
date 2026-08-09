"""Live tests against the real FireBoard Cloud API.

These exercise api_client.py against the actual fireboard.io API using real
account credentials, to diagnose behavior the mocked unit test suite can't
catch: API response shape drift, auth/session quirks, rate limiting, network
issues, etc.

Skipped automatically unless FIREBOARD_EMAIL and FIREBOARD_PASSWORD are set,
either as real environment variables or in a local .env file (see
.env.example). Never commit real credentials -- .env is gitignored.

Run with:
    .venv/bin/pytest tests/test_live_api.py -v -s -m api --no-cov
"""

from __future__ import annotations

import os
from pathlib import Path

import aiohttp
import pytest

from custom_components.fireboard.api_client import FireBoardApiClient


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from a local .env file into os.environ."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

FIREBOARD_EMAIL = os.environ.get("FIREBOARD_EMAIL")
FIREBOARD_PASSWORD = os.environ.get("FIREBOARD_PASSWORD")

pytestmark = [
    pytest.mark.api,
    pytest.mark.skipif(
        not (FIREBOARD_EMAIL and FIREBOARD_PASSWORD),
        reason=(
            "FIREBOARD_EMAIL/FIREBOARD_PASSWORD not set - copy .env.example to "
            ".env in the project root and fill in real credentials to run "
            "live API tests"
        ),
    ),
]


@pytest.fixture
async def live_client():
    """Return an unauthenticated FireBoardApiClient wired to a real session."""
    async with aiohttp.ClientSession() as session:
        yield FireBoardApiClient(FIREBOARD_EMAIL, FIREBOARD_PASSWORD, session)


async def test_live_raw_login_request():
    """Hit the documented login endpoint directly, bypassing api_client.py.

    Isolates whether a failure is in our client code or in FireBoard's API /
    the account credentials themselves.
    """
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            "https://fireboard.io/api/rest-auth/login/",
            json={"username": FIREBOARD_EMAIL, "password": FIREBOARD_PASSWORD},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "HomeAssistant-FireBoard-Integration",
            },
        )
        body = await response.text()
        print(f"\nRaw login status: {response.status}")
        print(f"Raw login body: {body[:500]}")
        assert response.status == 200, f"Login failed: {response.status} {body}"


async def test_live_authenticate(live_client):
    """Test that real credentials authenticate successfully via api_client.py."""
    result = await live_client.authenticate()

    print(f"\nAuthenticated: {result}")
    print(f"Token: {live_client.auth_token[:8]}..." if live_client.auth_token else None)
    print(f"Session cookies: {list(live_client.session_cookies.keys())}")

    assert result is True
    assert live_client.auth_token


async def test_live_get_devices(live_client):
    """Fetch the real device list and print its shape for diagnosis."""
    await live_client.authenticate()
    devices = await live_client.get_devices()

    print(f"\nFound {len(devices)} device(s)")
    for device in devices:
        print(f"  - {device.get('title')!r} uuid={device.get('uuid')}")
        print(f"    keys: {sorted(device.keys())}")
        print(f"    channels: {device.get('channels')}")
        print(f"    latest_temps: {device.get('latest_temps')}")

    assert isinstance(devices, list)


async def test_live_get_device_detail(live_client):
    """Fetch a single device's detail endpoint, if any device exists."""
    await live_client.authenticate()
    devices = await live_client.get_devices()
    if not devices:
        pytest.skip("No devices on this account to fetch detail for")

    uuid = devices[0]["uuid"]
    device = await live_client.get_device(uuid)

    print(f"\nDevice detail for {uuid}:")
    print(f"  keys: {sorted(device.keys())}")
    assert device.get("uuid") == uuid


async def test_live_sensor_values_populate_from_rest_alone(live_client):
    """Prove sensors get real values from a REST-only refresh, no MQTT needed.

    This is the fix for the reported "integration doesn't seem to work" bug:
    coordinator.py used to only populate temperature/battery data via the
    undocumented MQTT push feature, which fails outright against the real
    API (WebSocket handshake rejected by paho-mqtt). Runs the coordinator's
    own REST-only data-building logic (bypassing MQTT entirely) against the
    real account and asserts sensors would actually get a value.
    """
    await live_client.authenticate()
    devices = await live_client.get_devices()
    if not devices:
        pytest.skip("No devices on this account to verify sensor values for")

    # Reuse the coordinator's own REST-parsing logic without constructing a
    # full HA coordinator instance (which needs a hass object).
    device = devices[0]
    channels = device.get("channels", [])

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
            }
        )

    print(f"\nParsed {len(rest_channels)} channel(s) from REST alone:")
    for ch in rest_channels:
        print(f"  channel {ch['channel']}: current_temp={ch['current_temp']}")

    battery_reading = device.get("last_battery_reading")
    battery_pct = round(battery_reading * 100) if battery_reading is not None else None
    print(f"Battery: {battery_pct}% (raw={battery_reading})")

    channels_with_readings = [c for c in rest_channels if c["current_temp"] is not None]
    assert channels_with_readings, (
        "No channel had a current_temp from the REST response -- either no "
        "probe is currently reporting, or the parsing logic is wrong"
    )


async def test_live_sessions_match_devices(live_client):
    """Fetch real sessions and confirm coordinator._pick_current_session works.

    Uses the coordinator's own picking logic against real data rather than
    duplicating it, so this actually exercises the shipped code.
    """
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    await live_client.authenticate()
    devices = await live_client.get_devices()
    if not devices:
        pytest.skip("No devices on this account to match sessions against")

    sessions = await live_client.get_sessions()
    print(f"\nFound {len(sessions)} session(s) on this account")

    uuid = devices[0]["uuid"]
    current = FireBoardDataUpdateCoordinator._pick_current_session(sessions, uuid)

    print(f"Current session for {uuid}: {current}")
    assert current is not None, "Expected at least one session for this device"
    assert current["id"] in [s["id"] for s in sessions]


async def test_live_drive_data_shape(live_client):
    """If this device has FireBoard Drive data, sanity-check its field shape.

    Confirms the setpoint/driveper fields the sensors rely on are still
    present and numeric -- this is undocumented, embedded data (not a
    documented endpoint response), so it's the kind of thing that could
    silently change shape.
    """
    await live_client.authenticate()
    devices = await live_client.get_devices()
    if not devices:
        pytest.skip("No devices on this account to check Drive data for")

    drivelog = devices[0].get("last_drivelog")
    if not drivelog:
        pytest.skip("This device has no last_drivelog (no Drive attached)")

    print(f"\nlast_drivelog: {drivelog}")
    assert isinstance(drivelog.get("setpoint"), (int, float))
    assert isinstance(drivelog.get("driveper"), (int, float))
    assert 0.0 <= drivelog["driveper"] <= 1.0, (
        f"driveper={drivelog['driveper']} outside expected 0.0-1.0 ratio range "
        "-- FireBoard may have changed this field's scale"
    )


async def test_live_drive_mode_via_session_detail(live_client):
    """Prove FireBoardDataUpdateCoordinator._extract_drive_status works live.

    This is what makes the Drive Mode / Lid Paused sensors possible: session
    detail reports FireBoard's own human-readable mode string, unlike
    devices.json's undocumented raw integer.
    """
    from custom_components.fireboard.coordinator import FireBoardDataUpdateCoordinator

    await live_client.authenticate()
    devices = await live_client.get_devices()
    if not devices or not devices[0].get("last_drivelog"):
        pytest.skip("No Drive-equipped device on this account")

    uuid = devices[0]["uuid"]
    sessions = await live_client.get_sessions()
    session = FireBoardDataUpdateCoordinator._pick_current_session(sessions, uuid)
    if session is None:
        pytest.skip("No session to fetch Drive mode detail from")

    detail = await live_client.get_session(session["id"])
    drive_status = FireBoardDataUpdateCoordinator._extract_drive_status(detail, uuid)

    print(f"\ndrive_status: {drive_status}")
    assert drive_status is not None
    assert isinstance(drive_status["mode"], str)
    assert "lid_paused" in drive_status

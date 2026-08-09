"""Tests for FireBoard API client."""

from __future__ import annotations

from collections import deque
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.fireboard.api_client import (
    FireBoardApiClient,
    FireBoardApiClientAuthenticationError,
    FireBoardApiClientCommunicationError,
    FireBoardApiClientRateLimitError,
)
from custom_components.fireboard.const import (
    API_RATE_LIMIT_MAX_CALLS,
    API_RATE_LIMIT_WINDOW_SECONDS,
)

pytestmark = pytest.mark.asyncio


async def test_authenticate_success():
    """Test successful authentication with session cookies."""
    session = MagicMock(spec=aiohttp.ClientSession)
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={"key": "test-token-12345"})
    response.raise_for_status = MagicMock()

    session.post = AsyncMock(return_value=response)
    session.cookie_jar = MagicMock()

    client = FireBoardApiClient("test@example.com", "password", session)

    result = await client.authenticate()

    assert result is True
    assert client._token == "test-token-12345"
    assert client._cookie_jar is not None
    assert client.auth_token == "test-token-12345"


async def test_authenticate_invalid_credentials():
    """Test authentication with invalid credentials."""
    session = MagicMock(spec=aiohttp.ClientSession)
    response = MagicMock()
    response.status = 401

    session.post = AsyncMock(return_value=response)

    client = FireBoardApiClient("test@example.com", "wrong_password", session)

    with pytest.raises(FireBoardApiClientAuthenticationError):
        await client.authenticate()


async def test_authenticate_rate_limit():
    """Test authentication with rate limit."""
    session = MagicMock(spec=aiohttp.ClientSession)
    response = MagicMock()
    response.status = 429

    session.post = AsyncMock(return_value=response)

    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientRateLimitError):
        await client.authenticate()


@pytest.mark.asyncio
async def test_get_devices():
    """Test getting devices."""
    session = MagicMock(spec=aiohttp.ClientSession)

    # Mock authentication
    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()

    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    # Mock get devices
    devices_response = MagicMock()
    devices_response.status = 200
    devices_response.json = AsyncMock(return_value=[{"uuid": "device-1"}])
    devices_response.raise_for_status = MagicMock()

    session.request = AsyncMock(return_value=devices_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    devices = await client.get_devices()

    assert len(devices) == 1
    assert devices[0]["uuid"] == "device-1"


@pytest.mark.asyncio
async def test_request_without_authentication():
    """Test making a request without being authenticated."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientAuthenticationError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_token_refresh_on_401():
    """Test automatic token refresh when receiving 401."""
    session = MagicMock(spec=aiohttp.ClientSession)

    # Mock initial authentication
    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()

    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    # First request returns 401, second succeeds
    expired_response = MagicMock()
    expired_response.status = 401
    expired_response.raise_for_status = MagicMock()

    success_response = MagicMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value=[])
    success_response.raise_for_status = MagicMock()

    session.request = AsyncMock(side_effect=[expired_response, success_response])

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    # This should trigger re-authentication
    devices = await client.get_devices()

    # Verify authentication was called twice (initial + refresh)
    assert session.post.call_count == 2
    assert isinstance(devices, list)


@pytest.mark.asyncio
async def test_get_device():
    """Test getting a single device by UUID."""
    session = MagicMock(spec=aiohttp.ClientSession)

    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()
    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    device_response = MagicMock()
    device_response.status = 200
    device_response.json = AsyncMock(
        return_value={"uuid": "device-1", "title": "Grill"}
    )
    device_response.raise_for_status = MagicMock()
    session.request = AsyncMock(return_value=device_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    device = await client.get_device("device-1")

    assert device == {"uuid": "device-1", "title": "Grill"}
    called_url = session.request.call_args.args[1]
    assert called_url.endswith("devices/device-1.json")


@pytest.mark.asyncio
async def test_get_sessions():
    """Test getting the account's cook sessions."""
    session = MagicMock(spec=aiohttp.ClientSession)

    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()
    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    sessions_response = MagicMock()
    sessions_response.status = 200
    sessions_response.json = AsyncMock(
        return_value=[{"id": 1, "title": "Sun Cook", "device_ids": ["device-1"]}]
    )
    sessions_response.raise_for_status = MagicMock()
    session.request = AsyncMock(return_value=sessions_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    sessions = await client.get_sessions()

    assert sessions == [{"id": 1, "title": "Sun Cook", "device_ids": ["device-1"]}]
    called_url = session.request.call_args.args[1]
    assert called_url.endswith("sessions.json")


@pytest.mark.asyncio
async def test_get_session():
    """Test getting a single session's detail."""
    session = MagicMock(spec=aiohttp.ClientSession)

    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()
    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    detail_response = MagicMock()
    detail_response.status = 200
    detail_response.json = AsyncMock(
        return_value={"id": 1, "title": "Sun Cook", "devices": []}
    )
    detail_response.raise_for_status = MagicMock()
    session.request = AsyncMock(return_value=detail_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    detail = await client.get_session(1)

    assert detail == {"id": 1, "title": "Sun Cook", "devices": []}
    called_url = session.request.call_args.args[1]
    assert called_url.endswith("sessions/1.json")


async def test_authenticate_no_token_in_response():
    """Test authentication fails cleanly when the response has no token."""
    session = MagicMock(spec=aiohttp.ClientSession)
    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={})
    response.raise_for_status = MagicMock()

    session.post = AsyncMock(return_value=response)

    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientAuthenticationError):
        await client.authenticate()


async def test_authenticate_communication_error():
    """Test network errors during authentication surface as a communication error."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post = AsyncMock(side_effect=aiohttp.ClientError("boom"))

    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientCommunicationError):
        await client.authenticate()


async def test_authenticate_timeout():
    """Test a timed-out authentication request surfaces as a communication error."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.post = AsyncMock(side_effect=TimeoutError())

    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientCommunicationError):
        await client.authenticate()


@pytest.mark.asyncio
async def test_request_rate_limited_mid_session():
    """Test a 429 on a normal (already-authenticated) request raises rate limit."""
    session = MagicMock(spec=aiohttp.ClientSession)

    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()
    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    limited_response = MagicMock()
    limited_response.status = 429
    session.request = AsyncMock(return_value=limited_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    with pytest.raises(FireBoardApiClientRateLimitError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_request_communication_error():
    """Test network errors during a request surface as a communication error."""
    session = MagicMock(spec=aiohttp.ClientSession)

    auth_response = MagicMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"key": "test-token"})
    auth_response.raise_for_status = MagicMock()
    session.post = AsyncMock(return_value=auth_response)
    session.cookie_jar = MagicMock()

    session.request = AsyncMock(side_effect=aiohttp.ClientError("boom"))

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()

    with pytest.raises(FireBoardApiClientCommunicationError):
        await client.get_devices()


async def test_session_cookies_property_builds_dict_from_cookie_jar():
    """Test session_cookies exposes the cookie jar as a plain key/value dict."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = FireBoardApiClient("test@example.com", "password", session)

    class FakeCookie:
        def __init__(self, key, value):
            self.key = key
            self.value = value

    client._cookie_jar = [
        FakeCookie("sessionid", "abc123"),
        FakeCookie("csrftoken", "xyz789"),
    ]

    assert client.session_cookies == {"sessionid": "abc123", "csrftoken": "xyz789"}


async def test_session_cookies_property_empty_before_authentication():
    """Test session_cookies and auth_token default to empty/None pre-auth."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = FireBoardApiClient("test@example.com", "password", session)

    assert client.auth_token is None
    assert client.session_cookies == {}


async def test_local_rate_limit_blocks_before_hitting_the_network():
    """Test the client-side sliding window rejects a call over the limit.

    Rejects the call that would exceed FireBoard's documented rate limit,
    without needing a server 429 response.
    """
    session = MagicMock(spec=aiohttp.ClientSession)
    client = FireBoardApiClient("test@example.com", "password", session)

    for _ in range(API_RATE_LIMIT_MAX_CALLS):
        client._enforce_rate_limit()

    with pytest.raises(FireBoardApiClientRateLimitError):
        client._enforce_rate_limit()


async def test_local_rate_limit_recovers_once_window_elapses():
    """Test old calls fall out of the sliding window, freeing up capacity."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = FireBoardApiClient("test@example.com", "password", session)

    # Backdate every recorded call past the window so none of them count.
    for _ in range(API_RATE_LIMIT_MAX_CALLS):
        client._enforce_rate_limit()
    client._call_timestamps = deque(
        ts - API_RATE_LIMIT_WINDOW_SECONDS - 1 for ts in client._call_timestamps
    )

    # Should not raise: the backdated calls have all expired.
    client._enforce_rate_limit()

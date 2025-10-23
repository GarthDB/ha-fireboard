"""Tests for FireBoard API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.fireboard.api_client import (
    FireBoardApiClient,
    FireBoardApiClientAuthenticationError,
    FireBoardApiClientCommunicationError,
    FireBoardApiClientRateLimitError,
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

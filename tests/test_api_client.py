"""Tests for FireBoard API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from custom_components.fireboard.api_client import (
    FireBoardApiClient,
    FireBoardApiClientAuthenticationError,
    FireBoardApiClientCommunicationError,
    FireBoardApiClientRateLimitError,
)


@pytest.mark.asyncio
async def test_authenticate_success():
    """Test successful authentication."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"auth_token": "test-token"})
    session.post = AsyncMock(return_value=response)

    client = FireBoardApiClient("test@example.com", "password", session)

    result = await client.authenticate()

    assert result is True
    assert client._token == "test-token"


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials():
    """Test authentication with invalid credentials."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    response = AsyncMock()
    response.status = 401
    session.post = AsyncMock(return_value=response)

    client = FireBoardApiClient("test@example.com", "wrong_password", session)

    with pytest.raises(FireBoardApiClientAuthenticationError):
        await client.authenticate()


@pytest.mark.asyncio
async def test_authenticate_rate_limit():
    """Test authentication with rate limit."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    response = AsyncMock()
    response.status = 429
    session.post = AsyncMock(return_value=response)

    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientRateLimitError):
        await client.authenticate()


@pytest.mark.asyncio
async def test_get_devices():
    """Test getting devices."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    
    # Mock authentication
    auth_response = AsyncMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"auth_token": "test-token"})
    
    # Mock get devices
    devices_response = AsyncMock()
    devices_response.status = 200
    devices_response.json = AsyncMock(return_value=[{"uuid": "device-1"}])
    devices_response.raise_for_status = AsyncMock()
    
    session.post = AsyncMock(return_value=auth_response)
    session.request = AsyncMock(return_value=devices_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()
    
    devices = await client.get_devices()

    assert len(devices) == 1
    assert devices[0]["uuid"] == "device-1"


@pytest.mark.asyncio
async def test_get_temperatures():
    """Test getting temperatures for a device."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    
    # Mock authentication
    auth_response = AsyncMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"auth_token": "test-token"})
    
    # Mock get temperatures
    temp_response = AsyncMock()
    temp_response.status = 200
    temp_response.json = AsyncMock(
        return_value={"channels": [{"channel": 1, "current_temp": 225.0}]}
    )
    temp_response.raise_for_status = AsyncMock()
    
    session.post = AsyncMock(return_value=auth_response)
    session.request = AsyncMock(return_value=temp_response)

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()
    
    temps = await client.get_temperatures("device-uuid")

    assert "channels" in temps
    assert len(temps["channels"]) == 1
    assert temps["channels"][0]["current_temp"] == 225.0


@pytest.mark.asyncio
async def test_request_without_authentication():
    """Test making a request without being authenticated."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    client = FireBoardApiClient("test@example.com", "password", session)

    with pytest.raises(FireBoardApiClientAuthenticationError):
        await client.get_devices()


@pytest.mark.asyncio
async def test_token_refresh_on_401():
    """Test automatic token refresh when receiving 401."""
    session = AsyncMock(spec=aiohttp.ClientSession)
    
    # Mock initial authentication
    auth_response = AsyncMock()
    auth_response.status = 200
    auth_response.json = AsyncMock(return_value={"auth_token": "test-token"})
    
    # First request returns 401, second succeeds
    expired_response = AsyncMock()
    expired_response.status = 401
    
    success_response = AsyncMock()
    success_response.status = 200
    success_response.json = AsyncMock(return_value=[])
    success_response.raise_for_status = AsyncMock()
    
    session.post = AsyncMock(return_value=auth_response)
    session.request = AsyncMock(side_effect=[expired_response, success_response])

    client = FireBoardApiClient("test@example.com", "password", session)
    await client.authenticate()
    
    # This should trigger re-authentication
    devices = await client.get_devices()

    # Verify authentication was called twice (initial + refresh)
    assert session.post.call_count == 2
    assert isinstance(devices, list)


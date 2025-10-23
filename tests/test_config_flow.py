"""Tests for FireBoard config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType

from custom_components.fireboard.config_flow import (
    CannotConnect,
    InvalidAuth,
    RateLimitExceeded,
)
from custom_components.fireboard.const import CONF_POLLING_INTERVAL, DOMAIN


async def test_form(hass):
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result.get("errors") in (None, {})


async def test_user_success(hass, mock_config_entry_data):
    """Test successful user config."""
    with patch(
        "custom_components.fireboard.config_flow.FireBoardApiClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(return_value=True)
        mock_instance.get_devices = AsyncMock(return_value=[{"uuid": "device-1"}])
        mock_client.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=mock_config_entry_data,
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == f"FireBoard ({mock_config_entry_data[CONF_EMAIL]})"
        assert result["data"] == mock_config_entry_data


async def test_user_invalid_auth(hass, mock_config_entry_data):
    """Test invalid authentication."""
    with patch(
        "custom_components.fireboard.config_flow.FireBoardApiClient"
    ) as mock_client:
        from custom_components.fireboard.api_client import (
            FireBoardApiClientAuthenticationError,
        )

        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(
            side_effect=FireBoardApiClientAuthenticationError("Invalid credentials")
        )
        mock_client.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=mock_config_entry_data,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_user_cannot_connect(hass, mock_config_entry_data):
    """Test connection error."""
    with patch(
        "custom_components.fireboard.config_flow.FireBoardApiClient"
    ) as mock_client:
        from custom_components.fireboard.api_client import (
            FireBoardApiClientCommunicationError,
        )

        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(
            side_effect=FireBoardApiClientCommunicationError("Cannot connect")
        )
        mock_client.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=mock_config_entry_data,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_rate_limit(hass, mock_config_entry_data):
    """Test rate limit error."""
    with patch(
        "custom_components.fireboard.config_flow.FireBoardApiClient"
    ) as mock_client:
        from custom_components.fireboard.api_client import FireBoardApiClientRateLimitError

        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(
            side_effect=FireBoardApiClientRateLimitError("Rate limited")
        )
        mock_client.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=mock_config_entry_data,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "rate_limit"}


async def test_user_already_configured(hass, mock_config_entry_data):
    """Test we handle already configured."""
    # Create an existing entry
    entry = ConfigEntry(
        domain=DOMAIN,
        title=f"FireBoard ({mock_config_entry_data[CONF_EMAIL]})",
        data=mock_config_entry_data,
        unique_id=mock_config_entry_data[CONF_EMAIL].lower(),
    )
    # Mock that the entry exists
    hass.config_entries.async_entries = lambda domain: [entry] if domain == DOMAIN else []

    with patch(
        "custom_components.fireboard.config_flow.FireBoardApiClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.authenticate = AsyncMock(return_value=True)
        mock_instance.get_devices = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=mock_config_entry_data,
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"


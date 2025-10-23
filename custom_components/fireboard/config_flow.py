"""Config flow for FireBoard integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import (
    FireBoardApiClient,
    FireBoardApiClientAuthenticationError,
    FireBoardApiClientCommunicationError,
    FireBoardApiClientRateLimitError,
)
from .const import (
    CONF_POLLING_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DOMAIN,
    MAX_POLLING_INTERVAL,
    MIN_POLLING_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_POLLING_INTERVAL, default=DEFAULT_POLLING_INTERVAL): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_POLLING_INTERVAL, max=MAX_POLLING_INTERVAL),
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FireBoard."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()
        self._devices = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            devices = await self._test_connection(user_input)
            self._devices = devices
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except RateLimitExceeded:
            errors["base"] = "rate_limit"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        if not errors:
            # Use email as the unique ID to prevent duplicate accounts
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()

            # Create a title showing the account email
            title = f"FireBoard ({user_input[CONF_EMAIL]})"

            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def _test_connection(
        self, user_input: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Test connection to the FireBoard API.

        Args:
            user_input: User input from config flow

        Returns:
            List of devices from the API

        Raises:
            CannotConnect: If connection fails
            InvalidAuth: If authentication fails
            RateLimitExceeded: If rate limited

        """
        session = async_get_clientsession(self.hass)

        client = FireBoardApiClient(
            email=user_input[CONF_EMAIL],
            password=user_input[CONF_PASSWORD],
            session=session,
        )

        try:
            # Try to authenticate
            await client.authenticate()

            # Try to fetch devices to verify API access
            devices = await client.get_devices()

            _LOGGER.debug("Successfully connected to FireBoard API")
            _LOGGER.debug("Found %d devices", len(devices))

            return devices

        except FireBoardApiClientAuthenticationError as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise InvalidAuth from err
        except FireBoardApiClientRateLimitError as err:
            _LOGGER.error("Rate limit exceeded: %s", err)
            raise RateLimitExceeded from err
        except FireBoardApiClientCommunicationError as err:
            _LOGGER.error("Communication error: %s", err)
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.error("Unexpected error during connection test: %s", err)
            raise CannotConnect from err


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class RateLimitExceeded(HomeAssistantError):
    """Error to indicate rate limit was exceeded."""

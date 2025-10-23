"""FireBoard API client."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class FireBoardApiClientError(Exception):
    """Base exception for FireBoard API errors."""


class FireBoardApiClientAuthenticationError(FireBoardApiClientError):
    """Exception for authentication errors."""


class FireBoardApiClientCommunicationError(FireBoardApiClientError):
    """Exception for communication errors."""


class FireBoardApiClientRateLimitError(FireBoardApiClientError):
    """Exception for rate limit errors."""


class FireBoardApiClient:
    """FireBoard API client."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client.

        Args:
            email: FireBoard account email
            password: FireBoard account password
            session: aiohttp client session

        """
        self._email = email
        self._password = password
        self._session = session
        self._token: str | None = None
        self._base_url = API_BASE_URL

    async def authenticate(self) -> bool:
        """Authenticate with the FireBoard API.

        Returns:
            True if authentication was successful

        Raises:
            FireBoardApiClientAuthenticationError: If authentication fails
            FireBoardApiClientCommunicationError: If communication fails

        """
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self._session.post(
                    f"{self._base_url}/login",
                    json={
                        "email": self._email,
                        "password": self._password,
                    },
                )

                if response.status == 401:
                    raise FireBoardApiClientAuthenticationError(
                        "Invalid email or password"
                    )

                if response.status == 429:
                    raise FireBoardApiClientRateLimitError(
                        "Rate limit exceeded. Please wait before trying again."
                    )

                response.raise_for_status()
                data = await response.json()

                # Store the authentication token
                self._token = data.get("auth_token") or data.get("token")

                if not self._token:
                    raise FireBoardApiClientAuthenticationError(
                        "No authentication token returned"
                    )

                _LOGGER.debug("Successfully authenticated with FireBoard API")
                return True

        except aiohttp.ClientError as err:
            raise FireBoardApiClientCommunicationError(
                f"Error communicating with API: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise FireBoardApiClientCommunicationError(
                "Timeout communicating with API"
            ) from err

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to the request

        Returns:
            API response as dictionary

        Raises:
            FireBoardApiClientAuthenticationError: If not authenticated
            FireBoardApiClientRateLimitError: If rate limited
            FireBoardApiClientCommunicationError: If communication fails

        """
        if not self._token:
            raise FireBoardApiClientAuthenticationError("Not authenticated")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Token {self._token}"

        try:
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self._session.request(
                    method,
                    f"{self._base_url}/{endpoint}",
                    headers=headers,
                    **kwargs,
                )

                if response.status == 401:
                    # Token expired, try to re-authenticate
                    _LOGGER.debug("Token expired, re-authenticating...")
                    await self.authenticate()
                    # Retry the request with new token
                    headers["Authorization"] = f"Token {self._token}"
                    response = await self._session.request(
                        method,
                        f"{self._base_url}/{endpoint}",
                        headers=headers,
                        **kwargs,
                    )

                if response.status == 429:
                    raise FireBoardApiClientRateLimitError(
                        "Rate limit exceeded. Please increase polling interval."
                    )

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as err:
            raise FireBoardApiClientCommunicationError(
                f"Error communicating with API: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            raise FireBoardApiClientCommunicationError(
                "Timeout communicating with API"
            ) from err

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get all devices for the authenticated account.

        Returns:
            List of device dictionaries

        Raises:
            FireBoardApiClientError: If request fails

        """
        data = await self._request("GET", "devices")
        return data if isinstance(data, list) else []

    async def get_device(self, device_uuid: str) -> dict[str, Any]:
        """Get a specific device by UUID.

        Args:
            device_uuid: Device UUID

        Returns:
            Device dictionary

        Raises:
            FireBoardApiClientError: If request fails

        """
        return await self._request("GET", f"devices/{device_uuid}")

    async def get_temperatures(self, device_uuid: str) -> dict[str, Any]:
        """Get current temperatures for a device.

        Args:
            device_uuid: Device UUID

        Returns:
            Temperature data dictionary

        Raises:
            FireBoardApiClientError: If request fails

        """
        return await self._request("GET", f"devices/{device_uuid}/temps")

    async def get_sessions(
        self, device_uuid: str | None = None
    ) -> list[dict[str, Any]]:
        """Get sessions for the account or a specific device.

        Args:
            device_uuid: Optional device UUID to filter sessions

        Returns:
            List of session dictionaries

        Raises:
            FireBoardApiClientError: If request fails

        """
        endpoint = "sessions"
        if device_uuid:
            endpoint = f"devices/{device_uuid}/sessions"

        data = await self._request("GET", endpoint)
        return data if isinstance(data, list) else []


"""FireBoard API client with session cookie support."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_RATE_LIMIT_MAX_CALLS,
    API_RATE_LIMIT_WINDOW_SECONDS,
    API_TIMEOUT,
)

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
    """FireBoard API client with session cookie support."""

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
        self._cookie_jar: aiohttp.CookieJar | None = None
        self._csrf_token: str | None = None
        self._call_timestamps: deque[float] = deque()

    def _enforce_rate_limit(self) -> None:
        """Guard against exceeding FireBoard's documented API rate limit.

        FireBoard allows at most API_RATE_LIMIT_MAX_CALLS calls within any
        API_RATE_LIMIT_WINDOW_SECONDS window and locks out clients that
        exceed it, so we track our own call history and refuse to make a
        request that would push us over the limit rather than relying on
        the server to reject it.

        Raises:
            FireBoardApiClientRateLimitError: If making another call now
                would exceed the documented rate limit.

        """
        now = time.monotonic()
        window_start = now - API_RATE_LIMIT_WINDOW_SECONDS

        while self._call_timestamps and self._call_timestamps[0] < window_start:
            self._call_timestamps.popleft()

        if len(self._call_timestamps) >= API_RATE_LIMIT_MAX_CALLS:
            retry_after = self._call_timestamps[0] + API_RATE_LIMIT_WINDOW_SECONDS - now
            raise FireBoardApiClientRateLimitError(
                "Local rate limit reached "
                f"({API_RATE_LIMIT_MAX_CALLS} calls per "
                f"{API_RATE_LIMIT_WINDOW_SECONDS}s); "
                f"retry in {retry_after:.0f}s"
            )

        self._call_timestamps.append(now)

    async def authenticate(self) -> bool:
        """Authenticate with the FireBoard API and capture session cookies.

        Returns:
            True if authentication was successful

        Raises:
            FireBoardApiClientAuthenticationError: If authentication fails
            FireBoardApiClientCommunicationError: If communication fails

        """
        self._enforce_rate_limit()
        try:
            async with asyncio.timeout(API_TIMEOUT):
                # Auth endpoint is at /api/rest-auth/login/ (not /api/v1/)
                auth_url = self._base_url.replace("/v1", "") + "/rest-auth/login/"
                response = await self._session.post(
                    auth_url,
                    json={
                        "username": self._email,
                        "password": self._password,
                    },
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "HomeAssistant-FireBoard-Integration",
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

                # Store the authentication token for MQTT
                self._token = (
                    data.get("key") or data.get("auth_token") or data.get("token")
                )

                if not self._token:
                    raise FireBoardApiClientAuthenticationError(
                        "No authentication token returned"
                    )

                # Store the cookie jar for subsequent requests
                self._cookie_jar = self._session.cookie_jar

                # Extract CSRF token from cookies
                for cookie in self._cookie_jar:
                    if cookie.key == "csrftoken":
                        self._csrf_token = cookie.value
                        break

                # Debug: Check what cookies we have
                cookies = [
                    f"{cookie.key}={cookie.value}" for cookie in self._cookie_jar
                ]
                _LOGGER.debug(
                    "Successfully authenticated with FireBoard API. "
                    "Cookies: %s, CSRF: %s",
                    ", ".join(cookies) if cookies else "None",
                    self._csrf_token,
                )
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
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an authenticated API request with session cookies.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments to pass to the request

        Returns:
            API response as dictionary or list

        Raises:
            FireBoardApiClientAuthenticationError: If not authenticated
            FireBoardApiClientCommunicationError: If communication fails

        """
        if not self._token or not self._cookie_jar:
            raise FireBoardApiClientAuthenticationError("Not authenticated")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Token {self._token}"
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "HomeAssistant-FireBoard-Integration"
        headers["Referer"] = "https://fireboard.io/"
        headers["Origin"] = "https://fireboard.io"

        # Include CSRF token if we have it
        if self._csrf_token:
            headers["X-CSRFToken"] = self._csrf_token

        self._enforce_rate_limit()
        try:
            async with asyncio.timeout(API_TIMEOUT):
                url = f"{self._base_url}/{endpoint}"
                _LOGGER.debug(
                    "Making %s request to %s with %d cookies",
                    method,
                    url,
                    len(list(self._cookie_jar)),
                )
                response = await self._session.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs,
                )

                if response.status == 401:
                    # Token expired, try to re-authenticate
                    _LOGGER.debug("Token expired, re-authenticating...")
                    await self.authenticate()
                    # Retry the request with new token and CSRF
                    headers["Authorization"] = f"Token {self._token}"
                    if self._csrf_token:
                        headers["X-CSRFToken"] = self._csrf_token
                    self._enforce_rate_limit()
                    response = await self._session.request(
                        method,
                        url,
                        headers=headers,
                        **kwargs,
                    )

                if response.status == 429:
                    raise FireBoardApiClientRateLimitError("Rate limit exceeded")

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
            List of device dictionaries with channels and configuration

        Raises:
            FireBoardApiClientError: If request fails

        """
        data = await self._request("GET", "devices.json")
        return data if isinstance(data, list) else []

    async def get_device(self, device_uuid: str) -> dict[str, Any]:
        """Get a specific device by UUID.

        Args:
            device_uuid: Device UUID

        Returns:
            Device dictionary with current data

        Raises:
            FireBoardApiClientError: If request fails

        """
        result = await self._request("GET", f"devices/{device_uuid}.json")
        return result if isinstance(result, dict) else {}

    async def get_sessions(self) -> list[dict[str, Any]]:
        """Get all cook sessions for the authenticated account.

        Returns:
            List of session dictionaries, each including a "device_ids" list
            linking it to the devices it was recorded on. An ongoing session
            has "end_time" set to None.

        Raises:
            FireBoardApiClientError: If request fails

        """
        data = await self._request("GET", "sessions.json")
        return data if isinstance(data, list) else []

    async def get_session(self, session_id: int) -> dict[str, Any]:
        """Get detail for a single cook session.

        Unlike get_sessions(), this embeds each tied device's full current
        state, including a "last_drivelog" with human-readable "modetype"/
        "powermode" strings (sessions.json's device_ids-only entries and
        devices.json's embedded last_drivelog report these as raw,
        undocumented integers instead).

        Args:
            session_id: Session ID

        Returns:
            Session dictionary with an embedded "devices" list

        Raises:
            FireBoardApiClientError: If request fails

        """
        result = await self._request("GET", f"sessions/{session_id}.json")
        return result if isinstance(result, dict) else {}

    @property
    def auth_token(self) -> str | None:
        """Return the authentication token for MQTT connection."""
        return self._token

    @property
    def session_cookies(self) -> dict[str, str]:
        """Return session cookies for MQTT WebSocket connection."""
        cookies = {}
        if self._cookie_jar:
            for cookie in self._cookie_jar:
                cookies[cookie.key] = cookie.value
        return cookies

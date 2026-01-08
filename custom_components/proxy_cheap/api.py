"""API client for Proxy-Cheap."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_TIMEOUT,
    ENDPOINT_BALANCE,
    ENDPOINT_BUY_BANDWIDTH,
    ENDPOINT_EXTEND,
    ENDPOINT_PROXIES,
    ENDPOINT_PROXY,
    ENDPOINT_WHITELIST,
    ENDPOINT_AUTO_EXTEND_ENABLE,
    ENDPOINT_AUTO_EXTEND_DISABLE,
)

_LOGGER = logging.getLogger(__name__)


class ProxyCheapApiError(Exception):
    """Exception for API errors."""


class ProxyCheapAuthError(ProxyCheapApiError):
    """Exception for authentication errors."""


class ProxyCheapApi:
    """API client for Proxy-Cheap."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._api_secret = api_secret
        self._session = session
        self._close_session = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self._session

    async def close(self) -> None:
        """Close the session if we created it."""
        if self._close_session and self._session:
            await self._session.close()
            self._session = None

    def _get_headers(self) -> dict[str, str]:
        """Get the headers for API requests."""
        return {
            "X-Api-Key": self._api_key,
            "X-Api-Secret": self._api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request."""
        session = await self._get_session()
        url = f"{API_BASE_URL}/{endpoint}"

        try:
            async with asyncio.timeout(API_TIMEOUT):
                if method.upper() == "GET":
                    async with session.get(
                        url,
                        headers=self._get_headers(),
                        params=data,
                    ) as response:
                        return await self._handle_response(response)
                else:
                    async with session.post(
                        url,
                        headers=self._get_headers(),
                        json=data,
                    ) as response:
                        return await self._handle_response(response)
        except asyncio.TimeoutError as err:
            raise ProxyCheapApiError(f"Timeout connecting to API: {err}") from err
        except aiohttp.ClientError as err:
            raise ProxyCheapApiError(f"Error connecting to API: {err}") from err

    async def _handle_response(
        self, response: aiohttp.ClientResponse
    ) -> dict[str, Any]:
        """Handle the API response."""
        if response.status == 401:
            raise ProxyCheapAuthError("Invalid API credentials")
        if response.status == 403:
            raise ProxyCheapAuthError("Access forbidden - check API permissions")
        if response.status >= 400:
            text = await response.text()
            raise ProxyCheapApiError(
                f"API error {response.status}: {text}"
            )

        try:
            return await response.json()
        except Exception as err:
            text = await response.text()
            _LOGGER.error("Failed to parse response: %s", text)
            raise ProxyCheapApiError(f"Failed to parse response: {err}") from err

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance."""
        return await self._request("GET", ENDPOINT_BALANCE)

    async def get_proxies(self) -> list[dict[str, Any]]:
        """Get all proxies."""
        result = await self._request("GET", ENDPOINT_PROXIES)
        # Handle both list and dict responses
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "proxies" in result:
            return result["proxies"]
        if isinstance(result, dict) and "data" in result:
            return result["data"]
        return [result] if result else []

    async def get_proxy(self, proxy_id: int) -> dict[str, Any]:
        """Get details for a specific proxy."""
        endpoint = ENDPOINT_PROXY.format(proxy_id=proxy_id)
        return await self._request("GET", endpoint)

    async def update_whitelist(
        self, proxy_id: int, ips: list[str] | None = None
    ) -> dict[str, Any]:
        """Update whitelisted IPs for a proxy."""
        endpoint = ENDPOINT_WHITELIST.format(proxy_id=proxy_id)
        params = {"ips": ",".join(ips)} if ips else None
        return await self._request("GET", endpoint, params)

    async def extend_proxy(self, proxy_id: int, months: int) -> dict[str, Any]:
        """Extend a proxy's period."""
        endpoint = ENDPOINT_EXTEND.format(proxy_id=proxy_id)
        return await self._request("GET", endpoint, {"months": months})

    async def buy_bandwidth(self, proxy_id: int, amount_gb: float) -> dict[str, Any]:
        """Buy additional bandwidth for a proxy."""
        endpoint = ENDPOINT_BUY_BANDWIDTH.format(proxy_id=proxy_id)
        return await self._request("GET", endpoint, {"amount": amount_gb})

    async def set_auto_extend(
        self, proxy_id: int, enabled: bool
    ) -> dict[str, Any]:
        """Enable or disable auto-extend for a proxy."""
        if enabled:
            endpoint = ENDPOINT_AUTO_EXTEND_ENABLE.format(proxy_id=proxy_id)
        else:
            endpoint = ENDPOINT_AUTO_EXTEND_DISABLE.format(proxy_id=proxy_id)
        return await self._request("POST", endpoint)

    async def validate_credentials(self) -> bool:
        """Validate API credentials by fetching balance."""
        try:
            await self.get_balance()
            return True
        except ProxyCheapAuthError:
            return False
        except ProxyCheapApiError as err:
            _LOGGER.warning("API error during validation: %s", err)
            return False

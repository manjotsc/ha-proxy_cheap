"""DataUpdateCoordinator for Proxy-Cheap."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ProxyCheapApi, ProxyCheapApiError
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ProxyCheapCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from Proxy-Cheap API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ProxyCheapApi,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        proxy_names: dict[int, str] | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.proxy_names = proxy_names or {}

    def set_proxy_names(self, proxy_names: dict[int, str]) -> None:
        """Update the proxy names mapping."""
        self.proxy_names = proxy_names

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        try:
            # Fetch balance and proxies concurrently
            balance_data = await self.api.get_balance()
            proxies_data = await self.api.get_proxies()

            # Debug log the raw API response
            _LOGGER.debug("Raw balance data: %s", balance_data)
            _LOGGER.debug("Raw proxies data: %s", proxies_data)

            # Process proxies into a more usable format
            proxies = {}
            for proxy in proxies_data:
                _LOGGER.debug("Raw proxy object keys: %s", list(proxy.keys()))
                _LOGGER.debug("Raw proxy object: %s", proxy)
                proxy_id = proxy.get("id") or proxy.get("proxy_id")
                if proxy_id:
                    proxies[proxy_id] = self._normalize_proxy_data(proxy)

            return {
                "balance": balance_data.get("balance", 0),
                "currency": balance_data.get("currency", "USD"),
                "proxies": proxies,
                "proxy_count": len(proxies),
            }
        except ProxyCheapApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _normalize_proxy_data(self, proxy: dict[str, Any]) -> dict[str, Any]:
        """Normalize proxy data to a consistent format."""
        # Extract nested objects
        connection = proxy.get("connection", {}) or {}
        authentication = proxy.get("authentication", {}) or {}
        bandwidth = proxy.get("bandwidth", {}) or {}
        metadata = proxy.get("metadata", {}) or {}

        # Determine the port based on proxy type
        proxy_type = proxy.get("proxyType", "").upper()
        if proxy_type == "HTTP":
            port = connection.get("httpPort")
        elif proxy_type == "HTTPS":
            port = connection.get("httpsPort")
        elif proxy_type == "SOCKS5":
            port = connection.get("socks5Port")
        else:
            # Try to find any available port
            port = (
                connection.get("httpPort")
                or connection.get("httpsPort")
                or connection.get("socks5Port")
            )

        # Get bandwidth values
        bandwidth_total = bandwidth.get("total")
        bandwidth_used = bandwidth.get("used")

        # Calculate bandwidth remaining
        # If total is None (unlimited), remaining is also unlimited (None)
        # If total exists, calculate remaining (treat null used as 0)
        bandwidth_remaining = None
        if bandwidth_total is not None:
            used_for_calc = bandwidth_used if bandwidth_used is not None else 0
            bandwidth_remaining = bandwidth_total - used_for_calc

        # Track if bandwidth is unlimited
        bandwidth_unlimited = bandwidth_total is None

        # Normalize status to lowercase
        raw_status = proxy.get("status", "unknown")
        status = raw_status.lower() if isinstance(raw_status, str) else "unknown"

        # Get custom name - first check local config, then API fields
        proxy_id = proxy.get("id")
        custom_name = (
            self.proxy_names.get(proxy_id)
            or self.proxy_names.get(str(proxy_id))
            or proxy.get("name")
            or proxy.get("label")
            or proxy.get("alias")
            or proxy.get("displayName")
            or metadata.get("name")
            or metadata.get("label")
        )

        return {
            "id": proxy.get("id"),
            "name": custom_name,
            "ip_address": (
                connection.get("publicIp")
                or connection.get("connectIp")
            ),
            "port": port,
            "username": authentication.get("username"),
            "protocol": proxy.get("proxyType"),
            "network_type": proxy.get("networkType"),
            "country": proxy.get("countryCode"),
            "region": proxy.get("region"),
            "city": proxy.get("city"),
            "bandwidth_total": bandwidth_total,
            "bandwidth_used": bandwidth_used,
            "bandwidth_remaining": bandwidth_remaining,
            "bandwidth_unlimited": bandwidth_unlimited,
            "expiry_date": proxy.get("expiresAt"),
            "auto_extend_enabled": proxy.get("autoExtendEnabled"),
            "authentication_type": (
                "IP_WHITELIST" if authentication.get("whitelistedIps")
                else "USERNAME_PASSWORD" if authentication.get("username")
                else None
            ),
            "whitelisted_ips": authentication.get("whitelistedIps", []),
            "status": status,
            "created_at": proxy.get("createdAt"),
            "ip_version": connection.get("ipVersion"),
            "connect_ip": connection.get("connectIp"),
            "http_port": connection.get("httpPort"),
            "https_port": connection.get("httpsPort"),
            "socks5_port": connection.get("socks5Port"),
            "isp_name": metadata.get("ispName"),
            "order_id": metadata.get("orderId"),
            "routes": proxy.get("routes", []),
            # Keep the raw data for debugging (filtered)
            "_raw": self._filter_sensitive_data(proxy),
        }

    def _filter_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove sensitive data like passwords from the raw data."""
        filtered = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively filter nested dicts
                filtered[key] = {
                    k: v for k, v in value.items()
                    if "password" not in k.lower() and "secret" not in k.lower()
                }
            elif "password" not in key.lower() and "secret" not in key.lower():
                filtered[key] = value
        return filtered

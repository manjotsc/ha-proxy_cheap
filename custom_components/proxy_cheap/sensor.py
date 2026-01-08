"""Sensor platform for Proxy-Cheap integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS
from .coordinator import ProxyCheapCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse a datetime string into a datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Try ISO format first (e.g., "2026-12-24T12:53:31+00:00")
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            _LOGGER.warning("Unable to parse datetime: %s", value)
            return None
    return None


@dataclass(frozen=True, kw_only=True)
class ProxyCheapSensorEntityDescription(SensorEntityDescription):
    """Describes a Proxy-Cheap sensor entity."""

    value_fn: callable = lambda x: x
    enabled_default: bool = True


# Account-level sensors
ACCOUNT_SENSORS: tuple[ProxyCheapSensorEntityDescription, ...] = (
    ProxyCheapSensorEntityDescription(
        key="balance",
        translation_key="balance",
        name="Account Balance",
        icon="mdi:wallet",
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="USD",
        value_fn=lambda data: data.get("balance"),
    ),
    ProxyCheapSensorEntityDescription(
        key="proxy_count",
        translation_key="proxy_count",
        name="Total Proxies",
        icon="mdi:server-network",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("proxy_count", 0),
    ),
)


# Per-proxy sensors
# Sensors with enabled_default=False are disabled by default to reduce clutter with many proxies
PROXY_SENSORS: tuple[ProxyCheapSensorEntityDescription, ...] = (
    ProxyCheapSensorEntityDescription(
        key="status",
        translation_key="proxy_status",
        name="Status",
        icon="mdi:check-circle",
        value_fn=lambda proxy: proxy.get("status", "unknown"),
        enabled_default=True,
    ),
    ProxyCheapSensorEntityDescription(
        key="ip_address",
        translation_key="proxy_ip",
        name="IP Address",
        icon="mdi:ip-network",
        value_fn=lambda proxy: proxy.get("ip_address"),
        enabled_default=True,
    ),
    ProxyCheapSensorEntityDescription(
        key="port",
        translation_key="proxy_port",
        name="Port",
        icon="mdi:ethernet",
        value_fn=lambda proxy: proxy.get("port"),
        enabled_default=True,
    ),
    ProxyCheapSensorEntityDescription(
        key="username",
        translation_key="proxy_username",
        name="Username",
        icon="mdi:account",
        value_fn=lambda proxy: proxy.get("username"),
        enabled_default=False,  # Less commonly needed
    ),
    ProxyCheapSensorEntityDescription(
        key="protocol",
        translation_key="proxy_protocol",
        name="Protocol",
        icon="mdi:protocol",
        value_fn=lambda proxy: proxy.get("protocol"),
        enabled_default=False,  # Usually static
    ),
    ProxyCheapSensorEntityDescription(
        key="network_type",
        translation_key="proxy_network_type",
        name="Network Type",
        icon="mdi:access-point-network",
        value_fn=lambda proxy: proxy.get("network_type"),
        enabled_default=False,  # Usually static
    ),
    ProxyCheapSensorEntityDescription(
        key="country",
        translation_key="proxy_country",
        name="Country",
        icon="mdi:earth",
        value_fn=lambda proxy: proxy.get("country"),
        enabled_default=False,  # Usually static
    ),
    ProxyCheapSensorEntityDescription(
        key="bandwidth_total",
        translation_key="proxy_bandwidth_total",
        name="Bandwidth Total",
        icon="mdi:chart-donut",
        value_fn=lambda proxy: (
            "Unlimited" if proxy.get("bandwidth_unlimited")
            else f"{proxy.get('bandwidth_total'):.2f} GB" if proxy.get("bandwidth_total") is not None
            else None
        ),
        enabled_default=False,  # Often unlimited/static
    ),
    ProxyCheapSensorEntityDescription(
        key="bandwidth_used",
        translation_key="proxy_bandwidth_used",
        name="Bandwidth Used",
        icon="mdi:chart-donut-variant",
        value_fn=lambda proxy: (
            f"{proxy.get('bandwidth_used'):.2f} GB" if proxy.get("bandwidth_used") is not None
            else "0 GB"
        ),
        enabled_default=False,  # Enable if tracking usage
    ),
    ProxyCheapSensorEntityDescription(
        key="bandwidth_remaining",
        translation_key="proxy_bandwidth_remaining",
        name="Bandwidth Remaining",
        icon="mdi:gauge",
        value_fn=lambda proxy: (
            "Unlimited" if proxy.get("bandwidth_unlimited")
            else f"{proxy.get('bandwidth_remaining'):.2f} GB" if proxy.get("bandwidth_remaining") is not None
            else None
        ),
        enabled_default=True,  # Important for monitoring
    ),
    ProxyCheapSensorEntityDescription(
        key="expiry_date",
        translation_key="proxy_expiry",
        name="Expiry Date",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda proxy: _parse_datetime(proxy.get("expiry_date")),
        enabled_default=True,  # Important for monitoring
    ),
    ProxyCheapSensorEntityDescription(
        key="auto_extend",
        translation_key="proxy_auto_extend",
        name="Auto Extend",
        icon="mdi:autorenew",
        value_fn=lambda proxy: "Enabled" if proxy.get("auto_extend_enabled") else "Disabled",
        enabled_default=False,  # Usually static
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxy-Cheap sensors from a config entry."""
    coordinator: ProxyCheapCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Add account-level sensors
    for description in ACCOUNT_SENSORS:
        entities.append(ProxyCheapAccountSensor(coordinator, description, entry))

    # Add sensors for each proxy
    if coordinator.data and "proxies" in coordinator.data:
        for proxy_id, proxy_data in coordinator.data["proxies"].items():
            for description in PROXY_SENSORS:
                entities.append(
                    ProxyCheapProxySensor(
                        coordinator, description, entry, proxy_id, proxy_data
                    )
                )

    async_add_entities(entities)

    # Set up listener for new proxies
    @callback
    def async_check_new_proxies() -> None:
        """Check for new proxies and add sensors for them."""
        if not coordinator.data or "proxies" not in coordinator.data:
            return

        current_proxies = set(coordinator.data["proxies"].keys())
        known_proxies = getattr(coordinator, "_known_proxies", set())

        new_proxies = current_proxies - known_proxies
        if new_proxies:
            new_entities = []
            for proxy_id in new_proxies:
                proxy_data = coordinator.data["proxies"][proxy_id]
                for description in PROXY_SENSORS:
                    new_entities.append(
                        ProxyCheapProxySensor(
                            coordinator, description, entry, proxy_id, proxy_data
                        )
                    )
            if new_entities:
                async_add_entities(new_entities)

        coordinator._known_proxies = current_proxies

    coordinator._known_proxies = set(
        coordinator.data.get("proxies", {}).keys() if coordinator.data else []
    )
    coordinator.async_add_listener(async_check_new_proxies)


class ProxyCheapAccountSensor(CoordinatorEntity[ProxyCheapCoordinator], SensorEntity):
    """Sensor for account-level data."""

    entity_description: ProxyCheapSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxyCheapCoordinator,
        description: ProxyCheapSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Proxy-Cheap Account",
            manufacturer="Proxy-Cheap",
            model="API",
            entry_type="service",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class ProxyCheapProxySensor(CoordinatorEntity[ProxyCheapCoordinator], SensorEntity):
    """Sensor for individual proxy data."""

    entity_description: ProxyCheapSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxyCheapCoordinator,
        description: ProxyCheapSensorEntityDescription,
        entry: ConfigEntry,
        proxy_id: int | str,
        proxy_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._proxy_id = proxy_id
        self._entry_id = entry.entry_id

        # Set enabled by default based on options or fallback to description default
        enabled_sensors = entry.options.get(CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS)
        self._attr_entity_registry_enabled_default = description.key in enabled_sensors

        # Create a friendly name based on proxy location/type
        proxy_name = self._get_proxy_name(proxy_data)

        self._attr_unique_id = f"{entry.entry_id}_proxy_{proxy_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_proxy_{proxy_id}")},
            name=f"Proxy {proxy_name}",
            manufacturer="Proxy-Cheap",
            model=proxy_data.get("network_type", "Proxy"),
            via_device=(DOMAIN, entry.entry_id),
        )

    def _get_proxy_name(self, proxy_data: dict[str, Any]) -> str:
        """Generate a friendly name for the proxy."""
        # Use custom name if available
        if proxy_data.get("name"):
            return proxy_data["name"]

        # Fall back to country + network type
        parts = []
        if proxy_data.get("country"):
            parts.append(proxy_data["country"])
        if proxy_data.get("network_type"):
            parts.append(proxy_data["network_type"])
        if not parts:
            parts.append(str(self._proxy_id))
        return " ".join(parts)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        proxies = self.coordinator.data.get("proxies", {})
        proxy = proxies.get(self._proxy_id)
        if proxy is None:
            return None
        return self.entity_description.value_fn(proxy)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if self.coordinator.data is None:
            return {}

        proxies = self.coordinator.data.get("proxies", {})
        proxy = proxies.get(self._proxy_id)
        if proxy is None:
            return {}

        # All proxy sensors should have proxy_id for service calls
        base_attrs = {"proxy_id": self._proxy_id}

        # Only add detailed attributes to the status sensor to avoid duplication
        if self.entity_description.key != "status":
            return base_attrs

        attrs = {
            "proxy_id": self._proxy_id,
        }

        # Add whitelisted IPs if available
        if proxy.get("whitelisted_ips"):
            attrs["whitelisted_ips"] = proxy["whitelisted_ips"]

        # Add region if available
        if proxy.get("region"):
            attrs["region"] = proxy["region"]

        # Add city if available
        if proxy.get("city"):
            attrs["city"] = proxy["city"]

        # Add IP version if available
        if proxy.get("ip_version"):
            attrs["ip_version"] = proxy["ip_version"]

        # Add authentication type if available
        if proxy.get("authentication_type"):
            attrs["authentication_type"] = proxy["authentication_type"]

        # Add created date if available
        if proxy.get("created_at"):
            attrs["created_at"] = proxy["created_at"]

        # Add raw API data for debugging (exclude sensitive data)
        raw_data = proxy.get("_raw", {})
        if raw_data:
            # Include all raw field names for debugging
            attrs["raw_api_fields"] = list(raw_data.keys())
            # Include raw data (but filter out password fields)
            for key, value in raw_data.items():
                if "password" not in key.lower() and "secret" not in key.lower():
                    # Also filter nested dicts for passwords
                    if isinstance(value, dict):
                        filtered_value = {
                            k: v for k, v in value.items()
                            if "password" not in k.lower() and "secret" not in k.lower()
                        }
                        attrs[f"raw_{key}"] = filtered_value
                    else:
                        attrs[f"raw_{key}"] = value

        return attrs

"""Binary sensor platform for Proxy-Cheap integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATUS_ACTIVE, CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS
from .coordinator import ProxyCheapCoordinator


@dataclass(frozen=True, kw_only=True)
class ProxyCheapBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Proxy-Cheap binary sensor entity."""

    is_on_fn: callable = lambda x: False
    enabled_default: bool = True


PROXY_BINARY_SENSORS: tuple[ProxyCheapBinarySensorEntityDescription, ...] = (
    ProxyCheapBinarySensorEntityDescription(
        key="active",
        translation_key="proxy_active",
        name="Active",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda proxy: str(proxy.get("status", "")).lower() == STATUS_ACTIVE,
        enabled_default=True,  # Important for monitoring
    ),
    ProxyCheapBinarySensorEntityDescription(
        key="auto_extend_enabled",
        translation_key="proxy_auto_extend_enabled",
        name="Auto Extend Enabled",
        icon="mdi:autorenew",
        is_on_fn=lambda proxy: bool(proxy.get("auto_extend_enabled")),
        enabled_default=False,  # Usually static
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Proxy-Cheap binary sensors from a config entry."""
    coordinator: ProxyCheapCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Add binary sensors for each proxy
    if coordinator.data and "proxies" in coordinator.data:
        for proxy_id, proxy_data in coordinator.data["proxies"].items():
            for description in PROXY_BINARY_SENSORS:
                entities.append(
                    ProxyCheapProxyBinarySensor(
                        coordinator, description, entry, proxy_id, proxy_data
                    )
                )

    async_add_entities(entities)

    # Set up listener for new proxies
    @callback
    def async_check_new_proxies() -> None:
        """Check for new proxies and add binary sensors for them."""
        if not coordinator.data or "proxies" not in coordinator.data:
            return

        current_proxies = set(coordinator.data["proxies"].keys())
        known_proxies = getattr(coordinator, "_known_binary_proxies", set())

        new_proxies = current_proxies - known_proxies
        if new_proxies:
            new_entities = []
            for proxy_id in new_proxies:
                proxy_data = coordinator.data["proxies"][proxy_id]
                for description in PROXY_BINARY_SENSORS:
                    new_entities.append(
                        ProxyCheapProxyBinarySensor(
                            coordinator, description, entry, proxy_id, proxy_data
                        )
                    )
            if new_entities:
                async_add_entities(new_entities)

        coordinator._known_binary_proxies = current_proxies

    coordinator._known_binary_proxies = set(
        coordinator.data.get("proxies", {}).keys() if coordinator.data else []
    )
    coordinator.async_add_listener(async_check_new_proxies)


class ProxyCheapProxyBinarySensor(
    CoordinatorEntity[ProxyCheapCoordinator], BinarySensorEntity
):
    """Binary sensor for individual proxy data."""

    entity_description: ProxyCheapBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ProxyCheapCoordinator,
        description: ProxyCheapBinarySensorEntityDescription,
        entry: ConfigEntry,
        proxy_id: int | str,
        proxy_data: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._proxy_id = proxy_id
        self._entry_id = entry.entry_id

        # Set enabled by default based on options or fallback to description default
        enabled_sensors = entry.options.get(CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS)
        self._attr_entity_registry_enabled_default = description.key in enabled_sensors

        # Create a friendly name based on proxy location/type
        proxy_name = self._get_proxy_name(proxy_data)

        self._attr_unique_id = (
            f"{entry.entry_id}_proxy_{proxy_id}_{description.key}_binary"
        )
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
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        if self.coordinator.data is None:
            return None
        proxies = self.coordinator.data.get("proxies", {})
        proxy = proxies.get(self._proxy_id)
        if proxy is None:
            return None
        return self.entity_description.is_on_fn(proxy)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {"proxy_id": self._proxy_id}

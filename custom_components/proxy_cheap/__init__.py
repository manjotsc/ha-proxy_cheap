"""The Proxy-Cheap integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ProxyCheapApi, ProxyCheapApiError
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_PROXY_NAMES,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import ProxyCheapCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Proxy-Cheap from a config entry."""
    session = async_get_clientsession(hass)

    api = ProxyCheapApi(
        api_key=entry.data[CONF_API_KEY],
        api_secret=entry.data[CONF_API_SECRET],
        session=session,
    )

    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    proxy_names = entry.options.get(CONF_PROXY_NAMES, {})

    # Convert string keys to int if needed
    proxy_names_int = {}
    for k, v in proxy_names.items():
        try:
            proxy_names_int[int(k)] = v
        except (ValueError, TypeError):
            proxy_names_int[k] = v

    coordinator = ProxyCheapCoordinator(hass, api, scan_interval, proxy_names_int)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_setup_services(hass, entry, api, coordinator)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - update entity registry and reload."""
    from homeassistant.helpers import entity_registry as er
    from .const import CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS

    # Get enabled sensors from options
    enabled_sensors = entry.options.get(CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS)

    # Update entity registry to enable/disable entities
    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)

    for entity in entities:
        # Skip account-level sensors (balance, proxy_count)
        if "_proxy_" not in entity.unique_id:
            continue

        # Determine the sensor key from the unique_id
        # Format: {entry_id}_proxy_{proxy_id}_{key} or {entry_id}_proxy_{proxy_id}_{key}_binary
        # Get everything after _proxy_
        after_proxy = entity.unique_id.split("_proxy_", 1)[1]
        # Split by _ to get [proxy_id, key_parts..., maybe "binary"]
        parts = after_proxy.split("_")
        # First part is proxy_id, rest is sensor key (possibly with _binary at end)
        if parts[-1] == "binary":
            sensor_key = "_".join(parts[1:-1])
        else:
            sensor_key = "_".join(parts[1:])

        # Check if this sensor should be enabled
        should_enable = sensor_key in enabled_sensors

        # Update the entity's disabled state
        if entity.disabled and should_enable:
            ent_reg.async_update_entity(entity.entity_id, disabled_by=None)
        elif not entity.disabled and not should_enable:
            ent_reg.async_update_entity(
                entity.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
            )

    # Reload the integration
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_setup_services(
    hass: HomeAssistant,
    entry: ConfigEntry,
    api: ProxyCheapApi,
    coordinator: ProxyCheapCoordinator,
) -> None:
    """Set up services for Proxy-Cheap."""

    def _get_proxy_id_from_entity(entity_id: str) -> int:
        """Extract proxy_id from an entity's attributes."""
        state = hass.states.get(entity_id)
        if state is None:
            raise HomeAssistantError(f"Entity {entity_id} not found")

        # Try to get proxy_id from attributes
        proxy_id = state.attributes.get("proxy_id")
        if proxy_id is None:
            # Try to get from raw data
            proxy_id = state.attributes.get("raw_id")
        if proxy_id is None:
            raise HomeAssistantError(
                f"Could not find proxy_id for entity {entity_id}. "
                "Please select a proxy status sensor."
            )
        return int(proxy_id)

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle the refresh service call."""
        await coordinator.async_request_refresh()

    async def handle_extend_proxy(call: ServiceCall) -> None:
        """Handle the extend proxy service call."""
        entity_id = call.data["entity_id"]
        proxy_id = _get_proxy_id_from_entity(entity_id)
        months = call.data["months"]
        try:
            await api.extend_proxy(proxy_id, months)
            await coordinator.async_request_refresh()
        except ProxyCheapApiError as err:
            _LOGGER.error("Failed to extend proxy %s: %s", proxy_id, err)
            raise HomeAssistantError(f"Failed to extend proxy: {err}") from err

    async def handle_update_whitelist(call: ServiceCall) -> None:
        """Handle the update whitelist service call."""
        entity_id = call.data["entity_id"]
        proxy_id = _get_proxy_id_from_entity(entity_id)
        ips_input = call.data.get("ips", "")
        # Parse comma-separated IPs
        if isinstance(ips_input, str):
            ips = [ip.strip() for ip in ips_input.split(",") if ip.strip()]
        else:
            ips = ips_input or []
        try:
            await api.update_whitelist(proxy_id, ips)
            await coordinator.async_request_refresh()
        except ProxyCheapApiError as err:
            _LOGGER.error("Failed to update whitelist for proxy %s: %s", proxy_id, err)
            raise HomeAssistantError(f"Failed to update whitelist: {err}") from err

    async def handle_set_auto_extend(call: ServiceCall) -> None:
        """Handle the set auto extend service call."""
        entity_id = call.data["entity_id"]
        proxy_id = _get_proxy_id_from_entity(entity_id)
        enabled = call.data["enabled"]
        try:
            await api.set_auto_extend(proxy_id, enabled)
            await coordinator.async_request_refresh()
        except ProxyCheapApiError as err:
            _LOGGER.error("Failed to set auto extend for proxy %s: %s", proxy_id, err)
            raise HomeAssistantError(f"Failed to set auto extend: {err}") from err

    # Register all services
    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    hass.services.async_register(DOMAIN, "extend_proxy", handle_extend_proxy)
    hass.services.async_register(DOMAIN, "update_whitelist", handle_update_whitelist)
    hass.services.async_register(DOMAIN, "set_auto_extend", handle_set_auto_extend)

"""Config flow for Proxy-Cheap integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ProxyCheapApi, ProxyCheapAuthError, ProxyCheapApiError
from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_PROXY_NAMES,
    CONF_ENABLED_SENSORS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_ENABLED_SENSORS,
    SENSOR_KEYS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_API_SECRET): str,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): vol.All(vol.Coerce(int), vol.Range(min=60, max=3600)),
    }
)


class ProxyCheapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Proxy-Cheap."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ProxyCheapOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_API_KEY])
            self._abort_if_unique_id_configured()

            # Validate credentials
            session = async_get_clientsession(self.hass)
            api = ProxyCheapApi(
                api_key=user_input[CONF_API_KEY],
                api_secret=user_input[CONF_API_SECRET],
                session=session,
            )

            try:
                valid = await api.validate_credentials()
                if not valid:
                    errors["base"] = "invalid_auth"
            except ProxyCheapAuthError:
                errors["base"] = "invalid_auth"
            except ProxyCheapApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title="Proxy-Cheap",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class ProxyCheapOptionsFlow(OptionsFlow):
    """Handle options flow for Proxy-Cheap."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            # Parse proxy names from the text input
            proxy_names = {}
            names_input = user_input.get(CONF_PROXY_NAMES, "")
            if names_input:
                for line in names_input.strip().split("\n"):
                    line = line.strip()
                    if "=" in line:
                        proxy_id, name = line.split("=", 1)
                        proxy_id = proxy_id.strip()
                        name = name.strip()
                        if proxy_id and name:
                            try:
                                proxy_names[int(proxy_id)] = name
                            except ValueError:
                                proxy_names[proxy_id] = name

            # Get enabled sensors
            enabled_sensors = user_input.get(CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS)

            return self.async_create_entry(
                title="",
                data={
                    CONF_PROXY_NAMES: proxy_names,
                    CONF_ENABLED_SENSORS: enabled_sensors,
                },
            )

        # Get current values
        current_names = self.config_entry.options.get(CONF_PROXY_NAMES, {})
        current_sensors = self.config_entry.options.get(CONF_ENABLED_SENSORS, DEFAULT_ENABLED_SENSORS)

        # Format names as text for editing
        names_text = "\n".join(
            f"{proxy_id}={name}" for proxy_id, name in current_names.items()
        )

        # Get available proxies from coordinator if possible
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        description = "Enter proxy names (one per line, format: proxy_id=name)"
        if coordinator and coordinator.data:
            proxies = coordinator.data.get("proxies", {})
            if proxies:
                proxy_list = ", ".join(str(pid) for pid in proxies.keys())
                description = f"Available proxy IDs: {proxy_list}\n\nEnter names (one per line, format: proxy_id=name)"

        from homeassistant.helpers.selector import (
            SelectSelector,
            SelectSelectorConfig,
            SelectSelectorMode,
            SelectOptionDict,
            TextSelector,
            TextSelectorConfig,
            TextSelectorType,
        )

        # Create sensor options with friendly names
        sensor_options = [
            SelectOptionDict(value="status", label="Status"),
            SelectOptionDict(value="ip_address", label="IP Address"),
            SelectOptionDict(value="port", label="Port"),
            SelectOptionDict(value="username", label="Username"),
            SelectOptionDict(value="protocol", label="Protocol"),
            SelectOptionDict(value="network_type", label="Network Type"),
            SelectOptionDict(value="country", label="Country"),
            SelectOptionDict(value="bandwidth_total", label="Bandwidth Total"),
            SelectOptionDict(value="bandwidth_used", label="Bandwidth Used"),
            SelectOptionDict(value="bandwidth_remaining", label="Bandwidth Remaining"),
            SelectOptionDict(value="expiry_date", label="Expiry Date"),
            SelectOptionDict(value="auto_extend", label="Auto Extend (text)"),
            SelectOptionDict(value="active", label="Active (binary)"),
            SelectOptionDict(value="auto_extend_enabled", label="Auto Extend Enabled (binary)"),
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLED_SENSORS,
                        default=current_sensors,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=sensor_options,
                            multiple=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional(
                        CONF_PROXY_NAMES,
                        default=names_text,
                    ): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                }
            ),
            description_placeholders={"proxy_ids": description},
        )

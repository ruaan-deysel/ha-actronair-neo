"""Config flow for Actron Neo integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .actron_api import ActronNeoAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)

STEP_ZONE_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("zones_as_heater_coolers", default=False): bool,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = ActronNeoAPI(
        username=data["username"],
        password=data["password"],
        client_name="homeassistant-actron-neo",
        device_serial="",
        storage_path=hass.config.path(".storage")
    )

    try:
        await api.actron_que_api()
    except Exception as err:
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    return {"title": f"Actron Neo ({api.device_serial})", "device_serial": api.device_serial}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Actron Neo."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.api_info = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self.api_info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self.async_step_zone_config()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_zone_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the zone configuration step."""
        if user_input is not None:
            return self.async_create_entry(title=self.api_info["title"], data={
                "username": self.api_info["username"],
                "password": self.api_info["password"],
                "client_name": "homeassistant-actron-neo",
                "device_serial": self.api_info["device_serial"],
                "zones_as_heater_coolers": user_input["zones_as_heater_coolers"]
            })

        return self.async_show_form(
            step_id="zone_config", data_schema=STEP_ZONE_CONFIG_SCHEMA
        )

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    class OptionsFlowHandler(config_entries.OptionsFlow):
        def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
            """Initialize options flow."""
            self.config_entry = config_entry

        async def async_step_init(
            self, user_input: dict[str, Any] | None = None
        ) -> FlowResult:
            """Manage the options."""
            if user_input is not None:
                return self.async_create_entry(title="", data=user_input)

            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "zones_as_heater_coolers",
                            default=self.config_entry.options.get("zones_as_heater_coolers", False),
                        ): bool,
                    }
                ),
            )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
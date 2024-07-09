"""Config flow for Actron Air Neo integration."""

from __future__ import annotations
from typing import Any, Dict, Optional
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ActronNeoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Actron Neo integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate the input
                await self._test_credentials(user_input["username"], user_input["password"])
                return self.async_create_entry(title="Actron Neo", data=user_input)
            except Exception as e:
                errors["base"] = "auth"

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Optional("zones", default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_credentials(self, username: str, password: str):
        """Test the credentials provided by the user."""
        from .api import ActronNeoAPI

        api = ActronNeoAPI(username, password)
        await api.login()
        if not api._token:
            raise Exception("Invalid credentials")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ActronNeoOptionsFlowHandler(config_entry)

class ActronNeoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Actron Neo integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] = None) -> Dict[str, Any]:
        """Manage the options for the custom component."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = vol.Schema(
            {
                vol.Optional("zones", default=self.config_entry.options.get("zones", "")): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=options)

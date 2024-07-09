"""Config flow for Actron Neo integration."""

from __future__ import annotations
from typing import Final, Dict, Any, Optional
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

class ActronNeoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Actron Neo integration."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH
    data: Optional[Dict[str, Any]]
    
    def __init__(self):
        """Initialize."""
        _LOGGER.debug("%s - ConfigFlowHandler: __init__", DOMAIN)

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        _LOGGER.debug("%s - ConfigFlowHandler: async_step_user: %s", DOMAIN, user_input)
        errors = {}

        if user_input is not None:
            try:
                # Validate the input
                await self._test_credentials(user_input["username"], user_input["password"])
                return self.async_create_entry(
                    title="Actron Neo", data=user_input
                )
            except Exception as e:
                errors["base"] = "auth"

        data_schema = vol.Schema(
            {
                vol.Required("username", description="Enter your Actron Neo username"): str,
                vol.Required("password", description="Enter your Actron Neo password"): str,
                vol.Optional("zones", description="Comma-separated list of zones", default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_credentials(self, username: str, password: str):
        """Test the credentials provided by the user."""
        from .api import ActronNeoAPI

        api = ActronNeoAPI(username, password)
        if not api.login():
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
                vol.Optional("zones", default=self.config_entry.options.get("zones", ""), description="Comma-separated list of zones"): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=options)

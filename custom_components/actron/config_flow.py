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
                # Validate the input and fetch the serial number and zones
                serial_number, zones = await self._test_credentials(user_input["username"], user_input["password"])
                user_input["serial_number"] = serial_number
                user_input["zones"] = zones
                return self.async_create_entry(title=f"Actron Neo {serial_number}", data=user_input)
            except Exception as e:
                _LOGGER.error(f"Authentication failed: {e}")
                errors["base"] = "auth"

        data_schema = vol.Schema(
            {
                vol.Required("username", description={"en": "Email Address"}): str,
                vol.Required("password", description={"en": "Password"}): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_credentials(self, username: str, password: str):
        """Test the credentials provided by the user and fetch the serial number and zones."""
        from .api import ActronNeoAPI

        api = ActronNeoAPI(username, password)
        await api.login()
        if not api._token:
            raise Exception("Invalid credentials")
        return api._serial_number, api._zones

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ActronNeoOptionsFlowHandler(config_entry)

class ActronNeoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Actron Neo integration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for the custom component."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = vol.Schema(
            {
                # Include any options you want to manage here
            }
        )
        return self.async_show_form(step_id="init", data_schema=options)

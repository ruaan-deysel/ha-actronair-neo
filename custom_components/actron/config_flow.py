import logging
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ActronAirNeoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Actron Air Neo."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Implement logic to authenticate with Actron Air Neo
            try:
                valid = await self._test_credentials(user_input["username"], user_input["password"])
                if valid:
                    return self.async_create_entry(title="Actron Air Neo", data=user_input)
                else:
                    errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials are valid."""
        # Implement credential validation
        return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ActronAirNeoOptionsFlowHandler(config_entry)


class ActronAirNeoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Actron Air Neo."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Optional("zones_as_heater_coolers", default=self.config_entry.options.get("zones_as_heater_coolers", False)): bool,
        })

        return self.async_show_form(
            step_id="init", data_schema=data_schema
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

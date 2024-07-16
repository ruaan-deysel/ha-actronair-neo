import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
from .actron_api import ActronAirNeoApi  # Ensure this matches the class name in actron_api.py

class ActronAirNeoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ActronAirNeoOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.api = ActronAirNeoApi(user_input['username'], user_input['password'])
            if await self.api.authenticate():
                return self.async_create_entry(title="Actron Air Neo", data=user_input)
            else:
                errors["base"] = "cannot_connect"

        data_schema = {
            vol.Required("username"): str,
            vol.Required("password"): str,
        }
        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=errors)

class ActronAirNeoOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = {
            vol.Optional("option_key", default=self.config_entry.options.get("option_key", "")): str
        }
        return self.async_show_form(step_id="user", data_schema=vol.Schema(data_schema), errors=errors)

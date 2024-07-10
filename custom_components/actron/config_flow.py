# File: custom_components/actron_air_neo/config_flow.py
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .api import ActronApi
from .const import DOMAIN, API_URL

_LOGGER = logging.getLogger(__name__)

@callback
def configured_instances(hass):
    return [entry.data["username"] for entry in hass.config_entries.async_entries(DOMAIN)]

class ActronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if user_input["username"] in configured_instances(self.hass):
                return self.async_abort(reason="already_configured")
            
            errors = {}
            try:
                # Verify the credentials
                api = ActronApi(
                    username=user_input["username"],
                    password=user_input["password"],
                    device_name=user_input["device_name"],
                    device_id=user_input["device_id"]  # This is the serial number
                )
                api.authenticate()
                return self.async_create_entry(title=user_input["device_name"], data=user_input)
            except Exception as e:
                _LOGGER.error(f"Error authenticating with Actron API: {e}")
                errors["base"] = "cannot_connect"

            return self.async_show_form(
                step_id="user", data_schema=self._get_schema(), errors=errors
            )

        return self.async_show_form(step_id="user", data_schema=self._get_schema())

    def _get_schema(self):
        return vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): str,
            vol.Required("device_name"): str,
            vol.Required("device_id"): str,  # This is the serial number
        })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ActronOptionsFlowHandler(config_entry)

class ActronOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data_schema = vol.Schema({
            vol.Optional("update_interval", default=options.get("update_interval", 60)): int,
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)

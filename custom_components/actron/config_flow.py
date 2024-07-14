import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID
from .api import ActronApi, AuthenticationError
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

class ActronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self.api = None
        self.devices = []

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self.api = ActronApi(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD]
                )
                await self.api.authenticate()
                self.devices = await self.api.get_devices()
                if not self.devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_select_device()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.error("Unexpected error: %s", e)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_select_device(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Actron Air Neo {user_input[CONF_DEVICE_ID]}",
                data={
                    CONF_USERNAME: self.api.username,
                    CONF_PASSWORD: self.api.password,
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID]
                }
            )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In({device['serial']: device['name'] for device in self.devices})
            })
        )

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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "update_interval",
                    default=self.config_entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
                ): int,
            })
        )
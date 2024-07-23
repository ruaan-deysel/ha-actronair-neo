import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_REFRESH_INTERVAL, CONF_SERIAL_NUMBER, API_URL
from .api import ActronApi

_LOGGER = logging.getLogger(__name__)

class ActronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        errors = {}
        
        if user_input is not None:
            # Validate user input
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            refresh_interval = user_input[CONF_REFRESH_INTERVAL]

            session = aiohttp_client.async_get_clientsession(self.hass)
            api = ActronApi(username, password, session=session)

            try:
                await api.authenticate()
                devices = await api.get_devices()
                if not devices:
                    raise Exception("No devices found")
                serial_number = devices[0]['serial']
                return self.async_create_entry(
                    title="ActronNeo",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                        CONF_REFRESH_INTERVAL: refresh_interval,
                        CONF_SERIAL_NUMBER: serial_number
                    },
                )
            except Exception as e:
                _LOGGER.error("Error connecting to Actron API: %s", e)
                errors["base"] = "auth"

        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
            vol.Optional(CONF_REFRESH_INTERVAL, default=60): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ActronOptionsFlowHandler(config_entry)


class ActronOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        data_schema = vol.Schema({
            vol.Optional(CONF_REFRESH_INTERVAL, default=self.config_entry.data.get(CONF_REFRESH_INTERVAL, 60)): int,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
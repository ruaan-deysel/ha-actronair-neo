import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_REFRESH_INTERVAL, CONF_SERIAL_NUMBER
from .api import ActronApi, AuthenticationError, ApiError

_LOGGER = logging.getLogger(__name__)

class ActronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            try:
                return await self.validate_input(user_input)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_REFRESH_INTERVAL, default=60): int,
                }
            ),
            errors=errors,
        )

    async def validate_input(self, user_input: Dict[str, Any]) -> FlowResult:
        """Validate the user input allows us to connect."""
        username = user_input[CONF_USERNAME]
        password = user_input[CONF_PASSWORD]
        refresh_interval = user_input[CONF_REFRESH_INTERVAL]

        session = aiohttp_client.async_get_clientsession(self.hass)
        api = ActronApi(username, password, session=session)

        await api.authenticate()
        devices = await api.get_devices()
        
        if not devices:
            raise ApiError("No devices found")
        
        # For simplicity, we're selecting the first device found
        serial_number = devices[0]['serial']

        return self.async_create_entry(
            title=f"Actron Air Neo ({devices[0]['name']})",
            data={
                CONF_USERNAME: username,
                CONF_PASSWORD: password,
                CONF_REFRESH_INTERVAL: refresh_interval,
                CONF_SERIAL_NUMBER: serial_number
            },
        )

    @staticmethod
    @config_entries.HANDLERS.register("reauth")
    async def async_step_reauth(entry_data: Dict[str, Any]) -> FlowResult:
        """Handle initiation of re-authentication with Actron."""
        return await ActronConfigFlow().async_step_user()

class ActronOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REFRESH_INTERVAL,
                        default=self.config_entry.options.get(CONF_REFRESH_INTERVAL, 60),
                    ): int,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> ActronOptionsFlowHandler:
        return ActronOptionsFlowHandler(config_entry)
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import logging

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .api import ActronApi, AuthenticationError, ApiError

_LOGGER = logging.getLogger(__name__)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                api = ActronApi(user_input["username"], user_input["password"])
                await api.authenticate()
                devices = await api.get_devices()
                
                if not devices:
                    return self.async_abort(reason="no_devices")
                
                if len(devices) == 1:
                    device = devices[0]
                    return self.async_create_entry(
                        title=device["name"],
                        data={
                            "username": user_input["username"],
                            "password": user_input["password"],
                            "device_id": device["serial"],
                        }
                    )
                
                # If there are multiple devices, move to the device selection step
                return await self.async_step_select_device(devices=devices, user_input=user_input)

            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
            }),
            errors=errors,
        )

    async def async_step_select_device(self, devices, user_input=None):
        """Handle the device selection step."""
        if user_input is not None:
            selected_device = next(device for device in devices if device["serial"] == user_input["device_id"])
            return self.async_create_entry(
                title=selected_device["name"],
                data={
                    "username": user_input["username"],
                    "password": user_input["password"],
                    "device_id": user_input["device_id"],
                }
            )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): vol.In({device["serial"]: f"{device['name']} ({device['type']})" for device in devices}),
            })
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
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
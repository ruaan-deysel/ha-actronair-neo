import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .api import ActronApi, AuthenticationError, ApiError

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
                    return self.async_create_entry(
                        title=devices[0]["name"],
                        data={
                            "username": user_input["username"],
                            "password": user_input["password"],
                            "device_id": devices[0]["serial"]
                        }
                    )
                
                # If there are multiple devices, move to the device selection step
                return await self.async_step_select_device(devices=devices, user_input=user_input)

            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
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
            return self.async_create_entry(
                title=next(device["name"] for device in devices if device["serial"] == user_input["device_id"]),
                data={
                    "username": user_input["username"],
                    "password": user_input["password"],
                    "device_id": user_input["device_id"]
                }
            )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema({
                vol.Required("device_id"): vol.In({device["serial"]: device["name"] for device in devices}),
            })
        )
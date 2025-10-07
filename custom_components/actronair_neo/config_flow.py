"""Config flow for ActronAir Neo integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol  # type: ignore

from homeassistant import config_entries  # type: ignore
from homeassistant.core import HomeAssistant, callback  # type: ignore
from homeassistant.data_entry_flow import FlowResult  # type: ignore
from homeassistant.exceptions import HomeAssistantError  # type: ignore
from homeassistant.helpers import aiohttp_client  # type: ignore

from .api import ActronApi, AuthenticationError, ApiError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    CONF_ENABLE_ZONE_CONTROL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL): int,
        vol.Optional(CONF_ENABLE_ZONE_CONTROL, default=False): bool,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = aiohttp_client.async_get_clientsession(hass)
    api = ActronApi(
        username=data[CONF_USERNAME], password=data[CONF_PASSWORD], session=session
    )

    try:
        await api.initializer()
        devices = await api.get_devices()
        if not devices:
            raise CannotConnect("No devices found")

        # Return all devices for selection
        return {
            "devices": devices,
            "username": data[CONF_USERNAME],
            "password": data[CONF_PASSWORD],
            "refresh_interval": data.get(
                CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
            ),
            "enable_zone_control": data.get(CONF_ENABLE_ZONE_CONTROL, False),
        }
    except AuthenticationError as err:
        raise InvalidAuth from err
    except ApiError as err:
        raise CannotConnect from err


class ActronairNeoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ActronAir Neo."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._devices = []
        self._username = None
        self._password = None
        self._refresh_interval = DEFAULT_REFRESH_INTERVAL
        self._enable_zone_control = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self._devices = info["devices"]
                self._username = info["username"]
                self._password = info["password"]
                self._refresh_interval = info["refresh_interval"]
                self._enable_zone_control = info["enable_zone_control"]

                # If only one device is found, skip the selection step
                if len(self._devices) == 1:
                    return self.async_create_entry(
                        title=f"ActronAir Neo ({self._devices[0]['name']})",
                        data={
                            CONF_USERNAME: self._username,
                            CONF_PASSWORD: self._password,
                            CONF_REFRESH_INTERVAL: self._refresh_interval,
                            "serial_number": self._devices[0]["serial"],
                            "system_id": self._devices[0]["id"],
                        },
                        options={
                            CONF_ENABLE_ZONE_CONTROL: self._enable_zone_control,
                        },
                    )

                # If multiple devices are found, proceed to the selection step
                return await self.async_step_select_device()

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the device selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_serial = user_input["device"]
            selected_device = next(
                (
                    device
                    for device in self._devices
                    if device["serial"] == selected_serial
                ),
                None,
            )

            if selected_device:
                return self.async_create_entry(
                    title=f"ActronAir Neo ({selected_device['name']})",
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                        CONF_REFRESH_INTERVAL: self._refresh_interval,
                        "serial_number": selected_device["serial"],
                        "system_id": selected_device["id"],
                    },
                    options={
                        CONF_ENABLE_ZONE_CONTROL: self._enable_zone_control,
                    },
                )
            else:
                errors["base"] = "device_not_found"

        # Create a schema with a dropdown of available devices
        device_schema = vol.Schema(
            {
                vol.Required("device"): vol.In(
                    {
                        device["serial"]: f"{device['name']} ({device['serial']})"
                        for device in self._devices
                    }
                )
            }
        )

        return self.async_show_form(
            step_id="select_device", data_schema=device_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REFRESH_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                        ),
                    ): int,
                    vol.Optional(
                        CONF_ENABLE_ZONE_CONTROL,
                        default=self._config_entry.options.get(
                            CONF_ENABLE_ZONE_CONTROL, False
                        ),
                    ): bool,
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

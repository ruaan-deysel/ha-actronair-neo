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

        # For simplicity, we're selecting the first device found
        return {
            "title": f"ActronAir Neo ({devices[0]['name']})",
            "serial_number": devices[0]["serial"],
        }
    except AuthenticationError as err:
        raise InvalidAuth from err
    except ApiError as err:
        raise CannotConnect from err


class ActronairNeoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ActronAir Neo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_REFRESH_INTERVAL: user_input[CONF_REFRESH_INTERVAL],
                        "serial_number": info["serial_number"],
                    },
                    options={
                        CONF_ENABLE_ZONE_CONTROL: user_input[CONF_ENABLE_ZONE_CONTROL],
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
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

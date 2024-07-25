from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.components.climate.const import HVACMode

from .api import ActronApi, AuthenticationError, ApiError, RateLimitError
from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)

class ActronDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: ActronApi, device_id: str, update_interval: int):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_id = device_id
        _LOGGER.info(f"Initializing ActronDataCoordinator for device {device_id} with update interval {update_interval} seconds")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        _LOGGER.debug(f"Fetching data for device {self.device_id}")
        try:
            status = await self.api.get_ac_status(self.device_id)
            _LOGGER.debug(f"API status response: {status}")
            parsed_data = self._parse_data(status)
            _LOGGER.debug(f"Parsed data: {parsed_data}")
            return parsed_data
        except AuthenticationError as auth_err:
            _LOGGER.error(f"Authentication error for device {self.device_id}: {auth_err}")
            raise ConfigEntryAuthFailed("Authentication failed") from auth_err
        except RateLimitError as rate_err:
            _LOGGER.warning(f"Rate limit exceeded for device {self.device_id}: {rate_err}")
            raise UpdateFailed("Rate limit exceeded") from rate_err
        except ApiError as api_err:
            _LOGGER.error(f"API error for device {self.device_id}: {api_err}")
            raise UpdateFailed("Failed to fetch data from Actron API") from api_err
        except Exception as err:
            _LOGGER.exception(f"Unexpected error occurred for device {self.device_id}: {err}")
            raise UpdateFailed("Unexpected error occurred") from err

    def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the data from the API into a format suitable for the climate entity."""
        _LOGGER.debug(f"Parsing data for device {self.device_id}")
        try:
            user_settings = data.get("UserAirconSettings", {})
            master_info = data.get("MasterInfo", {})

            parsed_data = {
                "main": {
                    "is_on": user_settings.get("isOn", False),
                    "mode": user_settings.get("Mode", "OFF"),
                    "fan_mode": user_settings.get("FanMode", "AUTO"),
                    "temp_setpoint_cool": user_settings.get("TemperatureSetpoint_Cool_oC"),
                    "temp_setpoint_heat": user_settings.get("TemperatureSetpoint_Heat_oC"),
                    "indoor_temp": master_info.get("LiveTemp_oC"),
                    "indoor_humidity": master_info.get("LiveHumidity_pc"),
                }
            }

            _LOGGER.debug(f"Parsed main data for device {self.device_id}: {parsed_data['main']}")

            # Parse zone data if available
            parsed_data["zones"] = {}
            for i, zone in enumerate(data.get("RemoteZoneInfo", [])):
                if zone.get("NV_Exists", False):
                    zone_id = f"zone_{i+1}"
                    parsed_data["zones"][zone_id] = {
                        "name": zone.get("NV_Title", f"Zone {i+1}"),
                        "temp": zone.get("LiveTemp_oC"),
                        "humidity": zone.get("LiveHumidity_pc"),
                        "is_enabled": user_settings.get("EnabledZones", [])[i] if i < len(user_settings.get("EnabledZones", [])) else False,
                    }

            _LOGGER.debug(f"Parsed zone data for device {self.device_id}: {parsed_data['zones']}")

            return parsed_data

        except KeyError as e:
            _LOGGER.error(f"Failed to parse API response for device {self.device_id}: {e}")
            return {"main": {}, "zones": {}}

    async def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        _LOGGER.info(f"Setting HVAC mode to {hvac_mode} for device {self.device_id}")
        try:
            is_on = hvac_mode != HVACMode.OFF
            mode = hvac_mode if hvac_mode != HVACMode.OFF else None
            command = {
                "UserAirconSettings.isOn": is_on,
                "UserAirconSettings.Mode": mode
            }
            _LOGGER.debug(f"Sending command to set HVAC mode: {command}")
            await self.api.send_command(self.device_id, command)
            _LOGGER.info(f"Successfully set HVAC mode to {hvac_mode} for device {self.device_id}")
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set HVAC mode to {hvac_mode} for device {self.device_id}: {err}")
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        setting = "Cool" if is_cooling else "Heat"
        _LOGGER.info(f"Setting {setting} temperature to {temperature} for device {self.device_id}")
        try:
            command = {
                f"UserAirconSettings.TemperatureSetpoint_{setting}_oC": temperature
            }
            _LOGGER.debug(f"Sending command to set temperature: {command}")
            await self.api.send_command(self.device_id, command)
            _LOGGER.info(f"Successfully set {setting} temperature to {temperature} for device {self.device_id}")
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set {setting} temperature to {temperature} for device {self.device_id}: {err}")
            raise

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        _LOGGER.info(f"Setting fan mode to {fan_mode} for device {self.device_id}")
        try:
            command = {"UserAirconSettings.FanMode": fan_mode}
            _LOGGER.debug(f"Sending command to set fan mode: {command}")
            await self.api.send_command(self.device_id, command)
            _LOGGER.info(f"Successfully set fan mode to {fan_mode} for device {self.device_id}")
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set fan mode to {fan_mode} for device {self.device_id}: {err}")
            raise

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        _LOGGER.info(f"Setting zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}")
        try:
            command = {f"UserAirconSettings.EnabledZones[{zone_index}]": is_on}
            _LOGGER.debug(f"Sending command to set zone state: {command}")
            await self.api.send_command(self.device_id, command)
            _LOGGER.info(f"Successfully set zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}")
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}: {err}")
            raise

    async def async_force_update(self) -> None:
        """Force an immediate data update."""
        _LOGGER.info(f"Forcing an immediate data update for device {self.device_id}")
        await self.async_refresh()
        _LOGGER.info(f"Forced update completed for device {self.device_id}")
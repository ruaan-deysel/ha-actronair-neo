from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.components.climate.const import HVACMode

from .api import ActronApi, AuthenticationError, ApiError
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

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            if not self.api.bearer_token:
                await self.api.authenticate()

            status = await self.api.get_ac_status(self.device_id)
            _LOGGER.debug(f"API status response: {status}")
            parsed_data = self._parse_data(status)
            _LOGGER.debug(f"Parsed data: {parsed_data}")
            return parsed_data

        except AuthenticationError as auth_err:
            _LOGGER.error("Authentication error: %s", auth_err)
            raise ConfigEntryAuthFailed("Authentication failed") from auth_err
        except ApiError as api_err:
            _LOGGER.error("API error: %s", api_err)
            raise UpdateFailed("Failed to fetch data from Actron API") from api_err
        except Exception as err:
            _LOGGER.error("Unexpected error occurred: %s", err)
            raise UpdateFailed("Unexpected error occurred") from err

    def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            system_data_key = next((key for key in data.get("lastKnownState", {}).keys() if key.startswith("<") and key.endswith(">")), None)
            if not system_data_key:
                raise KeyError("No valid system data key found in the data")

            system_data = data["lastKnownState"][system_data_key]
            main_data = system_data.get("SystemStatus_Local", {})
            user_settings = data.get("UserAirconSettings", {})
            
            temp = main_data.get("SensorInputs", {}).get("SHTC1", {}).get("Temperature_oC")
            humidity = main_data.get("SensorInputs", {}).get("SHTC1", {}).get("RelativeHumidity_pc")

            parsed_data = {
                "main": {
                    "is_on": data.get("isOnline", False),
                    "mode": user_settings.get("Mode"),
                    "fan_mode": user_settings.get("FanMode"),
                    "temp_setpoint_cool": user_settings.get("TemperatureSetpoint_Cool_oC"),
                    "temp_setpoint_heat": user_settings.get("TemperatureSetpoint_Heat_oC"),
                    "indoor_temp": temp,
                    "indoor_humidity": humidity,
                }
            }

            # Parse zone data if available
            parsed_data["zones"] = {}
            for i, zone in enumerate(system_data.get("RemoteZoneInfo", [])):
                if zone.get("NV_Exists", False):
                    zone_id = f"zone_{i+1}"
                    parsed_data["zones"][zone_id] = {
                        "name": zone.get("NV_Title", f"Zone {i+1}"),
                        "temp": zone.get("LiveTemp_oC"),
                        "humidity": zone.get("LiveHumidity_pc"),
                        "is_enabled": user_settings.get("EnabledZones", [])[i] if i < len(user_settings.get("EnabledZones", [])) else False,
                    }

            return parsed_data

        except KeyError as e:
            _LOGGER.error(f"Failed to parse API response: {e}")
            return {}

    async def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        try:
            is_on = hvac_mode != HVACMode.OFF
            mode = hvac_mode if hvac_mode != HVACMode.OFF else None
            await self.api.send_command(self.device_id, {
                "UserAirconSettings.isOn": is_on,
                "UserAirconSettings.Mode": mode
            })
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set HVAC mode: %s", err)
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        try:
            setting = "Cool" if is_cooling else "Heat"
            await self.api.send_command(self.device_id, {
                f"UserAirconSettings.TemperatureSetpoint_{setting}_oC": temperature
            })
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set temperature: %s", err)
            raise

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        try:
            if fan_mode not in ["LOW", "MEDIUM", "HIGH"]:
                _LOGGER.error(f"Invalid fan mode: {fan_mode}")
                return
            await self.api.send_command(self.device_id, {"UserAirconSettings.FanMode": fan_mode})
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set fan mode: %s", err)
            raise

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        try:
            await self.api.send_command(self.device_id, {f"UserAirconSettings.EnabledZones[{zone_index}]": is_on})
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set zone state: %s", err)
            raise
import asyncio
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.components.climate.const import HVACMode

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .api import ActronApi, AuthenticationError, ApiError

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
        _LOGGER.debug("ActronDataCoordinator initialized with device_id: %s", device_id)

    async def _async_update_data(self) -> Dict[str, Any]:
        _LOGGER.debug("Starting data update for device: %s", self.device_id)
        try:
            if not self.api.bearer_token:
                _LOGGER.debug("No bearer token, authenticating...")
                await self.api.authenticate()
                _LOGGER.debug("Authentication successful")

            _LOGGER.debug("Fetching AC status from API")
            status = await self.api.get_ac_status(self.device_id)
            _LOGGER.debug("AC status fetched successfully")
            
            parsed_data = self._parse_data(status)
            _LOGGER.debug("Data parsed: %s", parsed_data)
            return parsed_data

        except AuthenticationError as auth_err:
            _LOGGER.error("Authentication error: %s", auth_err)
            raise ConfigEntryAuthFailed("Authentication failed") from auth_err
        except ApiError as api_err:
            _LOGGER.error("API error: %s", api_err)
            raise UpdateFailed("Failed to fetch data from Actron API") from api_err
        except asyncio.TimeoutError as timeout_err:
            _LOGGER.error("Timeout error: %s", timeout_err)
            raise UpdateFailed("Timeout while fetching data from Actron API") from timeout_err
        except Exception as err:
            _LOGGER.exception("Unexpected error occurred: %s", err)
            raise UpdateFailed("Unexpected error occurred") from err

    def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        _LOGGER.debug("Parsing raw data: %s", data)
        parsed_data = {
            "main": {
                "is_on": data.get("powerState") == "ON",
                "mode": data.get("climateMode", "OFF"),
                "fan_mode": data.get("fanMode", "AUTO"),
                "temp_setpoint_cool": data.get("masterCoolingSetTemp"),
                "temp_setpoint_heat": data.get("masterHeatingSetTemp"),
                "indoor_temp": data.get("masterCurrentTemp"),
                "indoor_humidity": data.get("masterCurrentHumidity"),
                "compressor_mode": data.get("compressorMode"),
                "fan_running": data.get("fanRunning", False),
                "away_mode": data.get("awayMode", False),
                "quiet_mode": data.get("quietMode", False),
                "compressor_chasing_temp": data.get("compressorChasingTemp"),
                "compressor_current_temp": data.get("compressorCurrentTemp"),
            },
            "zones": {}
        }
        
        for zone in data.get("zoneCurrentStatus", []):
            zone_id = f"zone_{zone['zoneIndex'] + 1}"
            parsed_data["zones"][zone_id] = {
                "name": zone.get("zoneName"),
                "temp": zone.get("currentTemp"),
                "humidity": zone.get("currentHumidity"),
                "is_enabled": zone.get("zoneEnabled", False),
                "temp_setpoint_cool": zone.get("currentCoolingSetTemp"),
                "temp_setpoint_heat": zone.get("currentHeatingSetTemp"),
                "sensor_battery": zone.get("zoneSensorBattery"),
            }

        _LOGGER.debug("Parsed data: %s", parsed_data)
        return parsed_data

    async def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        _LOGGER.debug("Setting HVAC mode to: %s", hvac_mode)
        try:
            mode = next(k for k, v in {"OFF": HVACMode.OFF, "AUTO": HVACMode.AUTO, "COOL": HVACMode.COOL, "HEAT": HVACMode.HEAT, "FAN": HVACMode.FAN_ONLY}.items() if v == hvac_mode)
            if mode == "OFF":
                await self.api.send_command(self.device_id, {"powerState": "OFF"})
            else:
                await self.api.send_command(self.device_id, {
                    "powerState": "ON",
                    "climateMode": mode
                })
            await self.async_request_refresh()
            _LOGGER.debug("HVAC mode set successfully")
        except Exception as err:
            _LOGGER.error("Failed to set HVAC mode: %s", err)
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        _LOGGER.debug("Setting temperature to: %s (Cooling: %s)", temperature, is_cooling)
        try:
            setting = "masterCoolingSetTemp" if is_cooling else "masterHeatingSetTemp"
            await self.api.send_command(self.device_id, {
                setting: temperature
            })
            await self.async_request_refresh()
            _LOGGER.debug("Temperature set successfully")
        except Exception as err:
            _LOGGER.error("Failed to set temperature: %s", err)
            raise

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        _LOGGER.debug("Setting fan mode to: %s", fan_mode)
        try:
            await self.api.send_command(self.device_id, {"fanMode": fan_mode})
            await self.async_request_refresh()
            _LOGGER.debug("Fan mode set successfully")
        except Exception as err:
            _LOGGER.error("Failed to set fan mode: %s", err)
            raise

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        _LOGGER.debug("Setting zone %s state to: %s", zone_index, is_on)
        try:
            await self.api.send_command(self.device_id, {f"zoneCurrentStatus[{zone_index}].zoneEnabled": is_on})
            await self.async_request_refresh()
            _LOGGER.debug("Zone state set successfully")
        except Exception as err:
            _LOGGER.error("Failed to set zone state: %s", err)
            raise
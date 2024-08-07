from datetime import timedelta
from typing import Any, Dict
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.const import (
    ATTR_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_FAN_ONLY,
)

from .api import ActronApi, AuthenticationError, ApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ActronDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: ActronApi, device_id: str, update_interval: int):
        """Initialize the Actron data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_id = device_id

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            _LOGGER.debug(f"Fetching data for device {self.device_id}")
            status = await self.api.get_ac_status(self.device_id)
            parsed_data = self._parse_data(status)
            _LOGGER.debug(f"Parsed data: {parsed_data}")
            return parsed_data
        except AuthenticationError as err:
            _LOGGER.error(f"Authentication error: {err}")
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            _LOGGER.error(f"Error communicating with API: {err}")
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the data from the API into a format suitable for the climate entity."""
        try:
            last_known_state = data.get("lastKnownState", {})
            user_aircon_settings = last_known_state.get("UserAirconSettings", {})
            master_info = last_known_state.get("MasterInfo", {})
            live_aircon = last_known_state.get("LiveAircon", {})

            parsed_data = {
                "main": {
                    "is_on": user_aircon_settings.get("isOn", False),
                    "mode": user_aircon_settings.get("Mode", "OFF"),
                    "fan_mode": user_aircon_settings.get("FanMode", "AUTO"),
                    "temp_setpoint_cool": user_aircon_settings.get("TemperatureSetpoint_Cool_oC"),
                    "temp_setpoint_heat": user_aircon_settings.get("TemperatureSetpoint_Heat_oC"),
                    "indoor_temp": master_info.get("LiveTemp_oC"),
                    "indoor_humidity": master_info.get("LiveHumidity_pc"),
                    "outdoor_temp": master_info.get("LiveOutdoorTemp_oC"),
                    "compressor_state": live_aircon.get("CompressorMode", "OFF"),
                    "EnabledZones": user_aircon_settings.get("EnabledZones", []),
                }
            }

            # Parse zone data
            parsed_data["zones"] = {}
            for i, zone in enumerate(last_known_state.get("RemoteZoneInfo", [])):
                if zone.get("NV_Exists", False):
                    zone_id = f"zone_{i+1}"
                    parsed_data["zones"][zone_id] = {
                        "name": zone.get("NV_Title", f"Zone {i+1}"),
                        "temp": zone.get("LiveTemp_oC"),
                        "humidity": zone.get("LiveHumidity_pc"),
                        "is_enabled": parsed_data["main"]["EnabledZones"][i] if i < len(parsed_data["main"]["EnabledZones"]) else False,
                        "temp_setpoint_cool": zone.get("TemperatureSetpoint_Cool_oC"),
                        "temp_setpoint_heat": zone.get("TemperatureSetpoint_Heat_oC"),
                    }

            _LOGGER.debug(f"Parsed {len(parsed_data['zones'])} zones")
            return parsed_data

        except Exception as e:
            _LOGGER.error(f"Failed to parse API response: {e}")
            return {"main": {}, "zones": {}}

    async def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        _LOGGER.info(f"Setting HVAC mode to {hvac_mode} for device {self.device_id}")
        try:
            await self.api.set_hvac_mode(self.device_id, hvac_mode)
        except ApiError as err:
            _LOGGER.error(f"Failed to set HVAC mode to {hvac_mode}: {err}")
            raise
        await self.async_request_refresh()

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        setting = "Cool" if is_cooling else "Heat"
        _LOGGER.info(f"Setting {setting} temperature to {temperature} for device {self.device_id}")
        try:
            await self.api.set_temperature(self.device_id, temperature, is_cooling)
        except ApiError as err:
            _LOGGER.error(f"Failed to set {setting} temperature to {temperature}: {err}")
            raise
        await self.async_request_refresh()

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        _LOGGER.info(f"Setting fan mode to {fan_mode} for device {self.device_id}")
        try:
            await self.api.set_fan_mode(self.device_id, fan_mode)
        except ApiError as err:
            _LOGGER.error(f"Failed to set fan mode to {fan_mode}: {err}")
            raise
        await self.async_request_refresh()

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        _LOGGER.info(f"Setting zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}")
        try:
            await self.api.set_zone_state(self.device_id, zone_index, is_on)
        except ApiError as err:
            _LOGGER.error(f"Failed to set zone {zone_index} state to {'on' if is_on else 'off'}: {err}")
            raise
        await self.async_request_refresh()

    def get_zone_status(self, zone_id: str) -> Dict[str, Any]:
        """Get the status of a specific zone."""
        return self.data["zones"].get(zone_id, {})

    def get_main_status(self) -> Dict[str, Any]:
        """Get the main status of the AC unit."""
        return self.data.get("main", {})
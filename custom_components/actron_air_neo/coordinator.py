from datetime import timedelta
from typing import Any, Dict, Optional
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.components.climate.const import HVACMode

from .api import ActronApi, AuthenticationError, ApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class ActronDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: ActronApi, device_id: str, update_interval: int):
        """Initialize the data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_id = device_id
        self.last_data = None

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            if not self.api.is_api_healthy():
                _LOGGER.warning("API is not healthy, using cached data")
                return self.last_data if self.last_data else {}

            _LOGGER.debug(f"Fetching data for device {self.device_id}")
            status = await self.api.get_ac_status(self.device_id)
            parsed_data = self._parse_data(status)
            self.last_data = parsed_data
            _LOGGER.debug(f"Parsed data: {parsed_data}")
            return parsed_data
        except AuthenticationError as err:
            _LOGGER.error(f"Authentication error: {err}")
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            _LOGGER.error(f"Error communicating with API: {err}")
            if self.last_data:
                _LOGGER.warning("Using cached data due to API error")
                return self.last_data
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
                },
                "zones": {}
            }

            # Parse zone data
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

            return parsed_data

        except Exception as e:
            _LOGGER.error(f"Failed to parse API response: {e}")
            raise UpdateFailed(f"Failed to parse API response: {e}")

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
            _LOGGER.error(f"Failed to set HVAC mode to {hvac_mode}: {err}")
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        setting = "Cool" if is_cooling else "Heat"
        try:
            await self.api.send_command(self.device_id, {
                f"UserAirconSettings.TemperatureSetpoint_{setting}_oC": temperature
            })
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set {setting} temperature to {temperature}: {err}")
            raise

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        try:
            await self.api.send_command(self.device_id, {"UserAirconSettings.FanMode": fan_mode})
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set fan mode to {fan_mode}: {err}")
            raise

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        try:
            current_zones = self.data['main'].get('EnabledZones', [])
            if zone_index < len(current_zones):
                current_zones[zone_index] = is_on
                await self.api.send_command(self.device_id, {"UserAirconSettings.EnabledZones": current_zones})
                await self.async_request_refresh()
            else:
                _LOGGER.error(f"Zone index {zone_index} is out of range")
        except Exception as err:
            _LOGGER.error(f"Failed to set zone {zone_index} state to {'on' if is_on else 'off'}: {err}")
            raise

    async def force_update(self) -> None:
        """Force an immediate update of the device data."""
        await self.async_refresh()
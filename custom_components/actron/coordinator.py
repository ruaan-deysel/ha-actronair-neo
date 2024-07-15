import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import ActronApi, AuthenticationError, ApiError
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL

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
            return self._parse_data(status)

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
        parsed_data = {}
        
        _LOGGER.debug("Received data: %s", data)
        
        system_data_key = next((key for key in data.get("lastKnownState", {}).keys() if key.startswith("<") and key.endswith(">")), None)
        if not system_data_key:
            _LOGGER.error("No valid system data key found in the data")
            return parsed_data

        system_data = data.get("lastKnownState", {}).get(system_data_key, {})
        
        user_settings = system_data.get("UserAirconSettings", {})
        live_aircon = system_data.get("LiveAircon", {})
        master_info = system_data.get("MasterInfo", {})

        parsed_data["main"] = {
            "is_on": user_settings.get("isOn", False),
            "mode": user_settings.get("Mode", "OFF"),
            "fan_mode": user_settings.get("FanMode", "AUTO"),
            "temp_setpoint_cool": user_settings.get("TemperatureSetpoint_Cool_oC"),
            "temp_setpoint_heat": user_settings.get("TemperatureSetpoint_Heat_oC"),
            "indoor_temp": master_info.get("LiveTemp_oC"),
            "indoor_humidity": master_info.get("LiveHumidity_pc"),
            "outdoor_temp": master_info.get("LiveOutdoorTemp_oC", 3000.0),
            "away_mode": user_settings.get("AwayMode", False),
            "quiet_mode": user_settings.get("QuietMode", False),
            "quiet_mode_enabled": user_settings.get("QuietModeEnabled", False),
            "quiet_mode_active": user_settings.get("QuietModeActive", False),
            "compressor_state": live_aircon.get("CompressorMode"),
            "fan_running": live_aircon.get("AmRunningFan", False),
        }

        # Handle potential invalid outdoor temperature
        if parsed_data["main"]["outdoor_temp"] == 3000.0:
            parsed_data["main"]["outdoor_temp"] = None

        parsed_data["zones"] = {}
        for zone in system_data.get("RemoteZoneInfo", []):
            zone_id = zone.get("NV_Title", "Unknown Zone")
            parsed_data["zones"][zone_id] = {
                "temp": zone.get("LiveTemp_oC"),
                "humidity": zone.get("LiveHumidity_pc"),
                "setpoint_cool": zone.get("TemperatureSetpoint_Cool_oC"),
                "setpoint_heat": zone.get("TemperatureSetpoint_Heat_oC"),
                "is_enabled": zone.get("CanOperate", False),
            }

        parsed_data["peripherals"] = {}
        for peripheral in system_data.get("AirconSystem", {}).get("Peripherals", []):
            peripheral_id = peripheral.get("SerialNumber", "Unknown")
            parsed_data["peripherals"][peripheral_id] = {
                "type": peripheral.get("DeviceType"),
                "zone_assignment": peripheral.get("ZoneAssignment"),
                "battery_level": peripheral.get("RemainingBatteryCapacity_pc"),
                "signal_strength": peripheral.get("RSSI", {}).get("Local"),
                "temp": peripheral.get("SensorInputs", {}).get("SHTC1", {}).get("Temperature_oC"),
                "humidity": peripheral.get("SensorInputs", {}).get("SHTC1", {}).get("RelativeHumidity_pc"),
            }

        return parsed_data

    async def set_away_mode(self, away_mode: bool) -> None:
        """Set the away mode."""
        try:
            await self.api.send_command(self.device_id, {"UserAirconSettings.AwayMode": away_mode})
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set away mode: %s", err)
            raise

    async def set_quiet_mode(self, quiet_mode: bool) -> None:
        """Set the quiet mode."""
        try:
            await self.api.send_command(self.device_id, {"UserAirconSettings.QuietMode": quiet_mode})
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set quiet mode: %s", err)
            raise
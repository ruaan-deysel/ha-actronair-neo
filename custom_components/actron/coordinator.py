import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
            raise UpdateFailed("Authentication failed") from auth_err
        except ApiError as api_err:
            _LOGGER.error("API error: %s", api_err)
            raise UpdateFailed("Failed to fetch data from Actron API") from api_err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise UpdateFailed("Unexpected error occurred") from err

    def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        parsed_data = {}
        system_data = data.get("<22H09780>", {})
        
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
            "outdoor_temp": live_aircon.get("OutdoorUnit", {}).get("AmbTemp"),
            "away_mode": user_settings.get("AwayMode", False),
        }

        parsed_data["zones"] = {}
        for zone in system_data.get("RemoteZoneInfo", []):
            zone_id = zone.get("NV_Title", "Unknown")
            parsed_data["zones"][zone_id] = {
                "temp": zone.get("LiveTemp_oC"),
                "humidity": zone.get("LiveHumidity_pc"),
                "setpoint_cool": zone.get("TemperatureSetpoint_Cool_oC"),
                "setpoint_heat": zone.get("TemperatureSetpoint_Heat_oC"),
                "is_enabled": zone.get("CanOperate", False),
            }

        return parsed_data

async def async_setup_coordinator(hass: HomeAssistant, api: ActronApi, device_id: str, update_interval: int) -> ActronDataCoordinator:
    coordinator = ActronDataCoordinator(hass, api, device_id, update_interval)
    await coordinator.async_config_entry_first_refresh()
    return coordinator
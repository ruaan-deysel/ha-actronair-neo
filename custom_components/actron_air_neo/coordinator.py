# coordinator.py

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
    """Class to manage fetching Actron Air Neo data."""

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
        except Exception as err:
            _LOGGER.error(f"Unexpected error occurred: {err}")
            if self.last_data:
                _LOGGER.warning("Using cached data due to unexpected error")
                return self.last_data
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the data from the API into a format suitable for the climate entity."""
        try:
            last_known_state = data.get("lastKnownState", {})
            user_aircon_settings = last_known_state.get("UserAirconSettings", {})
            master_info = last_known_state.get("MasterInfo", {})
            live_aircon = last_known_state.get("LiveAircon", {})
            system_info = data.get("systemInfo", {})

            parsed_data = {
                "main": {
                    "is_on": user_aircon_settings.get("isOn", False),
                    "mode": user_aircon_settings.get("Mode", "OFF"),
                    "fan_mode": user_aircon_settings.get("FanMode", "LOW"),
                    "temp_setpoint_cool": user_aircon_settings.get("TemperatureSetpoint_Cool_oC"),
                    "temp_setpoint_heat": user_aircon_settings.get("TemperatureSetpoint_Heat_oC"),
                    "indoor_temp": master_info.get("LiveTemp_oC"),
                    "indoor_humidity": master_info.get("LiveHumidity_pc"),
                    "wall_temp": master_info.get("LiveWallTemp_oC"),
                    "compressor_state": live_aircon.get("CompressorMode", "OFF"),
                    "EnabledZones": user_aircon_settings.get("EnabledZones", []),
                    "away_mode": user_aircon_settings.get("AwayMode", False),
                    "quiet_mode": user_aircon_settings.get("QuietMode", False),
                    "continuous_fan": user_aircon_settings.get("ContinuousFan", False),
                    "model": system_info.get("model"),
                    "serial_number": system_info.get("serial"),
                    "firmware_version": system_info.get("firmwareVersion"),
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
            command = self.api.create_command("ON" if hvac_mode != HVACMode.OFF else "OFF")
            await self.api.send_command(self.device_id, command)
            if hvac_mode != HVACMode.OFF:
                command = self.api.create_command("CLIMATE_MODE", mode=hvac_mode)
                await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set HVAC mode to {hvac_mode}: {err}")
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        try:
            command = self.api.create_command("SET_TEMP", temp=temperature, is_cool=is_cooling)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set {'cooling' if is_cooling else 'heating'} temperature to {temperature}: {err}")
            raise

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        try:
            command = self.api.create_command("FAN_MODE", mode=fan_mode)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set fan mode to {fan_mode}: {err}")
            raise

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        try:
            command = self.api.create_command("ZONE_ENABLE" if is_on else "ZONE_DISABLE", zone_index=zone_index)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set zone {zone_index} state to {'on' if is_on else 'off'}: {err}")
            raise

    async def set_away_mode(self, state: bool) -> None:
        """Set away mode."""
        try:
            command = self.api.create_command("AWAY_MODE", state=state)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set away mode to {state}: {err}")
            raise

    async def set_quiet_mode(self, state: bool) -> None:
        """Set quiet mode."""
        try:
            command = self.api.create_command("QUIET_MODE", state=state)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set quiet mode to {state}: {err}")
            raise

    async def set_continuous_fan(self, state: bool) -> None:
        """Set continuous fan."""
        try:
            command = self.api.create_command("CONTINUOUS_FAN", state=state)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set continuous fan to {state}: {err}")
            raise

    async def force_update(self) -> None:
        """Force an immediate update of the device data."""
        await self.async_refresh()
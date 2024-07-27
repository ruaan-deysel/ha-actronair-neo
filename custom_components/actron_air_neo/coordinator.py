from datetime import timedelta
from typing import Any, Dict
import asyncio

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
        self._last_update = {}
        self._failed_updates = 0
        _LOGGER.info(f"Initializing ActronDataCoordinator for device {device_id} with update interval {update_interval} seconds")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint with exponential backoff."""
        try:
            data = await self._fetch_data_with_backoff()
            self._failed_updates = 0  # Reset failed updates counter on success
            return data
        except Exception as err:
            self._failed_updates += 1
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_data_with_backoff(self) -> Dict[str, Any]:
        """Fetch data with exponential backoff."""
        max_attempts = 5
        base_delay = 5  # seconds

        for attempt in range(max_attempts):
            try:
                _LOGGER.debug(f"Fetching data for device {self.device_id} (Attempt {attempt + 1}/{max_attempts})")
                status = await self.api.get_ac_status(self.device_id)
                parsed_data = self._parse_data(status)
                if self._is_data_changed(parsed_data):
                    _LOGGER.debug(f"Data changed for device {self.device_id}")
                    self._last_update = parsed_data
                    return parsed_data
                else:
                    _LOGGER.debug(f"No change in data for device {self.device_id}")
                    return self._last_update
            except AuthenticationError as auth_err:
                _LOGGER.error(f"Authentication error for device {self.device_id}: {auth_err}")
                raise ConfigEntryAuthFailed("Authentication failed") from auth_err
            except (ApiError, RateLimitError) as err:
                if attempt == max_attempts - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                _LOGGER.warning(f"Error fetching data (Attempt {attempt + 1}/{max_attempts}). Retrying in {delay} seconds. Error: {err}")
                await asyncio.sleep(delay)

        raise UpdateFailed(f"Failed to fetch data after {max_attempts} attempts")

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

    def _is_data_changed(self, new_data: Dict[str, Any]) -> bool:
        """Check if the new data is different from the last update."""
        return new_data != self._last_update

    async def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        _LOGGER.info(f"Setting HVAC mode to {hvac_mode} for device {self.device_id}")
        try:
            is_on = hvac_mode != HVACMode.OFF
            mode = hvac_mode if hvac_mode != HVACMode.OFF else None
            result = await self.api.send_command(self.device_id, {
                "UserAirconSettings.isOn": is_on,
                "UserAirconSettings.Mode": mode
            })
            if isinstance(result, dict) and 'error' in result:
                _LOGGER.error(f"Failed to set HVAC mode: {result['error']}")
                return result
            _LOGGER.info(f"Successfully set HVAC mode to {hvac_mode} for device {self.device_id}")
        except Exception as err:
            _LOGGER.error(f"Failed to set HVAC mode to {hvac_mode} for device {self.device_id}: {err}")
            raise
        finally:
            await self.async_request_refresh()

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        setting = "Cool" if is_cooling else "Heat"
        _LOGGER.info(f"Setting {setting} temperature to {temperature} for device {self.device_id}")
        try:
            result = await self.api.send_command(self.device_id, {
                f"UserAirconSettings.TemperatureSetpoint_{setting}_oC": temperature
            })
            if isinstance(result, dict) and 'error' in result:
                _LOGGER.error(f"Failed to set temperature: {result['error']}")
                return result
            _LOGGER.info(f"Successfully set {setting} temperature to {temperature} for device {self.device_id}")
        except Exception as err:
            _LOGGER.error(f"Failed to set {setting} temperature to {temperature} for device {self.device_id}: {err}")
            raise
        finally:
            await self.async_request_refresh()

    async def set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode."""
        _LOGGER.info(f"Setting fan mode to {fan_mode} for device {self.device_id}")
        try:
            result = await self.api.send_command(self.device_id, {"UserAirconSettings.FanMode": fan_mode})
            if isinstance(result, dict) and 'error' in result:
                _LOGGER.error(f"Failed to set fan mode: {result['error']}")
                return result
            _LOGGER.info(f"Successfully set fan mode to {fan_mode} for device {self.device_id}")
        except Exception as err:
            _LOGGER.error(f"Failed to set fan mode to {fan_mode} for device {self.device_id}: {err}")
            raise
        finally:
            await self.async_request_refresh()

    async def set_zone_state(self, zone_index: int, is_on: bool) -> None:
        """Set zone state."""
        _LOGGER.info(f"Setting zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}")
        try:
            result = await self.api.send_command(self.device_id, {f"UserAirconSettings.EnabledZones[{zone_index}]": is_on})
            if isinstance(result, dict) and 'error' in result:
                _LOGGER.error(f"Failed to set zone state: {result['error']}")
                return result
            _LOGGER.info(f"Successfully set zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}")
        except Exception as err:
            _LOGGER.error(f"Failed to set zone {zone_index} state to {'on' if is_on else 'off'} for device {self.device_id}: {err}")
            raise
        finally:
            await self.async_request_refresh()

    async def async_force_update(self) -> None:
        """Force an immediate data update."""
        _LOGGER.info(f"Forcing an immediate data update for device {self.device_id}")
        await self.async_refresh()
        _LOGGER.info(f"Forced update completed for device {self.device_id}")
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
    def __init__(self, hass: HomeAssistant, api: ActronApi, update_interval: int):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.systems: Dict[str, Dict[str, Any]] = {}

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            if not self.api.bearer_token:
                await self.api.authenticate()

            systems = await self.api.list_ac_systems()
            data = {}

            for system in systems.get('_embedded', {}).get('ac-system', []):
                serial = system.get('serial')
                if not serial:
                    continue

                status = await self.api.get_ac_status(serial)
                events = await self.api.get_ac_events(serial)

                system_data = self._parse_system_data(system, status, events)
                data[serial] = system_data

            return data

        except AuthenticationError as auth_err:
            _LOGGER.error("Authentication error: %s", auth_err)
            raise UpdateFailed("Authentication failed") from auth_err
        except ApiError as api_err:
            _LOGGER.error("API error: %s", api_err)
            raise UpdateFailed("Failed to fetch data from Actron API") from api_err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            raise UpdateFailed("Unexpected error occurred") from err

    def _parse_system_data(self, system: Dict[str, Any], status: Dict[str, Any], events: Dict[str, Any]) -> Dict[str, Any]:
        user_settings = status.get('UserAirconSettings', {})
        system_status = status.get('SystemStatus_Local', {})
        
        parsed_data = {
            'name': system.get('description', 'Unknown'),
            'serial': system.get('serial', 'Unknown'),
            'isOn': user_settings.get('isOn', False),
            'mode': user_settings.get('Mode', 'OFF'),
            'fanMode': user_settings.get('FanMode', 'AUTO'),
            'TemperatureSetpoint_Cool_oC': user_settings.get('TemperatureSetpoint_Cool_oC'),
            'TemperatureSetpoint_Heat_oC': user_settings.get('TemperatureSetpoint_Heat_oC'),
        }

        if 'SensorInputs' in system_status:
            sensor_inputs = system_status['SensorInputs']
            if 'SHTC1' in sensor_inputs:
                shtc1 = sensor_inputs['SHTC1']
                parsed_data['indoor_temperature'] = shtc1.get('Temperature_oC')
                parsed_data['indoor_humidity'] = shtc1.get('RelativeHumidity_pc')
            if 'Battery' in sensor_inputs:
                parsed_data['battery_level'] = sensor_inputs['Battery'].get('Level')
        
        if 'Outdoor' in system_status:
            parsed_data['outdoor_temperature'] = system_status['Outdoor'].get('Temperature_oC')

        parsed_data['zones'] = self._parse_zone_data(status)
        parsed_data['events'] = events.get('events', [])

        return parsed_data

    def _parse_zone_data(self, status: Dict[str, Any]) -> Dict[str, Any]:
        zones = {}
        user_settings = status.get('UserAirconSettings', {})
        remote_zone_info = status.get('RemoteZoneInfo', {})

        for i, enabled in enumerate(user_settings.get('EnabledZones', [])):
            zone_data = remote_zone_info.get(str(i), {})
            zones[str(i)] = {
                'enabled': enabled,
                'name': zone_data.get('Name', f'Zone {i}'),
                'temperature': zone_data.get('Temperature_oC'),
                'target_temperature_cool': zone_data.get('TemperatureSetpoint_Cool_oC'),
                'target_temperature_heat': zone_data.get('TemperatureSetpoint_Heat_oC'),
            }

        return zones

async def async_setup_coordinator(hass: HomeAssistant, api: ActronApi, update_interval: int) -> ActronDataCoordinator:
    coordinator = ActronDataCoordinator(hass, api, update_interval)
    await coordinator.async_config_entry_first_refresh()
    return coordinator
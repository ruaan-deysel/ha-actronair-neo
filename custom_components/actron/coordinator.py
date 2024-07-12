import asyncio
import logging
from datetime import timedelta
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
        self.systems = {}

    async def _async_update_data(self):
        try:
            if not self.api.bearer_token:
                await self.api.authenticate()

            systems = await self.api.list_ac_systems()
            data = {}

            for system in systems:
                serial = system['serial']
                status = await self.api.get_ac_status(serial)
                
                # Extract relevant data from the status
                system_data = {
                    'name': system['name'],
                    'serial': serial,
                    'isOn': status.get('isOn', False),
                    'mode': status.get('mode', 'OFF'),
                    'fanMode': status.get('fanMode', 'AUTO'),
                    'TemperatureSetpoint_Cool_oC': status.get('TemperatureSetpoint_Cool_oC'),
                    'TemperatureSetpoint_Heat_oC': status.get('TemperatureSetpoint_Heat_oC'),
                }

                # Extract sensor data
                if 'SystemStatus_Local' in status:
                    local_status = status['SystemStatus_Local']
                    if 'SensorInputs' in local_status:
                        sensor_inputs = local_status['SensorInputs']
                        if 'SHTC1' in sensor_inputs:
                            shtc1 = sensor_inputs['SHTC1']
                            system_data['indoor_temperature'] = shtc1.get('Temperature_oC')
                            system_data['indoor_humidity'] = shtc1.get('RelativeHumidity_pc')
                        if 'Battery' in sensor_inputs:
                            system_data['battery_level'] = sensor_inputs['Battery'].get('Level')
                    if 'Outdoor' in local_status:
                        system_data['outdoor_temperature'] = local_status['Outdoor'].get('Temperature_oC')

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

async def async_setup_coordinator(hass: HomeAssistant, api: ActronApi, update_interval: int) -> ActronDataCoordinator:
    coordinator = ActronDataCoordinator(hass, api, update_interval)
    await coordinator.async_config_entry_first_refresh()
    return coordinator
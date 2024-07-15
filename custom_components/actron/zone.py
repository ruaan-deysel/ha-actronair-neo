import logging
from typing import Dict, Any

from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

class ActronZone:
    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        self.coordinator = coordinator
        self.zone_id = zone_id

    @property
    def temperature(self) -> float | None:
        return self.coordinator.data['zones'][self.zone_id]['temp']

    @property
    def humidity(self) -> float | None:
        return self.coordinator.data['zones'][self.zone_id]['humidity']

    @property
    def target_temperature_cool(self) -> float | None:
        return self.coordinator.data['zones'][self.zone_id]['setpoint_cool']

    @property
    def target_temperature_heat(self) -> float | None:
        return self.coordinator.data['zones'][self.zone_id]['setpoint_heat']

    @property
    def is_enabled(self) -> bool:
        return self.coordinator.data['zones'][self.zone_id]['is_enabled']

    async def set_temperature(self, temperature: float, mode: str) -> None:
        try:
            if mode == 'COOL':
                await self.coordinator.api.send_command(self.coordinator.device_id, {
                    f"RemoteZoneInfo[{self.zone_id}].TemperatureSetpoint_Cool_oC": temperature
                })
            elif mode == 'HEAT':
                await self.coordinator.api.send_command(self.coordinator.device_id, {
                    f"RemoteZoneInfo[{self.zone_id}].TemperatureSetpoint_Heat_oC": temperature
                })
            else:
                _LOGGER.error(f"Invalid mode {mode} for setting temperature")
                return

            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set temperature for zone {self.zone_id}: {err}")
            raise

    async def set_enabled(self, enabled: bool) -> None:
        try:
            await self.coordinator.api.send_command(self.coordinator.device_id, {
                f"UserAirconSettings.EnabledZones[{self.zone_id}]": enabled
            })
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error(f"Failed to set enabled state for zone {self.zone_id}: {err}")
            raise

    def get_data(self) -> Dict[str, Any]:
        return self.coordinator.data['zones'][self.zone_id]
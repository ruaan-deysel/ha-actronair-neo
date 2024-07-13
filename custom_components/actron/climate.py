import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    HVAC_MODES,
    FAN_MODES,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [ActronClimate(coordinator, zone_id) for zone_id in coordinator.data['zones']]
    async_add_entities(entities, True)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, coordinator, zone_id):
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_name = f"Actron Air Neo {coordinator.data['zones'][zone_id]['name']}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{zone_id}"
        self._attr_hvac_modes = list(HVAC_MODES.values())
        self._attr_fan_modes = FAN_MODES
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE |
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        )

    @property
    def current_temperature(self) -> Optional[float]:
        return self.coordinator.data['zones'][self._zone_id]['temperature']

    @property
    def target_temperature(self) -> Optional[float]:
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data['zones'][self._zone_id]['setpoint_cool']
        elif self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data['zones'][self._zone_id]['setpoint_heat']
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        system_status = self.coordinator.data['system_status']
        if not system_status['is_on']:
            return HVACMode.OFF
        return HVAC_MODES.get(system_status['mode'], HVACMode.OFF)

    @property
    def fan_mode(self) -> Optional[str]:
        return self.coordinator.data['system_status']['fan_mode']

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            if self.hvac_mode == HVACMode.COOL:
                await self.coordinator.api.send_command(self.coordinator.device_id, {
                    f"RemoteZoneInfo[{self._zone_id}].TemperatureSetpoint_Cool_oC": temp
                })
            elif self.hvac_mode == HVACMode.HEAT:
                await self.coordinator.api.send_command(self.coordinator.device_id, {
                    f"RemoteZoneInfo[{self._zone_id}].TemperatureSetpoint_Heat_oC": temp
                })
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.send_command(self.coordinator.device_id, {"UserAirconSettings.isOn": False})
        else:
            await self.coordinator.api.send_command(self.coordinator.device_id, {
                "UserAirconSettings.isOn": True,
                "UserAirconSettings.Mode": hvac_mode.upper()
            })
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.coordinator.api.send_command(self.coordinator.device_id, {"UserAirconSettings.FanMode": fan_mode})
        await self.coordinator.async_request_refresh()
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

FAN_LOW = "LOW"
FAN_MEDIUM = "MEDIUM"
FAN_HIGH = "HIGH"
FAN_AUTO = "AUTO"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ActronClimate(coordinator)], True)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Actron Air Neo"
        self._attr_unique_id = f"{coordinator.device_id}_climate"
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
        self._attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
        )

    @property
    def current_temperature(self):
        return self.coordinator.data['main'].get('indoor_temp')

    @property
    def target_temperature(self):
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data['main'].get('temp_setpoint_cool')
        elif self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data['main'].get('temp_setpoint_heat')
        return None

    @property
    def hvac_mode(self):
        if not self.coordinator.data['main'].get('is_on'):
            return HVACMode.OFF
        mode = self.coordinator.data['main'].get('mode')
        if mode == "COOL":
            return HVACMode.COOL
        elif mode == "HEAT":
            return HVACMode.HEAT
        elif mode == "FAN":
            return HVACMode.FAN_ONLY
        return HVACMode.OFF

    @property
    def fan_mode(self):
        return self.coordinator.data['main'].get('fan_mode')

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        is_cooling = self.hvac_mode == HVACMode.COOL
        await self.coordinator.api.set_temperature(temperature, is_cooling)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.set_hvac_mode(HVACMode.OFF)
        else:
            await self.coordinator.api.set_hvac_mode(hvac_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode):
        await self.coordinator.api.set_fan_mode(fan_mode)
        await self.coordinator.async_request_refresh()
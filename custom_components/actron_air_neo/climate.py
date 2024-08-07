from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MIN_TEMP, MAX_TEMP
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.AUTO]
FAN_MODES = [FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ActronClimate(coordinator)], True)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "ActronAir Neo"
        self._attr_unique_id = f"{coordinator.device_id}_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = HVAC_MODES
        self._attr_fan_modes = FAN_MODES
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE 
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_min_temp = MIN_TEMP
        self._attr_max_temp = MAX_TEMP

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data['main'].get('indoor_temp')

    @property
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data['main'].get('temp_setpoint_cool')
        elif self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data['main'].get('temp_setpoint_heat')
        elif self.hvac_mode == HVACMode.AUTO:
            return self.coordinator.data['main'].get('temp_setpoint_cool')  # Default to cooling setpoint in AUTO mode
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data['main'].get('is_on'):
            return HVACMode.OFF
        mode = self.coordinator.data['main'].get('mode')
        return self._actron_to_ha_hvac_mode(mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        if not self.coordinator.data['main'].get('is_on'):
            return HVACAction.OFF
        if self.hvac_mode == HVACMode.COOL:
            return HVACAction.COOLING
        elif self.hvac_mode == HVACMode.HEAT:
            return HVACAction.HEATING
        elif self.hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        elif self.hvac_mode == HVACMode.AUTO:
            current_temp = self.current_temperature
            target_temp = self.target_temperature
            if current_temp is not None and target_temp is not None:
                if current_temp < target_temp:
                    return HVACAction.HEATING
                elif current_temp > target_temp:
                    return HVACAction.COOLING
            return HVACAction.IDLE
        return HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        return self.coordinator.data['main'].get('fan_mode')

    @property
    def current_humidity(self) -> int | None:
        humidity = self.coordinator.data['main'].get('indoor_humidity')
        return round(humidity) if humidity is not None else None

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        temperature = min(max(temperature, MIN_TEMP), MAX_TEMP)
        is_cooling = self.hvac_mode in [HVACMode.COOL, HVACMode.AUTO]
        await self.coordinator.set_temperature(temperature, is_cooling)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        actron_mode = self._ha_to_actron_hvac_mode(hvac_mode)
        await self.coordinator.set_hvac_mode(actron_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.coordinator.set_fan_mode(fan_mode)

    async def async_turn_on(self) -> None:
        await self.coordinator.set_hvac_mode(self._ha_to_actron_hvac_mode(HVACMode.AUTO))

    async def async_turn_off(self) -> None:
        await self.coordinator.set_hvac_mode(self._ha_to_actron_hvac_mode(HVACMode.OFF))

    def _actron_to_ha_hvac_mode(self, mode: str | None) -> HVACMode:
        if mode is None:
            return HVACMode.OFF
        mode_map = {
            "AUTO": HVACMode.AUTO,
            "HEAT": HVACMode.HEAT,
            "COOL": HVACMode.COOL,
            "FAN": HVACMode.FAN_ONLY,
            "OFF": HVACMode.OFF,
        }
        return mode_map.get(mode.upper(), HVACMode.OFF)

    def _ha_to_actron_hvac_mode(self, mode: HVACMode) -> str:
        mode_map = {
            HVACMode.AUTO: "AUTO",
            HVACMode.HEAT: "HEAT",
            HVACMode.COOL: "COOL",
            HVACMode.FAN_ONLY: "FAN",
            HVACMode.OFF: "OFF",
        }
        return mode_map.get(mode, "OFF")
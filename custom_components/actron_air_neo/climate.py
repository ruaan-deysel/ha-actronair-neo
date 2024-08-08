from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACAction
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, MIN_TEMP, MAX_TEMP,
    HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_FAN, HVAC_MODE_AUTO,
    FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_AUTO
)
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_FAN, HVAC_MODE_AUTO]
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
        if self.hvac_mode == HVAC_MODE_COOL:
            return self.coordinator.data['main'].get('temp_setpoint_cool')
        elif self.hvac_mode == HVAC_MODE_HEAT:
            return self.coordinator.data['main'].get('temp_setpoint_heat')
        elif self.hvac_mode == HVAC_MODE_AUTO:
            return self.coordinator.data['main'].get('temp_setpoint_cool')  # Default to cooling setpoint in AUTO mode
        return None

    @property
    def hvac_mode(self) -> str:
        if not self.coordinator.data['main'].get('is_on'):
            return HVAC_MODE_OFF
        mode = self.coordinator.data['main'].get('mode')
        return self._actron_to_ha_hvac_mode(mode)

    @property
    def hvac_action(self) -> HVACAction | None:
        if not self.coordinator.data['main'].get('is_on'):
            return HVACAction.OFF
        compressor_state = self.coordinator.data['main'].get('compressor_state', 'OFF')
        if compressor_state == 'COOL':
            return HVACAction.COOLING
        elif compressor_state == 'HEAT':
            return HVACAction.HEATING
        elif self.hvac_mode == HVAC_MODE_FAN:
            return HVACAction.FAN
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
        is_cooling = self.hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_AUTO]
        try:
            await self.coordinator.set_temperature(temperature, is_cooling)
        except Exception as e:
            _LOGGER.error(f"Failed to set temperature: {e}")

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        actron_mode = self._ha_to_actron_hvac_mode(hvac_mode)
        try:
            await self.coordinator.set_hvac_mode(actron_mode)
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode: {e}")

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        try:
            await self.coordinator.set_fan_mode(fan_mode)
        except Exception as e:
            _LOGGER.error(f"Failed to set fan mode: {e}")

    async def async_turn_on(self) -> None:
        try:
            await self.coordinator.set_hvac_mode(self._ha_to_actron_hvac_mode(HVAC_MODE_AUTO))
        except Exception as e:
            _LOGGER.error(f"Failed to turn on: {e}")

    async def async_turn_off(self) -> None:
        try:
            await self.coordinator.set_hvac_mode(self._ha_to_actron_hvac_mode(HVAC_MODE_OFF))
        except Exception as e:
            _LOGGER.error(f"Failed to turn off: {e}")

    def _actron_to_ha_hvac_mode(self, mode: str | None) -> str:
        if mode is None:
            return HVAC_MODE_OFF
        mode_map = {
            "AUTO": HVAC_MODE_AUTO,
            "HEAT": HVAC_MODE_HEAT,
            "COOL": HVAC_MODE_COOL,
            "FAN": HVAC_MODE_FAN,
            "OFF": HVAC_MODE_OFF,
        }
        return mode_map.get(mode.upper(), HVAC_MODE_OFF)

    def _ha_to_actron_hvac_mode(self, mode: str) -> str:
        mode_map = {
            HVAC_MODE_AUTO: "AUTO",
            HVAC_MODE_HEAT: "HEAT",
            HVAC_MODE_COOL: "COOL",
            HVAC_MODE_FAN: "FAN",
            HVAC_MODE_OFF: "OFF",
        }
        return mode_map.get(mode, "OFF")
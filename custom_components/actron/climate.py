from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import FAN_LOW, FAN_MEDIUM, FAN_HIGH
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = {
    "OFF": HVACMode.OFF,
    "AUTO": HVACMode.AUTO,
    "COOL": HVACMode.COOL,
    "HEAT": HVACMode.HEAT,
    "FAN": HVACMode.FAN_ONLY,
}

FAN_MODES = {
    "LOW": FAN_LOW,
    "MED": FAN_MEDIUM,
    "HIGH": FAN_HIGH,
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Actron Air Neo climate device."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ActronClimate(coordinator)])

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Actron Air Neo"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}"
        self._attr_hvac_modes = list(HVAC_MODES.values())
        self._attr_fan_modes = list(FAN_MODES.values())
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE |
            ClimateEntityFeature.TURN_ON |
            ClimateEntityFeature.TURN_OFF
        )

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data['main']['indoor_temp']

    @property
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data['main']['temp_setpoint_cool']
        elif self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data['main']['temp_setpoint_heat']
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data['main']['is_on']:
            return HVACMode.OFF
        return HVAC_MODES.get(self.coordinator.data['main']['mode'], HVACMode.OFF)

    @property
    def fan_mode(self) -> str | None:
        fan_mode = self.coordinator.data['main']['fan_mode']
        if fan_mode == "MED":
            return FAN_MEDIUM
        return FAN_MODES.get(fan_mode, FAN_LOW)

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            is_cooling = self.hvac_mode == HVACMode.COOL
            await self.coordinator.set_temperature(temp, is_cooling)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        await self.coordinator.set_hvac_mode(hvac_mode)

    async def async_set_fan_mode(self, fan_mode: str):
        mode = next((k for k, v in FAN_MODES.items() if v == fan_mode), None)
        if mode:
            await self.coordinator.set_fan_mode(mode)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.coordinator.set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.coordinator.set_hvac_mode(HVACMode.OFF)
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import PRESET_AWAY, PRESET_NONE
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HVAC_MODES, FAN_MODES, FAN_MEDIUM
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Actron Air Neo climate devices."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [ActronClimate(coordinator, "main")]
    entities.extend([ActronZoneClimate(coordinator, zone_id) for zone_id in coordinator.data["zones"]])
    async_add_entities(entities)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_name = f"Actron Air Neo {zone_id}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{zone_id}"
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
        self._attr_fan_modes = FAN_MODES
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE |
            ClimateEntityFeature.PRESET_MODE |
            ClimateEntityFeature.TURN_ON |
            ClimateEntityFeature.TURN_OFF
        )
        self._attr_preset_modes = [PRESET_NONE, PRESET_AWAY]

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
        return fan_mode

    @property
    def preset_mode(self) -> str | None:
        return PRESET_AWAY if self.coordinator.data['main']['away_mode'] else PRESET_NONE

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            is_cooling = self.hvac_mode == HVACMode.COOL
            await self.coordinator.set_temperature(temp, is_cooling)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        await self.coordinator.set_hvac_mode(hvac_mode)

    async def async_set_fan_mode(self, fan_mode: str):
        if fan_mode == FAN_MEDIUM:
            fan_mode = "MED"
        await self.coordinator.set_fan_mode(fan_mode)

    async def async_set_preset_mode(self, preset_mode: str):
        await self.coordinator.set_preset_mode(preset_mode == PRESET_AWAY)

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.coordinator.set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.coordinator.set_hvac_mode(HVACMode.OFF)

class ActronZoneClimate(ActronClimate):
    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data['zones'][self._zone_id]['temp']

    @property
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.COOL:
            return self.coordinator.data['zones'][self._zone_id]['setpoint_cool']
        elif self.hvac_mode == HVACMode.HEAT:
            return self.coordinator.data['zones'][self._zone_id]['setpoint_heat']
        return None

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            is_cooling = self.hvac_mode == HVACMode.COOL
            await self.coordinator.set_zone_temperature(self._zone_id, temp, is_cooling)

    async def async_turn_on(self) -> None:
        """Turn the zone on."""
        await self.coordinator.set_zone_state(int(self._zone_id.split('_')[1]) - 1, True)

    async def async_turn_off(self) -> None:
        """Turn the zone off."""
        await self.coordinator.set_zone_state(int(self._zone_id.split('_')[1]) - 1, False)
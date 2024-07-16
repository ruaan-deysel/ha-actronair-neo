"""Support for Actron Neo climate devices."""
from __future__ import annotations

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_FAN,
    FAN_MODE_AUTO,
    FAN_MODE_LOW,
    FAN_MODE_MEDIUM,
    FAN_MODE_HIGH,
)
from .actron_api import ActronNeoAPI

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = {
    HVAC_MODE_OFF: HVACMode.OFF,
    HVAC_MODE_HEAT: HVACMode.HEAT,
    HVAC_MODE_COOL: HVACMode.COOL,
    HVAC_MODE_AUTO: HVACMode.AUTO,
    HVAC_MODE_FAN: HVACMode.FAN_ONLY,
}

FAN_MODES = {
    FAN_MODE_AUTO: FAN_AUTO,
    FAN_MODE_LOW: FAN_LOW,
    FAN_MODE_MEDIUM: FAN_MEDIUM,
    FAN_MODE_HIGH: FAN_HIGH,
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Actron Neo climate devices."""
    api = hass.data[DOMAIN][config_entry.entry_id]
    zones_as_heater_coolers = config_entry.data.get("zones_as_heater_coolers", False)
    
    # Create the master climate entity
    entities = [ActronNeoClimate(api, None, zones_as_heater_coolers)]
    
    # Create climate entities for each zone
    for zone in api.zones:
        entities.append(ActronNeoClimate(api, zone['index'], zones_as_heater_coolers))
    
    async_add_entities(entities, True)

class ActronNeoClimate(ClimateEntity):
    """Representation of an Actron Neo climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, api: ActronNeoAPI, zone_index: int | None, zones_as_heater_coolers: bool) -> None:
        """Initialize the climate device."""
        self._api = api
        self._zone_index = zone_index
        self._zones_as_heater_coolers = zones_as_heater_coolers
        
        if zone_index is None:
            self._attr_name = "Actron Neo Master"
            self._attr_unique_id = f"{api.client_name}_climate_master"
            self._attr_hvac_modes = list(HVAC_MODES.values())
            self._attr_fan_modes = list(FAN_MODES.values())
        else:
            zone = next((z for z in api.zones if z['index'] == zone_index), None)
            if zone:
                self._attr_name = f"Actron Neo {zone['name']}"
                self._attr_unique_id = f"{api.client_name}_climate_zone_{zone_index}"
                if zones_as_heater_coolers:
                    self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
                else:
                    self._attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO]
            else:
                _LOGGER.error(f"Zone with index {zone_index} not found")
        
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        if zone_index is None:
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        
        self._attr_hvac_mode = None
        self._attr_fan_mode = None
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_min_temp = None
        self._attr_max_temp = None

    async def async_update(self) -> None:
        """Update the entity."""
        try:
            status = await self._api.get_status()
            
            if self._zone_index is None:
                # Master climate entity
                self._update_master(status)
            else:
                # Zone climate entity
                self._update_zone(status)
            
        except Exception as e:
            _LOGGER.error(f"Failed to update Actron Neo climate: {str(e)}")

    def _update_master(self, status):
        """Update the master climate entity."""
        if not status['lastKnownState']['UserAirconSettings']['isOn']:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            self._attr_hvac_mode = HVAC_MODES[status['lastKnownState']['UserAirconSettings']['Mode']]
        
        self._attr_fan_mode = FAN_MODES[status['lastKnownState']['UserAirconSettings']['FanMode']]
        self._attr_current_temperature = status['lastKnownState']['MasterInfo']['LiveTemp_oC']
        
        if self._attr_hvac_mode == HVACMode.COOL:
            self._attr_target_temperature = status['lastKnownState']['UserAirconSettings']['TemperatureSetpoint_Cool_oC']
        elif self._attr_hvac_mode == HVACMode.HEAT:
            self._attr_target_temperature = status['lastKnownState']['UserAirconSettings']['TemperatureSetpoint_Heat_oC']

    def _update_zone(self, status):
        """Update a zone climate entity."""
        zone = next((z for z in self._api.zones if z['index'] == self._zone_index), None)
        if zone:
            if not zone['enabled']:
                self._attr_hvac_mode = HVACMode.OFF
            elif self._zones_as_heater_coolers:
                self._attr_hvac_mode = HVAC_MODES[status['lastKnownState']['UserAirconSettings']['Mode']]
            else:
                self._attr_hvac_mode = HVACMode.AUTO
            
            self._attr_current_temperature = zone['current_temp']
            self._attr_target_temperature = zone['set_temp_cool'] if self._attr_hvac_mode == HVACMode.COOL else zone['set_temp_heat']
            self._attr_min_temp = zone['min_temp']
            self._attr_max_temp = zone['max_temp']
        else:
            _LOGGER.error(f"Zone with index {self._zone_index} not found during update")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        try:
            if self._zone_index is None:
                # Master climate entity
                if self._attr_hvac_mode == HVACMode.COOL:
                    await self._api.set_temperature(temperature, HVAC_MODE_COOL)
                elif self._attr_hvac_mode == HVACMode.HEAT:
                    await self._api.set_temperature(temperature, HVAC_MODE_HEAT)
            else:
                # Zone climate entity
                await self._api.set_zone_temperature(self._zone_index, temperature, 
                                                    HVAC_MODE_COOL if self._attr_hvac_mode == HVACMode.COOL else HVAC_MODE_HEAT)
        except Exception as e:
            _LOGGER.error(f"Failed to set temperature for Actron Neo: {str(e)}")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        try:
            if self._zone_index is None:
                # Master climate entity
                for key, value in HVAC_MODES.items():
                    if value == hvac_mode:
                        await self._api.set_hvac_mode(key)
                        break
            else:
                # Zone climate entity
                if self._zones_as_heater_coolers:
                    if hvac_mode == HVACMode.OFF:
                        await self._api.set_zone_state(self._zone_index, False)
                    else:
                        await self._api.set_zone_state(self._zone_index, True)
                        await self._api.set_hvac_mode(HVAC_MODE_COOL if hvac_mode == HVACMode.COOL else HVAC_MODE_HEAT)
                else:
                    await self._api.set_zone_state(self._zone_index, hvac_mode != HVACMode.OFF)
        except Exception as e:
            _LOGGER.error(f"Failed to set HVAC mode for Actron Neo: {str(e)}")

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if self._zone_index is not None:
            _LOGGER.warning("Fan mode can only be set on the master climate entity")
            return

        try:
            for key, value in FAN_MODES.items():
                if value == fan_mode:
                    await self._api.set_fan_mode(key)
                    break
        except Exception as e:
            _LOGGER.error(f"Failed to set fan mode for Actron Neo: {str(e)}")

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation mode."""
        return self._attr_hvac_mode

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._attr_current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._attr_target_temperature

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._attr_fan_mode
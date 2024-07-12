import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, ATTR_INDOOR_TEMPERATURE, ATTR_OUTDOOR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for system in coordinator.data:
        entities.append(ActronClimate(system, coordinator))
    async_add_entities(entities, True)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, system, coordinator):
        super().__init__(coordinator)
        self._system = system
        self._attr_name = system['name']
        self._attr_unique_id = f"{DOMAIN}_{system['serial']}"
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO]
        self._attr_fan_modes = ["AUTO", "LOW", "MEDIUM", "HIGH"]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE
        )

    @property
    def current_temperature(self):
        return self.coordinator.data[self._system['serial']].get(ATTR_INDOOR_TEMPERATURE)

    @property
    def target_temperature(self):
        return self.coordinator.data[self._system['serial']].get('TemperatureSetpoint_Cool_oC')

    @property
    def hvac_mode(self):
        if self.coordinator.data[self._system['serial']].get('isOn'):
            return HVACMode.COOL  # Assuming cool mode, adjust as needed
        return HVACMode.OFF

    @property
    def fan_mode(self):
        return self.coordinator.data[self._system['serial']].get('fanMode', 'AUTO')

    @property
    def extra_state_attributes(self):
        return {
            ATTR_OUTDOOR_TEMPERATURE: self.coordinator.data[self._system['serial']].get(ATTR_OUTDOOR_TEMPERATURE)
        }

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            await self.coordinator.api.send_command(self._system['serial'], {
                "UserAirconSettings.TemperatureSetpoint_Cool_oC": kwargs[ATTR_TEMPERATURE],
                "type": "set-settings"
            })
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            command = {"isOn": False}
        else:
            command = {"isOn": True, "mode": hvac_mode.upper()}
        await self.coordinator.api.send_command(self._system['serial'], command)
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode):
        await self.coordinator.api.send_command(self._system['serial'], {"fanMode": fan_mode})
        await self.coordinator.async_request_refresh()
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode, PRESET_AWAY, PRESET_NONE
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, HVAC_MODES, FAN_MODES
from .coordinator import ActronDataCoordinator
from .zone import ActronZone

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the Actron Air Neo climate devices."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for zone_id in coordinator.data["zones"]:
        entities.append(ActronClimate(coordinator, ActronZone(coordinator, zone_id)))

    async_add_entities(entities)

class ActronClimate(CoordinatorEntity, ClimateEntity):
    def __init__(self, coordinator: ActronDataCoordinator, zone: ActronZone):
        super().__init__(coordinator)
        self._zone = zone
        self._attr_name = f"Actron Air Neo {zone.zone_id}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_{zone.zone_id}"
        self._attr_hvac_modes = list(HVAC_MODES.values())
        self._attr_fan_modes = FAN_MODES
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.FAN_MODE |
            ClimateEntityFeature.PRESET_MODE
        )
        self._attr_preset_modes = [PRESET_NONE, PRESET_AWAY]

    @property
    def current_temperature(self) -> float | None:
        return self._zone.temperature

    @property
    def target_temperature(self) -> float | None:
        if self.hvac_mode == HVACMode.COOL:
            return self._zone.target_temperature_cool
        elif self.hvac_mode == HVACMode.HEAT:
            return self._zone.target_temperature_heat
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data['main']['is_on']:
            return HVACMode.OFF
        return HVAC_MODES.get(self.coordinator.data['main']['mode'], HVACMode.OFF)

    @property
    def fan_mode(self) -> str | None:
        return self.coordinator.data['main']['fan_mode']

    @property
    def preset_mode(self) -> str | None:
        return PRESET_AWAY if self.coordinator.data['main']['away_mode'] else PRESET_NONE

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            await self._zone.set_temperature(temp, self.coordinator.data['main']['mode'])

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        try:
            if hvac_mode == HVACMode.OFF:
                await self.coordinator.api.send_command(self.coordinator.device_id, {"UserAirconSettings.isOn": False})
            else:
                await self.coordinator.api.send_command(self.coordinator.device_id, {
                    "UserAirconSettings.isOn": True,
                    "UserAirconSettings.Mode": hvac_mode.upper()
                })
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set HVAC mode: %s", err)
            raise

    async def async_set_fan_mode(self, fan_mode: str):
        try:
            await self.coordinator.api.send_command(self.coordinator.device_id, {"UserAirconSettings.FanMode": fan_mode})
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set fan mode: %s", err)
            raise

    async def async_set_preset_mode(self, preset_mode: str):
        try:
            if preset_mode == PRESET_AWAY:
                await self.coordinator.set_away_mode(True)
            else:  # PRESET_NONE
                await self.coordinator.set_away_mode(False)
        except Exception as err:
            _LOGGER.error("Failed to set preset mode: %s", err)
            raise

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": f"Actron Air Neo {self._zone.zone_id}",
            "manufacturer": "Actron Air",
            "model": "Neo",
        }
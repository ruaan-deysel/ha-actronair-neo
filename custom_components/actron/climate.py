import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from .api import ActronApi

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = ActronApi(
        username=config_entry.data["username"],
        password=config_entry.data["password"],
        device_id=config_entry.data["device_id"]
    )
    await api.authenticate()
    systems = await api.list_ac_systems()

    entities = []
    for system in systems:
        if isinstance(system, dict) and "name" in system and "serial" in system:
            entities.append(ActronClimate(system, api))
        else:
            _LOGGER.error(f"Unexpected system data structure: {system}")

    async_add_entities(entities, update_before_add=True)

class ActronClimate(ClimateEntity):
    def __init__(self, system, api):
        _LOGGER.debug(f"Initializing ActronClimate with system: {system}")
        self._system = system
        self._api = api
        self._name = system['name']
        self._unique_id = system['serial']
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
        self._attr_fan_modes = ["AUTO", "LOW", "MEDIUM", "HIGH"]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        self._target_temperature = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def hvac_mode(self):
        return self._attr_hvac_modes

    @property
    def fan_mode(self):
        return self._attr_fan_modes

    @property
    def temperature_unit(self):
        return self._attr_temperature_unit

    @property
    def supported_features(self):
        return self._attr_supported_features

    async def async_update(self):
        try:
            status = await self._api.get_ac_status(self._unique_id)
            _LOGGER.debug(f"AC status: {status}")
            if "UserAirconSettings" in status:
                user_settings = status["UserAirconSettings"]
                self._target_temperature = user_settings.get("TemperatureSetpoint_Cool_oC", None)
            else:
                _LOGGER.error("UserAirconSettings not available in the response.")
                _LOGGER.debug(f"Full API response: {status}")
        except KeyError as e:
            _LOGGER.error(f"Key error in AC status response: {e}")
            _LOGGER.debug(f"Full API response: {status}")
        except Exception as e:
            _LOGGER.error(f"Error updating AC status: {e}")

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            self._target_temperature = kwargs[ATTR_TEMPERATURE]
            await self._api.send_command(self._unique_id, {
                "UserAirconSettings.TemperatureSetpoint_Cool_oC": self._target_temperature,
                "type": "set-settings"
            })
        self.async_write_ha_state()

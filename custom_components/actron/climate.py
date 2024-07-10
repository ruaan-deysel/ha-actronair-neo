# File: custom_components/actron_air_neo/climate.py
import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature
)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from .api import ActronApi

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

HVAC_MODES = {
    "OFF": HVACMode.OFF,
    "HEAT": HVACMode.HEAT,
    "COOL": HVACMode.COOL,
    "AUTO": HVACMode.AUTO,
    "FAN": HVACMode.FAN_ONLY
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = ActronApi(
        username=config_entry.data["username"],
        password=config_entry.data["password"],
        device_id=config_entry.data["device_id"]
    )
    await api.authenticate()
    systems = await api.list_ac_systems()
    
    _LOGGER.debug(f"AC systems: {systems}")
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
        self._name = system.get("name")
        self._unique_id = system.get("serial")
        self._state = None
        self._target_temperature = None
        self._current_temperature = None
        self._fan_mode = None
        self._hvac_mode = None

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_modes(self):
        return list(HVAC_MODES.values())

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def fan_mode(self):
        return self._fan_mode

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            self._target_temperature = kwargs[ATTR_TEMPERATURE]
            await self._api.send_command(self._unique_id, {
                "UserAirconSettings.TemperatureSetpoint_Cool_oC": self._target_temperature,
                "type": "set-settings"
            })
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            command = {"UserAirconSettings.isOn": False, "type": "set-settings"}
        else:
            command = {"UserAirconSettings.isOn": True, "UserAirconSettings.Mode": hvac_mode, "type": "set-settings"}
        await self._api.send_command(self._unique_id, command)
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        self._fan_mode = fan_mode
        await self._api.send_command(self._unique_id, {
            "UserAirconSettings.FanMode": fan_mode,
            "type": "set-settings"
        })
        self.async_write_ha_state()

    async def async_update(self):
        try:
            status = await self._api.get_ac_status(self._unique_id)
            _LOGGER.debug(f"AC status: {status}")
            self._state = status["UserAirconSettings"]["isOn"]
            self._current_temperature = status["SystemStatus_Local"]["SensorInputs"]["SHTC1"]["Temperature_oC"]
            self._target_temperature = status["UserAirconSettings"]["TemperatureSetpoint_Cool_oC"]
            self._fan_mode = status["UserAirconSettings"]["FanMode"]
            self._hvac_mode = HVAC_MODES[status["UserAirconSettings"]["Mode"]]
        except KeyError as e:
            _LOGGER.error(f"Key error in AC status response: {e}")
        except Exception as e:
            _LOGGER.error(f"Error updating AC status: {e}")

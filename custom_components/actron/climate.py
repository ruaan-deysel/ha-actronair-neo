# File: custom_components/actron_ac/climate.py
import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_AUTO, HVAC_MODE_FAN_ONLY,
    SUPPORT_FAN_MODE, SUPPORT_TARGET_TEMPERATURE
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from .api import ActronApi

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

HVAC_MODES = {
    "OFF": HVAC_MODE_OFF,
    "HEAT": HVAC_MODE_HEAT,
    "COOL": HVAC_MODE_COOL,
    "AUTO": HVAC_MODE_AUTO,
    "FAN": HVAC_MODE_FAN_ONLY
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = ActronApi(
        username=config_entry.data["username"],
        password=config_entry.data["password"],
        device_name=config_entry.data["device_name"],
        device_id=config_entry.data["device_id"]
    )
    api.authenticate()
    systems = api.list_ac_systems()
    
    entities = []
    for system in systems:
        entities.append(ActronClimate(system, api))
    
    async_add_entities(entities, update_before_add=True)

class ActronClimate(ClimateEntity):
    def __init__(self, system, api):
        self._system = system
        self._api = api
        self._name = system["name"]
        self._unique_id = system["serial"]
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
        return TEMP_CELSIUS

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

    def set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            self._target_temperature = kwargs[ATTR_TEMPERATURE]
            self._api.send_command(self._unique_id, {
                "UserAirconSettings.TemperatureSetpoint_Cool_oC": self._target_temperature,
                "type": "set-settings"
            })
        self.schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_OFF:
            command = {"UserAirconSettings.isOn": False, "type": "set-settings"}
        else:
            command = {"UserAirconSettings.isOn": True, "UserAirconSettings.Mode": HVAC_MODES[hvac_mode], "type": "set-settings"}
        self._api.send_command(self._unique_id, command)
        self.schedule_update_ha_state()

    def set_fan_mode(self, fan_mode):
        self._fan_mode = fan_mode
        self._api.send_command(self._unique_id, {
            "UserAirconSettings.FanMode": fan_mode,
            "type": "set-settings"
        })
        self.schedule_update_ha_state()

    def update(self):
        status = self._api.get_ac_status(self._unique_id)
        self._state = status["isOn"]
        self._current_temperature = status["currentTemperature"]
        self._target_temperature = status["targetTemperature"]
        self._fan_mode = status["fanMode"]
        self._hvac_mode = HVAC_MODES[status["mode"]]

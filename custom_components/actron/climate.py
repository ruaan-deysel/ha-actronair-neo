"""Platform for Actron Neo climate integration."""

import logging
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    SUPPORT_TARGET_TEMPERATURE
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Actron Neo climate platform."""
    _LOGGER.info("Setting up Actron Neo climate platform")

    api = hass.data["actron_neo"]["api"]
    zones = hass.data["actron_neo"]["zones"]
    entities = [ActronNeoClimate(api, zone["id"], zone["name"]) for zone in zones]
    async_add_entities(entities)

class ActronNeoClimate(ClimateEntity):
    """Representation of an Actron Neo climate entity."""

    def __init__(self, api, zone_id, zone_name):
        """Initialize the climate entity."""
        self._api = api
        self._zone_id = zone_id
        self._name = f"Actron Neo Zone {zone_name}"
        self._hvac_mode = HVAC_MODE_OFF
        self._target_temperature = None
        self._current_temperature = None
        self._zone_enabled = None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def hvac_modes(self):
        """Return the list of available HVAC modes."""
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT, HVAC_MODE_COOL]

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            self._target_temperature = kwargs[ATTR_TEMPERATURE]
            self._api.set_temperature(self._zone_id, self._target_temperature)

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self._hvac_mode = hvac_mode
        self._api.set_hvac_mode(self._zone_id, self._hvac_mode)

    @property
    def is_on(self):
        """Return true if the zone is enabled."""
        return self._zone_enabled

    def turn_on(self):
        """Turn the zone on."""
        self._api.set_zone_state(self._zone_id, True)
        self._zone_enabled = True

    def turn_off(self):
        """Turn the zone off."""
        self._api.set_zone_state(self._zone_id, False)
        self._zone_enabled = False

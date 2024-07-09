"""Platform for Actron Air Neo switch integration."""

import logging
from homeassistant.components.switch import SwitchEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Actron Neo switch entities from a config entry."""
    _LOGGER.info("Setting up Actron Neo switch platform")

    api = hass.data["actron_neo"]["api"]
    zones = hass.data["actron_neo"]["zones"]
    entities = [ActronNeoZoneSwitch(api, zone["id"], zone["name"]) for zone in zones]
    async_add_entities(entities, update_before_add=True)

class ActronNeoZoneSwitch(SwitchEntity):
    """Representation of an Actron Neo zone switch."""

    def __init__(self, api, zone_id, zone_name):
        """Initialize the switch entity."""
        self._api = api
        self._zone_id = zone_id
        self._name = f"Actron Neo Zone {zone_name} Switch"
        self._is_on = False

    @property
    def name(self):
        """Return the name of the switch entity."""
        return self._name

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._api.set_zone_state(self._zone_id, True)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._api.set_zone_state(self._zone_id, False)
        self._is_on = False
        self.async_write_ha_state()

    async def async_update(self):
        """Fetch new state data for the entity."""
        status = await self._api.get_status()
        if status:
            for zone in status.get("zones", []):
                if zone.get("zoneId") == self._zone_id:
                    self._is_on = zone.get("enabled")
                    break

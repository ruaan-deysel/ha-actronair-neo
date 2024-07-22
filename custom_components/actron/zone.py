from homeassistant.components.switch import SwitchEntity
import logging

_LOGGER = logging.getLogger(__name__)

class ActronZone(SwitchEntity):
    def __init__(self, api, zone_name):
        self.api = api
        self.zone_name = zone_name

    @property
    async def async_is_on(self):
        status = await self.api.get_status()
        zone_status = any(zone["zoneName"] == self.zone_name and zone["zoneEnabled"] for zone in status["zoneCurrentStatus"])
        _LOGGER.debug("Zone %s is on: %s", self.zone_name, zone_status)
        return zone_status

    async def async_turn_on(self, **kwargs):
        _LOGGER.info("Turning on zone %s", self.zone_name)
        await self.api.set_zone_state(self.zone_name, True)

    async def async_turn_off(self, **kwargs):
        _LOGGER.info("Turning off zone %s", self.zone_name)
        await self.api.set_zone_state(self.zone_name, False)

from homeassistant.components.climate import ClimateEntity
from homeassistant.const import TEMP_CELSIUS
import logging

_LOGGER = logging.getLogger(__name__)

class ActronClimate(ClimateEntity):
    def __init__(self, api):
        self.api = api

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    async def async_current_temperature(self):
        status = await self.api.get_status()
        _LOGGER.debug("Current temperature: %s", status["masterCurrentTemp"])
        return status["masterCurrentTemp"]

    async def async_set_temperature(self, **kwargs):
        target_temp = kwargs.get("temperature")
        _LOGGER.info("Setting target temperature to %s", target_temp)
        await self.api.set_target_temperature(target_temp)

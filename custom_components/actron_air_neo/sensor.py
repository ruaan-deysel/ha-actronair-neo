from homeassistant.helpers.entity import Entity
from homeassistant.const import TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, DEVICE_CLASS_HUMIDITY
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Actron Neo sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        ActronTemperatureSensor(coordinator),
        ActronHumiditySensor(coordinator),
    ])

class ActronTemperatureSensor(Entity):
    """Representation of a Actron Neo Temperature Sensor."""

    def __init__(self, coordinator):
        self._coordinator = coordinator
        self._name = "Actron Temperature"
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        """Return the device class."""
        return DEVICE_CLASS_TEMPERATURE

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.info("Updating Actron Temperature Sensor")
        await self._coordinator.async_request_refresh()
        status = self._coordinator.data
        self._state = status.get("masterCurrentTemp")
        _LOGGER.debug("Current Temperature: %s", self._state)

class ActronHumiditySensor(Entity):
    """Representation of a Actron Neo Humidity Sensor."""

    def __init__(self, coordinator):
        self._coordinator = coordinator
        self._name = "Actron Humidity"
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    @property
    def device_class(self):
        """Return the device class."""
        return DEVICE_CLASS_HUMIDITY

    async def async_update(self):
        """Fetch new state data for the sensor."""
        _LOGGER.info("Updating Actron Humidity Sensor")
        await self._coordinator.async_request_refresh()
        status = self._coordinator.data
        self._state = status.get("masterCurrentHumidity")
        _LOGGER.debug("Current Humidity: %s", self._state)

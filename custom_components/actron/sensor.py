# File: custom_components/actron_air_neo/sensor.py
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.const import UnitOfTemperature
from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
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
            entities.append(ActronTemperatureSensor(system, api))
            entities.append(ActronHumiditySensor(system, api))
        else:
            _LOGGER.error(f"Unexpected system data structure: {system}")

    async_add_entities(entities, update_before_add=True)

class ActronTemperatureSensor(SensorEntity):
    def __init__(self, system, api):
        _LOGGER.debug(f"Initializing ActronTemperatureSensor with system: {system}")
        self._system = system
        self._api = api
        self._name = f"{system['name']} Temperature"
        self._unique_id = f"{system['serial']}_temperature"
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return UnitOfTemperature.CELSIUS

    @property
    def device_class(self):
        return SensorDeviceClass.TEMPERATURE

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    async def async_update(self):
        status = await self._api.get_ac_status(self._system["serial"])
        self._state = status["currentTemperature"]

class ActronHumiditySensor(SensorEntity):
    def __init__(self, system, api):
        _LOGGER.debug(f"Initializing ActronHumiditySensor with system: {system}")
        self._system = system
        self._api = api
        self._name = f"{system['name']} Humidity"
        self._unique_id = f"{system['serial']}_humidity"
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    async def async_update(self):
        status = await self._api.get_ac_status(self._system["serial"])
        self._state = status["currentHumidity"]

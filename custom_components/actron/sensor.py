# File: custom_components/actron_ac/sensor.py
import logging
from homeassistant.helpers.entity import Entity
from homeassistant.const import TEMP_CELSIUS, HUMIDITY_PERCENTAGE
from .api import ActronApi

_LOGGER = logging.getLogger(__name__)

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
        entities.append(ActronTemperatureSensor(system, api))
        entities.append(ActronHumiditySensor(system, api))

    async_add_entities(entities, update_before_add=True)

class ActronTemperatureSensor(Entity):
    def __init__(self, system, api):
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
        return TEMP_CELSIUS

    def update(self):
        status = self._api.get_ac_status(self._system["serial"])
        self._state = status["currentTemperature"]

class ActronHumiditySensor(Entity):
    def __init__(self, system, api):
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
        return HUMIDITY_PERCENTAGE

    def update(self):
        status = self._api.get_ac_status(self._system["serial"])
        self._state = status["currentHumidity"]

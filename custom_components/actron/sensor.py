import logging
from homeassistant.helpers.entity import Entity
from homeassistant.const import UnitOfTemperature, PERCENTAGE
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
            entities.append(ActronBatterySensor(system, api))
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
        try:
            status = await self._api.get_ac_status(self._system["serial"])
            _LOGGER.debug(f"AC status: {status}")
            # Check if the required keys exist in the response
            system_status = status.get("SystemStatus_Local", {})
            sensor_inputs = system_status.get("SensorInputs", {})
            shtc1 = sensor_inputs.get("SHTC1", {})
            temperature = shtc1.get("Temperature_oC", None)
            
            if temperature is not None:
                self._state = temperature
            else:
                _LOGGER.error("Temperature data not available in the response.")
                _LOGGER.debug(f"Full API response: {status}")
        except KeyError as e:
            _LOGGER.error(f"Key error in temperature sensor response: {e}")
            _LOGGER.debug(f"Full API response: {status}")
        except Exception as e:
            _LOGGER.error(f"Error updating temperature sensor: {e}")

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
        return PERCENTAGE

    @property
    def device_class(self):
        return SensorDeviceClass.HUMIDITY

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    async def async_update(self):
        try:
            status = await self._api.get_ac_status(self._system["serial"])
            _LOGGER.debug(f"AC status: {status}")
            system_status = status.get("SystemStatus_Local", {})
            sensor_inputs = system_status.get("SensorInputs", {})
            shtc1 = sensor_inputs.get("SHTC1", {})
            humidity = shtc1.get("RelativeHumidity_pc", None)
            
            if humidity is not None:
                self._state = humidity
            else:
                _LOGGER.error("Humidity data not available in the response.")
                _LOGGER.debug(f"Full API response: {status}")
        except KeyError as e:
            _LOGGER.error(f"Key error in humidity sensor response: {e}")
            _LOGGER.debug(f"Full API response: {status}")
        except Exception as e:
            _LOGGER.error(f"Error updating humidity sensor: {e}")

class ActronBatterySensor(SensorEntity):
    def __init__(self, system, api):
        _LOGGER.debug(f"Initializing ActronBatterySensor with system: {system}")
        self._system = system
        self._api = api
        self._name = f"{system['name']} Battery"
        self._unique_id = f"{system['serial']}_battery"
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
        return PERCENTAGE

    @property
    def device_class(self):
        return SensorDeviceClass.BATTERY

    @property
    def state_class(self):
        return SensorStateClass.MEASUREMENT

    async def async_update(self):
        try:
            status = await self._api.get_ac_status(self._system["serial"])
            _LOGGER.debug(f"AC status: {status}")
            system_status = status.get("SystemStatus_Local", {})
            sensor_inputs = system_status.get("SensorInputs", {})
            battery = sensor_inputs.get("Battery", {})
            battery_level = battery.get("Level", None)
            
            if battery_level is not None:
                self._state = battery_level
            else:
                _LOGGER.error("Battery data not available in the response.")
                _LOGGER.debug(f"Full API response: {status}")
        except KeyError as e:
            _LOGGER.error(f"Key error in battery sensor response: {e}")
            _LOGGER.debug(f"Full API response: {status}")
        except Exception as e:
            _LOGGER.error(f"Error updating battery sensor: {e}")

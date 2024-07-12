import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
)
from .const import DOMAIN, ATTR_INDOOR_TEMPERATURE, ATTR_OUTDOOR_TEMPERATURE, ATTR_FILTER_LIFE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for system in coordinator.data:
        entities.extend([
            ActronTemperatureSensor(system, coordinator, "indoor"),
            ActronTemperatureSensor(system, coordinator, "outdoor"),
            ActronFilterLifeSensor(system, coordinator),
        ])
    async_add_entities(entities, True)

class ActronTemperatureSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, system, coordinator, sensor_type):
        super().__init__(coordinator)
        self._system = system
        self._sensor_type = sensor_type
        self._attr_name = f"{system['name']} {sensor_type.capitalize()} Temperature"
        self._attr_unique_id = f"{DOMAIN}_{system['serial']}_{sensor_type}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        attr = ATTR_INDOOR_TEMPERATURE if self._sensor_type == "indoor" else ATTR_OUTDOOR_TEMPERATURE
        return self.coordinator.data[self._system['serial']].get(attr)

class ActronFilterLifeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, system, coordinator):
        super().__init__(coordinator)
        self._system = system
        self._attr_name = f"{system['name']} Filter Life"
        self._attr_unique_id = f"{DOMAIN}_{system['serial']}_filter_life"
        self._attr_device_class = SensorDeviceClass.BATTERY  # Using battery as an analog for filter life
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        return self.coordinator.data[self._system['serial']].get(ATTR_FILTER_LIFE)
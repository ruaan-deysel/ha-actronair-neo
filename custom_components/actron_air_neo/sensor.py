"""Support for Actron Air Neo sensors."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEVICE_MANUFACTURER, DEVICE_MODEL
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Actron Neo sensors from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ActronTemperatureSensor(coordinator, "indoor"),
        ActronTemperatureSensor(coordinator, "wall"),
        ActronHumiditySensor(coordinator),
        ActronInfoSensor(coordinator, "model"),
        ActronInfoSensor(coordinator, "serial_number"),
        ActronInfoSensor(coordinator, "firmware_version"),
    ])

class ActronTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, sensor_type: str):
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self._attr_name = f"ActronAir {sensor_type.capitalize()} Temperature"
        self._attr_unique_id = f"{coordinator.device_id}_{sensor_type}_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data['main'].get(f'{self.sensor_type}_temp')

class ActronHumiditySensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Humidity Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "ActronAir Indoor Humidity"
        self._attr_unique_id = f"{coordinator.device_id}_indoor_humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data['main'].get('indoor_humidity')

class ActronInfoSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Info Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, info_type: str):
        super().__init__(coordinator)
        self.info_type = info_type
        self._attr_name = f"ActronAir {info_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{coordinator.device_id}_{info_type}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data['main'].get(self.info_type)

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
            "sw_version": self.coordinator.data['main'].get('firmware_version'),
        }
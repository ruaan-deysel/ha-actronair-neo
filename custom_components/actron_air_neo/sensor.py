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

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up Actron Neo sensors from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ActronTemperatureSensor(coordinator),
        ActronHumiditySensor(coordinator),
        ActronOutdoorTemperatureSensor(coordinator),
    ])

class ActronTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "ActronAir Indoor Temperature"
        self._attr_unique_id = f"{coordinator.device_id}_indoor_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data['main'].get('indoor_temp')

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "is_on": self.coordinator.data['main'].get('is_on'),
            "mode": self.coordinator.data['main'].get('mode'),
            "compressor_state": self.coordinator.data['main'].get('compressor_state'),
        }

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

class ActronOutdoorTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Outdoor Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "ActronAir Outdoor Temperature"
        self._attr_unique_id = f"{coordinator.device_id}_outdoor_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data['main'].get('outdoor_temp')

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "fan_mode": self.coordinator.data['main'].get('fan_mode'),
        }
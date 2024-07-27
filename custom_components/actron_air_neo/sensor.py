from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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
    ])

class ActronTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Actron Temperature"
        self._attr_unique_id = f"{coordinator.device_id}_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = SensorDeviceClass.TEMPERATURE

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            return self.coordinator.data['main'].get('indoor_temp')
        except Exception as e:
            _LOGGER.error(f"Error getting temperature value: {e}")
            return None

class ActronHumiditySensor(CoordinatorEntity, SensorEntity):
    """Representation of an Actron Neo Humidity Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator):
        super().__init__(coordinator)
        self._attr_name = "Actron Humidity"
        self._attr_unique_id = f"{coordinator.device_id}_humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = SensorDeviceClass.HUMIDITY

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            return self.coordinator.data['main'].get('indoor_humidity')
        except Exception as e:
            _LOGGER.error(f"Error getting humidity value: {e}")
            return None
"""Support for ActronAir Neo sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo sensors from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ActronTemperatureSensor(coordinator, "indoor"),
        ActronHumiditySensor(coordinator, "indoor"),
    ]

    # Add zone sensors
    for zone_id, zone_data in coordinator.data['zones'].items():
        entities.extend([
            ActronZoneTemperatureSensor(coordinator, zone_id),
            ActronZoneHumiditySensor(coordinator, zone_id),
        ])

    async_add_entities(entities)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for ActronAir Neo sensors."""

    def __init__(
        self, 
        coordinator: ActronDataCoordinator, 
        sensor_type: str,
        device_class: SensorDeviceClass,
        name: str,
        unit_of_measurement: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_device_class = device_class
        self._attr_name = f"ActronAir Neo {name}"
        self._attr_unique_id = f"{coordinator.device_id}_{sensor_type}"
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": "ActronAir",
            "model": self.coordinator.data["main"]["model"],
            "sw_version": self.coordinator.data["main"]["firmware_version"],
        }

class ActronTemperatureSensor(ActronSensorBase):
    """Representation of an ActronAir Neo Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, location: str) -> None:
        """Initialize the temperature sensor."""
        super().__init__(
            coordinator,
            f"{location}_temperature",
            SensorDeviceClass.TEMPERATURE,
            f"{location.capitalize()} Temperature",
            UnitOfTemperature.CELSIUS,
        )
        self._location = location

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data["main"]["indoor_temp"]

class ActronHumiditySensor(ActronSensorBase):
    """Representation of an ActronAir Neo Humidity Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, location: str) -> None:
        """Initialize the humidity sensor."""
        super().__init__(
            coordinator,
            f"{location}_humidity",
            SensorDeviceClass.HUMIDITY,
            f"{location.capitalize()} Humidity",
            PERCENTAGE,
        )
        self._location = location

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self.coordinator.data["main"]["indoor_humidity"]

class ActronZoneTemperatureSensor(ActronSensorBase):
    """Representation of an ActronAir Neo Zone Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone temperature sensor."""
        zone_name = coordinator.data['zones'][zone_id]['name']
        super().__init__(
            coordinator,
            f"{zone_id}_temperature",
            SensorDeviceClass.TEMPERATURE,
            f"Zone {zone_name} Temperature",
            UnitOfTemperature.CELSIUS,
        )
        self._zone_id = zone_id

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data['zones'][self._zone_id]['temp']

class ActronZoneHumiditySensor(ActronSensorBase):
    """Representation of an ActronAir Neo Zone Humidity Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone humidity sensor."""
        zone_name = coordinator.data['zones'][zone_id]['name']
        super().__init__(
            coordinator,
            f"{zone_id}_humidity",
            SensorDeviceClass.HUMIDITY,
            f"Zone {zone_name} Humidity",
            PERCENTAGE,
        )
        self._zone_id = zone_id

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        return self.coordinator.data['zones'][self._zone_id]['humidity']
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Actron Air Neo sensors."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for zone_id in coordinator.data["zones"]:
        entities.extend([
            ActronZoneTemperatureSensor(coordinator, zone_id),
            ActronZoneHumiditySensor(coordinator, zone_id),
        ])

    async_add_entities(entities)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Actron Air Neo sensors."""

    def __init__(
        self,
        coordinator: ActronDataCoordinator,
        zone_id: str,
        name: str,
        device_class: SensorDeviceClass,
        state_class: SensorStateClass,
        native_unit_of_measurement: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_name = f"Actron Air Neo {coordinator.data['zones'][zone_id]['name']} {name}"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.device_id}_zone_{zone_id}_{name.lower().replace(' ', '_')}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = native_unit_of_measurement

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "Actron Air Neo",
            "manufacturer": "Actron Air",
            "model": "Neo",
        }

class ActronZoneTemperatureSensor(ActronSensorBase):
    """Representation of an Actron Air Neo zone temperature sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        """Initialize the temperature sensor."""
        super().__init__(
            coordinator,
            zone_id,
            "Temperature",
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
            UnitOfTemperature.CELSIUS,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data['zones'][self._zone_id]['temp']

class ActronZoneHumiditySensor(ActronSensorBase):
    """Representation of an Actron Air Neo zone humidity sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str):
        """Initialize the humidity sensor."""
        super().__init__(
            coordinator,
            zone_id,
            "Humidity",
            SensorDeviceClass.HUMIDITY,
            SensorStateClass.MEASUREMENT,
            PERCENTAGE,
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data['zones'][self._zone_id]['humidity']
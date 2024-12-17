"""Support for ActronAir Neo sensors."""
from __future__ import annotations

import logging
from typing import Any, Final

from homeassistant.components.sensor import ( # type: ignore
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry # type: ignore
from homeassistant.const import UnitOfTemperature # type: ignore
from homeassistant.core import HomeAssistant # type: ignore
from homeassistant.helpers.entity_platform import AddEntitiesCallback # type: ignore
from homeassistant.helpers.typing import StateType # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity # type: ignore

from .const import (
    DOMAIN,
    ATTR_BATTERY_LEVEL,
    ATTR_ZONE_NAME,
    ATTR_ZONE_TYPE,
    ATTR_SIGNAL_STRENGTH,
    ATTR_LAST_UPDATED,
)
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo sensors from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        ActronMainSensor(coordinator),
    ]

    # Add zone sensors
    for zone_id, zone_data in coordinator.data['zones'].items():
        _LOGGER.debug(f"Adding zone sensor for {zone_id}: {zone_data}")
        entities.append(ActronZoneSensor(coordinator, zone_id))

    async_add_entities(entities)

class ActronSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for ActronAir Neo sensors."""

    _attr_has_entity_name: Final = True

    def __init__(
        self, 
        coordinator: ActronDataCoordinator,
        unique_id: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.device_id}_{unique_id}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
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

class ActronMainSensor(ActronSensorBase):
    """Representation of the main ActronAir Neo Temperature Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the main temperature sensor."""
        super().__init__(
            coordinator,
            "main_temperature",
            "Indoor Temperature",
        )

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data["main"]["indoor_temp"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "humidity": self.coordinator.data["main"]["indoor_humidity"],
        }

class ActronZoneSensor(ActronSensorBase):
    """Representation of an ActronAir Neo Zone Sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone sensor."""
        self._zone_id = zone_id
        zone_data = coordinator.data['zones'][zone_id]
        
        # Just use the zone name directly
        super().__init__(
            coordinator,
            f"zone_{zone_id}_temperature",
            f"Zone {zone_data['name']}",
        )

    @property
    def native_value(self) -> StateType:
        """Return the temperature of the zone."""
        try:
            return self.coordinator.data['zones'][self._zone_id]['temp']
        except KeyError as err:
            _LOGGER.error("Failed to get temperature for zone %s: %s", self._zone_id, err)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self._zone_id in self.coordinator.data['zones']
            and self.coordinator.data['zones'][self._zone_id].get('temp') is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return zone specific attributes including humidity and battery level."""
        try:
            zone_data = self.coordinator.data['zones'][self._zone_id]
            peripheral_data = self.coordinator.get_zone_peripheral(self._zone_id)
            
            attributes = {
                ATTR_ZONE_NAME: zone_data['name'],
                "humidity": zone_data['humidity'],
                "enabled": zone_data['is_enabled'],
            }

            # Add battery level and other peripheral information if available
            if peripheral_data:
                if "RemainingBatteryCapacity_pc" in peripheral_data:
                    attributes[ATTR_BATTERY_LEVEL] = peripheral_data["RemainingBatteryCapacity_pc"]
                if "DeviceType" in peripheral_data:
                    attributes[ATTR_ZONE_TYPE] = peripheral_data["DeviceType"]
                if "Signal_of3" in peripheral_data and peripheral_data["Signal_of3"] != "NA":
                    attributes[ATTR_SIGNAL_STRENGTH] = peripheral_data["Signal_of3"]
                if "LastConnectionTime" in peripheral_data:
                    attributes[ATTR_LAST_UPDATED] = peripheral_data["LastConnectionTime"]
                if "ConnectionState" in peripheral_data:
                    attributes["connection_state"] = peripheral_data["ConnectionState"]

            _LOGGER.debug(f"Zone {self._zone_id} attributes: {attributes}")
            return attributes
            
        except Exception as ex:
            _LOGGER.error("Error getting attributes for zone %s: %s", self._zone_id, str(ex))
            return {}
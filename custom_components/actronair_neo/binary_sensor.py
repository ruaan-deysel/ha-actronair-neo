"""Support for ActronAir Neo diagnostic sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory  # Add this import
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo diagnostic sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ActronFilterStatusSensor(coordinator),
        ActronSystemStatusSensor(coordinator),
    ]
    async_add_entities(entities)

class ActronDiagnosticBase(CoordinatorEntity):
    """Base class for diagnostic entities."""
    
    def __init__(self, coordinator: ActronDataCoordinator, unique_suffix: str, name: str) -> None:
        """Initialize the base diagnostic entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_{unique_suffix}"
        self._attr_name = name
        self._attr_entity_category = EntityCategory.DIAGNOSTIC  # Use proper enum
        
    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.device_id)},
            "name": "ActronAir Neo",
            "manufacturer": "ActronAir",
            "model": self.coordinator.data["main"]["model"],
            "sw_version": self.coordinator.data["main"]["firmware_version"],
        }

class ActronFilterStatusSensor(ActronDiagnosticBase, BinarySensorEntity):
    """Binary sensor for filter status."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the filter status sensor."""
        super().__init__(coordinator, "filter_status", "Filter Status")

    @property
    def is_on(self) -> bool:
        """Return True if filter needs cleaning."""
        return self.coordinator.data["main"].get("filter_clean_required", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        return {
            "last_cleaned": "Unknown",  # Could be added if API provides this
            "recommended_cleaning_interval": "3 months",
            "status": "Needs Cleaning" if self.is_on else "Clean",
        }

class ActronSystemStatusSensor(ActronDiagnosticBase, BinarySensorEntity):
    """Binary sensor for system status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:hvac"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the system status sensor."""
        super().__init__(coordinator, "system_status", "System Status")

    @property
    def is_on(self) -> bool:
        """Return True if system is running."""
        return self.coordinator.data["main"]["is_on"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        data = self.coordinator.data["main"]
        
        # Get zone statuses
        zones = {}
        for zone_id, zone_data in self.coordinator.data.get("zones", {}).items():
            zones[zone_data["name"]] = {
                "enabled": zone_data["is_enabled"],
                "temperature": zone_data["temp"],
                "humidity": zone_data["humidity"]
            }
            
            # Add battery info for wireless zones
            peripheral_data = self.coordinator.get_zone_peripheral(zone_id)
            if peripheral_data and "RemainingBatteryCapacity_pc" in peripheral_data:
                zones[zone_data["name"]]["battery_level"] = peripheral_data["RemainingBatteryCapacity_pc"]
                zones[zone_data["name"]]["signal_strength"] = peripheral_data.get("Signal_of3", "Unknown")

        return {
            "compressor_state": data.get("compressor_state", "Unknown"),
            "operating_mode": data.get("mode", "Unknown"),
            "fan_mode": data.get("fan_mode", "Unknown"),
            "defrosting": data.get("defrosting", False),
            "quiet_mode": data.get("quiet_mode", False),
            "away_mode": data.get("away_mode", False),
            "indoor_temperature": data.get("indoor_temp"),
            "indoor_humidity": data.get("indoor_humidity"),
            "filter_status": "Needs Cleaning" if data.get("filter_clean_required") else "Clean",
            "firmware_version": data.get("firmware_version"),
            "zones": zones,
        }
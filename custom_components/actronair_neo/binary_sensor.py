"""Support for ActronAir Neo diagnostic sensors."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (  # type: ignore
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityCategory  # type: ignore
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .base_entity import ActronEntityBase
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
        # Removed redundant sensors - functionality moved to enhanced diagnostic sensors
        # ActronFilterStatusSensor(coordinator),  # -> sensor.actronair_neo_system_diagnostics.filter_status
        # ActronSystemStatusSensor(coordinator),  # -> sensor.actronair_neo_system_diagnostics + performance + connectivity
        ActronHealthMonitorSensor(
            coordinator
        ),  # Kept for unique error history and health monitoring
    ]

    # Add YourZone enabled binary sensors for each zone
    for zone_id, zone_data in coordinator.data["zones"].items():
        entities.append(ActronZoneYourZoneEnabledSensor(coordinator, zone_id))

    async_add_entities(entities)


class ActronDiagnosticBase(CoordinatorEntity):
    """Base class for diagnostic entities."""

    def __init__(
        self, coordinator: ActronDataCoordinator, unique_suffix: str, name: str
    ) -> None:
        """Initialize the base diagnostic entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_{unique_suffix}"
        self._attr_name = name
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

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


# REMOVED: ActronFilterStatusSensor - functionality moved to sensor.actronair_neo_system_diagnostics.filter_status
# This provides the same information in a more user-friendly format

# REMOVED: ActronSystemStatusSensor - functionality moved to enhanced diagnostic sensors:
# - sensor.actronair_neo_system_diagnostics (system status, modes, temperatures)
# - sensor.actronair_neo_performance_metrics (compressor, fan performance)
# - sensor.actronair_neo_connectivity_status (WiFi, cloud connection)
# This provides the same information with better organization and user experience

# All methods from ActronSystemStatusSensor removed - functionality moved to enhanced sensors

# All remaining methods and properties from ActronSystemStatusSensor removed


class ActronHealthMonitorSensor(ActronEntityBase, BinarySensorEntity):
    """System health monitor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the health monitor."""
        super().__init__(
            coordinator, "binary_sensor", "System Health", is_diagnostic=True
        )
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_icon = "mdi:alert-circle"

    @property
    def is_on(self) -> bool:
        """Return True if there are system issues."""
        try:
            raw_data = self.coordinator.data["raw_data"]
            last_known_state = raw_data.get("lastKnownState", {}).get(
                f"<{self.coordinator.device_id.upper()}>", {}
            )
            live_aircon = last_known_state.get("LiveAircon", {})

            # Check for various error conditions
            return bool(live_aircon.get("ErrCode", 0) != 0) or bool(
                last_known_state.get("Servicing", {}).get("NV_ErrorHistory", [])
            )

        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.exception("Error checking system health: %s", err)
            return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return simplified health-related attributes focusing on unique data."""
        try:
            raw_data = self.coordinator.data["raw_data"]
            last_known_state = raw_data.get("lastKnownState", {}).get(
                f"<{self.coordinator.device_id.upper()}>", {}
            )
            servicing = last_known_state.get("Servicing", {})
            last_known_state.get("LiveAircon", {})

            # Focus on unique health data not available in enhanced sensors
            error_history = servicing.get("NV_ErrorHistory", [])
            recent_events = servicing.get("NV_AC_EventHistory", [])[:5]

            return {
                # Unique health monitoring data
                "error_history": error_history,
                "recent_events": recent_events,
                "total_errors": len(error_history),
                "last_error": error_history[-1] if error_history else "None",
                # Health status summary
                "health_status": "Issues Detected" if self.is_on else "Healthy",
                "last_health_check": raw_data.get("lastStatusUpdate", "Unknown"),
                # Note: error_code now available in system_diagnostics sensor
                "note": "Current error code available in system_diagnostics sensor",
            }

        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.exception("Error getting health attributes: %s", err)
            return {
                "error": "Failed to get health attributes",
                "error_details": str(err),
            }


class ActronZoneYourZoneEnabledSensor(ActronEntityBase, BinarySensorEntity):
    """Binary sensor for YourZone enabled status."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the YourZone enabled sensor."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(
            coordinator,
            "binary_sensor",
            f"{zone_name} YourZone Enabled",
            is_diagnostic=True,
        )
        self.zone_id = zone_id
        self._attr_device_class = None
        self._attr_icon = "mdi:check-circle"

    @property
    def is_on(self) -> bool:
        """Return True if YourZone is enabled for this zone."""
        try:
            return self.coordinator.data["zones"][self.zone_id].get(
                "airflow_control_enabled", False
            )
        except KeyError:
            _LOGGER.exception(
                "Failed to get YourZone enabled status for zone %s", self.zone_id
            )
            return False

    @property
    def icon(self) -> str:
        """Return the icon based on state."""
        return "mdi:check-circle" if self.is_on else "mdi:close-circle"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.zone_id in self.coordinator.data["zones"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return YourZone-specific attributes."""
        try:
            zone_data = self.coordinator.data["zones"][self.zone_id]
            return {
                "zone_id": self.zone_id,
                "zone_name": zone_data.get("name"),
                "airflow_setpoint": zone_data.get("airflow_setpoint"),
                "airflow_control_locked": zone_data.get("airflow_control_locked"),
                "damper_position": zone_data.get("damper_position"),
            }
        except KeyError:
            _LOGGER.exception(
                "Key error getting YourZone attributes for zone %s", self.zone_id
            )
            return {}

"""Support for ActronAir Neo diagnostic sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .entity import ActronAirNeoEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import ActronDataCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo diagnostic sensors."""
    coordinator: ActronDataCoordinator = entry.runtime_data

    entities = [
        ActronHealthMonitorSensor(coordinator),
        ActronFastHeatingSensor(coordinator),
        ActronActiveWarningsSensor(coordinator),
    ]

    # Add YourZone enabled binary sensors for each zone
    entities.extend(
        ActronZoneYourZoneEnabledSensor(coordinator, zone_id)
        for zone_id in coordinator.data["zones"]
    )

    async_add_entities(entities)


class ActronHealthMonitorSensor(ActronAirNeoEntity, BinarySensorEntity):
    """System health monitor."""

    _attr_translation_key = "system_health"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the health monitor."""
        super().__init__(
            coordinator, "binary_sensor", "System Health", is_diagnostic=True
        )
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

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

        except (KeyError, TypeError, ValueError):
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

        except (KeyError, TypeError, ValueError):
            return {
                "error": "Failed to get health attributes",
            }


class ActronZoneYourZoneEnabledSensor(ActronAirNeoEntity, BinarySensorEntity):
    """Binary sensor for YourZone enabled status."""

    _attr_translation_key = "yourzone_enabled"

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

    @property
    def is_on(self) -> bool:
        """Return True if YourZone is enabled for this zone."""
        try:
            return self.coordinator.data["zones"][self.zone_id].get(
                "airflow_control_enabled", False
            )
        except KeyError:
            return False

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
            return {}


class ActronFastHeatingSensor(ActronAirNeoEntity, BinarySensorEntity):
    """Fast heating binary sensor."""

    _attr_translation_key = "fast_heating"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the fast heating sensor."""
        super().__init__(
            coordinator, "binary_sensor", "Fast Heating", is_diagnostic=True
        )
        self._attr_device_class = BinarySensorDeviceClass.HEAT

    @property
    def is_on(self) -> bool:
        """Return True if fast heating is active."""
        return self.coordinator.data["main"].get("fast_heating", False)


class ActronActiveWarningsSensor(ActronAirNeoEntity, BinarySensorEntity):
    """Active warnings binary sensor."""

    _attr_translation_key = "active_warnings"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the active warnings sensor."""
        super().__init__(
            coordinator, "binary_sensor", "Active Warnings", is_diagnostic=True
        )
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        """Return True if there are active warnings."""
        warnings = self.coordinator.data["main"].get("warnings", [])
        return len(warnings) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return warning details."""
        warnings = self.coordinator.data["main"].get("warnings", [])
        return {
            "warning_count": len(warnings),
            "warnings": warnings,
        }

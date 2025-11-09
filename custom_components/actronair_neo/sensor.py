"""Support for ActronAir Neo sensors."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

from homeassistant.components.sensor import (  # type: ignore
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (  # type: ignore
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity  # type: ignore

from .base_entity import ActronEntityBase
from .const import (
    ATTR_BATTERY_LEVEL,
    ATTR_LAST_UPDATED,
    ATTR_ZONE_NAME,
    ATTR_ZONE_TYPE,
    DOMAIN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _supports_power_monitoring(coordinator: ActronDataCoordinator) -> bool:
    """
    Determine if the outdoor unit supports power consumption monitoring.

    Power monitoring requires hardware support (current/voltage sensors) in the
    outdoor unit. Fixed Speed Classic units with basic controllers typically
    don't have this capability, while VSD units with advanced controllers do.

    Args:
        coordinator: The ActronDataCoordinator instance

    Returns:
        True if power monitoring is supported, False otherwise

    """
    try:
        # Get outdoor unit information from raw API data (more reliable during setup)
        raw_data = coordinator.data.get("raw_data", {})
        last_known_state = raw_data.get("lastKnownState", {})

        # Validate lastKnownState data is available
        if not last_known_state:
            _LOGGER.warning(
                "No lastKnownState data available for power monitoring check"
            )
            return False

        # Access AirconSystem directly from lastKnownState (no serial number wrapper)
        aircon_system = last_known_state.get("AirconSystem", {})
        outdoor_unit_info = aircon_system.get("OutdoorUnit", {})

        _LOGGER.debug(
            "Power monitoring check - outdoor_unit_info keys: %s",
            list(outdoor_unit_info.keys()) if outdoor_unit_info else "None",
        )

        family = outdoor_unit_info.get("Family", "")
        ctrl_board_type = outdoor_unit_info.get("CtrlBoardType", "")

        _LOGGER.debug(
            "Power monitoring check - Family: '%s', Controller: '%s'",
            family,
            ctrl_board_type,
        )

        # Fixed Speed Classic units with Type 100 controllers don't support
        # power monitoring. These units lack the necessary current transformers
        # and voltage sensing circuitry
        if "Fixed Speed" in family and "Type 100" in ctrl_board_type:
            _LOGGER.info(
                "Power monitoring not supported: Fixed Speed unit with Type 100 "
                "controller (Family: %s, Controller: %s)",
                family,
                ctrl_board_type,
            )
            return False

        # Additional runtime check: Verify if power fields are populated
        # This catches cases where API fields exist but hardware doesn't provide data
        # Access LiveAircon directly from lastKnownState (no serial number wrapper)
        live_aircon = last_known_state.get("LiveAircon", {})
        outdoor_unit_live = live_aircon.get("OutdoorUnit", {})

        comp_power = outdoor_unit_live.get("CompPower", 0)
        supply_voltage = outdoor_unit_live.get("SupplyVoltage_Vac", 0.0)
        supply_current = outdoor_unit_live.get("SupplyCurrentRMS_A", 0.0)
        compressor_on = outdoor_unit_live.get("CompressorOn", False)

        _LOGGER.debug(
            "Power monitoring check - CompPower: %s, Voltage: %s, Current: %s, "
            "Compressor: %s",
            comp_power,
            supply_voltage,
            supply_current,
            "ON" if compressor_on else "OFF",
        )

        # If compressor is running but all power fields are zero,
        # hardware doesn't support it
        if (
            compressor_on
            and comp_power == 0
            and supply_voltage == 0.0
            and supply_current == 0.0
        ):
            _LOGGER.info(
                "Power monitoring not supported: Compressor running but all "
                "power fields are zero (Family: %s, Controller: %s)",
                family,
                ctrl_board_type,
            )
            return False

        # If any power field has a non-zero value, power monitoring is supported
        if comp_power > 0 or supply_voltage > 0 or supply_current > 0:
            _LOGGER.info(
                "Power monitoring supported: Active power data detected "
                "(CompPower: %s W, Voltage: %s V, Current: %s A)",
                comp_power,
                supply_voltage,
                supply_current,
            )
            return True

        # Advanced/Inverter series units typically support power monitoring
        # Check for indicators in the Family field
        if any(
            indicator in family
            for indicator in ["Advance", "Inverter", "VSD", "Variable Speed"]
        ):
            _LOGGER.info(
                "Power monitoring likely supported: Advanced/Inverter unit detected "
                "(Family: %s, Controller: %s)",
                family,
                ctrl_board_type,
            )
            return True

        # Default to False for safety - don't create sensors if unsure
        _LOGGER.info(
            "Power monitoring support unknown, defaulting to disabled "
            "(Family: %s, Controller: %s)",
            family,
            ctrl_board_type,
        )
        return False

    except (KeyError, TypeError, AttributeError) as err:
        _LOGGER.warning(
            "Error checking power monitoring support: %s - defaulting to disabled", err
        )
        return False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo sensors from a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ActronMainSensor(coordinator),
        # Enhanced diagnostic sensors
        ActronSystemDiagnosticSensor(coordinator),
        ActronConnectivitySensor(coordinator),
        ActronPerformanceSensor(coordinator),
    ]

    # Only add power sensors if hardware supports power monitoring
    if _supports_power_monitoring(coordinator):
        # Get outdoor unit info from raw data for logging
        raw_data = coordinator.data.get("raw_data", {})
        last_known_state = raw_data.get("lastKnownState", {})
        if last_known_state:
            serial_key = next(iter(last_known_state.keys()))
            system_data = last_known_state.get(serial_key, {})
            aircon_system = system_data.get("AirconSystem", {})
            outdoor_unit_info = aircon_system.get("OutdoorUnit", {})
        else:
            outdoor_unit_info = {}

        _LOGGER.info(
            "Adding power monitoring sensors for device %s (Family: %s, "
            "Controller: %s)",
            coordinator.device_id,
            outdoor_unit_info.get("Family", "Unknown"),
            outdoor_unit_info.get("CtrlBoardType", "Unknown"),
        )
        entities.extend(
            [
                ActronCompressorPowerSensor(coordinator),
                ActronCompressorEnergySensor(coordinator),
            ]
        )
    else:
        # Get outdoor unit info from raw data for logging
        raw_data = coordinator.data.get("raw_data", {})
        last_known_state = raw_data.get("lastKnownState", {})
        if last_known_state:
            serial_key = next(iter(last_known_state.keys()))
            system_data = last_known_state.get(serial_key, {})
            aircon_system = system_data.get("AirconSystem", {})
            outdoor_unit_info = aircon_system.get("OutdoorUnit", {})
        else:
            outdoor_unit_info = {}

        _LOGGER.info(
            "Skipping power monitoring sensors for device %s - hardware does "
            "not support power measurement (Family: %s, Controller: %s). "
            "Consider using external power monitoring hardware.",
            coordinator.device_id,
            outdoor_unit_info.get("Family", "Unknown"),
            outdoor_unit_info.get("CtrlBoardType", "Unknown"),
        )

    # Add zone sensors
    for zone_id, zone_data in coordinator.data["zones"].items():
        _LOGGER.debug("Adding zone sensor for %s: %s", zone_id, zone_data)
        entities.append(ActronZoneSensor(coordinator, zone_id))
        # Add damper position sensor for each zone
        entities.append(ActronZoneDamperPositionSensor(coordinator, zone_id))

    # Add consolidated zone damper diagnostic sensor
    entities.append(ActronZoneDamperDiagnosticSensor(coordinator))

    async_add_entities(entities)


class ActronSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for ActronAir Neo sensors."""

    _ATTR_HAS_ENTITY_NAME: Final = True

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


class ActronMainSensor(ActronEntityBase, SensorEntity):
    """Main temperature sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the main temperature sensor."""
        super().__init__(coordinator, "sensor", "Avg. Inside Temp")
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.coordinator.data["main"]["indoor_temp"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        return {
            "Inside Humidity": self.coordinator.data["main"]["indoor_humidity"],
        }


class ActronZoneSensor(ActronEntityBase, SensorEntity):
    """Zone temperature sensor."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone sensor."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(coordinator, "sensor", f"Zone {zone_name}")
        self.zone_id = zone_id
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _format_signal_strength(self, signal: float | None) -> str:
        """Format signal strength with quality rating."""
        if not isinstance(signal, (int, float)):
            return "Unknown"

        if signal > -50:
            quality = "Excellent"
        elif signal > -60:
            quality = "Good"
        elif signal > -70:
            quality = "Fair"
        else:
            quality = "Poor"

        return f"{signal} dBm ({quality})"

    @property
    def native_value(self) -> StateType:
        """Return the temperature of the zone."""
        try:
            return self.coordinator.data["zones"][self.zone_id]["temp"]
        except KeyError:
            _LOGGER.exception("Failed to get temperature for zone %s", self.zone_id)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.zone_id in self.coordinator.data["zones"]
            and self.coordinator.data["zones"][self.zone_id].get("temp") is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return zone specific attributes including humidity and battery level."""
        try:
            zone_data = self.coordinator.data["zones"][self.zone_id]
            peripheral_data = self.coordinator.get_zone_peripheral(self.zone_id)

            attributes = {
                ATTR_ZONE_NAME: zone_data["name"],
                "humidity": zone_data["humidity"],
                "enabled": zone_data["is_enabled"],
            }

            # Add battery level from zone data if available (for wireless sensors)
            if zone_data.get("battery_level") is not None:
                attributes[ATTR_BATTERY_LEVEL] = zone_data["battery_level"]
                _LOGGER.debug(
                    "Zone %s has battery level: %s%%",
                    self.zone_id,
                    zone_data["battery_level"],
                )

            # Add peripheral type information if available
            if zone_data.get("peripheral_type") is not None:
                attributes[ATTR_ZONE_TYPE] = zone_data["peripheral_type"]

            # Add connection information for wireless sensors
            if zone_data.get("last_connection") is not None:
                attributes[ATTR_LAST_UPDATED] = zone_data["last_connection"]
            if zone_data.get("connection_state") is not None:
                attributes["connection_state"] = zone_data["connection_state"]

            # Add signal strength if available (with user-friendly formatting)
            if zone_data.get("signal_strength") is not None:
                signal = zone_data["signal_strength"]
                attributes["signal_strength"] = self._format_signal_strength(signal)

            # Fallback to peripheral data for additional information if available
            if peripheral_data:
                # Only use peripheral battery data if zone data doesn't have it
                if (
                    ATTR_BATTERY_LEVEL not in attributes
                    and "RemainingBatteryCapacity_pc" in peripheral_data
                ):
                    attributes[ATTR_BATTERY_LEVEL] = peripheral_data[
                        "RemainingBatteryCapacity_pc"
                    ]
                    _LOGGER.debug(
                        "Zone %s using peripheral battery level: %s%%",
                        self.zone_id,
                        peripheral_data["RemainingBatteryCapacity_pc"],
                    )

                # Use peripheral data for additional attributes if zone data
                # doesn't have them
                if ATTR_ZONE_TYPE not in attributes and "DeviceType" in peripheral_data:
                    attributes[ATTR_ZONE_TYPE] = peripheral_data["DeviceType"]
                if (
                    "signal_strength" not in attributes
                    and "Signal_of3" in peripheral_data
                    and peripheral_data["Signal_of3"] != "NA"
                ):
                    try:
                        signal = int(peripheral_data["Signal_of3"])
                        attributes["signal_strength"] = self._format_signal_strength(
                            signal
                        )
                    except (ValueError, TypeError):
                        attributes["signal_strength"] = peripheral_data["Signal_of3"]
                if (
                    ATTR_LAST_UPDATED not in attributes
                    and "LastConnectionTime" in peripheral_data
                ):
                    attributes[ATTR_LAST_UPDATED] = peripheral_data[
                        "LastConnectionTime"
                    ]
                if (
                    "connection_state" not in attributes
                    and "ConnectionState" in peripheral_data
                ):
                    attributes["connection_state"] = peripheral_data["ConnectionState"]

            _LOGGER.debug("Zone %s attributes: %s", self.zone_id, attributes)
            return attributes

        except KeyError:
            _LOGGER.exception("Key error getting attributes for zone %s", self.zone_id)
            return {}
        except TypeError:
            _LOGGER.exception("Type error getting attributes for zone %s", self.zone_id)
            return {}
        except ValueError:
            _LOGGER.exception(
                "Value error getting attributes for zone %s", self.zone_id
            )
            return {}


class ActronZoneDamperPositionSensor(ActronEntityBase, SensorEntity):
    """Zone damper position sensor (read-only)."""

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone damper position sensor."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(coordinator, "sensor", f"{zone_name} Damper Position")
        self.zone_id = zone_id
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:valve"
        self._attr_device_class = None

    @property
    def native_value(self) -> float | None:
        """Return the current damper position percentage."""
        try:
            return self.coordinator.data["zones"][self.zone_id].get("damper_position")
        except KeyError:
            _LOGGER.exception("Failed to get damper position for zone %s", self.zone_id)
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.zone_id in self.coordinator.data["zones"]
            and self.coordinator.data["zones"][self.zone_id].get("damper_position")
            is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return damper-specific attributes."""
        try:
            zone_data = self.coordinator.data["zones"][self.zone_id]
            return {
                "zone_id": self.zone_id,
                "zone_name": zone_data.get("name"),
                "zone_max_position": zone_data.get("zone_max_position"),
                "zone_min_position": zone_data.get("zone_min_position"),
                "yourzone_enabled": zone_data.get("airflow_control_enabled"),
                "airflow_setpoint": zone_data.get("airflow_setpoint"),
            }
        except KeyError:
            _LOGGER.exception(
                "Key error getting damper attributes for zone %s", self.zone_id
            )
            return {}


class ActronZoneDamperDiagnosticSensor(ActronEntityBase, SensorEntity):
    """Consolidated zone damper positions diagnostic sensor."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the zone damper diagnostic sensor."""
        super().__init__(
            coordinator, "sensor", "Zone Damper Positions", is_diagnostic=True
        )
        self._attr_native_unit_of_measurement = None
        self._attr_state_class = None
        self._attr_icon = "mdi:valve"

    @property
    def native_value(self) -> str:
        """Return summary of damper positions."""
        try:
            zones = self.coordinator.data.get("zones", {})
            open_dampers = []
            total_zones = 0

            for zone_id, zone_data in zones.items():
                total_zones += 1
                damper_position = zone_data.get("damper_position", 0)
                if damper_position > 0:
                    open_dampers.append(
                        f"{zone_data.get('name', zone_id)}: {damper_position}%"
                    )

            if not open_dampers:
                return f"All Closed ({total_zones} zones)"
            if len(open_dampers) == 1:
                return f"1 Open: {open_dampers[0]}"
            return f"{len(open_dampers)} Open of {total_zones}"

        except (KeyError, TypeError):
            return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all zone damper positions and statuses."""
        try:
            zones = self.coordinator.data.get("zones", {})
            attributes = {}

            # Individual zone damper data
            for zone_id, zone_data in zones.items():
                zone_name = zone_data.get("name", zone_id)
                damper_position = zone_data.get("damper_position", 0)

                # Determine damper status
                if damper_position == 0:
                    damper_status = "Closed"
                elif damper_position >= 90:
                    damper_status = "Fully Open"
                elif damper_position >= 50:
                    damper_status = "Mostly Open"
                elif damper_position >= 25:
                    damper_status = "Partially Open"
                else:
                    damper_status = "Mostly Closed"

                # Add zone-specific attributes
                attributes[f"{zone_name.lower().replace(' ', '_')}_position"] = (
                    f"{damper_position}%"
                )
                attributes[f"{zone_name.lower().replace(' ', '_')}_status"] = (
                    damper_status
                )
                attributes[f"{zone_name.lower().replace(' ', '_')}_airflow_active"] = (
                    "Yes"
                    if (damper_position > 0 and zone_data.get("is_enabled", False))
                    else "No"
                )

            # Summary statistics
            positions = [
                zone_data.get("damper_position", 0) for zone_data in zones.values()
            ]
            open_count = sum(1 for pos in positions if pos > 0)
            avg_position = sum(positions) / len(positions) if positions else 0
            zones_with_airflow = sum(
                1
                for zone_data in zones.values()
                if zone_data.get("damper_position", 0) > 0
                and zone_data.get("is_enabled", False)
            )

            attributes.update(
                {
                    "total_zones": str(len(zones)),
                    "open_dampers": str(open_count),
                    "closed_dampers": str(len(zones) - open_count),
                    "average_position": f"{avg_position:.1f}%",
                    "max_position": f"{max(positions) if positions else 0}%",
                    "zones_with_airflow": str(zones_with_airflow),
                }
            )

            return attributes

        except (KeyError, TypeError):
            _LOGGER.exception("Error getting damper diagnostic attributes")
            return {"error": "Failed to retrieve damper data"}


class ActronSystemDiagnosticSensor(ActronEntityBase, SensorEntity):
    """Enhanced system diagnostic sensor with live data and user-friendly formatting."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the system diagnostic sensor."""
        super().__init__(
            coordinator, "sensor", "System Diagnostics", is_diagnostic=True
        )
        self._attr_icon = "mdi:information-outline"
        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        self._attr_state_class = None

    @property
    def native_value(self) -> str:
        """Return the overall system status."""
        try:
            main_data = self.coordinator.data["main"]
            if main_data.get("is_on", False):
                mode = main_data.get("mode", "Unknown").title()
                return f"Running ({mode})"
            return "Standby"
        except (KeyError, TypeError):
            return "Unknown"

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime to human readable string."""
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return "Unknown"

        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _format_temperature(self, value: Any) -> str:
        """Format temperature value."""
        if value is None or value == "Unknown":
            return "Unknown"
        try:
            return f"{float(value):.1f}°C"
        except (ValueError, TypeError):
            return str(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return enhanced diagnostic attributes with live data."""
        try:
            main_data = self.coordinator.data["main"]
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            # System status from live data
            system_status = last_known_state.get("SystemStatus_Local", {})
            live_aircon = last_known_state.get("LiveAircon", {})

            return {
                # System Information
                "model": main_data.get("model", "Unknown"),
                "firmware_version": main_data.get("firmware_version", "Unknown"),
                "serial_number": main_data.get("serial_number", "Unknown"),
                # Live System Status
                "system_uptime": self._format_uptime(system_status.get("Uptime_s", 0)),
                "operating_mode": main_data.get("mode", "Unknown").title(),
                "fan_mode": main_data.get("fan_mode", "Unknown").title(),
                "quiet_mode_active": main_data.get("quiet_mode", False),
                "away_mode_active": main_data.get("away_mode", False),
                # Live Performance Data (Enhanced for GitHub Issue #16)
                "compressor_running": live_aircon.get("SystemOn", False),
                "compressor_capacity": f"{live_aircon.get('CompressorCapacity', 0)}%",
                "compressor_usage": live_aircon.get(
                    "CompressorCapacity", 0
                ),  # Raw percentage for automations
                "fan_running": live_aircon.get("AmRunningFan", False),
                "fan_speed": f"{live_aircon.get('FanRPM', 0)} RPM",
                "fan_speed_rpm": live_aircon.get(
                    "FanRPM", 0
                ),  # Raw RPM for automations
                "current_fan_speed": live_aircon.get(
                    "FanRPM", 0
                ),  # Alias for user request
                # Power and Electrical Data (GitHub Issue #16)
                "compressor_power": self._format_power_value(
                    live_aircon.get("OutdoorUnit", {}).get("CompPower", 0)
                ),
                "supply_voltage": (
                    f"{live_aircon.get('OutdoorUnit', {}).get('SupplyVoltage_Vac', 0):.1f} VAC"
                ),
                "supply_current": (
                    f"{live_aircon.get('OutdoorUnit', {}).get('SuppyCurrentRMS_A', 0):.1f} A"
                ),
                "supply_power": self._format_power_value(
                    live_aircon.get("OutdoorUnit", {}).get("SuppyPowerRMS_W", 0)
                ),
                "system_capacity": (
                    f"{last_known_state.get('AirconSystem', {}).get('OutdoorUnit', {}).get('Capacity_kW', 0)} kW"
                ),
                # Air Volume Data (if available)
                "air_volume": (
                    f"{last_known_state.get('UserAirconSettings', {}).get('VFT', {}).get('Airflow', 0):.1f} m³/h"
                )
                if last_known_state.get("UserAirconSettings", {})
                .get("VFT", {})
                .get("Supported", False)
                else "Not Supported",
                # Live Temperature Readings
                "indoor_temperature": self._format_temperature(
                    main_data.get("indoor_temp")
                ),
                "indoor_humidity": f"{main_data.get('indoor_humidity', 0):.1f}%",
                "coil_inlet_temperature": self._format_temperature(
                    live_aircon.get("CoilInlet")
                ),
                "ambient_temperature": self._format_temperature(
                    system_status.get("SensorInputs", {})
                    .get("SHTC1", {})
                    .get("Temperature_oC")
                ),
                # System Health
                "filter_status": "Needs Cleaning"
                if main_data.get("filter_clean_required")
                else "Clean",
                "defrosting_active": main_data.get("defrosting", False),
                "error_code": live_aircon.get("ErrCode", 0),
                # Last Update Information
                "last_api_update": raw_data.get("lastStatusUpdate", "Unknown"),
                "data_freshness": "Live"
                if self.coordinator.last_update_success
                else "Stale",
            }

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Error getting system diagnostic attributes")
            return {
                "error": "Failed to retrieve system diagnostics",
            }

    def _format_power_value(self, power_value: float) -> str:
        """Format power value with appropriate units."""
        if power_value == 0:
            return "0 W"
        if power_value >= 1000:
            return f"{power_value / 1000:.1f} kW"
        return f"{power_value:.0f} W"


class ActronConnectivitySensor(ActronEntityBase, SensorEntity):
    """Enhanced connectivity sensor with signal quality and connection health."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the connectivity sensor."""
        super().__init__(
            coordinator, "sensor", "Connectivity Status", is_diagnostic=True
        )
        self._attr_icon = "mdi:wifi"
        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        self._attr_state_class = None

    @property
    def native_value(self) -> str:
        """Return the connectivity status."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})

            # Primary indicator: device online status and recent API activity
            device_online = raw_data.get("isOnline", False)

            # Secondary indicator: cloud connection state
            last_known_state = raw_data.get("lastKnownState", {})

            # Get the device-specific section (e.g., "<22H09780>")
            device_section = None
            for key, value in last_known_state.items():
                if key.startswith("<") and key.endswith(">"):
                    device_section = value
                    break

            if not device_section:
                # Fallback to old structure if device section not found
                device_section = last_known_state

            cloud_status = device_section.get("Cloud", {})
            connection_state = cloud_status.get("ConnectionState", "Unknown")

            # Determine status based on multiple indicators
            if device_online and self.coordinator.last_update_success:
                # Device is online and we have recent successful updates
                if connection_state == "Connected":
                    return "Online"
                if connection_state == "Unknown":
                    return "Online (Cloud Status Unknown)"
                return f"Online (Cloud: {connection_state})"
            if device_online:
                # Device reports online but we may have update issues
                return "Online (Limited Connectivity)"
            # Device appears offline
            if connection_state != "Unknown":
                return f"Offline ({connection_state})"
            return "Offline"

        except (KeyError, TypeError):
            return "Unknown"

    def _format_wifi_signal(self, signal: float | None) -> dict[str, str]:
        """Format WiFi signal strength with quality rating."""
        if not isinstance(signal, (int, float)):
            return {"strength": "Unknown", "quality": "Unknown", "bars": "0/4"}

        if signal > -50:
            quality = "Excellent"
            bars = "4/4"
        elif signal > -60:
            quality = "Good"
            bars = "3/4"
        elif signal > -70:
            quality = "Fair"
            bars = "2/4"
        else:
            quality = "Poor"
            bars = "1/4"

        return {"strength": f"{signal} dBm", "quality": quality, "bars": bars}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return enhanced connectivity attributes."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            # Get the device-specific section (e.g., "<22H09780>")
            device_section = None
            for key, value in last_known_state.items():
                if key.startswith("<") and key.endswith(">"):
                    device_section = value
                    break

            if not device_section:
                # Fallback to old structure if device section not found
                device_section = last_known_state

            system_status = device_section.get("SystemStatus_Local", {})
            cloud_status = device_section.get("Cloud", {})
            wifi_info = system_status.get("WiFi", {})

            # WiFi signal analysis
            wifi_signal = self._format_wifi_signal(
                system_status.get("WifiStrength_of3")
            )

            return {
                # Connection Status
                "cloud_connection": cloud_status.get("ConnectionState", "Unknown"),
                "connection_uptime": self._format_uptime(
                    cloud_status.get("Connection", {})
                    .get("UpTime", {})
                    .get("CurrentSession_s", 0)
                ),
                # WiFi Information
                "wifi_network": wifi_info.get("ApSSID", "Unknown"),
                "wifi_signal_strength": wifi_signal["strength"],
                "wifi_signal_quality": wifi_signal["quality"],
                "wifi_signal_bars": wifi_signal["bars"],
                "wifi_channel": str(wifi_info.get("RFChannel", "Unknown")),
                "wifi_firmware": wifi_info.get("FirmwareVersion", "Unknown"),
                # Connection Statistics
                "packets_sent": cloud_status.get("SentPackets", 0),
                "packets_received": cloud_status.get("ReceivedPackets", 0),
                "failed_packets": cloud_status.get("FailedSentPackets", 0),
                "connection_sessions": cloud_status.get("Connection", {})
                .get("SessionCount", {})
                .get("SinceLastMCUReset", 0),
                # Error Monitoring
                "wifi_hardware_errors": wifi_info.get("HardwareErrorCount", 0),
                "dns_failures": cloud_status.get("Connection", {})
                .get("ErrorCount", {})
                .get("DNSFailures", 0),
                "socket_errors": cloud_status.get("Connection", {})
                .get("ErrorCount", {})
                .get("AbortedSockets", 0),
                # Data Freshness
                "last_contact": raw_data.get("timeSinceLastContact", "Unknown"),
                "last_status_update": raw_data.get("lastStatusUpdate", "Unknown"),
                "device_online": raw_data.get("isOnline", False),
            }

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Error getting connectivity attributes")
            return {
                "error": "Failed to retrieve connectivity data",
            }

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime to human readable string."""
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return "Unknown"

        days, remainder = divmod(int(seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class ActronPerformanceSensor(ActronEntityBase, SensorEntity):
    """Enhanced performance sensor with real-time operational metrics."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the performance sensor."""
        super().__init__(
            coordinator, "sensor", "Performance Metrics", is_diagnostic=True
        )
        self._attr_icon = "mdi:speedometer"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = None
        self._attr_state_class = None

    @property
    def native_value(self) -> float | None:
        """Return the overall system efficiency percentage."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})
            live_aircon = last_known_state.get("LiveAircon", {})

            # Calculate efficiency based on compressor capacity and system status
            if live_aircon.get("SystemOn", False):
                capacity = live_aircon.get("CompressorCapacity", 0)
                return float(capacity) if capacity is not None else 0.0
            return 0.0

        except (KeyError, TypeError, ValueError):
            return None

    def _format_temperature(self, value: Any) -> str:
        """Format temperature value."""
        if value is None or value == "Unknown":
            return "Unknown"
        try:
            return f"{float(value):.1f}°C"
        except (ValueError, TypeError):
            return str(value)

    def _format_power(self, value: Any) -> str:
        """Format power value."""
        if value is None or value == "Unknown":
            return "Unknown"
        try:
            power = float(value)
            if power >= 1000:
                return f"{power / 1000:.1f} kW"
            return f"{power:.0f} W"
        except (ValueError, TypeError):
            return str(value)

    def _get_operational_status(self, live_aircon: dict) -> str:
        """Determine operational status from live data."""
        if not live_aircon.get("SystemOn", False):
            return "Standby"

        compressor_on = live_aircon.get("CompressorMode", "OFF") != "OFF"
        fan_running = live_aircon.get("AmRunningFan", False)

        if compressor_on and fan_running:
            return "Active Cooling/Heating"
        if fan_running:
            return "Fan Only"
        if compressor_on:
            return "Compressor Only"
        return "System On (Idle)"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return enhanced performance attributes with live operational data."""
        try:
            main_data = self.coordinator.data["main"]
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            live_aircon = last_known_state.get("LiveAircon", {})
            outdoor_unit = live_aircon.get("OutdoorUnit", {})
            system_status = last_known_state.get("SystemStatus_Local", {})

            return {
                # Operational Status
                "operational_status": self._get_operational_status(live_aircon),
                "system_running": live_aircon.get("SystemOn", False),
                "defrosting": main_data.get("defrosting", False),
                # Compressor Performance
                "compressor_mode": live_aircon.get("CompressorMode", "Unknown"),
                "compressor_capacity": f"{live_aircon.get('CompressorCapacity', 0)}%",
                "compressor_power": self._format_power(
                    outdoor_unit.get("CompPower", 0)
                ),
                "compressor_speed": f"{outdoor_unit.get('CompSpeed', 0)} RPM",
                "compressor_running": outdoor_unit.get("CompressorOn", False),
                # Fan Performance
                "fan_running": live_aircon.get("AmRunningFan", False),
                "fan_speed": f"{live_aircon.get('FanRPM', 0)} RPM",
                "fan_power": f"{live_aircon.get('FanPWM', 0)}%",
                # Temperature Control
                "target_temperature": self._format_temperature(
                    live_aircon.get("CompressorChasingTemperature")
                ),
                "current_temperature": self._format_temperature(
                    live_aircon.get("CompressorLiveTemperature")
                ),
                "coil_inlet_temp": self._format_temperature(
                    live_aircon.get("CoilInlet")
                ),
                "outdoor_coil_temp": self._format_temperature(
                    outdoor_unit.get("CoilTemp")
                ),
                # System Efficiency Metrics
                "indoor_temp": self._format_temperature(main_data.get("indoor_temp")),
                "indoor_humidity": f"{main_data.get('indoor_humidity', 0):.1f}%",
                "ambient_temp": self._format_temperature(
                    system_status.get("SensorInputs", {})
                    .get("SHTC1", {})
                    .get("Temperature_oC")
                ),
                # Valve and Control
                "reverse_valve_position": outdoor_unit.get(
                    "ReverseValvePosition", "Unknown"
                ),
                "defrost_mode": outdoor_unit.get("DefrostMode", 0),
                "drm_active": outdoor_unit.get("DRM", False),
                # Error Monitoring
                "error_code": live_aircon.get("ErrCode", 0),
                "outdoor_errors": {
                    "error_1": outdoor_unit.get("ErrCode_1", 0),
                    "error_2": outdoor_unit.get("ErrCode_2", 0),
                    "error_3": outdoor_unit.get("ErrCode_3", 0),
                    "error_4": outdoor_unit.get("ErrCode_4", 0),
                    "error_5": outdoor_unit.get("ErrCode_5", 0),
                },
                # Zone Performance Summary
                "active_zones": sum(
                    1
                    for zone in self.coordinator.data.get("zones", {}).values()
                    if zone.get("is_enabled", False)
                ),
                "total_zones": len(self.coordinator.data.get("zones", {})),
                # Power Management
                "quiet_mode": main_data.get("quiet_mode", False),
                "away_mode": main_data.get("away_mode", False),
                "continuous_fan": main_data.get("fan_continuous", False),
            }

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Error getting performance attributes")
            return {
                "error": "Failed to retrieve performance data",
            }


class ActronCompressorPowerSensor(ActronEntityBase, SensorEntity):
    """Compressor power sensor for energy dashboard compatibility."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the compressor power sensor."""
        super().__init__(coordinator, "sensor", "Compressor Power")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:flash"

    @property
    def native_value(self) -> float | None:
        """Return the compressor power in watts."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
                _LOGGER.debug("No lastKnownState data available for power sensor")
                return None

            # Access LiveAircon directly from lastKnownState (no serial number wrapper)
            live_aircon = last_known_state.get("LiveAircon", {})

            # Check if compressor is running
            compressor_running = live_aircon.get("SystemOn", False)

            if not compressor_running:
                return 0.0

            # Get compressor power from outdoor unit
            outdoor_unit = live_aircon.get("OutdoorUnit", {})
            compressor_power = outdoor_unit.get("CompPower", 0)

            # Return power as float, ensuring it's not negative
            return (
                max(0.0, float(compressor_power))
                if compressor_power is not None
                else 0.0
            )

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Error getting compressor power")
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
                return {"error": "No lastKnownState data available"}

            # Access LiveAircon directly from lastKnownState (no serial number wrapper)
            live_aircon = last_known_state.get("LiveAircon", {})
            outdoor_unit = live_aircon.get("OutdoorUnit", {})

            return {
                "compressor_running": live_aircon.get("SystemOn", False),
                "compressor_capacity": f"{live_aircon.get('CompressorCapacity', 0)}%",
                "compressor_mode": live_aircon.get("CompressorMode", "Unknown"),
                "system_mode": self.coordinator.data.get("main", {}).get(
                    "mode", "Unknown"
                ),
                "raw_power_value": outdoor_unit.get("CompPower", 0),
            }

        except (KeyError, TypeError):
            _LOGGER.exception("Error getting compressor power attributes")
            return {"error": "Failed to retrieve power data"}


class ActronCompressorEnergySensor(ActronEntityBase, SensorEntity):
    """Compressor energy sensor for energy dashboard compatibility."""

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the compressor energy sensor."""
        super().__init__(coordinator, "sensor", "Compressor Energy")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:lightning-bolt"

        # Initialize energy tracking variables
        self._last_power = 0.0
        self._last_update = None
        self._total_energy = 0.0

    @property
    def native_value(self) -> float | None:
        """Return the total energy consumption in kWh."""
        try:
            # Get current power reading
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
                _LOGGER.debug("No lastKnownState data available for energy sensor")
                return None

            # Access LiveAircon directly from lastKnownState (no serial number wrapper)
            live_aircon = last_known_state.get("LiveAircon", {})

            # Check if compressor is running
            compressor_running = live_aircon.get("SystemOn", False)

            if not compressor_running:
                current_power = 0.0
            else:
                # Get compressor power from outdoor unit
                outdoor_unit = live_aircon.get("OutdoorUnit", {})
                compressor_power = outdoor_unit.get("CompPower", 0)
                current_power = (
                    max(0.0, float(compressor_power))
                    if compressor_power is not None
                    else 0.0
                )

            # Calculate energy using trapezoidal integration
            current_time = datetime.now(UTC)

            if self._last_update is not None:
                # Calculate time difference in hours
                time_diff = (current_time - self._last_update).total_seconds() / 3600.0

                # Use trapezoidal rule for integration
                # (average of current and last power * time)
                if time_diff > 0 and time_diff < 1.0:  # Ignore large gaps (> 1 hour)
                    avg_power = (current_power + self._last_power) / 2.0
                    energy_increment = (
                        avg_power * time_diff
                    ) / 1000.0  # Convert W*h to kWh
                    self._total_energy += energy_increment

            # Update tracking variables
            self._last_power = current_power
            self._last_update = current_time

            return round(self._total_energy, 3)

        except (KeyError, TypeError, ValueError):
            _LOGGER.exception("Error calculating compressor energy")
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
                return {"error": "No lastKnownState data available"}

            # Access LiveAircon directly from lastKnownState (no serial number wrapper)
            live_aircon = last_known_state.get("LiveAircon", {})

            return {
                "current_power_w": self._last_power,
                "compressor_running": live_aircon.get("SystemOn", False),
                "compressor_capacity": f"{live_aircon.get('CompressorCapacity', 0)}%",
                "integration_method": "trapezoidal",
                "last_update": self._last_update.isoformat()
                if self._last_update
                else None,
            }

        except (KeyError, TypeError):
            _LOGGER.exception("Error getting compressor energy attributes")
            return {"error": "Failed to retrieve energy data"}

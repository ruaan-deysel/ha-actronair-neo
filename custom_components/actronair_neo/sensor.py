"""Support for ActronAir Neo sensors."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.entity import EntityCategory  # type: ignore[import-untyped]

from .const import (
    ATTR_BATTERY_LEVEL,
    ATTR_LAST_UPDATED,
    ATTR_ZONE_NAME,
    ATTR_ZONE_TYPE,
)
from .entity import ActronAirNeoEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import ActronDataCoordinator

PARALLEL_UPDATES = 0


def _get_device_section(last_known_state: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the serial-keyed device section from lastKnownState.

    The API nests device-specific data (SystemStatus_Local, Cloud, etc.)
    inside a key like "<SERIAL_NUMBER>". This helper finds that section.

    Args:
        last_known_state: The lastKnownState dict from the raw API response

    Returns:
        The device section dict, or empty dict if not found

    """
    for key, value in last_known_state.items():
        if key.startswith("<") and key.endswith(">") and isinstance(value, dict):
            return value
    return {}


def _supports_power_monitoring(
    coordinator: ActronDataCoordinator,
) -> bool:
    """
    Determine if the outdoor unit supports power consumption monitoring.

    Power monitoring requires hardware support (current/voltage sensors)
    in the outdoor unit. Fixed Speed Classic units with basic controllers
    typically don't have this capability.

    Args:
        coordinator: The ActronDataCoordinator instance

    Returns:
        True if power monitoring is supported, False otherwise

    """
    try:
        result = _check_power_monitoring_support(coordinator)
    except (KeyError, TypeError, AttributeError):
        return False
    else:
        return result


def _check_power_monitoring_support(
    coordinator: ActronDataCoordinator,
) -> bool:
    """
    Check hardware support for power monitoring.

    Args:
        coordinator: The ActronDataCoordinator instance

    Returns:
        True if power monitoring is supported

    """
    raw_data = coordinator.data.get("raw_data", {})
    last_known_state = raw_data.get("lastKnownState", {})

    if not last_known_state:
        return False

    # Handle both shapes: last_known_state may be keyed by serial number
    # (matching async_setup_entry) or may directly contain AirconSystem.
    if "AirconSystem" in last_known_state or "LiveAircon" in last_known_state:
        resolved_state = last_known_state
    else:
        serial_key = next(iter(last_known_state.keys()), None)
        if serial_key is None:
            return False
        resolved_state = last_known_state.get(serial_key, {})

    aircon_system = resolved_state.get("AirconSystem", {})
    outdoor_unit_info = aircon_system.get("OutdoorUnit", {})

    family = outdoor_unit_info.get("Family", "")
    ctrl_board_type = outdoor_unit_info.get("CtrlBoardType", "")

    # Fixed Speed Classic units with Type 100 controllers don't support
    # power monitoring
    if "Fixed Speed" in family and "Type 100" in ctrl_board_type:
        return False

    return _check_power_fields(resolved_state, family, ctrl_board_type)


def _check_power_fields(
    last_known_state: dict,
    family: str,
    ctrl_board_type: str,  # noqa: ARG001
) -> bool:
    """
    Check if power fields are populated in live data.

    Args:
        last_known_state: Raw API last known state
        family: Outdoor unit family string
        ctrl_board_type: Controller board type string

    Returns:
        True if power monitoring is supported

    """
    live_aircon = last_known_state.get("LiveAircon", {})
    outdoor_unit_live = live_aircon.get("OutdoorUnit", {})

    comp_power = outdoor_unit_live.get("CompPower", 0)
    supply_voltage = outdoor_unit_live.get("SupplyVoltage_Vac", 0.0)
    supply_current = outdoor_unit_live.get("SupplyCurrentRMS_A", 0.0)
    compressor_on = outdoor_unit_live.get("CompressorOn", False)

    # If compressor is running but all power fields are zero,
    # hardware doesn't support it
    if (
        compressor_on
        and comp_power == 0
        and supply_voltage == 0.0
        and supply_current == 0.0
    ):
        return False

    # If any power field has a non-zero value, power monitoring is supported
    if comp_power > 0 or supply_voltage > 0 or supply_current > 0:
        return True

    # Advanced/Inverter series units typically support power monitoring
    return any(
        indicator in family
        for indicator in [
            "Advance",
            "Inverter",
            "VSD",
            "Variable Speed",
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ActronAir Neo sensors from a config entry."""
    coordinator: ActronDataCoordinator = entry.runtime_data

    entities = [
        ActronMainSensor(coordinator),
        # Enhanced diagnostic sensors
        ActronSystemDiagnosticSensor(coordinator),
        ActronConnectivitySensor(coordinator),
        ActronPerformanceSensor(coordinator),
        ActronServiceReminderSensor(coordinator),
    ]

    # Add outdoor temperature sensor if data is available
    outdoor_temp = coordinator.data["main"].get("outdoor_temp")
    if outdoor_temp is not None:
        entities.append(ActronOutdoorTemperatureSensor(coordinator))

    # Only add power sensors if hardware supports power monitoring
    if _supports_power_monitoring(coordinator):
        entities.extend(
            [
                ActronCompressorPowerSensor(coordinator),
                ActronCompressorEnergySensor(coordinator),
            ]
        )

    # Add zone sensors
    for zone_id, zone_data in coordinator.data["zones"].items():
        entities.append(ActronZoneSensor(coordinator, zone_id))

        # Add humidity sensor if zone reports humidity
        if zone_data.get("humidity") is not None:
            entities.append(ActronZoneHumiditySensor(coordinator, zone_id))

        # Add battery sensor only for wireless zones (battery_level populated)
        if zone_data.get("battery_level") is not None:
            entities.append(ActronZoneBatterySensor(coordinator, zone_id))

    async_add_entities(entities)


class ActronMainSensor(ActronAirNeoEntity, SensorEntity):
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


class ActronZoneSensor(ActronAirNeoEntity, SensorEntity):
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

        if signal > -50:  # noqa: PLR2004
            quality = "Excellent"
        elif signal > -60:  # noqa: PLR2004
            quality = "Good"
        elif signal > -70:  # noqa: PLR2004
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
            attributes = self._build_zone_attributes(zone_data)
            if peripheral_data:
                self._enrich_from_peripheral(attributes, peripheral_data)
        except (KeyError, TypeError, ValueError):
            return {}
        else:
            return attributes

    def _build_zone_attributes(self, zone_data: dict[str, Any]) -> dict[str, Any]:
        """Build base zone attributes from zone data."""
        attributes: dict[str, Any] = {
            ATTR_ZONE_NAME: zone_data["name"],
            "humidity": zone_data["humidity"],
            "enabled": zone_data["is_enabled"],
        }

        if zone_data.get("battery_level") is not None:
            attributes[ATTR_BATTERY_LEVEL] = zone_data["battery_level"]

        if zone_data.get("peripheral_type") is not None:
            attributes[ATTR_ZONE_TYPE] = zone_data["peripheral_type"]

        if zone_data.get("last_connection") is not None:
            attributes[ATTR_LAST_UPDATED] = zone_data["last_connection"]
        if zone_data.get("connection_state") is not None:
            attributes["connection_state"] = zone_data["connection_state"]

        if zone_data.get("signal_strength") is not None:
            signal = zone_data["signal_strength"]
            attributes["signal_strength"] = self._format_signal_strength(signal)

        return attributes

    def _enrich_from_peripheral(
        self,
        attributes: dict[str, Any],
        peripheral_data: dict[str, Any],
    ) -> None:
        """Enrich zone attributes from peripheral data."""
        if (
            ATTR_BATTERY_LEVEL not in attributes
            and "RemainingBatteryCapacity_pc" in peripheral_data
        ):
            attributes[ATTR_BATTERY_LEVEL] = peripheral_data[
                "RemainingBatteryCapacity_pc"
            ]

        if ATTR_ZONE_TYPE not in attributes and "DeviceType" in peripheral_data:
            attributes[ATTR_ZONE_TYPE] = peripheral_data["DeviceType"]

        if (
            "signal_strength" not in attributes
            and "Signal_of3" in peripheral_data
            and peripheral_data["Signal_of3"] != "NA"
        ):
            try:
                signal = int(peripheral_data["Signal_of3"])
                if 0 <= signal <= 3:  # noqa: PLR2004
                    # Signal_of3 is a 0-3 bars scale, not dBm
                    bars_map = {
                        0: "Poor (0 bars)",
                        1: "Fair (1 bar)",
                        2: "Good (2 bars)",
                        3: "Excellent (3 bars)",
                    }
                    attributes["signal_strength"] = bars_map[signal]
                else:
                    # Assume dBm value
                    attributes["signal_strength"] = self._format_signal_strength(signal)
            except (ValueError, TypeError):
                attributes["signal_strength"] = peripheral_data["Signal_of3"]

        if (
            ATTR_LAST_UPDATED not in attributes
            and "LastConnectionTime" in peripheral_data
        ):
            attributes[ATTR_LAST_UPDATED] = peripheral_data["LastConnectionTime"]

        if (
            "connection_state" not in attributes
            and "ConnectionState" in peripheral_data
        ):
            attributes["connection_state"] = peripheral_data["ConnectionState"]


class ActronZoneHumiditySensor(ActronAirNeoEntity, SensorEntity):
    """Zone humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "zone_humidity"

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone humidity sensor."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(coordinator, "sensor", f"Zone {zone_name} Humidity")
        self.zone_id = zone_id

    @property
    def native_value(self) -> StateType:
        """Return the humidity of the zone."""
        try:
            return self.coordinator.data["zones"][self.zone_id].get("humidity")
        except KeyError:
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.zone_id in self.coordinator.data["zones"]
            and self.coordinator.data["zones"][self.zone_id].get("humidity") is not None
        )


class ActronZoneBatterySensor(ActronAirNeoEntity, SensorEntity):
    """
    Zone sensor battery level.

    Only created for wireless zone sensors that report battery level.
    Wired sensors do not have battery data.
    """

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "zone_battery"

    def __init__(self, coordinator: ActronDataCoordinator, zone_id: str) -> None:
        """Initialize the zone battery sensor."""
        zone_name = coordinator.data["zones"][zone_id]["name"]
        super().__init__(coordinator, "sensor", f"Zone {zone_name} Battery")
        self.zone_id = zone_id

    @property
    def native_value(self) -> StateType:
        """Return the battery level of the zone sensor."""
        try:
            return self.coordinator.data["zones"][self.zone_id].get("battery_level")
        except KeyError:
            return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.zone_id in self.coordinator.data["zones"]
            and self.coordinator.data["zones"][self.zone_id].get("battery_level")
            is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes about the wireless sensor."""
        try:
            zone_data = self.coordinator.data["zones"][self.zone_id]
        except KeyError:
            return {}

        attrs: dict[str, Any] = {}
        if zone_data.get("peripheral_type") is not None:
            attrs["sensor_type"] = zone_data["peripheral_type"]
        if zone_data.get("signal_strength") is not None:
            attrs["signal_strength_dbm"] = zone_data["signal_strength"]
        if zone_data.get("connection_state") is not None:
            attrs["connection_state"] = zone_data["connection_state"]
        if zone_data.get("last_connection") is not None:
            attrs["last_connection"] = zone_data["last_connection"]
        return attrs


class ActronSystemDiagnosticSensor(ActronAirNeoEntity, SensorEntity):
    """Enhanced system diagnostic sensor with live data and user-friendly formatting."""

    _attr_translation_key = "system_diagnostics"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the system diagnostic sensor."""
        super().__init__(
            coordinator, "sensor", "System Diagnostics", is_diagnostic=True
        )
        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        self._attr_state_class = None

    @property
    def native_value(self) -> str:
        """Return the overall system status."""
        try:
            main_data = self.coordinator.data["main"]
        except (KeyError, TypeError):
            return "Unknown"
        else:
            if main_data.get("is_on", False):
                mode = main_data.get("mode", "Unknown").title()
                return f"Running ({mode})"
            return "Standby"

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

            # SystemStatus_Local is inside the serial-keyed device section
            device_section = _get_device_section(last_known_state)
            system_status = device_section.get("SystemStatus_Local", {})
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
                    f"{live_aircon.get('OutdoorUnit', {}).get('SupplyVoltage_Vac', 0):.1f}"  # noqa: E501
                    " VAC"
                ),
                "supply_current": (
                    f"{live_aircon.get('OutdoorUnit', {}).get('SupplyCurrentRMS_A', live_aircon.get('OutdoorUnit', {}).get('SuppyCurrentRMS_A', 0)):.1f}"  # noqa: E501
                    " A"
                ),
                "supply_power": self._format_power_value(
                    live_aircon.get("OutdoorUnit", {}).get(
                        "SupplyPowerRMS_W",
                        live_aircon.get("OutdoorUnit", {}).get("SuppyPowerRMS_W", 0),
                    )
                ),
                "system_capacity": self._format_system_capacity(last_known_state),
                # Air Volume Data (if available)
                "air_volume": self._format_air_volume(last_known_state),
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
            return {
                "error": "Failed to retrieve system diagnostics",
            }

    def _format_power_value(self, power_value: float) -> str:
        """Format power value with appropriate units."""
        if power_value == 0:
            return "0 W"
        if power_value >= 1000:  # noqa: PLR2004
            return f"{power_value / 1000:.1f} kW"
        return f"{power_value:.0f} W"

    def _format_system_capacity(self, last_known_state: dict[str, Any]) -> str:
        """Format system capacity from last known state."""
        capacity = (
            last_known_state.get("AirconSystem", {})
            .get("OutdoorUnit", {})
            .get("Capacity_kW", 0)
        )
        return f"{capacity} kW"

    def _format_air_volume(self, last_known_state: dict[str, Any]) -> str:
        """Format air volume from last known state."""
        vft = last_known_state.get("UserAirconSettings", {}).get("VFT", {})
        if not vft.get("Supported", False):
            return "Not Supported"
        airflow = vft.get("Airflow", 0)
        return f"{airflow:.1f} m\u00b3/h"


class ActronConnectivitySensor(ActronAirNeoEntity, SensorEntity):
    """Enhanced connectivity sensor with signal quality and connection health."""

    _attr_translation_key = "connectivity_status"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the connectivity sensor."""
        super().__init__(
            coordinator, "sensor", "Connectivity Status", is_diagnostic=True
        )
        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        self._attr_state_class = None

    @property
    def native_value(self) -> str:
        """Return the connectivity status."""
        try:
            status = self._determine_connectivity_status()
        except (KeyError, TypeError):
            return "Unknown"
        else:
            return status

    def _determine_connectivity_status(self) -> str:
        """Determine connectivity status from raw data."""
        raw_data = self.coordinator.data.get("raw_data", {})
        device_online = raw_data.get("isOnline", False)
        last_known_state = raw_data.get("lastKnownState", {})

        # Get the device-specific section (e.g., "<22H09780>")
        device_section = None
        for key, value in last_known_state.items():
            if key.startswith("<") and key.endswith(">"):
                device_section = value
                break

        if not device_section:
            device_section = last_known_state

        cloud_status = device_section.get("Cloud", {})
        connection_state = cloud_status.get("ConnectionState", "Unknown")

        if device_online and self.coordinator.last_update_success:
            if connection_state == "Connected":
                return "Online"
            if connection_state == "Unknown":
                return "Online (Cloud Status Unknown)"
            return f"Online (Cloud: {connection_state})"
        if device_online:
            return "Online (Limited Connectivity)"
        if connection_state != "Unknown":
            return f"Offline ({connection_state})"
        return "Offline"

    def _format_wifi_signal(self, signal: float | None) -> dict[str, str]:
        """Format WiFi signal strength with quality rating."""
        if not isinstance(signal, (int, float)):
            return {"strength": "Unknown", "quality": "Unknown", "bars": "0/4"}

        if signal > -50:  # noqa: PLR2004
            quality = "Excellent"
            bars = "4/4"
        elif signal > -60:  # noqa: PLR2004
            quality = "Good"
            bars = "3/4"
        elif signal > -70:  # noqa: PLR2004
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

            # SystemStatus_Local and Cloud are in the serial-keyed device section
            device_section = _get_device_section(last_known_state)

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


class ActronPerformanceSensor(ActronAirNeoEntity, SensorEntity):
    """Enhanced performance sensor with real-time operational metrics."""

    _attr_translation_key = "performance_metrics"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the performance sensor."""
        super().__init__(
            coordinator, "sensor", "Performance Metrics", is_diagnostic=True
        )
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_class = None
        self._attr_state_class = None
        # Explicitly disable polling - coordinator handles updates
        self._attr_should_poll = False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        try:
            if not super().available:
                return False

            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            has_data = "LiveAircon" in last_known_state
        except (KeyError, TypeError, AttributeError):
            return False
        else:
            return has_data

    @property
    def native_value(self) -> float | None:
        """Return the overall system efficiency percentage."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})
            live_aircon = last_known_state.get("LiveAircon", {})

            if not live_aircon:
                return None

            # Calculate efficiency based on compressor capacity and system status
            # Return capacity even when system is off (0%) for consistent updates
            capacity = live_aircon.get("CompressorCapacity", 0)
            return float(capacity) if capacity is not None else 0.0

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
        except (ValueError, TypeError):
            return str(value)
        else:
            if power >= 1000:  # noqa: PLR2004
                return f"{power / 1000:.1f} kW"
            return f"{power:.0f} W"

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
            main_data = self.coordinator.data.get("main", {})
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
                return {"status": "No data available"}

            live_aircon = last_known_state.get("LiveAircon", {})
            outdoor_unit = live_aircon.get("OutdoorUnit", {})
            # SystemStatus_Local is inside the serial-keyed device section
            device_section = _get_device_section(last_known_state)
            system_status = device_section.get("SystemStatus_Local", {})

            if not live_aircon:
                return {"status": "No live data available"}

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
                "outdoor_ambient_temp": self._format_temperature(
                    outdoor_unit.get("AmbTemp")
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
            return {
                "error": "Failed to retrieve performance data",
            }


class ActronCompressorPowerSensor(ActronAirNeoEntity, SensorEntity):
    """Compressor power sensor for energy dashboard compatibility."""

    _attr_translation_key = "compressor_power"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the compressor power sensor."""
        super().__init__(coordinator, "sensor", "Compressor Power")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the compressor power in watts."""
        try:
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
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
            return {"error": "Failed to retrieve power data"}


class ActronCompressorEnergySensor(ActronAirNeoEntity, SensorEntity):
    """Compressor energy sensor for energy dashboard compatibility."""

    _attr_translation_key = "compressor_energy"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the compressor energy sensor."""
        super().__init__(coordinator, "sensor", "Compressor Energy")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

        # Initialize energy tracking variables
        self._last_power = 0.0
        self._last_update: datetime | None = None
        self._total_energy = 0.0

    @property
    def native_value(self) -> float | None:
        """Return the total energy consumption in kWh."""
        try:
            # Get current power reading
            raw_data = self.coordinator.data.get("raw_data", {})
            last_known_state = raw_data.get("lastKnownState", {})

            if not last_known_state:
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
            return {"error": "Failed to retrieve energy data"}


class ActronOutdoorTemperatureSensor(ActronAirNeoEntity, SensorEntity):
    """Outdoor temperature sensor."""

    _attr_translation_key = "outdoor_temperature"

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the outdoor temperature sensor."""
        super().__init__(coordinator, "sensor", "Outdoor Temperature")
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> StateType:
        """Return the outdoor temperature."""
        return self.coordinator.data["main"].get("outdoor_temp")

    @property
    def available(self) -> bool:
        """Return if entity is available (None means sensor unavailable)."""
        return (
            super().available
            and self.coordinator.data["main"].get("outdoor_temp") is not None
        )


class ActronServiceReminderSensor(ActronAirNeoEntity, SensorEntity):
    """Service reminder sensor."""

    _attr_translation_key = "service_reminder"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ActronDataCoordinator) -> None:
        """Initialize the service reminder sensor."""
        super().__init__(coordinator, "sensor", "Service Reminder", is_diagnostic=True)

    @property
    def native_value(self) -> StateType:
        """Return the service reminder time."""
        return self.coordinator.data["main"].get("service_reminder_time", "NA")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "enabled": self.coordinator.data["main"].get(
                "service_reminder_enabled", False
            ),
        }

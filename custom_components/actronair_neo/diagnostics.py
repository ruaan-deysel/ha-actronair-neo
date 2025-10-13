"""Diagnostics support for ActronAir Neo."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.diagnostics import async_redact_data  # type: ignore
from homeassistant.config_entries import ConfigEntry  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.util import dt as dt_util  # type: ignore

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

TO_REDACT = {
    "username", "password", "devices", "unique_id",
    "MAC", "mac", "serial", "id", "ip_address", "MACAddress"
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    try:
        if not coordinator or not coordinator.data:
            raise ValueError("No coordinator data available")

        # First get the correct path to the data
        raw_data = coordinator.data.get("raw_data", {})
        # Use device serial to access the correct data
        device_serial = coordinator.data["main"]["serial_number"]
        last_known_state = raw_data.get("lastKnownState", {}).get(f"<{device_serial.upper()}>", {})
        aircon_system = last_known_state.get("AirconSystem", {})
        live_aircon = last_known_state.get("LiveAircon", {})
        indoor_unit = aircon_system.get("IndoorUnit", {})
        outdoor_unit = aircon_system.get("OutdoorUnit", {})

        diagnostics_data = {
            "entry": async_redact_data(entry.as_dict(), TO_REDACT),
            "data": {
                "info": {
                    "model": coordinator.data["main"]["model"],
                    "firmware_version": coordinator.data["main"]["firmware_version"],
                    "indoor_unit": {
                        "model": indoor_unit.get("NV_ModelNumber", "Not Available"),
                        "firmware": indoor_unit.get("IndoorFW", "Not Available"),
                        "serial": async_redact_data(indoor_unit.get("SerialNumber", "Not Available"), TO_REDACT),
                        "supported_fan_modes": indoor_unit.get("NV_SupportedFanModes", "Not Available"),
                        "auto_fan_enabled": indoor_unit.get("NV_AutoFanEnabled", False),
                    },
                    "outdoor_unit": {
                        "family": outdoor_unit.get("Family", "Not Available"),
                        "firmware": outdoor_unit.get("SoftwareVersion", "Not Available"),
                        "model": outdoor_unit.get("ModelNumber", "Not Available"),
                        "serial": async_redact_data(outdoor_unit.get("SerialNumber", "Not Available"), TO_REDACT),
                    },
                    "controller": {
                        "model": aircon_system.get("MasterWCModel", "Not Available"),
                        "serial": async_redact_data(aircon_system.get("MasterSerial", "Not Available"), TO_REDACT),
                        "firmware": aircon_system.get("MasterWCFirmwareVersion", "Not Available"),
                    },
                    "last_update": dt_util.now().isoformat(),
                },
                "system_status": {
                    "filter_clean_required": coordinator.data["main"].get("filter_clean_required", False),
                    "defrosting": coordinator.data["main"].get("defrosting", False),
                    "system_on": coordinator.data["main"].get("is_on", False),
                    "mode": coordinator.data["main"].get("mode", "OFF"),
                    "fan_mode": coordinator.data["main"].get("fan_mode", "OFF"),
                    "quiet_mode": coordinator.data["main"].get("quiet_mode", False),
                    "away_mode": coordinator.data["main"].get("away_mode", False),
                    "connection": {
                        "state": last_known_state.get("Cloud", {}).get("ConnectionState", "Unknown"),
                        "wifi_signal": last_known_state.get("SystemStatus_Local", {}).get("WifiStrength_of3", "No Signal"),
                        "wifi_ssid": async_redact_data(last_known_state.get("SystemStatus_Local", {}).get("WiFi", {}).get("ApSSID", "Not Available"), TO_REDACT),
                    },
                    "compressor": {
                        "state": coordinator.data["main"].get("compressor_state", "OFF"),
                        "capacity": live_aircon.get("CompressorCapacity", "Not Available"),
                        "current_temp": live_aircon.get("CompressorLiveTemperature", "Not Available"),
                        "target_temp": live_aircon.get("CompressorChasingTemperature", "Not Available"),
                    },
                    "fan": {
                        "running": live_aircon.get("AmRunningFan", False),
                        "pwm": live_aircon.get("FanPWM", "Not Available"),
                        "rpm": live_aircon.get("FanRPM", "Not Available"),
                    }
                },
                "environmental": {
                    "indoor": {
                        "temperature": coordinator.data["main"].get("indoor_temp", "Not Available"),
                        "humidity": coordinator.data["main"].get("indoor_humidity", "Not Available"),
                    },
                    "system": {
                        "coil_inlet": live_aircon.get("CoilInlet", "Not Available"),
                        "coil_temp": live_aircon.get("OutdoorUnit", {}).get("CoilTemp", "Not Available"),
                        "ambient_temp": last_known_state.get("SystemStatus_Local", {}).get("SensorInputs", {}).get("SHTC1", {}).get("Temperature_oC", "Not Available"),
                    }
                },
                "zones": {},
                "peripherals": []
            }
        }

        # Get RemoteZoneInfo for zone capabilities
        remote_zone_info = last_known_state.get("RemoteZoneInfo", [])

        # Add zone information with enhanced capability details
        for zone_id, zone_data in coordinator.data["zones"].items():
            zone_info = {
                "name": zone_data["name"],
                "enabled": zone_data["is_enabled"],
                "temperature": zone_data["temp"],
                "humidity": zone_data["humidity"],
                "controller": {
                    "type": "Zone Temperature Sensor",
                    "status": "Enabled" if zone_data["is_enabled"] else "Disabled",
                },
                "capabilities": {}
            }

            # Find matching RemoteZoneInfo for this zone
            matching_zone_info = next(
                (zone for zone in remote_zone_info
                if zone.get("NV_Title") == zone_data["name"]),
                {}
            )

            # Add capability information
            if matching_zone_info:
                zone_info["capabilities"] = {
                    "variable_air_volume": matching_zone_info.get("NV_VAV", False),
                    "individual_temp_control": matching_zone_info.get("NV_ITC", False),
                    "individual_temp_display": matching_zone_info.get("NV_ITD", False),
                    "temperature_setpoints": {
                        "cool": matching_zone_info.get("TemperatureSetpoint_Cool_oC"),
                        "heat": matching_zone_info.get("TemperatureSetpoint_Heat_oC"),
                    }
                }

            # Add wireless sensor information if available
            peripheral = coordinator.get_zone_peripheral(zone_id)
            if peripheral:
                zone_info["wireless_sensor"] = {
                    "type": peripheral.get("DeviceType", "Unknown"),
                    "battery_level": peripheral.get("RemainingBatteryCapacity_pc", "Not Available"),
                    "signal_strength": peripheral.get("Signal_of3", "Not Available"),
                    "firmware": peripheral.get("Firmware", {}).get("InstalledVersion", {}).get("NRF52", "Not Available"),
                    "last_connection": peripheral.get("LastConnectionTime", "Not Available"),
                    "connection_state": peripheral.get("ConnectionState", "Unknown"),
                    "readings": {
                        "temperature": peripheral.get("SensorInputs", {}).get("SHTC1", {}).get("Temperature_oC", "Not Available"),
                        "humidity": peripheral.get("SensorInputs", {}).get("SHTC1", {}).get("RelativeHumidity_pc", "Not Available"),
                        "ambient": peripheral.get("SensorInputs", {}).get("Thermistors", {}).get("Ambient_oC", "Not Available"),
                    }
                }

            diagnostics_data["data"]["zones"][zone_id] = zone_info

        return diagnostics_data

    except KeyError as ex:
        _LOGGER.error("KeyError generating diagnostics: %s", str(ex))
        return {
            "error": {
                "type": "KeyError",
                "message": str(ex),
                "coordinator_available": bool(coordinator),
                "has_data": bool(coordinator and coordinator.data),
                "timestamp": datetime.now().isoformat(),
            },
            "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        }
    except ValueError as ex:
        _LOGGER.error("ValueError generating diagnostics: %s", str(ex))
        return {
            "error": {
                "type": "ValueError",
                "message": str(ex),
                "coordinator_available": bool(coordinator),
                "has_data": bool(coordinator and coordinator.data),
                "timestamp": datetime.now().isoformat(),
            },
            "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        }
    except (TypeError, AttributeError) as ex:
        _LOGGER.error("Error generating diagnostics: %s", str(ex))
        return {
            "error": {
                "type": type(ex).__name__,
                "message": str(ex),
                "coordinator_available": bool(coordinator),
                "has_data": bool(coordinator and coordinator.data),
                "timestamp": datetime.now().isoformat(),
            },
            "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        }

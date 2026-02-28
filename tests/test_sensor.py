"""Tests for the ActronAir Neo sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.actronair_neo.const import ATTR_BATTERY_LEVEL, ATTR_ZONE_TYPE
from custom_components.actronair_neo.sensor import (
    ActronCompressorEnergySensor,
    ActronCompressorPowerSensor,
    ActronConnectivitySensor,
    ActronMainSensor,
    ActronOutdoorTemperatureSensor,
    ActronPerformanceSensor,
    ActronServiceReminderSensor,
    ActronSystemDiagnosticSensor,
    ActronZoneBatterySensor,
    ActronZoneHumiditySensor,
    ActronZoneSensor,
    _check_power_fields,
    _get_device_section,
    _supports_power_monitoring,
    async_setup_entry,
)

from .conftest import create_mock_coordinator


@pytest.fixture
def coordinator(mock_api, mock_status):
    """Create a coordinator for sensor tests."""
    coord = create_mock_coordinator(MagicMock(), mock_api, mock_status)
    coord.last_update_success = True
    coord.get_zone_peripheral = MagicMock(return_value={})
    return coord


class TestHelperFunctions:
    """Test helper functions in sensor module."""

    def test_get_device_section_found(self):
        last_known_state = {"<ABC123>": {"Cloud": {}}, "LiveAircon": {}}
        assert _get_device_section(last_known_state) == {"Cloud": {}}

    def test_get_device_section_not_found(self):
        assert _get_device_section({"LiveAircon": {}}) == {}

    def test_supports_power_monitoring_false_on_bad_data(self, coordinator):
        coordinator.data = None
        assert _supports_power_monitoring(coordinator) is False

    def test_supports_power_monitoring_true(self, coordinator, mock_status):
        mock_status["raw_data"]["lastKnownState"]["LiveAircon"] = {
            "OutdoorUnit": {
                "CompPower": 700,
                "SupplyVoltage_Vac": 230.0,
                "SupplyCurrentRMS_A": 3.0,
                "CompressorOn": True,
            }
        }
        mock_status["raw_data"]["lastKnownState"]["AirconSystem"] = {
            "OutdoorUnit": {"Family": "Advance", "CtrlBoardType": "Type 300"}
        }
        assert _supports_power_monitoring(coordinator) is True

    def test_check_power_fields_false_when_running_but_zero(self):
        state = {
            "LiveAircon": {
                "OutdoorUnit": {
                    "CompPower": 0,
                    "SupplyVoltage_Vac": 0.0,
                    "SupplyCurrentRMS_A": 0.0,
                    "CompressorOn": True,
                }
            }
        }
        assert _check_power_fields(state, "Classic", "Type 100") is False

    def test_check_power_fields_true_on_family_indicator(self):
        state = {
            "LiveAircon": {
                "OutdoorUnit": {
                    "CompPower": 0,
                    "SupplyVoltage_Vac": 0.0,
                    "SupplyCurrentRMS_A": 0.0,
                    "CompressorOn": False,
                }
            }
        }
        assert _check_power_fields(state, "Variable Speed", "Type 200") is True


class TestAsyncSetupEntry:
    """Test platform setup entry."""

    @pytest.mark.asyncio
    async def test_setup_adds_entities(self, coordinator, mock_status):
        mock_entry = MagicMock()
        mock_entry.runtime_data = coordinator
        added: list = []

        mock_status["main"]["outdoor_temp"] = 21.0
        mock_status["zones"]["zone_1"]["battery_level"] = 80
        mock_status["zones"]["zone_1"]["humidity"] = 50

        await async_setup_entry(MagicMock(), mock_entry, added.extend)

        names = {type(entity).__name__ for entity in added}
        assert "ActronMainSensor" in names
        assert "ActronSystemDiagnosticSensor" in names
        assert "ActronConnectivitySensor" in names
        assert "ActronPerformanceSensor" in names
        assert "ActronServiceReminderSensor" in names
        assert "ActronOutdoorTemperatureSensor" in names
        assert "ActronZoneSensor" in names
        assert "ActronZoneHumiditySensor" in names
        assert "ActronZoneBatterySensor" in names


class TestMainAndZoneSensors:
    """Test main and zone sensors."""

    def test_main_sensor_values(self, coordinator):
        sensor = ActronMainSensor(coordinator)
        assert sensor.native_value == 22.5
        assert sensor.extra_state_attributes["Inside Humidity"] == 45.0

    def test_zone_sensor_native_and_available(self, coordinator, mock_status):
        sensor = ActronZoneSensor(coordinator, "zone_1")
        assert sensor.native_value == 22.0
        assert sensor.available is True

        mock_status["zones"]["zone_1"]["temp"] = None
        assert sensor.available is False

    def test_zone_sensor_format_signal(self, coordinator):
        sensor = ActronZoneSensor(coordinator, "zone_1")
        assert "Excellent" in sensor._format_signal_strength(-45)
        assert "Good" in sensor._format_signal_strength(-55)
        assert "Fair" in sensor._format_signal_strength(-65)
        assert "Poor" in sensor._format_signal_strength(-80)
        assert sensor._format_signal_strength(None) == "Unknown"

    def test_zone_sensor_attributes_with_peripheral(self, coordinator, mock_status):
        sensor = ActronZoneSensor(coordinator, "zone_1")
        coordinator.get_zone_peripheral.return_value = {
            "RemainingBatteryCapacity_pc": 77,
            "DeviceType": "WallSensor",
            "Signal_of3": "3",
            "LastConnectionTime": "2025-01-01T00:00:00Z",
            "ConnectionState": "CONNECTED",
        }
        mock_status["zones"]["zone_1"]["battery_level"] = None
        mock_status["zones"]["zone_1"]["peripheral_type"] = None
        mock_status["zones"]["zone_1"]["signal_strength"] = None
        attrs = sensor.extra_state_attributes
        assert attrs[ATTR_BATTERY_LEVEL] == 77
        assert attrs[ATTR_ZONE_TYPE] == "WallSensor"
        assert attrs["signal_strength"] == "Excellent (3 bars)"

    def test_zone_sensor_handles_bad_data(self, coordinator):
        sensor = ActronZoneSensor(coordinator, "zone_1")
        coordinator.data["zones"] = None
        assert sensor.extra_state_attributes == {}

    def test_zone_humidity_sensor(self, coordinator, mock_status):
        sensor = ActronZoneHumiditySensor(coordinator, "zone_1")
        assert sensor.native_value == 45.0
        assert sensor.available is True
        del mock_status["zones"]["zone_1"]
        assert sensor.native_value is None

    def test_zone_battery_sensor(self, coordinator, mock_status):
        sensor = ActronZoneBatterySensor(coordinator, "zone_1")
        assert sensor.native_value == 80
        attrs = sensor.extra_state_attributes
        assert attrs["sensor_type"] == "WallSensor"
        assert attrs["connection_state"] == "CONNECTED"

        del mock_status["zones"]["zone_1"]
        assert sensor.extra_state_attributes == {}


class TestDiagnosticAndConnectivitySensors:
    """Test diagnostic and connectivity sensors."""

    def test_system_diagnostic_native_value(self, coordinator, mock_status):
        sensor = ActronSystemDiagnosticSensor(coordinator)
        assert "Running" in sensor.native_value

        mock_status["main"]["is_on"] = False
        assert sensor.native_value == "Standby"

    def test_system_diagnostic_attributes_and_formatters(self, coordinator):
        sensor = ActronSystemDiagnosticSensor(coordinator)
        assert sensor._format_uptime(65) == "1m"
        assert sensor._format_uptime(-1) == "Unknown"
        assert sensor._format_temperature(21.234).endswith("°C")
        assert sensor._format_temperature("bad") == "bad"
        assert sensor._format_power_value(0) == "0 W"
        assert "kW" in sensor._format_power_value(2500)
        assert "W" in sensor._format_power_value(250)
        attrs = sensor.extra_state_attributes
        assert "model" in attrs
        assert "compressor_running" in attrs

    def test_system_diagnostic_error_path(self, coordinator):
        sensor = ActronSystemDiagnosticSensor(coordinator)
        coordinator.data = None
        assert sensor.extra_state_attributes["error"] == (
            "Failed to retrieve system diagnostics"
        )

    def test_connectivity_statuses(self, coordinator, mock_status):
        sensor = ActronConnectivitySensor(coordinator)
        mock_status["raw_data"]["isOnline"] = True
        mock_status["raw_data"]["lastKnownState"]["<ABC123>"] = {
            "Cloud": {"ConnectionState": "Connected"}
        }
        assert sensor.native_value == "Online"

        coordinator.last_update_success = False
        assert "Limited" in sensor.native_value

        mock_status["raw_data"]["isOnline"] = False
        mock_status["raw_data"]["lastKnownState"]["<ABC123>"] = {
            "Cloud": {"ConnectionState": "Disconnected"}
        }
        assert "Offline" in sensor.native_value

    def test_connectivity_attrs_and_signal_format(self, coordinator):
        sensor = ActronConnectivitySensor(coordinator)
        signal = sensor._format_wifi_signal(-45)
        assert signal["bars"] == "4/4"
        assert sensor._format_wifi_signal(None)["quality"] == "Unknown"
        attrs = sensor.extra_state_attributes
        assert "cloud_connection" in attrs
        assert "device_online" in attrs

    def test_connectivity_error_paths(self, coordinator):
        sensor = ActronConnectivitySensor(coordinator)
        coordinator.data = {"raw_data": {"isOnline": False, "lastKnownState": {}}}
        assert sensor.native_value == "Offline"


class TestPerformanceAndPowerSensors:
    """Test performance/power/energy/outdoor/service sensors."""

    def test_performance_sensor_paths(self, coordinator, mock_status):
        sensor = ActronPerformanceSensor(coordinator)
        assert sensor.available is True
        assert sensor.native_value is not None

        attrs = sensor.extra_state_attributes
        assert "operational_status" in attrs
        assert "active_zones" in attrs

        mock_status["raw_data"]["lastKnownState"] = {}
        assert sensor.available is False
        assert sensor.extra_state_attributes["status"] == "No data available"

    def test_performance_helpers(self, coordinator):
        sensor = ActronPerformanceSensor(coordinator)
        assert sensor._format_temperature(None) == "Unknown"
        assert sensor._format_temperature(23) == "23.0°C"
        assert sensor._format_power(None) == "Unknown"
        assert sensor._format_power(800) == "800 W"
        assert sensor._format_power(1800).endswith("kW")
        assert sensor._get_operational_status({"SystemOn": False}) == "Standby"

    def test_compressor_power_sensor_paths(self, coordinator, mock_status):
        sensor = ActronCompressorPowerSensor(coordinator)
        mock_status["raw_data"]["lastKnownState"]["LiveAircon"]["SystemOn"] = False
        assert sensor.native_value == 0.0

        mock_status["raw_data"]["lastKnownState"]["LiveAircon"]["SystemOn"] = True
        mock_status["raw_data"]["lastKnownState"]["LiveAircon"]["OutdoorUnit"] = {
            "CompPower": -10
        }
        assert sensor.native_value == 0.0
        assert "compressor_running" in sensor.extra_state_attributes

        mock_status["raw_data"]["lastKnownState"] = {}
        assert sensor.extra_state_attributes["error"] == (
            "No lastKnownState data available"
        )

    def test_compressor_energy_sensor_paths(self, coordinator, mock_status):
        sensor = ActronCompressorEnergySensor(coordinator)
        first = sensor.native_value
        assert first is not None
        attrs = sensor.extra_state_attributes
        assert attrs["integration_method"] == "trapezoidal"

        mock_status["raw_data"]["lastKnownState"] = {}
        assert sensor.native_value is None
        assert sensor.extra_state_attributes["error"] == (
            "No lastKnownState data available"
        )

    def test_outdoor_and_service_sensors(self, coordinator, mock_status):
        outdoor = ActronOutdoorTemperatureSensor(coordinator)
        service = ActronServiceReminderSensor(coordinator)
        mock_status["main"]["outdoor_temp"] = 19.5
        mock_status["main"]["service_reminder_time"] = "30d"
        mock_status["main"]["service_reminder_enabled"] = True

        assert outdoor.native_value == 19.5
        assert outdoor.available is True
        assert service.native_value == "30d"
        assert service.extra_state_attributes["enabled"] is True

        mock_status["main"]["outdoor_temp"] = None
        assert outdoor.available is False


class TestSensorRemainingBranches:
    """Targeted tests for remaining uncovered sensor branches."""

    def test_supports_power_monitoring_edge_paths(self, coordinator, mock_status):
        mock_status["raw_data"]["lastKnownState"] = {}
        assert _supports_power_monitoring(coordinator) is False

        mock_status["raw_data"]["lastKnownState"] = {None: {}}
        assert _supports_power_monitoring(coordinator) is False

        mock_status["raw_data"]["lastKnownState"] = {"SERIAL": {}}
        assert _supports_power_monitoring(coordinator) is False

        mock_status["raw_data"]["lastKnownState"] = {
            "LiveAircon": {"OutdoorUnit": {}},
            "AirconSystem": {
                "OutdoorUnit": {"Family": "Fixed Speed", "CtrlBoardType": "Type 100"}
            },
        }
        assert _supports_power_monitoring(coordinator) is False

    @pytest.mark.asyncio
    async def test_setup_without_power_sensors(self, coordinator, mock_status):
        mock_entry = MagicMock()
        mock_entry.runtime_data = coordinator
        mock_status["main"]["outdoor_temp"] = None
        mock_status["zones"]["zone_1"]["humidity"] = None
        mock_status["zones"]["zone_1"]["battery_level"] = None

        added: list = []
        with patch(
            "custom_components.actronair_neo.sensor._supports_power_monitoring",
            return_value=False,
        ):
            await async_setup_entry(MagicMock(), mock_entry, added.extend)

        names = {type(entity).__name__ for entity in added}
        assert "ActronCompressorPowerSensor" not in names
        assert "ActronCompressorEnergySensor" not in names

    @pytest.mark.asyncio
    async def test_setup_with_power_sensors(self, coordinator):
        mock_entry = MagicMock()
        mock_entry.runtime_data = coordinator
        added: list = []
        with patch(
            "custom_components.actronair_neo.sensor._supports_power_monitoring",
            return_value=True,
        ):
            await async_setup_entry(MagicMock(), mock_entry, added.extend)
        names = {type(entity).__name__ for entity in added}
        assert "ActronCompressorPowerSensor" in names
        assert "ActronCompressorEnergySensor" in names

    def test_zone_sensor_additional_paths(self, coordinator, mock_status):
        sensor = ActronZoneSensor(coordinator, "zone_1")
        del mock_status["zones"]["zone_1"]
        assert sensor.native_value is None

        mock_status["zones"]["zone_1"] = {
            "name": "Zone 1",
            "temp": 22.0,
            "humidity": 40,
            "is_enabled": True,
            "battery_level": 70,
            "peripheral_type": "WallSensor",
            "last_connection": "2025-01-01",
            "connection_state": "CONNECTED",
            "signal_strength": -55,
        }
        attrs = sensor.extra_state_attributes
        assert attrs[ATTR_BATTERY_LEVEL] == 70
        assert attrs[ATTR_ZONE_TYPE] == "WallSensor"
        assert "signal_strength" in attrs

        coordinator.get_zone_peripheral.return_value = {"Signal_of3": "invalid"}
        attrs = sensor.extra_state_attributes
        assert attrs["signal_strength"]

    def test_zone_sensor_enrich_peripheral_fields(self, coordinator, mock_status):
        sensor = ActronZoneSensor(coordinator, "zone_1")
        mock_status["zones"]["zone_1"]["battery_level"] = None
        mock_status["zones"]["zone_1"]["peripheral_type"] = None
        mock_status["zones"]["zone_1"]["signal_strength"] = None
        mock_status["zones"]["zone_1"]["last_connection"] = None
        mock_status["zones"]["zone_1"]["connection_state"] = None
        coordinator.get_zone_peripheral.return_value = {
            "RemainingBatteryCapacity_pc": 50,
            "DeviceType": "Remote",
            "Signal_of3": "1",
            "LastConnectionTime": "now",
            "ConnectionState": "connected",
        }
        attrs = sensor.extra_state_attributes
        assert attrs["signal_strength"] == "Fair (1 bar)"
        assert attrs["connection_state"] == "connected"
        assert attrs["last_updated"] == "now"

        coordinator.get_zone_peripheral.return_value = {
            "Signal_of3": "10",
            "ConnectionState": "ok",
        }
        attrs = sensor.extra_state_attributes
        assert "dBm" in attrs["signal_strength"]

        coordinator.get_zone_peripheral.return_value = {
            "Signal_of3": "NaN",
            "ConnectionState": "ok",
        }
        attrs = sensor.extra_state_attributes
        assert attrs["signal_strength"] == "NaN"

    def test_zone_battery_sensor_keyerror_and_available(self, coordinator, mock_status):
        sensor = ActronZoneBatterySensor(coordinator, "zone_1")
        assert sensor.available is True
        del mock_status["zones"]["zone_1"]
        assert sensor.native_value is None
        assert sensor.available is False

    def test_system_diagnostic_remaining_helpers(self, coordinator):
        sensor = ActronSystemDiagnosticSensor(coordinator)
        assert sensor._format_uptime(90061) == "1d 1h 1m"
        assert sensor._format_uptime(3660) == "1h 1m"
        coordinator.data = {}
        assert sensor.native_value == "Unknown"

    def test_service_reminder_air_volume_and_capacity(self, coordinator):
        sensor = ActronSystemDiagnosticSensor(coordinator)
        state = {
            "AirconSystem": {"OutdoorUnit": {"Capacity_kW": 12.5}},
            "UserAirconSettings": {"VFT": {"Supported": True, "Airflow": 123.4}},
        }
        assert sensor._format_system_capacity(state) == "12.5 kW"
        assert sensor._format_air_volume(state) == "123.4 m³/h"

    def test_connectivity_remaining_paths(self, coordinator, mock_status):
        sensor = ActronConnectivitySensor(coordinator)
        coordinator.last_update_success = True
        mock_status["raw_data"]["isOnline"] = True
        mock_status["raw_data"]["lastKnownState"] = {
            "<A>": {"Cloud": {"ConnectionState": "Unknown"}}
        }
        assert sensor.native_value == "Online (Cloud Status Unknown)"

        mock_status["raw_data"]["lastKnownState"] = {
            "<A>": {"Cloud": {"ConnectionState": "Retrying"}}
        }
        assert sensor.native_value == "Online (Cloud: Retrying)"

        signal = sensor._format_wifi_signal(-62)
        assert signal["quality"] == "Fair"
        assert sensor._format_wifi_signal(-55)["quality"] == "Good"
        assert sensor._format_wifi_signal(-75)["bars"] == "1/4"
        assert sensor._format_uptime(-1) == "Unknown"
        assert sensor._format_uptime(90000) == "1d 1h"
        assert sensor._format_uptime(3700) == "1h 1m"

        with patch.object(
            sensor, "_determine_connectivity_status", side_effect=TypeError
        ):
            assert sensor.native_value == "Unknown"

        with patch(
            "custom_components.actronair_neo.sensor._get_device_section",
            side_effect=TypeError,
        ):
            assert sensor.extra_state_attributes["error"]

    def test_connectivity_extra_state_exception_path(self, coordinator):
        sensor = ActronConnectivitySensor(coordinator)
        with patch(
            "custom_components.actronair_neo.sensor._get_device_section",
            side_effect=TypeError,
        ):
            assert sensor.extra_state_attributes["error"]

    def test_performance_native_exception_path(self, coordinator, mock_status):
        sensor = ActronPerformanceSensor(coordinator)
        mock_status["raw_data"]["lastKnownState"]["LiveAircon"] = {
            "CompressorCapacity": "bad"
        }
        assert sensor.native_value is None

    def test_performance_remaining_paths(self, coordinator, mock_status):
        sensor = ActronPerformanceSensor(coordinator)
        coordinator.last_update_success = False
        assert sensor.available is False

        coordinator.last_update_success = True
        mock_status["raw_data"]["lastKnownState"]["LiveAircon"] = {}
        assert sensor.native_value is None
        assert sensor.extra_state_attributes["status"] == "No live data available"

        assert sensor._format_temperature("bad") == "bad"
        assert sensor._format_power("bad") == "bad"
        assert (
            sensor._get_operational_status(
                {"SystemOn": True, "CompressorMode": "ON", "AmRunningFan": True}
            )
            == "Active Cooling/Heating"
        )
        assert (
            sensor._get_operational_status(
                {"SystemOn": True, "CompressorMode": "OFF", "AmRunningFan": True}
            )
            == "Fan Only"
        )
        assert (
            sensor._get_operational_status(
                {"SystemOn": True, "CompressorMode": "OFF", "AmRunningFan": False}
            )
            == "System On (Idle)"
        )
        assert (
            sensor._get_operational_status(
                {"SystemOn": True, "CompressorMode": "ON", "AmRunningFan": False}
            )
            == "Compressor Only"
        )

        mock_status["raw_data"]["lastKnownState"]["LiveAircon"] = {"SystemOn": True}
        with patch.object(sensor, "_get_operational_status", side_effect=TypeError):
            assert sensor.extra_state_attributes["error"]

        coordinator.data = {"raw_data": {"lastKnownState": {"LiveAircon": {}}}}
        assert sensor.available is True

        coordinator.data = {"raw_data": []}
        assert sensor.available is False

    def test_power_and_energy_remaining_paths(self, coordinator, mock_status):
        power_sensor = ActronCompressorPowerSensor(coordinator)
        energy_sensor = ActronCompressorEnergySensor(coordinator)

        mock_status["raw_data"]["lastKnownState"]["LiveAircon"] = {
            "SystemOn": True,
            "CompressorCapacity": 40,
            "OutdoorUnit": {"CompPower": 800},
        }
        _ = energy_sensor.native_value
        energy_sensor._last_update = (
            energy_sensor._last_update.replace(microsecond=0)
            if energy_sensor._last_update
            else energy_sensor._last_update
        )
        _ = energy_sensor.native_value

        mock_status["raw_data"]["lastKnownState"] = None
        assert power_sensor.native_value is None
        assert power_sensor.extra_state_attributes["error"]
        assert energy_sensor.native_value is None
        assert energy_sensor.extra_state_attributes["error"]

        mock_status["raw_data"]["lastKnownState"] = {
            "LiveAircon": {"SystemOn": True, "OutdoorUnit": {"CompPower": "bad"}}
        }
        assert power_sensor.native_value is None
        assert energy_sensor.native_value is None

        coordinator.data = MagicMock()
        coordinator.data.get = MagicMock(side_effect=TypeError)
        assert power_sensor.extra_state_attributes["error"]
        assert energy_sensor.extra_state_attributes["error"]

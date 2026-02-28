"""Tests for the ActronAir Neo binary sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.actronair_neo.binary_sensor import (
    ActronActiveWarningsSensor,
    ActronFastHeatingSensor,
    ActronHealthMonitorSensor,
    ActronZoneYourZoneEnabledSensor,
    async_setup_entry,
)

from .conftest import MOCK_SERIAL, create_mock_coordinator


@pytest.fixture
def coordinator(mock_api, mock_status):
    """Create a coordinator for testing."""
    return create_mock_coordinator(MagicMock(), mock_api, mock_status)


# ── async_setup_entry Tests ──────────────────────────────────────


class TestAsyncSetupEntry:
    @pytest.mark.asyncio
    async def test_setup_creates_entities(self, coordinator):
        mock_entry = MagicMock()
        mock_entry.runtime_data = coordinator
        added: list = []
        await async_setup_entry(MagicMock(), mock_entry, added.extend)
        # 3 main sensors + 2 zones = 5
        assert len(added) == 5
        types = {type(e).__name__ for e in added}
        assert "ActronHealthMonitorSensor" in types
        assert "ActronFastHeatingSensor" in types
        assert "ActronActiveWarningsSensor" in types
        assert "ActronZoneYourZoneEnabledSensor" in types


# ── Health Monitor Sensor Tests ──────────────────────────────────


class TestHealthMonitorSensor:
    """Tests for the ActronHealthMonitorSensor entity."""

    def test_is_on_no_errors(self, coordinator):
        """Test health monitor reports False when no errors."""
        sensor = ActronHealthMonitorSensor(coordinator)
        assert sensor.is_on is False

    def test_is_on_with_error_code(self, coordinator, mock_status):
        """Test health monitor reports True when ErrCode is non-zero."""
        serial_key = f"<{MOCK_SERIAL.upper()}>"
        mock_status["raw_data"]["lastKnownState"][serial_key]["LiveAircon"][
            "ErrCode"
        ] = 42
        sensor = ActronHealthMonitorSensor(coordinator)
        assert sensor.is_on is True

    def test_is_on_with_error_history(self, coordinator, mock_status):
        """Test health monitor reports True when error history exists."""
        serial_key = f"<{MOCK_SERIAL.upper()}>"
        mock_status["raw_data"]["lastKnownState"][serial_key]["Servicing"][
            "NV_ErrorHistory"
        ] = ["E001"]
        sensor = ActronHealthMonitorSensor(coordinator)
        assert sensor.is_on is True

    def test_is_on_no_raw_data(self, coordinator, mock_status):
        """Test health monitor handles missing raw data gracefully."""
        mock_status["raw_data"] = {}
        sensor = ActronHealthMonitorSensor(coordinator)
        assert sensor.is_on is False

    def test_is_on_key_error_path(self, coordinator, mock_status):
        """Test health monitor handles KeyError path gracefully."""
        del mock_status["raw_data"]
        sensor = ActronHealthMonitorSensor(coordinator)
        assert sensor.is_on is False

    def test_unique_id(self, coordinator):
        """Test unique ID generation."""
        sensor = ActronHealthMonitorSensor(coordinator)
        assert MOCK_SERIAL in sensor.unique_id

    def test_extra_state_attributes_healthy(self, coordinator):
        """Test extra attributes when system is healthy."""
        sensor = ActronHealthMonitorSensor(coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs["health_status"] == "Healthy"
        assert attrs["total_errors"] == 0
        assert attrs["error_history"] == []
        assert attrs["last_error"] == "None"

    def test_extra_state_attributes_with_errors(self, coordinator, mock_status):
        """Test extra attributes when errors exist."""
        serial_key = f"<{MOCK_SERIAL.upper()}>"
        mock_status["raw_data"]["lastKnownState"][serial_key]["Servicing"][
            "NV_ErrorHistory"
        ] = ["E001", "E002"]
        sensor = ActronHealthMonitorSensor(coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs["health_status"] == "Issues Detected"
        assert attrs["total_errors"] == 2
        assert attrs["last_error"] == "E002"

    def test_extra_state_attributes_error_path(self, coordinator, mock_status):
        """Test extra attributes fallback when data shape is invalid."""
        del mock_status["raw_data"]
        sensor = ActronHealthMonitorSensor(coordinator)
        assert (
            sensor.extra_state_attributes["error"] == "Failed to get health attributes"
        )


# ── YourZone Enabled Sensor Tests ────────────────────────────────


class TestZoneYourZoneEnabledSensor:
    """Tests for the ActronZoneYourZoneEnabledSensor entity."""

    def test_is_on_disabled(self, coordinator):
        """Test sensor reports False when airflow control is disabled."""
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        # Default in _create_mock_zone has airflow_control_enabled = False
        assert sensor.is_on is False

    def test_is_on_enabled(self, coordinator, mock_status):
        """Test sensor reports True when airflow control is enabled."""
        mock_status["zones"]["zone_1"]["airflow_control_enabled"] = True
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        assert sensor.is_on is True

    def test_unique_id(self, coordinator):
        """Test unique ID includes serial number."""
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        assert MOCK_SERIAL in sensor.unique_id

    def test_extra_state_attributes(self, coordinator):
        """Test extra state attributes."""
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        attrs = sensor.extra_state_attributes
        assert attrs["zone_id"] == "zone_1"
        assert attrs["zone_name"] == "Living Room"
        assert attrs["airflow_setpoint"] == 50

    def test_extra_state_attributes_missing_zone(self, coordinator, mock_status):
        """Test zone attrs returns empty dict when zone is missing."""
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        del mock_status["zones"]["zone_1"]
        assert sensor.extra_state_attributes == {}

    def test_zone_missing_returns_false(self, coordinator, mock_status):
        """Test is_on returns False when zone key is missing."""
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        del mock_status["zones"]["zone_1"]
        assert sensor.is_on is False

    def test_available_false_when_zone_missing(self, coordinator, mock_status):
        """Test availability follows zone existence."""
        sensor = ActronZoneYourZoneEnabledSensor(coordinator, "zone_1")
        del mock_status["zones"]["zone_1"]
        assert sensor.available is False


# ── Fast Heating Sensor Tests ────────────────────────────────────


class TestFastHeatingSensor:
    def test_is_on_false(self, coordinator):
        sensor = ActronFastHeatingSensor(coordinator)
        assert sensor.is_on is False

    def test_is_on_true(self, coordinator, mock_status):
        mock_status["main"]["fast_heating"] = True
        sensor = ActronFastHeatingSensor(coordinator)
        assert sensor.is_on is True


# ── Active Warnings Sensor Tests ─────────────────────────────────


class TestActiveWarningsSensor:
    def test_is_on_no_warnings(self, coordinator):
        sensor = ActronActiveWarningsSensor(coordinator)
        assert sensor.is_on is False

    def test_is_on_with_warnings(self, coordinator, mock_status):
        mock_status["main"]["warnings"] = ["W001", "W002"]
        sensor = ActronActiveWarningsSensor(coordinator)
        assert sensor.is_on is True

    def test_extra_state_attributes_empty(self, coordinator):
        sensor = ActronActiveWarningsSensor(coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs["warning_count"] == 0
        assert attrs["warnings"] == []

    def test_extra_state_attributes_with_warnings(self, coordinator, mock_status):
        mock_status["main"]["warnings"] = ["W001"]
        sensor = ActronActiveWarningsSensor(coordinator)
        attrs = sensor.extra_state_attributes
        assert attrs["warning_count"] == 1
        assert attrs["warnings"] == ["W001"]

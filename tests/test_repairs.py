"""Tests for the ActronAir Neo repairs flow."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.data_entry_flow import FlowResultType

from custom_components.actronair_neo.repairs import (
    ApiAuthenticationFailedRepairFlow,
    DeviceOfflineRepairFlow,
    SensorUnavailableRepairFlow,
    async_check_issues,
    async_create_fix_flow,
    async_health_check,
)


class TestApiAuthenticationFailedRepairFlow:
    """Tests for the API authentication failure repair flow."""

    @pytest.mark.asyncio
    async def test_init_step_shows_form(self):
        """Test init step shows form."""
        flow = ApiAuthenticationFailedRepairFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_init()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_step_with_input_creates_entry(self):
        """Test init step with user input creates entry."""
        flow = ApiAuthenticationFailedRepairFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_init(user_input={})
        assert result["type"] is FlowResultType.CREATE_ENTRY


class TestDeviceOfflineRepairFlow:
    """Tests for the device offline repair flow."""

    @pytest.mark.asyncio
    async def test_init_step_shows_form(self):
        """Test init step shows form."""
        flow = DeviceOfflineRepairFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_init()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_step_with_input_creates_entry(self):
        """Test init step with user input creates entry."""
        flow = DeviceOfflineRepairFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_init(user_input={})
        assert result["type"] is FlowResultType.CREATE_ENTRY


class TestSensorUnavailableRepairFlow:
    """Tests for the sensor unavailable repair flow."""

    @pytest.mark.asyncio
    async def test_init_step_shows_form(self):
        """Test init step shows form."""
        flow = SensorUnavailableRepairFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_init()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_step_with_input_creates_entry(self):
        """Test init step with user input creates entry."""
        flow = SensorUnavailableRepairFlow()
        flow.hass = MagicMock()
        result = await flow.async_step_init(user_input={})
        assert result["type"] is FlowResultType.CREATE_ENTRY


class TestAsyncCreateFixFlow:
    """Tests for the fix flow factory."""

    @pytest.mark.asyncio
    async def test_creates_auth_repair_flow(self):
        """Test fix flow routes authentication issues correctly."""
        hass = MagicMock()
        flow = await async_create_fix_flow(hass, "api_authentication_failed", None)
        assert isinstance(flow, ApiAuthenticationFailedRepairFlow)

    @pytest.mark.asyncio
    async def test_creates_device_offline_repair_flow(self):
        """Test fix flow routes device offline issues correctly."""
        hass = MagicMock()
        flow = await async_create_fix_flow(hass, "device_offline", None)
        assert isinstance(flow, DeviceOfflineRepairFlow)

    @pytest.mark.asyncio
    async def test_creates_sensor_unavailable_repair_flow(self):
        """Test fix flow routes sensor unavailable issues correctly."""
        hass = MagicMock()
        flow = await async_create_fix_flow(hass, "sensor_unavailable", None)
        assert isinstance(flow, SensorUnavailableRepairFlow)

    @pytest.mark.asyncio
    async def test_creates_confirm_flow_for_unknown_issue(self):
        """Test fix flow returns ConfirmRepairFlow for unknown issues."""
        hass = MagicMock()
        flow = await async_create_fix_flow(hass, "unknown_issue", None)
        assert isinstance(flow, ConfirmRepairFlow)

    @pytest.mark.asyncio
    async def test_creates_repair_flow_with_data(self):
        """Test fix flow factory with data."""
        hass = MagicMock()
        data = {"key": "value"}
        flow = await async_create_fix_flow(hass, "device_offline", data)
        assert isinstance(flow, DeviceOfflineRepairFlow)


@pytest.mark.asyncio
async def test_async_check_issues_creates_and_deletes_issue_paths():
    """Test issue checks for auth/device/sensor branches."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.api_error_count = 6
    coordinator.device_id = "ABC123"
    coordinator.last_update_success = False
    coordinator.data = {
        "zones": {
            "zone_1": {
                "name": "Living",
                "temp": None,
                "capabilities": {"exists": True},
            }
        }
    }
    entry = MagicMock()
    entry.runtime_data = coordinator

    with (
        pytest.MonkeyPatch.context() as mp,
    ):
        created: list[str] = []
        deleted: list[str] = []

        def _create_issue(*_args, **kwargs):
            created.append(kwargs["translation_key"])

        def _delete_issue(*_args):
            deleted.append(_args[2])

        mp.setattr(
            "custom_components.actronair_neo.repairs.async_create_issue", _create_issue
        )
        mp.setattr(
            "custom_components.actronair_neo.repairs.async_delete_issue", _delete_issue
        )
        await async_check_issues(hass, entry)

    assert "api_authentication_failed" in created
    assert "device_offline" in created
    assert "sensor_unavailable" in created
    assert deleted == []


@pytest.mark.asyncio
async def test_async_check_issues_delete_paths():
    """Test issue checks remove issues when healthy."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.api_error_count = 0
    coordinator.device_id = "ABC123"
    coordinator.last_update_success = True
    coordinator.data = {"zones": {"zone_1": {"name": "Living", "temp": 22}}}
    entry = MagicMock()
    entry.runtime_data = coordinator

    deleted: list[str] = []
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "custom_components.actronair_neo.repairs.async_create_issue",
            lambda *_args, **_kwargs: None,
        )
        mp.setattr(
            "custom_components.actronair_neo.repairs.async_delete_issue",
            lambda *_args: deleted.append(_args[2]),
        )
        await async_check_issues(hass, entry)

    assert "api_authentication_failed" in deleted
    assert "device_offline" in deleted
    assert "sensor_unavailable" in deleted


@pytest.mark.asyncio
async def test_async_health_check_degraded_and_unhealthy():
    """Test health check includes issues and status transitions."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.api_error_count = 12
    coordinator.last_successful_api_request = "2025-01-01T00:00:00Z"
    coordinator.api_cache_size = 1
    coordinator.data = {
        "zones": {
            "zone_1": {"name": "Living", "battery_level": 10, "signal_strength": -80}
        }
    }
    entry = MagicMock()
    entry.runtime_data = coordinator

    result = await async_health_check(hass, entry)
    assert result["overall_status"] == "unhealthy"
    assert len(result["issues"]) >= 2


@pytest.mark.asyncio
async def test_async_health_check_degraded_warning_only():
    """Test health check returns degraded when only warning issues exist."""
    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.api_error_count = 4
    coordinator.last_successful_api_request = "2025-01-01T00:00:00Z"
    coordinator.api_cache_size = 0
    coordinator.data = {
        "zones": {
            "zone_1": {"name": "Living", "battery_level": 50, "signal_strength": -60}
        }
    }
    entry = MagicMock()
    entry.runtime_data = coordinator

    result = await async_health_check(hass, entry)
    assert result["overall_status"] == "degraded"

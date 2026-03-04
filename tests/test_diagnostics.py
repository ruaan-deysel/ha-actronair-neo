"""Tests for the ActronAir Neo diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState

from custom_components.actronair_neo.diagnostics import (
    TO_REDACT,
    async_get_config_entry_diagnostics,
)

# Patch target for the internal API factory
_PATCH_CREATE_API = "custom_components.actronair_neo._create_api_client"


async def test_diagnostics(
    hass,
    mock_config_entry,
    mock_api,
    mock_ac_status_response,
    enable_custom_integrations,
):
    """Test diagnostics output."""
    mock_api.get_ac_status = AsyncMock(return_value=mock_ac_status_response)

    with patch(_PATCH_CREATE_API, return_value=mock_api):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert "entry" in result
    assert "data" in result


async def test_diagnostics_no_coordinator_data(
    hass,
    mock_config_entry,
    mock_api,
    mock_ac_status_response,
    enable_custom_integrations,
):
    """Test diagnostics when coordinator data is None."""
    mock_api.get_ac_status = AsyncMock(return_value=mock_ac_status_response)

    with patch(_PATCH_CREATE_API, return_value=mock_api):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Clear coordinator data
    coordinator = mock_config_entry.runtime_data
    coordinator.data = None

    with pytest.raises(ValueError, match="No coordinator data available"):
        await async_get_config_entry_diagnostics(hass, mock_config_entry)


def test_to_redact_contents():
    """Test the TO_REDACT set contains expected keys."""
    assert "access_token" in TO_REDACT
    assert "refresh_token" in TO_REDACT
    assert "serial" in TO_REDACT
    assert "MAC" in TO_REDACT


async def test_diagnostics_includes_zone_wireless_sensor(
    hass,
    mock_config_entry,
):
    """Test diagnostics includes enhanced zone peripheral details."""
    coordinator = MagicMock()
    coordinator.data = {
        "main": {
            "model": "Neo",
            "firmware_version": "1.0",
            "serial_number": "ABC123",
            "compressor_state": "COOL",
            "is_on": True,
            "mode": "COOL",
            "fan_mode": "AUTO",
            "indoor_temp": 22.0,
            "indoor_humidity": 45.0,
        },
        "zones": {
            "zone_1": {
                "name": "Living",
                "is_enabled": True,
                "temp": 22.0,
                "humidity": 45.0,
            }
        },
    }
    coordinator.get_diagnostics_snapshot = MagicMock(
        return_value={
            "lastKnownState": {
                "<ABC123>": {"SystemStatus_Local": {}, "Cloud": {}},
                "AirconSystem": {
                    "IndoorUnit": {},
                    "OutdoorUnit": {},
                    "MasterSerial": "ABC123",
                },
                "LiveAircon": {},
                "RemoteZoneInfo": [{"NV_Title": "Living"}],
            }
        }
    )
    coordinator.get_zone_peripheral = MagicMock(
        return_value={
            "DeviceType": "WallSensor",
            "RemainingBatteryCapacity_pc": 78,
            "Signal_of3": "2",
            "Firmware": {"InstalledVersion": {"NRF52": "1.0.0"}},
            "SensorInputs": {
                "SHTC1": {"Temperature_oC": 22.0, "RelativeHumidity_pc": 45.0},
                "Thermistors": {"Ambient_oC": 21.0},
            },
        }
    )
    mock_config_entry.runtime_data = coordinator

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    zone_1 = result["data"]["zones"]["zone_1"]
    assert "wireless_sensor" in zone_1
    assert zone_1["wireless_sensor"]["type"] == "WallSensor"


async def test_diagnostics_type_error_path(hass, mock_config_entry):
    """Test diagnostics handles unexpected structure with TypeError payload."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = {
        "main": None,
        "zones": {},
    }
    mock_config_entry.runtime_data.get_diagnostics_snapshot = MagicMock(return_value={})

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert result["error"]["type"] == "unexpected"


async def test_diagnostics_key_error_path(hass, mock_config_entry):
    """Test diagnostics handles missing keys with KeyError payload."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = {
        "main": {},
        "zones": {},
    }
    mock_config_entry.runtime_data.get_diagnostics_snapshot = MagicMock(
        return_value={"lastKnownState": {}}
    )

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert result["error"]["type"] == "KeyError"


async def test_diagnostics_value_error_path(hass, mock_config_entry):
    """Test diagnostics handles value formatting failures with ValueError payload."""
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.get_zone_peripheral = MagicMock(
        side_effect=ValueError("bad")
    )
    mock_config_entry.runtime_data.data = {
        "main": {
            "model": "Neo",
            "firmware_version": "1.0",
            "serial_number": "ABC123",
            "indoor_humidity": "bad-humidity",
        },
        "zones": {
            "zone_1": {
                "name": "Living",
                "is_enabled": True,
                "temp": 22.0,
                "humidity": 45.0,
            }
        },
    }
    mock_config_entry.runtime_data.get_diagnostics_snapshot = MagicMock(
        return_value={
            "lastKnownState": {
                "<ABC123>": {},
                "AirconSystem": {},
                "LiveAircon": {},
            }
        }
    )

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert result["error"]["type"] == "ValueError"

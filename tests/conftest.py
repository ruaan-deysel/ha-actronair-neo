"""Fixtures for ActronAir Neo tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock Home Assistant imports
HomeAssistant = MagicMock()


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture
def mock_api():
    """Create a mock ActronApi instance."""
    api = MagicMock()
    api.get_ac_status = AsyncMock()
    api.send_command = AsyncMock()
    api.create_command = MagicMock()
    api.is_api_healthy = MagicMock(return_value=True)
    api.initializer = AsyncMock()
    api.get_devices = AsyncMock()
    return api


@pytest.fixture
def mock_ac_status_response():
    """Return a mock AC status response."""
    return {
        "lastKnownState": {
            "MasterInfo": {"LiveTemp_oC": 22.5, "LiveHumidity_pc": 45.0},
            "LiveAircon": {
                "CompressorMode": "COOL",
                "Filter": {"NeedsAttention": False, "TimeToClean_days": 30},
            },
            "UserAirconSettings": {
                "isOn": True,
                "Mode": "COOL",
                "FanMode": "AUTO",
                "TemperatureSetpoint_Cool_oC": 21.0,
                "TemperatureSetpoint_Heat_oC": 24.0,
                "EnabledZones": [True, True, False, False, False, False, False, False],
                "AwayMode": False,
                "QuietMode": False,
            },
            "AirconSystem": {
                "MasterSerial": "ABC123",
                "MasterWCFirmwareVersion": "1.2.3",
                "IndoorUnit": {"NV_ModelNumber": "NEO-12"},
            },
            "Alerts": {"CleanFilter": False, "Defrosting": False},
        }
    }


@pytest.fixture
def mock_devices_response():
    """Create a mock devices response."""
    return [
        {"serial": "ABC123", "name": "Living Room AC", "type": "Neo", "id": "12345"},
        {"serial": "DEF456", "name": "Bedroom AC", "type": "Neo", "id": "67890"},
    ]


@pytest.fixture
def mock_token_response():
    """Create a mock token response."""
    return {
        "access_token": "mock_access_token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "mock_refresh_token",
    }


@pytest.fixture
def mock_command_response():
    """Create a mock command response."""
    return {"success": True, "message": "Command executed successfully"}

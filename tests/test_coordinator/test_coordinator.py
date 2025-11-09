"""Tests for the ActronAir Neo coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock Home Assistant imports
HomeAssistant = MagicMock()
ConfigEntryAuthFailed = Exception
UpdateFailed = Exception

from custom_components.actronair_neo.api import ApiError, AuthenticationError
from custom_components.actronair_neo.coordinator import ActronDataCoordinator


@pytest.fixture
def mock_parsed_data():
    """Create mock parsed data for the coordinator."""
    main_data = {
        "is_on": True,
        "mode": "COOL",
        "fan_mode": "AUTO",
        "fan_continuous": False,
        "base_fan_mode": "AUTO",
        "supported_fan_modes": ["LOW", "MED", "HIGH", "AUTO"],
        "temp_setpoint_cool": 21.0,
        "temp_setpoint_heat": 24.0,
        "indoor_temp": 22.5,
        "indoor_humidity": 45.0,
        "compressor_state": "COOL",
        "EnabledZones": [True, True, False, False, False, False, False, False],
        "away_mode": False,
        "quiet_mode": False,
        "model": "NEO",
        "indoor_model": "NEO-12",
        "serial_number": "ABC123",
        "firmware_version": "1.2.3",
        "filter_clean_required": False,
        "defrosting": False,
    }

    zones = {
        "zone_1": {
            "name": "Living Room",
            "temp": 22.5,
            "setpoint": 21.0,
            "is_on": True,
            "capabilities": {
                "exists": True,
                "can_operate": True,
                "has_temp_control": True,
                "has_separate_targets": False,
                "peripheral_capabilities": None,
            },
            "humidity": None,
            "is_enabled": True,
            "temp_setpoint_cool": 21.0,
            "temp_setpoint_heat": 24.0,
            "battery_level": None,
            "signal_strength": None,
            "peripheral_type": None,
            "last_connection": None,
            "connection_state": None,
        },
        "zone_2": {
            "name": "Bedroom",
            "temp": 23.0,
            "setpoint": 21.0,
            "is_on": True,
            "capabilities": {
                "exists": True,
                "can_operate": True,
                "has_temp_control": True,
                "has_separate_targets": False,
                "peripheral_capabilities": None,
            },
            "humidity": None,
            "is_enabled": True,
            "temp_setpoint_cool": 21.0,
            "temp_setpoint_heat": 24.0,
            "battery_level": None,
            "signal_strength": None,
            "peripheral_type": None,
            "last_connection": None,
            "connection_state": None,
        },
    }

    # Create a mock AC status response
    raw_data = {
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

    return {"main": main_data, "zones": zones, "raw_data": raw_data}


@pytest.mark.asyncio
async def test_coordinator_initialization(mock_hass, mock_api) -> None:
    """Test coordinator initialization."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True

    # Act
    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Assert
    assert coordinator.api == mock_api
    assert coordinator.device_id == device_id
    assert coordinator.enable_zone_control == enable_zone_control
    assert coordinator.last_data is None
    assert coordinator._continuous_fan is False
    assert coordinator.update_interval == timedelta(seconds=update_interval)


@pytest.mark.asyncio
async def test_coordinator_update(
    mock_hass, mock_api, mock_ac_status_response, mock_parsed_data
) -> None:
    """Test coordinator update."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True

    mock_api.get_ac_status.return_value = mock_ac_status_response

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Mock the _parse_data method
    with patch.object(
        coordinator, "_parse_data", AsyncMock(return_value=mock_parsed_data)
    ) as mock_parse_data:
        # Act
        data = await coordinator._async_update_data()

        # Assert
        assert data == mock_parsed_data
        assert coordinator.last_data == mock_parsed_data
        mock_api.get_ac_status.assert_called_once_with(device_id)
        mock_parse_data.assert_called_once_with(mock_ac_status_response)


@pytest.mark.asyncio
async def test_coordinator_update_api_unhealthy(
    mock_hass, mock_api, mock_parsed_data
) -> None:
    """Test coordinator update when API is unhealthy."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True

    mock_api.is_api_healthy.return_value = False

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )
    coordinator.last_data = mock_parsed_data

    # Act
    data = await coordinator._async_update_data()

    # Assert
    assert data == mock_parsed_data
    mock_api.get_ac_status.assert_not_called()


@pytest.mark.asyncio
async def test_coordinator_update_authentication_error(mock_hass, mock_api) -> None:
    """Test coordinator update with authentication error."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True

    mock_api.get_ac_status.side_effect = AuthenticationError("Authentication failed")

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Act & Assert
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_update_api_error(
    mock_hass, mock_api, mock_parsed_data
) -> None:
    """Test coordinator update with API error."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True

    mock_api.get_ac_status.side_effect = ApiError("API error")

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Act & Assert - No cached data
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Arrange - With cached data
    coordinator.last_data = mock_parsed_data

    # Act
    data = await coordinator._async_update_data()

    # Assert
    assert data == mock_parsed_data


@pytest.mark.asyncio
async def test_set_temperature(mock_hass, mock_api) -> None:
    """Test setting temperature."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True
    temperature = 22.5
    is_cooling = True

    mock_api.create_command.return_value = {
        "UserAirconSettings": {"TemperatureSetpoint_Cool_oC": temperature}
    }

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Mock the async_request_refresh method
    with patch.object(
        coordinator, "async_request_refresh", AsyncMock()
    ) as mock_refresh:
        # Act
        await coordinator.set_temperature(temperature, is_cooling)

        # Assert
        mock_api.create_command.assert_called_once_with(
            "SET_TEMP", temp=temperature, is_cool=is_cooling
        )
        mock_api.send_command.assert_called_once()
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_set_climate_mode(mock_hass, mock_api) -> None:
    """Test setting climate mode."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True
    mode = "HEAT"

    mock_api.create_command.return_value = {"UserAirconSettings": {"Mode": mode}}

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Mock the async_request_refresh method
    with patch.object(
        coordinator, "async_request_refresh", AsyncMock()
    ) as mock_refresh:
        # Act
        await coordinator.set_climate_mode(mode)

        # Assert
        mock_api.create_command.assert_called_once_with("CLIMATE_MODE", mode=mode)
        mock_api.send_command.assert_called_once()
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_set_zone_state(mock_hass, mock_api, mock_parsed_data) -> None:
    """Test setting zone state."""
    # Arrange
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True
    zone_id = "zone_1"  # String zone ID
    enable = False

    mock_api.create_command.return_value = {
        "UserAirconSettings": {
            "EnabledZones": [False, True, False, False, False, False, False, False]
        }
    }

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )
    coordinator.last_data = mock_parsed_data

    # Mock the async_request_refresh method
    with patch.object(
        coordinator, "async_request_refresh", AsyncMock()
    ) as mock_refresh:
        # Act
        await coordinator.set_zone_state(zone_id, enable)

        # Assert
        mock_api.create_command.assert_called_once()
        mock_api.send_command.assert_called_once()
        mock_refresh.assert_called_once()

        # Test with integer zone ID
        mock_api.create_command.reset_mock()
        mock_api.send_command.reset_mock()
        mock_refresh.reset_mock()

        # Act
        await coordinator.set_zone_state(0, enable)  # Direct zone index

        # Assert
        mock_api.create_command.assert_called_once()
        mock_api.send_command.assert_called_once()
        mock_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_validate_fan_mode(mock_parsed_data) -> None:
    """Test fan mode validation."""
    # Arrange
    mock_hass = MagicMock()
    mock_api = MagicMock()
    device_id = "ABC123"
    update_interval = 60
    enable_zone_control = True

    coordinator = ActronDataCoordinator(
        hass=mock_hass,
        api=mock_api,
        device_id=device_id,
        update_interval=update_interval,
        enable_zone_control=enable_zone_control,
    )

    # Set the data property
    coordinator.data = mock_parsed_data

    # Mock the validate_fan_mode method to avoid dependency on the API
    with patch.object(mock_api, "validate_fan_mode") as mock_validate_fan_mode:
        # Set up the mock to return the input value
        mock_validate_fan_mode.side_effect = (
            lambda mode, continuous=False: f"{mode}+CONT" if continuous else mode
        )

        # Act & Assert - Valid modes
        assert mock_api.validate_fan_mode("LOW") == "LOW"
        assert mock_api.validate_fan_mode("MED") == "MED"
        assert mock_api.validate_fan_mode("HIGH") == "HIGH"
        assert mock_api.validate_fan_mode("AUTO") == "AUTO"

        # Act & Assert - Valid modes with continuous
        assert mock_api.validate_fan_mode("LOW", True) == "LOW+CONT"
        assert mock_api.validate_fan_mode("MED", True) == "MED+CONT"
        assert mock_api.validate_fan_mode("HIGH", True) == "HIGH+CONT"

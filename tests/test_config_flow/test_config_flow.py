"""Tests for the ActronAir Neo config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock Home Assistant imports
class FlowResultType:
    FORM = "form"
    CREATE_ENTRY = "create_entry"


class ConfigEntry:
    def __init__(self) -> None:
        self.options = {}


config_entries = MagicMock()
config_entries.ConfigEntry = ConfigEntry
data_entry_flow = MagicMock()
data_entry_flow.FlowResultType = FlowResultType
HomeAssistant = MagicMock()

from custom_components.actronair_neo.api import ApiError, AuthenticationError
from custom_components.actronair_neo.config_flow import (
    ActronairNeoConfigFlow,
    CannotConnect,
    InvalidAuth,
    validate_input,
)
from custom_components.actronair_neo.const import (
    CONF_ENABLE_ZONE_CONTROL,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_USERNAME,
    DEFAULT_REFRESH_INTERVAL,
)


@pytest.mark.asyncio
async def test_validate_input_success(
    mock_hass, mock_api, mock_devices_response
) -> None:
    """Test successful validation of user input."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
    }

    mock_api.get_devices.return_value = mock_devices_response
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with (
        patch(
            "custom_components.actronair_neo.config_flow.ActronApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession",
            return_value=mock_session,
        ),
    ):
        # Act
        result = await validate_input(mock_hass, user_input)

        # Assert
        assert result["devices"] == mock_devices_response
        assert result["username"] == user_input[CONF_USERNAME]
        assert result["password"] == user_input[CONF_PASSWORD]
        assert result["refresh_interval"] == user_input[CONF_REFRESH_INTERVAL]
        mock_api.initializer.assert_called_once()
        mock_api.get_devices.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_authentication_error(mock_hass, mock_api) -> None:
    """Test validation with authentication error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "wrong_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
    }

    mock_api.initializer.side_effect = AuthenticationError("Authentication failed")
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with (
        patch(
            "custom_components.actronair_neo.config_flow.ActronApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession",
            return_value=mock_session,
        ),
    ):
        # Act & Assert
        with pytest.raises(InvalidAuth):
            await validate_input(mock_hass, user_input)


@pytest.mark.asyncio
async def test_validate_input_connection_error(mock_hass, mock_api) -> None:
    """Test validation with connection error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
    }

    mock_api.initializer.side_effect = ApiError("Connection error")
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with (
        patch(
            "custom_components.actronair_neo.config_flow.ActronApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession",
            return_value=mock_session,
        ),
    ):
        # Act & Assert
        with pytest.raises(CannotConnect):
            await validate_input(mock_hass, user_input)


@pytest.mark.asyncio
async def test_validate_input_no_devices(mock_hass, mock_api) -> None:
    """Test validation with no devices found."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
    }

    mock_api.get_devices.return_value = []
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with (
        patch(
            "custom_components.actronair_neo.config_flow.ActronApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession",
            return_value=mock_session,
        ),
    ):
        # Act & Assert
        with pytest.raises(CannotConnect):
            await validate_input(mock_hass, user_input)


@pytest.mark.asyncio
async def test_config_flow_step_user_single_device() -> None:
    """Test the user step of the config flow with a single device."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False,
    }

    # Mock validate_input to return a single device
    mock_device = {
        "serial": "ABC123",
        "name": "Living Room AC",
        "type": "Neo",
        "id": "12345",
    }

    validate_result = {
        "devices": [mock_device],
        "username": user_input[CONF_USERNAME],
        "password": user_input[CONF_PASSWORD],
        "refresh_interval": user_input[CONF_REFRESH_INTERVAL],
        "enable_zone_control": user_input[CONF_ENABLE_ZONE_CONTROL],
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(return_value=validate_result),
    ):
        # Create the config flow
        flow = ActronairNeoConfigFlow()
        flow.hass = MagicMock()

        # Act
        result = await flow.async_step_user(user_input)

        # Assert - Should create entry directly with single device
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == f"ActronAir Neo ({mock_device['name']})"
        assert result["data"][CONF_USERNAME] == user_input[CONF_USERNAME]
        assert result["data"][CONF_PASSWORD] == user_input[CONF_PASSWORD]
        assert (
            result["data"][CONF_REFRESH_INTERVAL] == user_input[CONF_REFRESH_INTERVAL]
        )
        assert result["data"]["serial_number"] == mock_device["serial"]
        assert result["data"]["system_id"] == mock_device["id"]
        assert (
            result["options"][CONF_ENABLE_ZONE_CONTROL]
            == user_input[CONF_ENABLE_ZONE_CONTROL]
        )


@pytest.mark.asyncio
async def test_config_flow_step_user_cannot_connect() -> None:
    """Test the user step of the config flow with connection error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False,
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(side_effect=CannotConnect("Cannot connect")),
    ):
        # Create the config flow
        flow = ActronairNeoConfigFlow()
        flow.hass = MagicMock()

        # Act
        result = await flow.async_step_user(user_input)

        # Assert
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_config_flow_step_user_invalid_auth() -> None:
    """Test the user step of the config flow with authentication error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "wrong_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False,
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(side_effect=InvalidAuth("Invalid auth")),
    ):
        # Create the config flow
        flow = ActronairNeoConfigFlow()
        flow.hass = MagicMock()

        # Act
        result = await flow.async_step_user(user_input)

        # Assert
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
async def test_config_flow_step_user_unknown_error() -> None:
    """Test the user step of the config flow with unknown error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False,
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(side_effect=Exception("Unknown error")),
    ):
        # Create the config flow
        flow = ActronairNeoConfigFlow()
        flow.hass = MagicMock()

        # Act
        result = await flow.async_step_user(user_input)

        # Assert
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["errors"]["base"] == "unknown"


@pytest.mark.asyncio
async def test_config_flow_step_user_multiple_devices() -> None:
    """Test the user step of the config flow with multiple devices."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False,
    }

    # Mock validate_input to return multiple devices
    mock_devices = [
        {"serial": "ABC123", "name": "Living Room AC", "type": "Neo", "id": "12345"},
        {"serial": "DEF456", "name": "Bedroom AC", "type": "Neo", "id": "67890"},
    ]

    validate_result = {
        "devices": mock_devices,
        "username": user_input[CONF_USERNAME],
        "password": user_input[CONF_PASSWORD],
        "refresh_interval": user_input[CONF_REFRESH_INTERVAL],
        "enable_zone_control": user_input[CONF_ENABLE_ZONE_CONTROL],
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(return_value=validate_result),
    ):
        # Create the config flow
        flow = ActronairNeoConfigFlow()
        flow.hass = MagicMock()

        # Act
        result = await flow.async_step_user(user_input)

        # Assert - Should show device selection form
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "select_device"


@pytest.mark.asyncio
async def test_config_flow_step_select_device() -> None:
    """Test the device selection step of the config flow."""
    # Arrange
    mock_devices = [
        {"serial": "ABC123", "name": "Living Room AC", "type": "Neo", "id": "12345"},
        {"serial": "DEF456", "name": "Bedroom AC", "type": "Neo", "id": "67890"},
    ]

    user_input = {
        "device": "DEF456"  # Select the second device
    }

    # Create the config flow and set up the state
    flow = ActronairNeoConfigFlow()
    flow.hass = MagicMock()
    flow._devices = mock_devices
    flow._username = "test_user"
    flow._password = "test_password"
    flow._refresh_interval = DEFAULT_REFRESH_INTERVAL
    flow._enable_zone_control = True

    # Act
    result = await flow.async_step_select_device(user_input)

    # Assert
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "ActronAir Neo (Bedroom AC)"
    assert result["data"][CONF_USERNAME] == "test_user"
    assert result["data"][CONF_PASSWORD] == "test_password"
    assert result["data"][CONF_REFRESH_INTERVAL] == DEFAULT_REFRESH_INTERVAL
    assert result["data"]["serial_number"] == "DEF456"
    assert result["data"]["system_id"] == "67890"
    assert result["options"][CONF_ENABLE_ZONE_CONTROL]


@pytest.mark.asyncio
async def test_config_flow_step_select_device_not_found() -> None:
    """Test the device selection step with an invalid device."""
    # Arrange
    mock_devices = [
        {"serial": "ABC123", "name": "Living Room AC", "type": "Neo", "id": "12345"}
    ]

    user_input = {
        "device": "INVALID"  # Invalid device serial
    }

    # Create the config flow and set up the state
    flow = ActronairNeoConfigFlow()
    flow.hass = MagicMock()
    flow._devices = mock_devices
    flow._username = "test_user"
    flow._password = "test_password"
    flow._refresh_interval = DEFAULT_REFRESH_INTERVAL
    flow._enable_zone_control = False

    # Act
    result = await flow.async_step_select_device(user_input)

    # Assert - Should show form again with error
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_device"
    assert result["errors"]["base"] == "device_not_found"


@pytest.mark.asyncio
async def test_config_flow_step_user_show_form() -> None:
    """Test the user step of the config flow showing the form."""
    # Create the config flow
    flow = ActronairNeoConfigFlow()
    flow.hass = MagicMock()

    # Act
    result = await flow.async_step_user()

    # Assert
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_options_flow() -> None:
    """Test the options flow."""
    # Arrange
    config_entry = MagicMock(spec=config_entries.ConfigEntry)
    config_entry.options = {CONF_REFRESH_INTERVAL: 120, CONF_ENABLE_ZONE_CONTROL: True}

    # Create the options flow
    flow = ActronairNeoConfigFlow.async_get_options_flow(config_entry)
    flow.hass = MagicMock()

    # Act - Show form
    result = await flow.async_step_init()

    # Assert
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    # Act - Submit form
    user_input = {CONF_REFRESH_INTERVAL: 180, CONF_ENABLE_ZONE_CONTROL: False}
    result = await flow.async_step_init(user_input)

    # Assert
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input

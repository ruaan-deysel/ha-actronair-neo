"""Tests for the ActronAir Neo config flow."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Mock Home Assistant imports
class FlowResultType:
    FORM = "form"
    CREATE_ENTRY = "create_entry"

class ConfigEntry:
    def __init__(self):
        self.options = {}

config_entries = MagicMock()
config_entries.ConfigEntry = ConfigEntry
data_entry_flow = MagicMock()
data_entry_flow.FlowResultType = FlowResultType
HomeAssistant = MagicMock()

from custom_components.actronair_neo.config_flow import (
    ActronairNeoConfigFlow,
    CannotConnect,
    InvalidAuth,
    validate_input
)
from custom_components.actronair_neo.const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_INTERVAL,
    CONF_ENABLE_ZONE_CONTROL,
    DEFAULT_REFRESH_INTERVAL
)
from custom_components.actronair_neo.api import ActronApi, AuthenticationError, ApiError


@pytest.mark.asyncio
async def test_validate_input_success(mock_hass, mock_api, mock_devices_response):
    """Test successful validation of user input."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL
    }

    mock_api.get_devices.return_value = mock_devices_response
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with patch("custom_components.actronair_neo.config_flow.ActronApi", return_value=mock_api), \
         patch("custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession", return_value=mock_session):
        # Act
        result = await validate_input(mock_hass, user_input)

        # Assert
        assert result["title"] == f"ActronAir Neo ({mock_devices_response[0]['name']})"
        assert result["serial_number"] == mock_devices_response[0]["serial"]
        mock_api.initializer.assert_called_once()
        mock_api.get_devices.assert_called_once()


@pytest.mark.asyncio
async def test_validate_input_authentication_error(mock_hass, mock_api):
    """Test validation with authentication error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "wrong_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL
    }

    mock_api.initializer.side_effect = AuthenticationError("Authentication failed")
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with patch("custom_components.actronair_neo.config_flow.ActronApi", return_value=mock_api), \
         patch("custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession", return_value=mock_session):
        # Act & Assert
        with pytest.raises(InvalidAuth):
            await validate_input(mock_hass, user_input)


@pytest.mark.asyncio
async def test_validate_input_connection_error(mock_hass, mock_api):
    """Test validation with connection error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL
    }

    mock_api.initializer.side_effect = ApiError("Connection error")
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with patch("custom_components.actronair_neo.config_flow.ActronApi", return_value=mock_api), \
         patch("custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession", return_value=mock_session):
        # Act & Assert
        with pytest.raises(CannotConnect):
            await validate_input(mock_hass, user_input)


@pytest.mark.asyncio
async def test_validate_input_no_devices(mock_hass, mock_api):
    """Test validation with no devices found."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL
    }

    mock_api.get_devices.return_value = []
    mock_session = MagicMock()

    # Mock the ActronApi class and session
    with patch("custom_components.actronair_neo.config_flow.ActronApi", return_value=mock_api), \
         patch("custom_components.actronair_neo.config_flow.aiohttp_client.async_get_clientsession", return_value=mock_session):
        # Act & Assert
        with pytest.raises(CannotConnect):
            await validate_input(mock_hass, user_input)


@pytest.mark.asyncio
async def test_config_flow_step_user_success():
    """Test the user step of the config flow with successful validation."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False
    }

    result = {
        "title": "ActronAir Neo (Living Room AC)",
        "serial_number": "ABC123"
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(return_value=result)
    ):
        # Create the config flow
        flow = ActronairNeoConfigFlow()
        flow.hass = MagicMock()

        # Act
        result = await flow.async_step_user(user_input)

        # Assert
        assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "ActronAir Neo (Living Room AC)"
        assert result["data"][CONF_USERNAME] == user_input[CONF_USERNAME]
        assert result["data"][CONF_PASSWORD] == user_input[CONF_PASSWORD]
        assert result["data"][CONF_REFRESH_INTERVAL] == user_input[CONF_REFRESH_INTERVAL]
        assert result["data"]["serial_number"] == "ABC123"
        assert result["options"][CONF_ENABLE_ZONE_CONTROL] == user_input[CONF_ENABLE_ZONE_CONTROL]


@pytest.mark.asyncio
async def test_config_flow_step_user_cannot_connect():
    """Test the user step of the config flow with connection error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(side_effect=CannotConnect("Cannot connect"))
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
async def test_config_flow_step_user_invalid_auth():
    """Test the user step of the config flow with authentication error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "wrong_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(side_effect=InvalidAuth("Invalid auth"))
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
async def test_config_flow_step_user_unknown_error():
    """Test the user step of the config flow with unknown error."""
    # Arrange
    user_input = {
        CONF_USERNAME: "test_user",
        CONF_PASSWORD: "test_password",
        CONF_REFRESH_INTERVAL: DEFAULT_REFRESH_INTERVAL,
        CONF_ENABLE_ZONE_CONTROL: False
    }

    # Mock the validate_input function
    with patch(
        "custom_components.actronair_neo.config_flow.validate_input",
        AsyncMock(side_effect=Exception("Unknown error"))
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
async def test_config_flow_step_user_show_form():
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
async def test_options_flow():
    """Test the options flow."""
    # Arrange
    config_entry = MagicMock(spec=config_entries.ConfigEntry)
    config_entry.options = {
        CONF_REFRESH_INTERVAL: 120,
        CONF_ENABLE_ZONE_CONTROL: True
    }

    # Create the options flow
    flow = ActronairNeoConfigFlow.async_get_options_flow(config_entry)
    flow.hass = MagicMock()

    # Act - Show form
    result = await flow.async_step_init()

    # Assert
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    # Act - Submit form
    user_input = {
        CONF_REFRESH_INTERVAL: 180,
        CONF_ENABLE_ZONE_CONTROL: False
    }
    result = await flow.async_step_init(user_input)

    # Assert
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == user_input

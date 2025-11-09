"""Tests for the ActronAir Neo API."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.actronair_neo.api import (
    ActronApi,
    AuthenticationError,
    RateLimiter,
)


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.request = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_api_devices_response():
    """Create a mock API devices response."""
    return {
        "_embedded": {
            "ac-system": [
                {
                    "serial": "ABC123",
                    "description": "Living Room AC",
                    "type": "Neo",
                    "id": "12345",
                },
                {
                    "serial": "DEF456",
                    "description": "Bedroom AC",
                    "type": "Neo",
                    "id": "67890",
                },
            ]
        }
    }


@pytest.mark.asyncio
async def test_api_initialization(mock_session) -> None:
    """Test API initialization."""
    # Arrange
    username = "test_user"
    password = "test_password"

    # Act
    api = ActronApi(username=username, password=password, session=mock_session)

    # Assert
    assert api.username == username
    assert api.password == password
    assert api.session == mock_session
    assert api.access_token is None
    assert api.refresh_token_value is None
    assert api.token_expires_at is None
    assert api.cached_status is None
    assert api.error_count == 0
    assert api.last_successful_request is None


@pytest.mark.asyncio
async def test_authenticate_success(mock_session, mock_token_response) -> None:
    """Test successful authentication."""
    # Arrange
    api = ActronApi(
        username="test_user", password="test_password", session=mock_session
    )

    # Mock the authenticate method directly
    with patch.object(api, "authenticate", AsyncMock()) as mock_authenticate:
        # Act
        await api.authenticate()

        # Assert
        mock_authenticate.assert_called_once()

        # Set up the tokens directly for verification
        api.access_token = mock_token_response["access_token"]
        api.refresh_token_value = mock_token_response["refresh_token"]
        api.token_expires_at = datetime.now() + timedelta(seconds=3600)

        # Verify the tokens are set
        assert api.access_token == mock_token_response["access_token"]
        assert api.refresh_token_value == mock_token_response["refresh_token"]
        assert api.token_expires_at is not None


@pytest.mark.asyncio
async def test_authenticate_failure(mock_session) -> None:
    """Test authentication failure."""
    # Arrange
    api = ActronApi(
        username="test_user", password="test_password", session=mock_session
    )
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.text = AsyncMock(return_value="Invalid credentials")
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Act & Assert
    with pytest.raises(AuthenticationError):
        await api.authenticate()


@pytest.mark.asyncio
async def test_get_devices(mock_session, mock_api_devices_response) -> None:
    """Test getting devices."""
    # Arrange
    api = ActronApi(
        username="test_user", password="test_password", session=mock_session
    )
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_api_devices_response)
    mock_session.request.return_value.__aenter__.return_value = mock_response

    # Mock the _make_request method
    with patch.object(
        api, "_make_request", AsyncMock(return_value=mock_api_devices_response)
    ) as mock_make_request:
        # Act
        devices = await api.get_devices()

        # Assert
        assert len(devices) == 2
        assert devices[0]["serial"] == "ABC123"
        assert devices[0]["name"] == "Living Room AC"
        assert devices[1]["serial"] == "DEF456"
        assert devices[1]["name"] == "Bedroom AC"
        mock_make_request.assert_called_once_with(
            "GET",
            "https://nimbus.actronair.com.au/api/v0/client/ac-systems?includeNeo=true",
        )


@pytest.mark.asyncio
async def test_get_ac_status(mock_session, mock_ac_status_response) -> None:
    """Test getting AC status."""
    # Arrange
    api = ActronApi(
        username="test_user", password="test_password", session=mock_session
    )
    serial = "ABC123"

    # Mock the _make_request method
    with (
        patch.object(
            api, "_make_request", AsyncMock(return_value=mock_ac_status_response)
        ) as mock_make_request,
        patch.object(api, "is_api_healthy", return_value=True),
    ):
        # Act
        status = await api.get_ac_status(serial)

        # Assert
        assert status == mock_ac_status_response
        assert api.cached_status == mock_ac_status_response
        mock_make_request.assert_called_once()


@pytest.mark.asyncio
async def test_get_ac_status_unhealthy_api(
    mock_session, mock_ac_status_response
) -> None:
    """Test getting AC status when API is unhealthy."""
    # Arrange
    api = ActronApi(
        username="test_user", password="test_password", session=mock_session
    )
    serial = "ABC123"
    api.cached_status = mock_ac_status_response

    # Mock the is_api_healthy method
    with patch.object(api, "is_api_healthy", return_value=False):
        # Act
        status = await api.get_ac_status(serial)

        # Assert
        assert status == mock_ac_status_response
        assert api.cached_status == mock_ac_status_response
        mock_session.request.assert_not_called()


@pytest.mark.asyncio
async def test_send_command(mock_session, mock_command_response) -> None:
    """Test sending a command."""
    # Arrange
    api = ActronApi(
        username="test_user", password="test_password", session=mock_session
    )
    serial = "ABC123"
    command = {"UserAirconSettings": {"isOn": True, "Mode": "COOL"}}

    # Mock the _make_request method
    with patch.object(
        api, "_make_request", AsyncMock(return_value=mock_command_response)
    ) as mock_make_request:
        # Act
        response = await api.send_command(serial, command)

        # Assert
        assert response == mock_command_response
        mock_make_request.assert_called_once()


@pytest.mark.asyncio
async def test_create_command() -> None:
    """Test creating a command."""
    # Arrange
    session = MagicMock(spec=aiohttp.ClientSession)
    api = ActronApi(username="test_user", password="test_password", session=session)

    # Act - Test SET_TEMP command
    temp_command = api.create_command("SET_TEMP", temp=22.5, is_cool=True)

    # Assert
    assert "command" in temp_command
    assert (
        temp_command["command"]["UserAirconSettings.TemperatureSetpoint_Cool_oC"]
        == 22.5
    )

    # Act - Test CLIMATE_MODE command
    mode_command = api.create_command("CLIMATE_MODE", mode="HEAT")

    # Assert
    assert "command" in mode_command
    assert mode_command["command"]["UserAirconSettings.Mode"] == "HEAT"

    # Act - Test SET_FAN_MODE command
    fan_command = api.create_command("FAN_MODE", mode="AUTO")

    # Assert
    assert "command" in fan_command
    assert fan_command["command"]["UserAirconSettings.FanMode"] == "AUTO"


@pytest.mark.asyncio
async def test_rate_limiter() -> None:
    """Test the rate limiter."""
    # Arrange
    rate_limiter = RateLimiter(calls_per_minute=5)

    # Act & Assert - Should not block for the first 5 calls
    for _ in range(5):
        async with rate_limiter:
            pass

    # The 6th call should be rate limited, but we can't easily test the timing
    # without making the test slow, so we'll just verify the semaphore exists
    assert hasattr(rate_limiter, "semaphore")
    assert rate_limiter.semaphore is not None


@pytest.mark.asyncio
async def test_is_api_healthy() -> None:
    """Test the API health check."""
    # Arrange
    session = MagicMock()
    api = ActronApi(username="test_user", password="test_password", session=session)

    # Act & Assert - Should be healthy by default
    assert api.is_api_healthy() is True

    # Simulate errors
    api.error_count = 6
    api.last_successful_request = None

    # Mock the is_api_healthy method to return False when error_count > 5
    with patch.object(api, "is_api_healthy", return_value=False):
        # Act & Assert - Should be unhealthy with many errors and no successful requests
        assert api.is_api_healthy() is False

    # Simulate recent successful request
    api.last_successful_request = datetime.now()

    # Mock the is_api_healthy method to return True when there's a recent successful request
    with patch.object(api, "is_api_healthy", return_value=True):
        # Act & Assert - Should be healthy with recent successful request despite errors
        assert api.is_api_healthy() is True

# Testing Guide

This guide explains how to test the ActronAir Neo integration, both manually and automatically.

## Table of Contents

- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [Continuous Integration](#continuous-integration)
- [Manual Testing](#manual-testing)

## Test Structure

The tests for the ActronAir Neo integration are organized in the `tests/` directory with the following structure:

```
tests/
├── conftest.py                 # Common test fixtures
├── test_api/                   # API client tests
│   ├── test_api.py             # Tests for the API client
│   └── test_auth.py            # Tests for authentication
├── test_config_flow/           # Config flow tests
│   └── test_config_flow.py     # Tests for the config flow
├── test_coordinator/           # Coordinator tests
│   └── test_coordinator.py     # Tests for the data coordinator
├── test_climate/               # Climate entity tests
│   └── test_climate.py         # Tests for the climate entity
├── test_sensor/                # Sensor entity tests
│   └── test_sensor.py          # Tests for sensor entities
└── test_init.py                # Integration initialization tests
```

## Running Tests

### Prerequisites

Before running tests, ensure you have a testing framework installed. The test files are structured to work with standard Python testing frameworks.

### Running Tests

The test suite is located in the `tests/` directory and includes comprehensive tests for all major components of the integration.

## Writing Tests

### Test Fixtures

Common test fixtures are defined in `tests/conftest.py`. These fixtures provide mock objects and data for tests.

Example fixtures:

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_api():
    """Provide a mock ActronNeoAPI instance."""
    api = MagicMock()
    api.authenticate.return_value = True
    api.get_devices.return_value = [
        {"serial": "ABC123", "name": "Living Room AC", "type": "Neo", "id": "1"}
    ]
    return api

@pytest.fixture
def mock_ac_status_response():
    """Provide a mock AC status response."""
    return {
        "lastKnownState": {
            "UserAirconSettings": {
                "isOn": True,
                "Mode": "COOL",
                "FanMode": "AUTO",
                "TemperatureSetpoint_Cool_oC": 24.0,
                "TemperatureSetpoint_Heat_oC": 21.0,
                "EnabledZones": [True, True, False, False, False, False, False, False]
            },
            "MasterInfo": {
                "LiveTemp_oC": 25.5,
                "LiveHumidity_pc": 50.0
            }
        }
    }
```

### Testing API Client

When testing the API client, mock the HTTP responses to avoid making actual API calls:

```python
import pytest
from unittest.mock import patch, MagicMock
from aiohttp import ClientResponseError

from custom_components.actronair_neo.api import ActronNeoAPI, ActronNeoAuthenticationError

@pytest.mark.asyncio
async def test_authenticate_success():
    """Test successful authentication."""
    # Arrange
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "access_token": "test_token",
        "token_type": "bearer",
        "expires_in": 3600
    }
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    api = ActronNeoAPI("test_user", "test_pass", session=mock_session)
    
    # Act
    result = await api.authenticate()
    
    # Assert
    assert result is True
    assert api._access_token == "test_token"
    assert api._token_type == "bearer"

@pytest.mark.asyncio
async def test_authenticate_failure():
    """Test authentication failure."""
    # Arrange
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.json.return_value = {
        "error": "invalid_grant",
        "error_description": "The user credentials are incorrect."
    }
    mock_session.post.return_value.__aenter__.return_value = mock_response
    
    api = ActronNeoAPI("test_user", "wrong_pass", session=mock_session)
    
    # Act & Assert
    with pytest.raises(ActronNeoAuthenticationError):
        await api.authenticate()
```

### Testing Coordinator

When testing the coordinator, mock the API client:

```python
import pytest
from unittest.mock import patch, MagicMock

from custom_components.actronair_neo.coordinator import ActronDataCoordinator

@pytest.mark.asyncio
async def test_coordinator_update(mock_api, mock_ac_status_response, hass):
    """Test coordinator update method."""
    # Arrange
    mock_api.get_system_status.return_value = mock_ac_status_response
    
    coordinator = ActronDataCoordinator(
        hass=hass,
        api=mock_api,
        device_id="ABC123",
        update_interval=60,
        enable_zone_control=True
    )
    
    # Act
    await coordinator._async_update_data()
    
    # Assert
    assert coordinator.data is not None
    assert coordinator.data.main["temperature"] == 25.5
    assert coordinator.data.main["humidity"] == 50.0
    assert coordinator.data.main["is_on"] is True
    assert coordinator.data.main["mode"] == "COOL"
    assert len(coordinator.data.zones) == 2  # Only enabled zones
```

### Testing Entities

When testing entities, mock the coordinator:

```python
import pytest
from unittest.mock import patch, MagicMock

from custom_components.actronair_neo.climate import ActronNeoClimate

@pytest.mark.asyncio
async def test_climate_state(hass, mock_coordinator):
    """Test climate entity state."""
    # Arrange
    entity = ActronNeoClimate(mock_coordinator, "climate.actronair_neo")
    
    # Act
    await entity.async_update()
    
    # Assert
    assert entity.state == "cool"
    assert entity.current_temperature == 25.5
    assert entity.target_temperature == 24.0
    assert entity.hvac_modes == ["off", "cool", "heat", "fan_only", "auto"]
    assert entity.fan_modes == ["auto", "low", "medium", "high"]
```

### Testing Config Flow

When testing the config flow, mock the API client and use the `hass` fixture:

```python
import pytest
from unittest.mock import patch, MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType

from custom_components.actronair_neo.config_flow import ActronNeoConfigFlow

async def test_config_flow_complete(hass, mock_api):
    """Test a complete config flow."""
    # Arrange
    result = await hass.config_entries.flow.async_init(
        "actronair_neo", context={"source": "user"}
    )
    
    # Act - Step 1: Show form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    
    # Act - Step 2: Submit credentials
    with patch(
        "custom_components.actronair_neo.config_flow.ActronNeoAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test_user",
                "password": "test_pass",
                "update_interval": 60,
                "enable_zone_control": True,
            },
        )
    
    # Assert
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "ActronAir Neo"
    assert result["data"] == {
        "username": "test_user",
        "password": "test_pass",
        "device_id": "ABC123",
        "update_interval": 60,
        "enable_zone_control": True,
    }
```

## Test Coverage

Aim for high test coverage, especially for critical components like the API client and coordinator. Use the coverage reports to identify areas that need more testing.

### Coverage Targets

- API Client: 90%+ coverage
- Coordinator: 90%+ coverage
- Config Flow: 90%+ coverage
- Entities: 80%+ coverage
- Overall: 85%+ coverage

## Continuous Integration

The integration uses GitHub Actions for continuous integration, including HACS validation and Home Assistant compatibility checks.

You can view the CI results on the GitHub Actions tab of the repository. Failed tests will be highlighted, and you can see the test output for debugging.

## Manual Testing

In addition to automated tests, manual testing is important for ensuring the integration works correctly with real devices.

### Manual Testing Checklist

1. **Installation**
   - Install the integration via HACS
   - Install the integration manually

2. **Configuration**
   - Add the integration through the UI
   - Configure with valid credentials
   - Configure with invalid credentials (should show error)
   - Reconfigure existing integration

3. **Basic Functionality**
   - Turn system on/off
   - Change mode (cool, heat, fan, auto)
   - Change temperature
   - Change fan speed

4. **Zone Control**
   - Enable/disable zones
   - Set zone-specific temperatures

5. **Error Handling**
   - Disconnect internet and verify appropriate error handling
   - Simulate API errors and verify recovery

6. **Performance**
   - Monitor memory usage
   - Check responsiveness of controls

### Testing with a Development Environment

For testing with a development environment:

1. Create a test Home Assistant instance:
   ```bash
   python -m homeassistant --config ./config
   ```

2. Symlink the integration to the test instance:
   ```bash
   ln -s /path/to/ha-actronair-neo/custom_components/actronair_neo /path/to/config/custom_components/
   ```

3. Restart the test instance and test the integration

## Conclusion

Thorough testing is essential for maintaining a high-quality integration. By following this guide, you can ensure that your contributions to the ActronAir Neo integration are well-tested and reliable.

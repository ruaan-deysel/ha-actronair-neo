# API Reference

This document provides a detailed reference for the ActronAir Neo API client implementation in the integration.

## API Client Overview

The API client (`api.py`) is responsible for all communication with the ActronAir Neo cloud API. It handles authentication, data retrieval, and command execution.

## Class: `ActronNeoAPI`

The main API client class that handles all interactions with the ActronAir Neo cloud API.

### Initialization

```python
def __init__(
    self,
    username: str,
    password: str,
    session: Optional[aiohttp.ClientSession] = None,
    request_timeout: int = 10,
) -> None:
```

**Parameters:**
- `username` (str): ActronAir Neo account username
- `password` (str): ActronAir Neo account password
- `session` (Optional[aiohttp.ClientSession]): Optional aiohttp session for making requests
- `request_timeout` (int): Timeout for API requests in seconds (default: 10)

**Example:**
```python
from custom_components.actronair_neo.api import ActronNeoAPI
import aiohttp

async def setup_api():
    session = aiohttp.ClientSession()
    api = ActronNeoAPI(
        username="your_username",
        password="your_password",
        session=session,
        request_timeout=15
    )
    return api
```

### Authentication Methods

#### `async def authenticate(self) -> bool`

Authenticates with the ActronAir Neo API using the provided credentials.

**Returns:**
- `bool`: True if authentication was successful, False otherwise

**Raises:**
- `ActronNeoAuthenticationError`: If authentication fails
- `ActronNeoAPIError`: If there's an API error during authentication

**Example:**
```python
try:
    authenticated = await api.authenticate()
    if authenticated:
        print("Authentication successful")
    else:
        print("Authentication failed")
except ActronNeoAuthenticationError as e:
    print(f"Authentication error: {e}")
```

#### `async def refresh_token(self) -> bool`

Refreshes the authentication token if it has expired.

**Returns:**
- `bool`: True if token refresh was successful, False otherwise

**Raises:**
- `ActronNeoAuthenticationError`: If token refresh fails
- `ActronNeoAPIError`: If there's an API error during token refresh

### Data Retrieval Methods

#### `async def get_devices(self) -> List[ActronNeoDeviceInfo]`

Retrieves a list of available ActronAir Neo devices associated with the account.

**Returns:**
- `List[ActronNeoDeviceInfo]`: List of device information objects

**Raises:**
- `ActronNeoAPIError`: If there's an API error during device retrieval
- `ActronNeoAuthenticationError`: If authentication is required

**Example:**
```python
try:
    devices = await api.get_devices()
    for device in devices:
        print(f"Device: {device['name']} (Serial: {device['serial']})")
except ActronNeoAPIError as e:
    print(f"API error: {e}")
```

#### `async def get_system_status(self, device_id: str) -> Dict[str, Any]`

Retrieves the current status of a specific ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device

**Returns:**
- `Dict[str, Any]`: Raw system status data

**Raises:**
- `ActronNeoAPIError`: If there's an API error during status retrieval
- `ActronNeoAuthenticationError`: If authentication is required

**Example:**
```python
try:
    status = await api.get_system_status("ABC123456")
    print(f"System is on: {status['UserAirconSettings']['isOn']}")
    print(f"Current mode: {status['UserAirconSettings']['Mode']}")
except ActronNeoAPIError as e:
    print(f"API error: {e}")
```

#### `async def get_system_events(self, device_id: str) -> Dict[str, Any]`

Retrieves recent events for a specific ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device

**Returns:**
- `Dict[str, Any]`: Raw system events data

**Raises:**
- `ActronNeoAPIError`: If there's an API error during events retrieval
- `ActronNeoAuthenticationError`: If authentication is required

### Command Methods

#### `async def send_command(self, device_id: str, command: Dict[str, Any]) -> bool`

Sends a command to a specific ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device
- `command` (Dict[str, Any]): The command to send

**Returns:**
- `bool`: True if the command was successful, False otherwise

**Raises:**
- `ActronNeoAPIError`: If there's an API error during command execution
- `ActronNeoAuthenticationError`: If authentication is required

**Example:**
```python
try:
    # Turn on the system in cooling mode
    command = {
        "UserAirconSettings.isOn": True,
        "UserAirconSettings.Mode": "COOL",
        "type": "set-settings"
    }
    success = await api.send_command("ABC123456", command)
    if success:
        print("Command sent successfully")
    else:
        print("Command failed")
except ActronNeoAPIError as e:
    print(f"API error: {e}")
```

#### `async def set_power(self, device_id: str, power_on: bool) -> bool`

Turns a specific ActronAir Neo device on or off.

**Parameters:**
- `device_id` (str): The serial number or ID of the device
- `power_on` (bool): True to turn on, False to turn off

**Returns:**
- `bool`: True if the command was successful, False otherwise

**Raises:**
- `ActronNeoAPIError`: If there's an API error during command execution
- `ActronNeoAuthenticationError`: If authentication is required

#### `async def set_mode(self, device_id: str, mode: str) -> bool`

Sets the operating mode of a specific ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device
- `mode` (str): The mode to set ("COOL", "HEAT", "FAN", "AUTO")

**Returns:**
- `bool`: True if the command was successful, False otherwise

**Raises:**
- `ActronNeoAPIError`: If there's an API error during command execution
- `ActronNeoAuthenticationError`: If authentication is required
- `ValueError`: If the mode is invalid

#### `async def set_temperature(self, device_id: str, temperature: float, mode: str) -> bool`

Sets the target temperature of a specific ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device
- `temperature` (float): The target temperature in degrees Celsius
- `mode` (str): The mode ("COOL", "HEAT", "AUTO")

**Returns:**
- `bool`: True if the command was successful, False otherwise

**Raises:**
- `ActronNeoAPIError`: If there's an API error during command execution
- `ActronNeoAuthenticationError`: If authentication is required
- `ValueError`: If the temperature is out of range or the mode is invalid

#### `async def set_fan_mode(self, device_id: str, fan_mode: str) -> bool`

Sets the fan mode of a specific ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device
- `fan_mode` (str): The fan mode to set ("LOW", "MED", "HIGH", "AUTO", etc.)

**Returns:**
- `bool`: True if the command was successful, False otherwise

**Raises:**
- `ActronNeoAPIError`: If there's an API error during command execution
- `ActronNeoAuthenticationError`: If authentication is required
- `ValueError`: If the fan mode is invalid

#### `async def set_zone_state(self, device_id: str, zone_index: int, enabled: bool) -> bool`

Enables or disables a specific zone on an ActronAir Neo device.

**Parameters:**
- `device_id` (str): The serial number or ID of the device
- `zone_index` (int): The index of the zone (0-7)
- `enabled` (bool): True to enable the zone, False to disable it

**Returns:**
- `bool`: True if the command was successful, False otherwise

**Raises:**
- `ActronNeoAPIError`: If there's an API error during command execution
- `ActronNeoAuthenticationError`: If authentication is required
- `ValueError`: If the zone index is out of range

### Utility Methods

#### `def validate_mode(self, mode: str) -> str`

Validates and normalizes an operating mode.

**Parameters:**
- `mode` (str): The mode to validate

**Returns:**
- `str`: The validated mode

**Raises:**
- `ValueError`: If the mode is invalid

#### `def validate_fan_mode(self, fan_mode: str, continuous: bool = False) -> str`

Validates and normalizes a fan mode.

**Parameters:**
- `fan_mode` (str): The fan mode to validate
- `continuous` (bool): Whether to set continuous fan operation

**Returns:**
- `str`: The validated fan mode

**Raises:**
- `ValueError`: If the fan mode is invalid or continuous is not supported for the mode

#### `async def is_api_healthy(self) -> bool`

Checks if the API is healthy and accessible.

**Returns:**
- `bool`: True if the API is healthy, False otherwise

## Exception Classes

### `ActronNeoAPIError`

Base exception class for all API-related errors.

```python
class ActronNeoAPIError(Exception):
    """Exception raised for errors in the ActronAir Neo API."""
    pass
```

### `ActronNeoAuthenticationError`

Exception raised for authentication errors.

```python
class ActronNeoAuthenticationError(ActronNeoAPIError):
    """Exception raised for authentication errors."""
    pass
```

### `ActronNeoRateLimitError`

Exception raised when API rate limits are exceeded.

```python
class ActronNeoRateLimitError(ActronNeoAPIError):
    """Exception raised when API rate limits are exceeded."""
    pass
```

## Type Definitions

The API client uses several type definitions from `types.py`:

### `ActronNeoDeviceInfo`

```python
class ActronNeoDeviceInfo(TypedDict):
    """Type for ActronAir Neo device information."""
    serial: str
    name: str
    type: str
    id: str
```

### `ActronNeoRawData`

```python
class ActronNeoRawData(TypedDict):
    """Type for raw ActronAir Neo API response data."""
    lastKnownState: Dict[str, Any]
```

## Rate Limiting

The API client implements rate limiting to prevent exceeding the ActronAir Neo API's rate limits:

```python
self._rate_limiter = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
```

All API requests are wrapped with this rate limiter to ensure compliance with API limits.

## Best Practices

When using the API client:

1. **Reuse the API instance** to benefit from token caching
2. **Handle exceptions** appropriately to provide a good user experience
3. **Implement backoff strategies** for retrying failed requests
4. **Close the session** when done to free resources

```python
try:
    # Use the API
    await api.authenticate()
    devices = await api.get_devices()
except ActronNeoAuthenticationError:
    # Handle authentication errors
    print("Authentication failed. Check credentials.")
except ActronNeoRateLimitError:
    # Handle rate limit errors
    print("Rate limit exceeded. Try again later.")
except ActronNeoAPIError as e:
    # Handle other API errors
    print(f"API error: {e}")
finally:
    # Clean up
    if session and not session.closed:
        await session.close()
```

## Next Steps

- [Architecture Overview](architecture.md): Understand how the API client fits into the overall architecture
- [Testing Guide](testing.md): Learn how to test the API client

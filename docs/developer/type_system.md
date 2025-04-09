# Type System

This document explains the type system used in the ActronAir Neo integration, including the TypedDict classes, type annotations, and best practices for type safety.

## Overview

The ActronAir Neo integration uses Python's type hints throughout the codebase to ensure type safety and improve code quality. The main types are defined in `types.py` and are used consistently across the integration.

## Core Type Definitions

### `ActronNeoDeviceInfo`

Represents information about an ActronAir Neo device.

```python
class ActronNeoDeviceInfo(TypedDict):
    """Type for ActronAir Neo device information."""
    serial: str
    name: str
    type: str
    id: str
```

### `ActronNeoZoneInfo`

Represents information about a zone in an ActronAir Neo system.

```python
class ActronNeoZoneInfo(TypedDict):
    """Type for ActronAir Neo zone information."""
    index: int
    name: str
    enabled: bool
    temperature: float
    humidity: Optional[float]
    setpoint: float
    type: str
    temperature_available: bool
    control_available: bool
    is_master: bool
```

### `ActronNeoMainInfo`

Represents the main information about an ActronAir Neo system.

```python
class ActronNeoMainInfo(TypedDict):
    """Type for ActronAir Neo main system information."""
    temperature: float
    humidity: float
    is_on: bool
    mode: str
    fan_mode: str
    cool_setpoint: float
    heat_setpoint: float
    filter_status: bool
    filter_days_remaining: int
    compressor_mode: str
    compressor_state: str
    fan_state: str
    defrost_mode: bool
    away_mode: bool
    quiet_mode: bool
```

### `ActronNeoRawData`

Represents the raw data received from the ActronAir Neo API.

```python
class ActronNeoRawData(TypedDict):
    """Type for raw ActronAir Neo API response data."""
    lastKnownState: Dict[str, Any]
```

### `ActronNeoData`

Represents the processed data used by the coordinator and entities.

```python
class ActronNeoData:
    """Class to hold data from ActronAir Neo API."""
    
    def __init__(
        self,
        main: ActronNeoMainInfo,
        zones: List[ActronNeoZoneInfo],
        raw_data: ActronNeoRawData
    ) -> None:
        """Initialize the data class."""
        self.main = main
        self.zones = zones
        self.raw_data = raw_data
```

## Using Type Annotations

### Function Annotations

All functions and methods should include type annotations for parameters and return values.

```python
def get_zone_temperature(zone_index: int) -> float:
    """Get the temperature for a specific zone.
    
    Args:
        zone_index: The index of the zone
        
    Returns:
        The temperature in degrees Celsius
    """
    # Implementation
    return 21.5
```

### Variable Annotations

Variables should be annotated, especially in class definitions.

```python
class ActronNeoClimate(ClimateEntity):
    """ActronAir Neo climate entity."""
    
    _attr_name: str
    _attr_unique_id: str
    _enable_turn_on_off_backwards_compatibility: bool = False
    _coordinator: ActronDataCoordinator
    _zone_index: Optional[int] = None
```

### Optional Types

Use `Optional[T]` for values that might be None.

```python
def get_zone_humidity(zone_index: int) -> Optional[float]:
    """Get the humidity for a specific zone if available.
    
    Args:
        zone_index: The index of the zone
        
    Returns:
        The humidity in percent, or None if not available
    """
    # Implementation
    return None
```

### Union Types

Use `Union[T1, T2, ...]` for values that might be one of several types.

```python
def get_value(key: str) -> Union[str, int, float, bool, None]:
    """Get a value from the system data.
    
    Args:
        key: The key to look up
        
    Returns:
        The value, which could be of various types
    """
    # Implementation
    return "value"
```

### Type Aliases

Use type aliases for complex types to improve readability.

```python
# Type aliases
CommandType = Dict[str, Any]
ZoneList = List[ActronNeoZoneInfo]
```

## Type Checking

The integration uses mypy for static type checking. To run type checking:

```bash
mypy custom_components/actronair_neo
```

### Common Type Issues and Solutions

#### Missing Return Type Annotation

```python
# Bad
def get_temperature():
    return 21.5

# Good
def get_temperature() -> float:
    return 21.5
```

#### Inconsistent Return Types

```python
# Bad
def get_value(key: str) -> str:
    if key == "temperature":
        return 21.5  # Error: Returning float, expected str
    return "value"

# Good
def get_value(key: str) -> Union[str, float]:
    if key == "temperature":
        return 21.5
    return "value"
```

#### Missing Parameter Type Annotation

```python
# Bad
def set_temperature(temperature):
    # Implementation
    pass

# Good
def set_temperature(temperature: float) -> None:
    # Implementation
    pass
```

#### Any Type

Avoid using `Any` when possible, but it's sometimes necessary for dynamic data.

```python
# Avoid when possible
def process_data(data: Any) -> None:
    # Implementation
    pass

# Better
def process_data(data: Dict[str, Any]) -> None:
    # Implementation
    pass
```

## Best Practices

### 1. Use TypedDict for API Responses

Use TypedDict to define the structure of API responses.

```python
class ApiResponse(TypedDict):
    status: str
    data: Dict[str, Any]
    error: Optional[str]
```

### 2. Use Enums for Constants

Use Enum classes for constants with a fixed set of values.

```python
from enum import Enum, auto

class HvacMode(str, Enum):
    """HVAC mode enum."""
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"
    FAN_ONLY = "fan_only"
```

### 3. Document Complex Types

Add docstrings to complex type definitions.

```python
class ActronNeoZoneInfo(TypedDict):
    """Type for ActronAir Neo zone information.
    
    Attributes:
        index: The zone index (0-7)
        name: The zone name
        enabled: Whether the zone is enabled
        temperature: The current temperature in degrees Celsius
        humidity: The current humidity in percent, if available
        setpoint: The target temperature in degrees Celsius
        type: The zone type
        temperature_available: Whether temperature sensing is available
        control_available: Whether the zone can be controlled
        is_master: Whether this is the master zone
    """
    index: int
    name: str
    enabled: bool
    temperature: float
    humidity: Optional[float]
    setpoint: float
    type: str
    temperature_available: bool
    control_available: bool
    is_master: bool
```

### 4. Use Type Guards

Use type guards to narrow types in conditional blocks.

```python
from typing import TypeGuard

def is_zone_info(obj: Any) -> TypeGuard[ActronNeoZoneInfo]:
    """Check if an object is a valid zone info object."""
    return (
        isinstance(obj, dict)
        and "index" in obj
        and "name" in obj
        and "enabled" in obj
    )

def process_zone(zone: Any) -> None:
    if is_zone_info(zone):
        # Now TypeScript knows zone is ActronNeoZoneInfo
        print(f"Zone {zone['name']} is {'enabled' if zone['enabled'] else 'disabled'}")
    else:
        print("Not a valid zone")
```

### 5. Use Protocol for Duck Typing

Use Protocol for structural typing (duck typing).

```python
from typing import Protocol

class HasTemperature(Protocol):
    """Protocol for objects that have a temperature."""
    temperature: float

def print_temperature(obj: HasTemperature) -> None:
    """Print the temperature of an object."""
    print(f"Temperature: {obj.temperature}°C")

# Can be used with any object that has a temperature attribute
print_temperature({"temperature": 21.5})
```

## Type Compatibility with Home Assistant

The integration uses Home Assistant's type definitions where appropriate.

```python
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)

class ActronNeoClimate(ClimateEntity):
    """ActronAir Neo climate entity."""
    
    _attr_hvac_modes: list[HVACMode] = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
```

## Conclusion

Using a consistent type system throughout the codebase helps catch errors early, improves code readability, and makes the integration more maintainable. By following these guidelines, you can ensure that your contributions to the ActronAir Neo integration maintain high type safety standards.

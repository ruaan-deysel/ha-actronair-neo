---
type: "agent_requested"
description: "Example description"
---

# Home Assistant Custom Integration Development Rules

## Overview
These rules apply to all Home Assistant custom integration development in Python. All code must meet Gold tier on the Home Assistant Integration Quality Scale and follow official Home Assistant development best practices.

## Python Best Practices

### Code Quality Standards
- Use Python 3.11+ features and syntax
- Follow PEP 8 style guide
- Use type hints for all function signatures and class attributes
- Write docstrings for all public modules, classes, and functions (Google style)
- Keep functions small and focused (single responsibility principle)
- Use descriptive variable and function names
- Avoid global variables and mutable default arguments

### Code Linting and Formatting
**CRITICAL**: Before considering any code complete, you MUST run all linters and fix ALL errors and warnings:

1. **Black** - Code formatting (must run first)
   ```bash
   black custom_components/your_integration/
   ```

2. **Ruff** - Fast linting (replaces flake8, isort, pyupgrade)
   ```bash
   ruff check custom_components/your_integration/ --fix
   ruff format custom_components/your_integration/
   ```

3. **Pylint** - Comprehensive static analysis
   ```bash
   pylint custom_components/your_integration/
   ```

4. **MyPy** - Type checking
   ```bash
   mypy custom_components/your_integration/
   ```

**If any linter reports errors or warnings, you MUST fix them immediately before proceeding.**

## Configuration Flow Requirements

### UI-Based Configuration Only
- **NEVER** use YAML-based configuration
- **ALWAYS** implement `config_flow.py` with ConfigFlow class
- Use `async_step_user` for initial setup
- Implement proper validation in config flow steps
- Support reconfiguration via `async_step_reconfigure`
- Provide clear, user-friendly error messages
- Use translation strings for all UI text

### Config Flow Best Practices
```python
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

class YourIntegrationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate input
            try:
                # Test connection
                await self._test_connection(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create entry
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({...}),
            errors=errors
        )
```

## Home Assistant Integration Quality Scale - Gold Tier

### Required Components for Gold Tier
1. **Proper domain and unique_id**
   - Use consistent domain naming
   - Implement unique_id for all entities
   - Support entity registry

2. **Config Flow with validation**
   - Already covered above

3. **Proper async patterns**
   - See section below

4. **Device and Entity Registry**
   - Create devices properly
   - Link entities to devices
   - Support device info

5. **Proper coordinator usage**
   - Use DataUpdateCoordinator for polling
   - Handle updates efficiently
   - Implement proper error handling

6. **Translations**
   - Provide `strings.json` with all UI strings
   - Support multiple languages where possible

7. **Documentation**
   - Clear README.md
   - Integration documentation
   - Configuration examples

8. **Testing**
   - Unit tests with pytest
   - Test config flow
   - Test entity platforms
   - Aim for >90% code coverage

## Async/Await Patterns

### Always Use Async
- **All I/O operations MUST be async**
- Use `asyncio` for concurrent operations
- Never use `time.sleep()` - use `await asyncio.sleep()` instead
- Never use blocking I/O - use `aiohttp`, `aiomqtt`, etc.

### Async Function Guidelines
```python
# CORRECT
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up from a config entry."""
    coordinator = MyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    return True

# INCORRECT - Never do this
def setup_entry(hass, entry):
    coordinator = MyCoordinator(hass, entry)
    coordinator.refresh()  # Blocking call
    return True
```

### Using DataUpdateCoordinator
```python
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

class MyCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api = MyAPI(entry.data[CONF_HOST])

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            async with asyncio.timeout(10):
                return await self.api.async_get_data()
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
```

## Entity Platforms

### Entity Implementation
- Inherit from appropriate base classes: `SensorEntity`, `BinarySensorEntity`, `SwitchEntity`, etc.
- Implement required properties: `name`, `unique_id`, `device_info`
- Use `CoordinatorEntity` when using DataUpdateCoordinator
- Follow naming conventions: entities should be descriptive

### Sensor Example
```python
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class MySensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_sensor"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name="My Device",
            manufacturer="Manufacturer",
            model="Model",
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        return self.coordinator.data.get(self._device_id, {}).get("value")
```

### Platform Setup
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: MyCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MySensor(coordinator, device_id)
        for device_id in coordinator.data
    ]

    async_add_entities(entities)
```

## Device and Entity Registry

### Device Info
```python
from homeassistant.helpers.entity import DeviceInfo

device_info = DeviceInfo(
    identifiers={(DOMAIN, unique_device_id)},
    name="Device Name",
    manufacturer="Manufacturer Name",
    model="Model Name",
    sw_version="1.0.0",
    hw_version="rev1",
    configuration_url="http://device.local",
)
```

### Entity Registry
- Always provide `unique_id` for entities
- Use consistent identifier format
- Enable entity registry support for customization

## Config Entry Setup/Unload

### Proper Entry Setup
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up integration from a config entry."""
    # Initialize coordinator
    coordinator = MyCoordinator(hass, entry)

    # First refresh to validate connection
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    # Register services if needed
    await async_setup_services(hass)

    # Set up entry update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True
```

### Proper Entry Unload
```python
async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    # Remove coordinator
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
```

### Entry Reload
```python
async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
```

## Error Handling and Logging

### Logging Best Practices
```python
import logging

_LOGGER = logging.getLogger(__name__)

# Use appropriate log levels:
_LOGGER.debug("Detailed information for debugging")
_LOGGER.info("General informational messages")
_LOGGER.warning("Warning messages for recoverable issues")
_LOGGER.error("Error messages for failures")
_LOGGER.exception("Error with full traceback")
```

### Exception Handling
```python
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers.update_coordinator import UpdateFailed

# During setup
try:
    await api.authenticate()
except AuthenticationError as err:
    raise ConfigEntryAuthFailed from err
except ConnectionError as err:
    raise ConfigEntryNotReady from err

# During updates
try:
    data = await api.fetch_data()
except ApiError as err:
    raise UpdateFailed(f"Failed to fetch data: {err}") from err
```

### Error Messages
- Use clear, user-friendly error messages
- Include relevant context in exceptions
- Always use exception chaining with `from err`
- Never expose sensitive information in logs

## Development Container Integration

### Starting/Stopping Home Assistant
**ALWAYS** use the devcontainer scripts for HA operations:

```bash
# Setup the development environment
scripts/setup

# Start Home Assistant in development mode
scripts/develop

# Home Assistant will run with your integration loaded
# The server runs at http://localhost:8123
```

### Monitoring Logs
**You MUST monitor Home Assistant logs** to catch errors and warnings:

The logs are accessible in the devcontainer at:
- Real-time logs: `tail -f config/home-assistant.log`
- Or use: `docker logs -f homeassistant` if running in Docker

**After any code change:**
1. Stop HA (Ctrl+C in develop script)
2. Run all linters and fix issues
3. Start HA with `scripts/develop`
4. Monitor logs for errors or warnings
5. Test the integration functionality
6. Check logs again for any runtime issues

### Log Monitoring Checklist
- ✅ No ERROR level messages from your integration
- ✅ No WARNING level messages from your integration
- ✅ Proper DEBUG/INFO messages for important operations
- ✅ Config flow completes without errors
- ✅ Entities register correctly
- ✅ Data updates work without exceptions

## Testing Requirements

### Test Structure
```python
"""Tests for the integration."""
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test setup of config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "test.local"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN in hass.data
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=custom_components.your_integration tests/

# Run specific test file
pytest tests/test_config_flow.py
```

## Workflow Summary

### For Every Code Change:
1. **Write/modify code** following all guidelines above
2. **Run Black** to format code
3. **Run Ruff** with --fix to lint and fix issues
4. **Run Pylint** and fix all warnings/errors
5. **Run MyPy** and fix all type errors
6. **Run tests** with pytest
7. **Stop HA** if running
8. **Start HA** with `scripts/develop`
9. **Monitor logs** for any errors or warnings from your integration
10. **Test functionality** in Home Assistant UI
11. **Check logs again** after testing
12. **Repeat steps 1-11** if any issues found

### Critical Failure Points
If ANY of the following occur, STOP and fix immediately:
- ❌ Linter errors or warnings
- ❌ Type checking errors
- ❌ Test failures
- ❌ ERROR or WARNING in HA logs from your integration
- ❌ Config flow doesn't work
- ❌ Entities don't appear or update

## File Structure

Standard integration structure:
```
custom_components/
└── your_integration/
    ├── __init__.py          # Integration setup
    ├── config_flow.py       # Config flow UI
    ├── const.py             # Constants
    ├── coordinator.py       # Data coordinator
    ├── sensor.py            # Sensor platform
    ├── binary_sensor.py     # Binary sensor platform
    ├── switch.py            # Switch platform
    ├── manifest.json        # Integration metadata
    ├── strings.json         # UI translations
    └── translations/
        └── en.json          # English translations
```

## Additional Resources

- Home Assistant Developer Docs: https://developers.home-assistant.io/
- Integration Quality Scale: https://developers.home-assistant.io/docs/integration_quality_scale_index
- Architecture Patterns: https://developers.home-assistant.io/docs/architecture_index
- Development Checklist: https://developers.home-assistant.io/docs/development_checklist

## Remember

- **Quality over speed** - Take time to do it right
- **Test thoroughly** - Use the devcontainer and monitor logs
- **Fix linter issues immediately** - Never commit code with warnings
- **Use async properly** - No blocking operations
- **Follow HA patterns** - Use coordinators, proper entity setup
- **Gold tier quality** - Your integration represents professional quality
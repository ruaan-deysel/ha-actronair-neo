# Claude AI Instructions for ActronAir Neo Integration

This file provides coding guidelines for Claude AI when working on the ActronAir Neo Home Assistant custom integration.

## Project Context

**ActronAir Neo Integration** - A Home Assistant custom component for controlling ActronAir Neo air conditioning systems.

- **Domain**: `actronair_neo`
- **Repository**: https://github.com/ruaan-deysel/ha-actronair-neo
- **License**: Apache License 2.0

## Critical Rules

### 🚫 Documentation Policy

**NEVER** generate unsolicited documentation:
- Do NOT create validation documents, summary documents, or reference documents unless explicitly requested
- Do NOT create README files or markdown documentation without being asked
- Do NOT create project summaries or status reports
- Only create documentation when the user specifically requests it
- Focus on code changes, not documentation generation

## Home Assistant Integration Standards

### Architecture Components

1. **Config Flow** (`config_flow.py`)
   - Async config flow for user setup
   - Input validation with voluptuous schemas
   - Options flow for runtime configuration

2. **Data Coordinator** (`coordinator.py`)
   - Use `DataUpdateCoordinator` for centralized data fetching
   - Proper async/await patterns
   - Graceful API error handling
   - Configurable refresh intervals
   - Retry logic with exponential backoff

3. **Entity Platforms**
   - Climate: Main HVAC control
   - Sensor: Temperature, humidity, status
   - Binary Sensor: On/off states
   - Switch: Toggle controls

4. **Entity Implementation**
   - Inherit from appropriate Home Assistant base classes
   - Use proper device classes (DEVICE_CLASS_TEMPERATURE, etc.)
   - Use proper state classes (STATE_CLASS_MEASUREMENT, etc.)
   - Implement CoordinatorEntity for automatic updates
   - Set unique IDs correctly

5. **Manifest** (`manifest.json`)
   - Domain: `actronair_neo`
   - Semantic versioning
   - List all external dependencies
   - iot_class: `cloud_polling`

6. **Translations** (`strings.json`)
   - All user-facing text must be translatable
   - Maintain proper translation structure

## Python Code Standards

### Code Quality

- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Type Hints**: Required for all function signatures
- **Async/Await**: Follow Home Assistant patterns
- **Error Handling**: Proper exception handling and logging
- **Logging**: Use `_LOGGER` for all log statements

### Code Organization

- Single-responsibility modules
- Type definitions in `types.py`
- Constants in `const.py`
- Base classes in `base_entity.py`
- Avoid circular dependencies

### Type Hints Example

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    return True

def calculate_value(data: dict[str, Any]) -> float:
    """Calculate a value from data."""
    return float(data.get("value", 0))
```

## ⚠️ MANDATORY: Code Quality Validation

**ALWAYS** follow these steps after making code changes:

1. Run `scripts/lint` to validate code
2. Fix all linting errors and warnings
3. Do NOT commit code that fails linting
4. Verify changes don't break existing functionality

### Linting Command

```bash
scripts/lint
```

This runs:
- `ruff format .` - Code formatting
- `ruff check . --fix` - Code quality checks with auto-fixes

## Development Workflow

### Setup Commands

```bash
scripts/setup      # Initial setup
scripts/develop    # Start Home Assistant in dev mode
scripts/lint       # Check code quality
```

### Testing and Validation

- **ALWAYS** check `config/home-assistant.log` after making changes
- Monitor the devcontainer Home Assistant instance for runtime errors
- Verify changes don't break existing functionality
- Test entity creation and updates

### Testing

```bash
python -m pytest tests/                                    # Run all tests
python -m pytest tests/test_config_flow.py                # Run specific test
python -m pytest --cov=custom_components/actronair_neo tests/  # With coverage
```

## API Integration

### ActronAir API (`api.py`)

Use custom exception classes:
- `ApiError`: General API errors
- `AuthenticationError`: Authentication failures
- `ConfigurationError`: Configuration issues
- `ZoneError`: Zone-related errors
- `DeviceOfflineError`: Device offline
- `RateLimitError`: Rate limiting

### Data Types (`types.py`)

- Use TypedDict for API response structures
- Define all data structures used by coordinator
- Keep type definitions organized and documented

## File Structure

```
custom_components/actronair_neo/
├── __init__.py              # Integration setup
├── api.py                   # API client
├── base_entity.py           # Base entity class
├── binary_sensor.py         # Binary sensor platform
├── climate.py               # Climate platform
├── config_flow.py           # Configuration flow
├── const.py                 # Constants
├── coordinator.py           # Data coordinator
├── diagnostics.py           # Diagnostics
├── manifest.json            # Manifest
├── repairs.py               # Repair flows
├── sensor.py                # Sensor platform
├── services.yaml            # Services
├── strings.json             # Translations
├── switch.py                # Switch platform
├── types.py                 # Type definitions
├── zone_presets.py          # Zone presets
└── translations/            # Translation files
```

## Common Tasks

### Adding a New Entity Type

1. Create platform file (e.g., `button.py`)
2. Implement entity class from appropriate base
3. Add to `PLATFORMS` list in `__init__.py`
4. Add translations to `strings.json`
5. Update coordinator for necessary data
6. Run `scripts/lint`
7. Test with `scripts/develop`

### Modifying the Coordinator

1. Update `coordinator.py` data fetching
2. Update `types.py` if needed
3. Update entity platforms
4. Run `scripts/lint`
5. Check `config/home-assistant.log`
6. Test with `scripts/develop`

### Fixing Bugs

1. Identify issue in logs or code
2. Write test case reproducing bug
3. Fix in appropriate module
4. Run `scripts/lint`
5. Run tests
6. Check logs for side effects

## References

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Integration Development](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Entity Documentation](https://developers.home-assistant.io/docs/entity/)
- [Data Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Ruff Documentation](https://docs.astral.sh/ruff/)


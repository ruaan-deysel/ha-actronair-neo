---
type: "always_apply"
---

# ActronAir Neo Integration - Project Rules for AI Coding Agents

This document defines the coding standards, best practices, and workflows for the ActronAir Neo Home Assistant custom integration project.

## Project Overview

**ActronAir Neo Integration** is a Home Assistant custom component that enables seamless control and monitoring of ActronAir Neo air conditioning systems. The integration provides climate control, real-time monitoring, zone management, and automation capabilities.

- **Domain**: `actronair_neo`
- **Repository**: https://github.com/ruaan-deysel/ha-actronair-neo
- **Documentation**: https://ruaan-deysel.github.io/ha-actronair-neo/
- **License**: Apache License 2.0

## Documentation Policy

### CRITICAL: Never Generate Unsolicited Documentation

- **NEVER** generate validation documents, summary documents, or reference documents unless explicitly requested by the user
- **NEVER** create unsolicited README files or markdown documentation
- **NEVER** create project summaries or status reports without being asked
- Only create documentation when the user specifically and explicitly requests it
- Focus on code changes, not documentation generation

## Home Assistant Integration Best Practices

### Architecture Requirements

1. **Config Flow** (`config_flow.py`)
   - Implement proper async config flow for user setup
   - Validate user input before creating config entries
   - Support options flow for runtime configuration changes
   - Use voluptuous schemas for input validation

2. **Data Coordinator** (`coordinator.py`)
   - Use `DataUpdateCoordinator` for centralized data fetching
   - Implement proper async/await patterns
   - Handle API errors gracefully with appropriate exceptions
   - Support configurable refresh intervals
   - Implement retry logic with exponential backoff

3. **Entity Platforms**
   - **Climate** (`climate.py`): Main HVAC control entity
   - **Sensor** (`sensor.py`): Temperature, humidity, and status sensors
   - **Binary Sensor** (`binary_sensor.py`): On/off state sensors
   - **Switch** (`switch.py`): Toggle controls for system features

4. **Entity Implementation**
   - Inherit from appropriate Home Assistant entity base classes
   - Use proper device classes (e.g., `DEVICE_CLASS_TEMPERATURE`)
   - Use proper state classes (e.g., `STATE_CLASS_MEASUREMENT`)
   - Implement `CoordinatorEntity` for automatic updates
   - Set unique IDs correctly for entity registry

5. **Manifest Configuration** (`manifest.json`)
   - Maintain correct domain name: `actronair_neo`
   - Keep version updated following semantic versioning
   - List all external dependencies in `requirements`
   - Set correct `iot_class` (currently: `cloud_polling`)
   - Include proper codeowners and documentation URLs

6. **Translations** (`strings.json` and `translations/`)
   - Use translation strings for all user-facing text
   - Maintain proper translation structure
   - Support multiple languages through translation files

## Python Development Best Practices

### Code Style and Quality

- **Formatter**: Use `ruff format` for code formatting
- **Linter**: Use `ruff check` for code quality checks
- **Type Hints**: Use type hints for all function signatures
- **Async/Await**: Follow Home Assistant async patterns correctly
- **Error Handling**: Implement proper exception handling and logging
- **Logging**: Use `_LOGGER` for all logging statements

### Code Organization

- Keep modules focused and single-responsibility
- Use type definitions in `types.py` for complex data structures
- Use constants in `const.py` for all magic values
- Implement base classes in `base_entity.py` for shared functionality
- Use proper imports and avoid circular dependencies

### Type Hints and Async Patterns

```python
# Correct async pattern
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration."""
    # Implementation
    return True

# Use type hints for all functions
def calculate_value(data: dict[str, Any]) -> float:
    """Calculate a value from data."""
    return float(data.get("value", 0))
```

## Code Quality and Validation

### MANDATORY: Run Linting After Every Change

- **ALWAYS** run `scripts/lint` after making code changes
- **ALWAYS** validate code meets quality standards before considering work complete
- **ALWAYS** fix all linting errors and warnings before finishing
- Do not commit or push code that fails linting checks

### Linting Command

```bash
scripts/lint
```

This command runs:

1. `ruff format .` - Code formatting
2. `ruff check . --fix` - Code quality checks with auto-fixes

## Development Workflow

### Development Environment Setup

When working in the devcontainer environment:

1. **Initial Setup**
   ```bash
   scripts/setup
   ```
   - Installs dependencies
   - Prepares development environment

2. **Start Development Mode**
   ```bash
   scripts/develop
   ```
   - Starts Home Assistant in development mode
   - Enables hot-reload for testing changes
   - Mounts the integration for live testing

3. **Code Quality Check**
   ```bash
   scripts/lint
   ```
   - Runs formatting and linting
   - Auto-fixes common issues
   - Reports remaining issues

### Testing and Validation

- **ALWAYS** check Home Assistant logs for errors, warnings, or issues after making changes
- Monitor the Home Assistant instance running in the devcontainer for any runtime errors
- Check logs at `config/home-assistant.log` for integration errors
- Verify changes don't break existing functionality
- Test entity creation and updates work correctly

### Log Monitoring

- Home Assistant logs are located at: `config/home-assistant.log`
- Check logs after:
  - Making code changes
  - Restarting the integration
  - Testing new features
  - Fixing bugs

## Testing Requirements

### Test Coverage

- Verify changes don't break existing functionality
- Check logs at `config/home-assistant.log` (or via the devcontainer) for integration errors
- Test entity creation and updates work correctly
- Run existing tests to ensure no regressions

### Test Execution

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_config_flow.py

# Run with coverage
python -m pytest --cov=custom_components/actronair_neo tests/
```

### Test Organization

- Tests are located in the `tests/` directory
- Use `conftest.py` for shared test fixtures
- Follow pytest conventions for test discovery
- Mock external API calls appropriately

## API Integration

### ActronAir API (`api.py`)

- Implement proper error handling for API calls
- Use custom exception classes:
  - `ApiError`: General API errors
  - `AuthenticationError`: Authentication failures
  - `ConfigurationError`: Configuration issues
  - `ZoneError`: Zone-related errors
  - `DeviceOfflineError`: Device offline
  - `RateLimitError`: Rate limiting

### Data Types (`types.py`)

- Use TypedDict for API response structures
- Define all data structures used by the coordinator
- Keep type definitions organized and documented

## File Structure

```
custom_components/actronair_neo/
├── __init__.py              # Integration setup and platform loading
├── api.py                   # ActronAir API client
├── base_entity.py           # Base entity class
├── binary_sensor.py         # Binary sensor platform
├── climate.py               # Climate platform (main HVAC control)
├── config_flow.py           # Configuration flow
├── const.py                 # Constants and configuration
├── coordinator.py           # Data coordinator
├── diagnostics.py           # Diagnostics support
├── manifest.json            # Integration manifest
├── repairs.py               # Repair flows
├── sensor.py                # Sensor platform
├── services.yaml            # Service definitions
├── strings.json             # Translation strings
├── switch.py                # Switch platform
├── types.py                 # Type definitions
├── zone_presets.py          # Zone preset management
└── translations/            # Translation files
```

## Common Tasks

### Adding a New Entity Type

1. Create a new platform file (e.g., `button.py`)
2. Implement entity class inheriting from appropriate base
3. Add platform to `PLATFORMS` list in `__init__.py`
4. Add translations to `strings.json`
5. Update coordinator to provide necessary data
6. Run `scripts/lint` to validate
7. Test in devcontainer with `scripts/develop`

### Modifying the Coordinator

1. Update data fetching logic in `coordinator.py`
2. Update type definitions in `types.py` if needed
3. Update entity platforms to use new data
4. Run `scripts/lint`
5. Check `config/home-assistant.log` for errors
6. Test with `scripts/develop`

### Fixing Bugs

1. Identify the issue in logs or code
2. Write a test case that reproduces the bug
3. Fix the bug in the appropriate module
4. Run `scripts/lint` to validate
5. Run tests to ensure fix works
6. Check logs for any side effects

## References

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Home Assistant Integration Development](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [Home Assistant Entity Documentation](https://developers.home-assistant.io/docs/entity/)
- [Home Assistant Data Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

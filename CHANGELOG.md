# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the ActronAir Neo Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2026.3.2] - 2026-03-14

### Fixed

- **Zone Damper Position availability (issue #77)**: Restored the read-only damper position sensor for non-YourZone systems so existing zone damper entities no longer become unavailable after upgrading
- **Concurrent zone switch updates (issue #76)**: Serialized `EnabledZones` writes in the coordinator and preserved optimistic zone state changes across refreshes so rapid on/off operations no longer overwrite each other with stale zone arrays

## [2026.3.1] - 2026-03-08

### Fixed

- **fix(climate): serialize ZoneCapabilities before exposing as state attribute**: The `ZoneCapabilities` attribute was previously exposed as a raw dictionary, which caused issues with Home Assistant's state machine. Now it is serialized to a JSON string before being set as a state attribute, ensuring proper handling and display in the UI.

## [2026.3.0] - 2026-03-01

### Added

- **Que-to-Neo Hybrid Support (issue #59)**: Systems with Que outdoor units upgraded to Neo controllers are now supported
  - Automatic platform detection: NX-Gen (Que) devices route API calls to `que.actronair.com.au`
  - Per-device base URL stored in config entry for reliable routing across restarts
  - Improved 503 error handling to parse structured `{"type": "unavailable"}` responses from the API
- **Cover Entity for Zone Dampers**: Replaced zone airflow number + damper sensor with a `CoverDeviceClass.DAMPER` cover entity per zone
  - Supports open/close and set position (0–100%)
  - Reports current damper position from the API
- **Zone Humidity Sensors**: Per-zone humidity readings (gated on sensor availability)
- **Zone Battery Sensors**: Battery level for wireless zone sensors (gated on `battery_level` presence)
- **Outdoor Temperature Sensor**: Dedicated sensor for outdoor ambient temperature
- **Service Reminder Sensor**: Reports days until the next service is due
- **Active Warnings Binary Sensor**: Indicates when the system has active warnings
- **Fast Heating Binary Sensor**: Indicates when the system is in fast-heating mode
- **Turbo Mode Switch**: Enable/disable turbo mode on supported systems
- **After Hours Switch & Number**: Toggle after-hours mode and set the duration (minutes)
- **Quiet Mode Gating**: Quiet mode switch now only appears when the system reports quiet mode capability
- **OAuth2 Device Code Flow**: Authentication uses RFC 8628 device code flow — no more username/password entry
- **Custom Exception Hierarchy**: `exceptions.py` with `ApiError`, `AuthenticationError`, `DeviceOfflineError`, `RateLimitError`, `ZoneError`, `ConfigurationError` — all inheriting from `HomeAssistantError`
- **Structured API Client Package**: `api/` package with separate `client.py`, `auth.py`, `models.py`, `const.py` modules
- **Pydantic Models**: API data structures use Pydantic `BaseModel` with validation
- **Response Caching & Request Deduplication**: API client deduplicates concurrent status requests and caches responses
- **Rate Limiting**: Built-in rate limiter prevents API throttling
- **Icons**: `icons.json` for entity-specific MDI icons
- **Strict Typing**: `py.typed` marker, full type annotations throughout the codebase

### Changed

- **Polling interval** standardised to 30 seconds (matches official `actron_air` integration); removed configurable refresh interval option
- **Base Entity** refactored: `base_entity.py` replaced by `entity.py` (`ActronAirNeoEntity`) with `serial_number` in `DeviceInfo`
- **Config Entry** migrated to version 2 (OAuth2 tokens, no more stored credentials)
- **Coordinator** (`ActronDataCoordinator`) extensively reworked: maps API exceptions to `ConfigEntryAuthFailed` / `UpdateFailed`, uses `async_config_entry_first_refresh()`
- **Diagnostics**: Fixed `SystemStatus_Local` path to correctly read from the serial-keyed device section instead of the top-level response
- **Sensor data paths**: All sensors using `SystemStatus_Local`, `LiveOutdoorTemp_oC`, and related fields now read from the correct API response level
- **Project build system**: Migrated to uv-native `pyproject.toml` with PEP 735 dependency groups and hatchling build backend
- **Logging**: Reduced from ~195 log calls to ~15 — noisy debug/info logging removed, kept only actionable warnings and errors

### Fixed

- **Ambient Temperature Unknown (issue #57)**: Fixed three bugs causing outdoor temperature to show "Unknown"
  - `SystemStatus_Local` was read from wrong level of the API response (top-level instead of serial-keyed device section)
  - Added `OutdoorUnit.AmbTemp` as fallback when `LiveOutdoorTemp_oC` returns sentinel value (3000.0)
  - Outdoor temperature fallback gated on `AmbientSensErr` being `false` (Classic models report `AmbTemp: 0` with sensor error)
- **Performance Metrics Sensor**: Fixed inconsistent and delayed updates
  - Added explicit `should_poll = False` to prevent duplicate polling
  - Added `available` property to validate data availability before updates
  - Improved error handling with debug/warning logging instead of silent failures
- **Energy tracking sensors** (Compressor Power and Compressor Energy) not being created for Advanced/Inverter series units

### Removed

- **Legacy `api.py`**: Monolithic API client replaced by the `api/` package
- **Legacy `base_entity.py`**: Replaced by `entity.py`
- **`CONF_USERNAME` / `CONF_PASSWORD`**: No longer used (device code flow)
- **`CONF_REFRESH_INTERVAL`**: Polling interval is no longer user-configurable
- **`ConfigurationMigrationRepairFlow`**: Dead repair flow code removed
- **Zone Airflow Number Entity**: Replaced by the cover entity
- **Zone Damper Position Sensor**: Replaced by the cover entity
- **`requirements.txt` / `requirements_test.txt`**: Dependencies managed via `pyproject.toml`

## [2025.11.0] - 2025-11-09

### Added

- **YourZone Airflow Control Feature**: Full support for ActronAir's YourZone granular airflow control
  - Number entities for adjusting zone airflow percentage (0-100% in 5% increments) for zones with YourZone enabled
  - Sensor entities displaying current damper position percentage for all zones
  - Binary sensor entities showing YourZone enabled status for each zone
  - Automatic entity creation only for zones with `AirflowControlEnabled: true`
  - Entities become unavailable when airflow control is locked (`AirflowControlLocked: true`)
  - Full integration with ActronAir Neo Cloud API using existing `RemoteZoneInfo` data
- Strict typing throughout the codebase
- Improved type definitions with TypedDict classes
- Automated GitHub Actions workflow for creating releases from version tags
- Comprehensive release process documentation in CONTRIBUTING.md

### Changed

- **YourZone Entity Categorization**: Improved entity organization for better Home Assistant UI experience
  - Number entities for airflow control now use `EntityCategory.CONFIG` (appear in configuration section)
  - YourZone enabled binary sensors now use `EntityCategory.DIAGNOSTIC` (appear in diagnostics section)
  - All YourZone entities have proper unique IDs for UI management
- Refactored API client for better type safety
- Updated coordinator to use specific type definitions
- Restructured CHANGELOG.md to follow Keep a Changelog format exactly

### Fixed

- Various type annotation issues
- Fixed energy tracking sensors (Compressor Power and Compressor Energy) not being created for Advanced/Inverter series units due to incorrect API data access pattern (issue #43)
  - Removed incorrect serial number wrapper when accessing `lastKnownState` data
  - Enhanced power monitoring detection to properly identify Advanced/Inverter series units
  - Added improved debug logging for power monitoring capability detection
- Code quality improvements:
  - Fixed 14 linting errors in sensor.py (TRY401 verbose-log-message, E501 line-too-long)
  - Removed redundant exception objects from logging.exception() calls
  - Fixed undefined variable references that could cause runtime errors
  - Removed unused import (homeassistant.helpers.service) from `__init__.py`
- Security audit completed with bandit - no critical vulnerabilities found (1 low-severity intentional exception handling pattern)

### Removed

## [2025.10.3] - 2025-10-15

### Added

- Initial public release of ActronAir Neo integration
- Support for climate control (heating, cooling, fan-only modes)
- Zone control functionality with individual zone temperature management
- Fan mode control (low, medium, high, auto)
- Temperature control with precise setpoint adjustment
- Real-time temperature and humidity monitoring
- System status monitoring (on/off, mode, errors)
- Filter status monitoring
- Away mode support
- Quiet mode support
- Continuous fan mode support
- Compressor power and energy monitoring for Advanced/Inverter series units
- Integration with Home Assistant Energy Dashboard
- Comprehensive diagnostics support
- Automatic entity migration for seamless updates
- OAuth2 authentication with automatic token refresh
- Rate limiting to prevent API throttling
- Extensive error handling and logging

# Changelog

All notable changes to the ActronAir Neo Home Assistant integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

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

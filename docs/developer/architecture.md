# Architecture Overview

This document provides a comprehensive overview of the ActronAir Neo integration architecture, explaining how the different components work together.

## High-Level Architecture

The ActronAir Neo integration follows a layered architecture pattern:

```ascii
┌─────────────────────────────────────────────────────────┐
│                  Home Assistant Core                    │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                 ActronAir Neo Integration                │
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Config    │    │             │    │  Entities   │  │
│  │    Flow     │◄──►│ Coordinator │◄──►│ (Climate,   │  │
│  │             │    │             │    │  Sensors)   │  │
│  └─────────────┘    └──────┬──────┘    └─────────────┘  │
│                            │                            │
│  ┌─────────────────────────▼─────────────────────────┐  │
│  │                    API Client                     │  │
│  └─────────────────────────┬─────────────────────────┘  │
│                            │                            │
└───────────────────────────┬─────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────┐
│                  ActronAir Neo Cloud API                 │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Client (`api.py`)

The API client is responsible for all communication with the ActronAir Neo cloud API. It handles:

- Authentication and token management
- API requests and responses
- Rate limiting
- Error handling
- Data parsing and validation

The API client is designed to be a standalone component that could potentially be used outside of the Home Assistant integration.

Key classes:

- `ActronNeoAPI`: Main API client class
- `ActronNeoAuthenticationError`: Custom exception for authentication issues
- `ActronNeoAPIError`: Custom exception for API errors

### 2. Data Coordinator (`coordinator.py`)

The coordinator is the central component that manages data flow between the API and the entities. It:

- Periodically fetches data from the API
- Processes and structures the data
- Provides a consistent interface for entities to access data
- Handles command execution
- Manages error recovery

The coordinator uses Home Assistant's `DataUpdateCoordinator` class to efficiently manage data updates and minimize API calls.

Key classes:

- `ActronDataCoordinator`: Main coordinator class
- `ActronNeoData`: Data structure class

### 3. Config Flow (`config_flow.py`)

The config flow handles the integration setup and configuration process. It:

- Manages the UI for adding and configuring the integration
- Validates user input
- Handles authentication with the API
- Discovers available devices
- Stores configuration data

Key classes:

- `ActronNeoConfigFlow`: Main config flow class
- `ActronNeoOptionsFlow`: Options flow for reconfiguration

### 4. Entities

The entities represent the different devices and sensors in Home Assistant:

- **Climate Entity** (`climate.py`): Controls the air conditioning system
- **Sensor Entities** (`sensor.py`): Provides temperature, humidity, and other readings
- **Binary Sensor Entities** (`binary_sensor.py`): Provides status information
- **Switch Entities** (`switch.py`): Controls zones and other toggleable features

All entities inherit from a base entity class that provides common functionality.

Key classes:

- `ActronNeoClimate`: Main climate control entity
- `ActronNeoBaseSensor`: Base class for all sensor entities
- `ActronNeoZoneSwitch`: Zone control switch entity

## Data Flow

### Initialization Flow

1. User adds the integration through the Home Assistant UI
2. Config flow collects credentials and configuration options
3. Config flow validates credentials with the API
4. Config flow discovers available devices
5. Home Assistant creates the coordinator instance
6. Coordinator performs initial data fetch
7. Home Assistant creates entity instances
8. Entities register with Home Assistant

### Update Flow

1. Coordinator's update interval triggers
2. Coordinator requests data from the API
3. API client fetches data from the ActronAir Neo cloud
4. API client processes and returns the data
5. Coordinator updates its internal data store
6. Coordinator notifies entities of the update
7. Entities refresh their state based on the new data

### Command Flow

1. User interacts with an entity in Home Assistant
2. Entity calls the appropriate method on the coordinator
3. Coordinator validates the command
4. Coordinator calls the API client with the command
5. API client sends the command to the ActronAir Neo cloud
6. API client receives and processes the response
7. Coordinator updates its internal data store
8. Entities refresh their state based on the new data

## Type System

The integration uses Python's type hints throughout the codebase to ensure type safety and improve code quality. Key type definitions are in `types.py`:

- `ActronNeoDeviceInfo`: Type for device information
- `ActronNeoZoneInfo`: Type for zone information
- `ActronNeoMainInfo`: Type for main system information
- `ActronNeoRawData`: Type for raw API response data

## Error Handling

The integration implements a robust error handling strategy:

1. **API-level errors** are caught and converted to specific exceptions
2. **Coordinator-level errors** are logged and handled with exponential backoff
3. **Entity-level errors** are caught to prevent cascading failures

## Configuration Storage

The integration stores configuration in Home Assistant's configuration registry:

- **Authentication credentials** are stored securely
- **Device information** is stored for quick startup
- **User preferences** are stored for persistence across restarts

## Development Tools

The integration includes several utility tools to help with development and troubleshooting:

- **API Explorer**: A command-line tool for interacting with the ActronAir Neo API
- **API Documentation**: Detailed documentation of the API structure and endpoints
- **Diagnostics Generator**: Tool to generate system diagnostics reports

These tools are located in the `utils/` directory of the repository. See the [Utility Tools](utility_tools.md) page for more information.

## Next Steps

- [API Reference](api_reference.md): Detailed documentation of the API client
- [Contributing Guide](contributing.md): How to contribute to the integration
- [Testing Guide](testing.md): How to test the integration
- [Utility Tools](utility_tools.md): Tools for API exploration and diagnostics

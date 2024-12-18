"""Constants for the ActronAir Neo integration."""
from typing import Final

# Integration information
DOMAIN: Final = "actronair_neo"
VERSION: Final = "2024.12.17"

# Configuration constants
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_REFRESH_INTERVAL: Final = "refresh_interval"
CONF_SERIAL_NUMBER: Final = "serial_number"
CONF_ENABLE_ZONE_CONTROL: Final = "enable_zone_control"

# Default values
DEFAULT_REFRESH_INTERVAL: Final = 60  # seconds

# API related constants
API_URL: Final = "https://nimbus.actronair.com.au"
API_TIMEOUT: Final = 30  # seconds
MAX_RETRIES: Final = 3
MAX_REQUESTS_PER_MINUTE: Final = 20
MIN_FAN_MODE_INTERVAL: Final = 5  # seconds between fan mode changes

# HVAC modes
HVAC_MODE_OFF: Final = "OFF"
HVAC_MODE_COOL: Final = "COOL"
HVAC_MODE_HEAT: Final = "HEAT"
HVAC_MODE_FAN: Final = "FAN"
HVAC_MODE_AUTO: Final = "AUTO"

# Fan modes
FAN_LOW: Final = "LOW"
FAN_MEDIUM: Final = "MED"
FAN_HIGH: Final = "HIGH"
FAN_AUTO: Final = "AUTO"

# Fan modes with continuous option
FAN_MODE_SUFFIX_CONT: Final = "+CONT"
FAN_LOW_CONT: Final = f"{FAN_LOW}{FAN_MODE_SUFFIX_CONT}"
FAN_MEDIUM_CONT: Final = f"{FAN_MEDIUM}{FAN_MODE_SUFFIX_CONT}"
FAN_HIGH_CONT: Final = f"{FAN_HIGH}{FAN_MODE_SUFFIX_CONT}"
FAN_AUTO_CONT: Final = f"{FAN_AUTO}{FAN_MODE_SUFFIX_CONT}"

# Valid fan modes set
VALID_FAN_MODES = {"LOW", "MED", "HIGH", "AUTO"}

# Temperature limits
MIN_TEMP: Final = 10
MAX_TEMP: Final = 30

# Device attributes
ATTR_INDOOR_TEMPERATURE: Final = "indoor_temperature"
ATTR_INDOOR_HUMIDITY: Final = "indoor_humidity"
ATTR_SETPOINT_COOL: Final = "setpoint_cool"
ATTR_SETPOINT_HEAT: Final = "setpoint_heat"
ATTR_COMPRESSOR_STATE: Final = "compressor_state"
ATTR_AWAY_MODE: Final = "away_mode"
ATTR_QUIET_MODE: Final = "quiet_mode"
ATTR_MODEL: Final = "model"
ATTR_SERIAL_NUMBER: Final = "serial_number"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
ATTR_CONTINUOUS_FAN: Final = "continuous_fan"
ATTR_ENABLED_ZONES: Final = "enabled_zones"

# Error messages
ERROR_AUTH: Final = "invalid_auth"
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_UNKNOWN: Final = "unknown"

# Device identifiers
DEVICE_MANUFACTURER: Final = "ActronAir"
DEVICE_MODEL: Final = "Neo"

# Service names
SERVICE_FORCE_UPDATE: Final = "force_update"

# Update intervals
UPDATE_INTERVAL: Final = 60  # seconds

# Zone related constants
MAX_ZONES: Final = 8
ATTR_ZONE_TEMP: Final = "zone_temperature"
ATTR_ZONE_HUMIDITY: Final = "zone_humidity"
ATTR_ZONE_NAME: Final = "zone_name"
ATTR_ZONE_ENABLED: Final = "zone_enabled"

# System modes
MODE_COOL: Final = "COOL"
MODE_HEAT: Final = "HEAT"
MODE_AUTO: Final = "AUTO"
MODE_FAN: Final = "FAN"

# System states
STATE_ON: Final = "ON"
STATE_OFF: Final = "OFF"

# Config flow steps
STEP_USER: Final = "user"
STEP_VALIDATE: Final = "validate"

# Platforms
PLATFORM_CLIMATE: Final = "climate"
PLATFORM_SENSOR: Final = "sensor"
PLATFORM_SWITCH: Final = "switch"
PLATFORM_BINARY_SENSOR: Final = "binary_sensor"

PLATFORMS: Final = [
    PLATFORM_CLIMATE,
    PLATFORM_SENSOR,
    PLATFORM_SWITCH,
    PLATFORM_BINARY_SENSOR,
]

# Entity categories
ENTITY_CATEGORY_CONFIG: Final = "config"
ENTITY_CATEGORY_DIAGNOSTIC: Final = "diagnostic"

# Icons
ICON_HVAC: Final = "mdi:hvac"
ICON_THERMOMETER: Final = "mdi:thermometer"
ICON_HUMIDITY: Final = "mdi:water-percent"
ICON_FAN: Final = "mdi:fan"
ICON_ZONE: Final = "mdi:view-dashboard-variant"

# Diagnostic Attributes
ATTR_BATTERY_LEVEL: Final = "battery_level"
ATTR_FILTER_STATUS: Final = "filter_status"
ATTR_DEFROST_STATUS: Final = "defrost_status"
ATTR_ZONE_STATUS: Final = "zone_status"
ATTR_COMPRESSOR_STATUS: Final = "compressor_status"
ATTR_ZONE_TYPE: Final = "zone_type"
ATTR_SIGNAL_STRENGTH: Final = "signal_strength"
ATTR_LAST_UPDATED: Final = "last_updated"

# Sensor related constants
SENSOR_TEMPERATURE: Final = "temperature"
SENSOR_HUMIDITY: Final = "humidity"
SENSOR_BATTERY: Final = "battery"
SENSOR_SIGNAL: Final = "signal_strength"

# Device state attributes
ATTR_PERIPHERAL_TYPE: Final = "peripheral_type"
ATTR_CONNECTION_STATE: Final = "connection_state"
ATTR_LAST_CONNECTION: Final = "last_connection"
ATTR_INDOOR_TEMP: Final = "indoor_temperature"
ATTR_PERIPHERAL_INFO: Final = "peripheral_info"

# Diagnostic categories
DIAG_SYSTEM: Final = "system_status"
DIAG_ENVIRONMENTAL: Final = "environmental"
DIAG_ZONES: Final = "zones"
DIAG_INFO: Final = "info"

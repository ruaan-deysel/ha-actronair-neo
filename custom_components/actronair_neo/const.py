"""Constants for the ActronAir Neo integration."""

DOMAIN = "actronair_neo"

# Configuration constants
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_SERIAL_NUMBER = "serial_number"

# Default values
DEFAULT_REFRESH_INTERVAL = 60  # seconds

# API related constants
API_URL = "https://nimbus.actronair.com.au"
API_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
MAX_REQUESTS_PER_MINUTE = 20

# HVAC modes
HVAC_MODE_OFF = "OFF"
HVAC_MODE_COOL = "COOL"
HVAC_MODE_HEAT = "HEAT"
HVAC_MODE_FAN = "FAN"
HVAC_MODE_AUTO = "AUTO"

# Fan modes
FAN_LOW = "LOW"
FAN_MEDIUM = "MED"
FAN_HIGH = "HIGH"

# Temperature limits
MIN_TEMP = 10
MAX_TEMP = 30

# Device attributes
ATTR_INDOOR_TEMPERATURE = "indoor_temperature"
ATTR_INDOOR_HUMIDITY = "indoor_humidity"
ATTR_SETPOINT_COOL = "setpoint_cool"
ATTR_SETPOINT_HEAT = "setpoint_heat"
ATTR_COMPRESSOR_STATE = "compressor_state"
ATTR_AWAY_MODE = "away_mode"
ATTR_QUIET_MODE = "quiet_mode"
ATTR_MODEL = "model"
ATTR_SERIAL_NUMBER = "serial_number"
ATTR_FIRMWARE_VERSION = "firmware_version"

# Error messages
ERROR_AUTH = "invalid_auth"
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_UNKNOWN = "unknown"

# Device identifiers
DEVICE_MANUFACTURER = "ActronAir"
DEVICE_MODEL = "Neo"

# Service names
SERVICE_FORCE_UPDATE = "force_update"

# Coordinator update interval
UPDATE_INTERVAL = 60  # seconds

# Zone related constants
MAX_ZONES = 8
ATTR_ZONE_TEMP = "zone_temperature"
ATTR_ZONE_HUMIDITY = "zone_humidity"
ATTR_ZONE_NAME = "zone_name"
ATTR_ZONE_ENABLED = "zone_enabled"

# System modes
MODE_COOL = "COOL"
MODE_HEAT = "HEAT"
MODE_AUTO = "AUTO"
MODE_FAN = "FAN"

# System states
STATE_ON = "ON"
STATE_OFF = "OFF"

# Fan modes with continuous option
FAN_LOW_CONT = "LOW-CONT"
FAN_MEDIUM_CONT = "MED-CONT"
FAN_HIGH_CONT = "HIGH-CONT"
FAN_AUTO_CONT = "AUTO-CONT"

# Additional attributes
ATTR_ENABLED_ZONES = "enabled_zones"

# Config flow steps
STEP_USER = "user"
STEP_VALIDATE = "validate"

# Platforms
PLATFORM_CLIMATE = "climate"
PLATFORM_SENSOR = "sensor"
PLATFORM_SWITCH = "switch"

# List of all supported platforms
PLATFORMS = [PLATFORM_CLIMATE, PLATFORM_SENSOR, PLATFORM_SWITCH]

# Entity categories
ENTITY_CATEGORY_CONFIG = "config"
ENTITY_CATEGORY_DIAGNOSTIC = "diagnostic"

# Icons
ICON_HVAC = "mdi:hvac"
ICON_THERMOMETER = "mdi:thermometer"
ICON_HUMIDITY = "mdi:water-percent"
ICON_FAN = "mdi:fan"
ICON_ZONE = "mdi:view-dashboard-variant"
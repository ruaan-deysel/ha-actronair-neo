from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    Platform
)

DOMAIN = "actron_air_neo"
API_URL = "https://nimbus.actronair.com.au"

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

DEFAULT_UPDATE_INTERVAL = 60

# HVAC modes
HVAC_MODE_OFF = "OFF"
HVAC_MODE_AUTO = "AUTO"
HVAC_MODE_COOL = "COOL"
HVAC_MODE_HEAT = "HEAT"
HVAC_MODE_FAN_ONLY = "FAN"

# Fan modes
FAN_AUTO = "AUTO"
FAN_LOW = "LOW"
FAN_MEDIUM = "MED"
FAN_HIGH = "HIGH"
FAN_AUTO_CONT = "AUTO-CONT"
FAN_LOW_CONT = "LOW-CONT"
FAN_MEDIUM_CONT = "MED-CONT"
FAN_HIGH_CONT = "HIGH-CONT"

# Attributes
ATTR_INDOOR_TEMPERATURE = "indoor_temperature"
ATTR_OUTDOOR_TEMPERATURE = "outdoor_temperature"
ATTR_INDOOR_HUMIDITY = "indoor_humidity"
ATTR_ZONE_TEMPERATURE = "zone_temperature"
ATTR_ZONE_HUMIDITY = "zone_humidity"
ATTR_BATTERY_LEVEL = "battery_level"
ATTR_SIGNAL_STRENGTH = "signal_strength"
ATTR_IS_ENABLED = "is_enabled"
ATTR_SETPOINT_COOL = "setpoint_cool"
ATTR_SETPOINT_HEAT = "setpoint_heat"

# Units
TEMP_UNIT = UnitOfTemperature.CELSIUS
PERCENTAGE_UNIT = PERCENTAGE
SIGNAL_STRENGTH_UNIT = SIGNAL_STRENGTH_DECIBELS_MILLIWATT

# Command types
CMD_SET_SETTINGS = "set-settings"

# API keys
API_KEY_USER_AIRCON_SETTINGS = "UserAirconSettings"
API_KEY_REMOTE_ZONE_INFO = "RemoteZoneInfo"
API_KEY_IS_ON = "isOn"
API_KEY_MODE = "Mode"
API_KEY_FAN_MODE = "FanMode"
API_KEY_TEMP_SETPOINT_COOL = "TemperatureSetpoint_Cool_oC"
API_KEY_TEMP_SETPOINT_HEAT = "TemperatureSetpoint_Heat_oC"
API_KEY_ENABLED_ZONES = "EnabledZones"

# Device types
DEVICE_TYPE_ZONE_SENSOR = "Zone Sensor"

# Event types
EVENT_TYPE_AC_ON_OFF = "AC On/Off"
EVENT_TYPE_REG_WRITE = "IDU->WC Reg Write"

# Error messages
ERROR_AUTHENTICATION = "Authentication failed"
ERROR_API_REQUEST = "Failed to fetch data from Actron API"
ERROR_UNEXPECTED = "Unexpected error occurred"
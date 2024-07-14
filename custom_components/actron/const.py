from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    Platform
)
from homeassistant.components.climate.const import HVACMode

DOMAIN = "actron_air_neo"
API_URL = "https://nimbus.actronair.com.au"

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

DEFAULT_UPDATE_INTERVAL = 60

# HVAC modes
HVAC_MODES = {
    "OFF": HVACMode.OFF,
    "AUTO": HVACMode.AUTO,
    "COOL": HVACMode.COOL,
    "HEAT": HVACMode.HEAT,
    "FAN": HVACMode.FAN_ONLY,
}

# Fan modes
FAN_AUTO = "AUTO"
FAN_LOW = "LOW"
FAN_MEDIUM = "MED"
FAN_HIGH = "HIGH"

FAN_MODES = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]

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
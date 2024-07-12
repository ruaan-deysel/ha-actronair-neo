from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
)

DOMAIN = "actron_air_neo"
API_URL = "https://nimbus.actronair.com.au"

PLATFORMS = ["climate", "sensor"]

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
ATTR_FILTER_LIFE = "filter_life"
ATTR_ZONE_TEMP = "zone_temperature"

# Units
TEMP_UNIT = UnitOfTemperature.CELSIUS
PERCENTAGE_UNIT = PERCENTAGE

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
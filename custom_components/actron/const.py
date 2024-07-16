"""Constants for the Actron Neo integration."""

DOMAIN = "actron_neo"
PLATFORMS = ["climate"]

BASE_URL = "https://nimbus.actronair.com.au"

HVAC_MODE_OFF = "OFF"
HVAC_MODE_HEAT = "HEAT"
HVAC_MODE_COOL = "COOL"
HVAC_MODE_AUTO = "AUTO"
HVAC_MODE_FAN = "FAN"

FAN_MODE_AUTO = "AUTO"
FAN_MODE_LOW = "LOW"
FAN_MODE_MEDIUM = "MEDIUM"
FAN_MODE_HIGH = "HIGH"

DEFAULT_MIN_TEMP = 10
DEFAULT_MAX_TEMP = 32

ATTR_ZONE_INDEX = "zone_index"
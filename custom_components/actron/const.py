"""Constants for Actron Air Neo integration."""

DOMAIN = "actron_air_neo"

# API-related constants
BASE_URL = "https://nimbus.actronair.com.au"
LOGIN_URL = f"{BASE_URL}/api/v0/client/user-devices"
TOKEN_URL = f"{BASE_URL}/api/v0/oauth/token"
STATUS_URL = f"{BASE_URL}/api/v0/client/ac-systems"
COMMAND_URL = f"{BASE_URL}/api/v0/client/ac-systems/cmds/send"

# Configuration keys
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SERIAL_NUMBER = "serial_number"
CONF_ZONES = "zones"

# Default values
DEFAULT_CLIENT = "ios"
DEFAULT_DEVICE_NAME = "homeassistant"
DEFAULT_DEVICE_ID = "homeassistant-unique-id"

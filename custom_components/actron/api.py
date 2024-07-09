"""API communication with Actron Neo system."""

import requests
import logging

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://nimbus.actronair.com.au"

class ActronNeoAPI:
    """Class to handle API communication with Actron Neo system."""

    def __init__(self, username, password):
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._token = None
        self._session = requests.Session()
        self.login()
    
    def login(self):
        """Login to the Actron Neo system and obtain a bearer token."""
        try:
            # Step 1: Request pairing token
            response = self._session.post(
                f"{BASE_URL}/api/v0/client/user-devices",
                data={
                    "username": self._username,
                    "password": self._password,
                    "client": "ios",
                    "deviceName": "homeassistant",
                    "deviceUniqueIdentifier": "homeassistant-unique-id"
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()
            pairing_token = response.json().get("pairingToken")
            
            # Step 2: Request bearer token
            response = self._session.post(
                f"{BASE_URL}/api/v0/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": pairing_token,
                    "client_id": "app"
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()
            self._token = response.json().get("access_token")
            _LOGGER.info("Successfully logged into Actron Neo system")
        
        except requests.RequestException as error:
            _LOGGER.error(f"Failed to authenticate with Actron Neo API: {error}")
    
    def _get_headers(self):
        """Return the headers for API requests."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
    
    def get_status(self):
        """Get current status of the HVAC system."""
        try:
            response = self._session.get(
                f"{BASE_URL}/api/v0/client/ac-systems/status/latest",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as error:
            _LOGGER.error(f"Failed to retrieve status from Actron Neo API: {error}")
            return None
    
    def set_temperature(self, zone_id, temperature):
        """Set target temperature for a zone."""
        try:
            response = self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send",
                json={
                    "command": {
                        f"RemoteZoneInfo[{zone_id}].TemperatureSetpoint_Cool_oC": temperature,
                        "type": "set-settings"
                    }
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            _LOGGER.info(f"Set temperature to {temperature} for zone {zone_id}")
        
        except requests.RequestException as error:
            _LOGGER.error(f"Failed to set temperature for zone {zone_id}: {error}")
    
    def set_hvac_mode(self, zone_id, mode):
        """Set HVAC mode for a zone."""
        try:
            response = self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send",
                json={
                    "command": {
                        "UserAirconSettings.isOn": True,
                        "UserAirconSettings.Mode": mode,
                        "type": "set-settings"
                    }
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            _LOGGER.info(f"Set HVAC mode to {mode} for zone {zone_id}")
        
        except requests.RequestException as error:
            _LOGGER.error(f"Failed to set HVAC mode for zone {zone_id}: {error}")

    def set_zone_state(self, zone_id, state):
        """Set the state (on/off) for a zone."""
        try:
            response = self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send",
                json={
                    "command": {
                        f"UserAirconSettings.EnabledZones[{zone_id}]": state,
                        "type": "set-settings"
                    }
                },
                headers=self._get_headers()
            )
            response.raise_for_status()
            _LOGGER.info(f"Set state to {state} for zone {zone_id}")
        
        except requests.RequestException as error:
            _LOGGER.error(f"Failed to set state for zone {zone_id}: {error}")


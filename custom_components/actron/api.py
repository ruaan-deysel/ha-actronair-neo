"""API communication with Actron Air Neo system."""

import aiohttp
import asyncio
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
        self._session = aiohttp.ClientSession()
        self._serial_number = None
        self._zones = []
        asyncio.create_task(self.login())
    
    async def login(self):
        """Login to the Actron Neo system and obtain a bearer token, serial number, and zones."""
        try:
            # Step 1: Request pairing token
            async with self._session.post(
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
            ) as response:
                response.raise_for_status()
                data = await response.json()
                pairing_token = data.get("pairingToken")
            
            # Step 2: Request bearer token
            async with self._session.post(
                f"{BASE_URL}/api/v0/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": pairing_token,
                    "client_id": "app"
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self._token = data.get("access_token")
                _LOGGER.info("Successfully logged into Actron Neo system")

            # Step 3: Retrieve serial number and zones
            await self._retrieve_serial_number_and_zones()
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to authenticate with Actron Neo API: {error}")
    
    async def _get_headers(self):
        """Return the headers for API requests."""
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
    
    async def _retrieve_serial_number_and_zones(self):
        """Retrieve the serial number and zones of the device."""
        try:
            async with self._session.get(
                f"{BASE_URL}/api/v0/client/ac-systems?includeNeo=true",
                headers=await self._get_headers()
            ) as response:
                response.raise_for_status()
                data = await response.json()
                _LOGGER.debug(f"Received data from ac-systems API: {data}")
                systems = data.get("items", [])
                if systems:
                    system = systems[0]
                    self._serial_number = system.get("serialNumber")
                    self._zones = system.get("zones", [])
                    _LOGGER.info(f"Retrieved serial number: {self._serial_number} and zones: {self._zones}")
                else:
                    _LOGGER.error("No systems found")
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to retrieve serial number and zones: {error}")
            _LOGGER.debug(f"Response content: {await response.text()}")

    async def get_status(self):
        """Get current status of the HVAC system."""
        try:
            async with self._session.get(
                f"{BASE_URL}/api/v0/client/ac-systems/status/latest?serial={self._serial_number}",
                headers=await self._get_headers()
            ) as response:
                response.raise_for_status()
                return await response.json()
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to retrieve status from Actron Neo API: {error}")
            return None
    
    async def set_temperature(self, zone_id, temperature):
        """Set target temperature for a zone."""
        try:
            async with self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send?serial={self._serial_number}",
                json={
                    "command": {
                        f"RemoteZoneInfo[{zone_id}].TemperatureSetpoint_Cool_oC": temperature,
                        "type": "set-settings"
                    }
                },
                headers=await self._get_headers()
            ) as response:
                response.raise_for_status()
                _LOGGER.info(f"Set temperature to {temperature} for zone {zone_id}")
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to set temperature for zone {zone_id}: {error}")
    
    async def set_hvac_mode(self, mode):
        """Set HVAC mode for the system."""
        try:
            async with self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send?serial={self._serial_number}",
                json={
                    "command": {
                        "UserAirconSettings.isOn": True,
                        "UserAirconSettings.Mode": mode,
                        "type": "set-settings"
                    }
                },
                headers=await self._get_headers()
            ) as response:
                response.raise_for_status()
                _LOGGER.info(f"Set HVAC mode to {mode}")
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to set HVAC mode: {error}")

    async def set_zone_state(self, zone_id, state):
        """Set the state (on/off) for a zone."""
        try:
            async with self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send?serial={self._serial_number}",
                json={
                    "command": {
                        f"UserAirconSettings.EnabledZones[{zone_id}]": state,
                        "type": "set-settings"
                    }
                },
                headers=await self._get_headers()
            ) as response:
                response.raise_for_status()
                _LOGGER.info(f"Set state to {state} for zone {zone_id}")
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to set state for zone {zone_id}: {error}")

    async def close_session(self):
        """Close the aiohttp session."""
        await self._session.close()

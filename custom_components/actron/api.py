import aiohttp
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://nimbus.actronair.com.au"

class ActronNeoAPI:
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._token = None
        self._session = aiohttp.ClientSession()
        self._serial_number = None
        self._zones = []
        asyncio.create_task(self.login())
    
    async def login(self):
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
                headers={"Content-Type": "application/x-www-form-urlencoded"}
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
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                self._token = data.get("access_token")
                _LOGGER.info("Successfully logged into Actron Neo system")
            
            # Step 3: Retrieve serial number and zones
            await self._retrieve_serial_number_and_zones()
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to login to Actron Neo system: {error}")
    
    async def _get_headers(self):
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }
    
    async def get_status(self):
        try:
            async with self._session.get(
                f"{BASE_URL}/api/v0/client/ac-systems?serial={self._serial_number}",
                headers=await self._get_headers()
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        
        except aiohttp.ClientError as error:
            _LOGGER.error(f"Failed to get system status: {error}")
    
    async def set_temperature(self, zone_id, temperature):
        try:
            async with self._session.post(
                f"{BASE_URL}/api/v0/client/ac-systems/cmds/send?serial={self._serial_number}",
                json={
                    "command": {
                        f"UserAirconSettings.TemperatureSetpoint_Cool_oC": temperature,
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
        await self._session.close()

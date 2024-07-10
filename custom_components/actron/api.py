# File: custom_components/actron_air_neo/api.py
import aiohttp
import logging
from .const import API_URL

_LOGGER = logging.getLogger(__name__)

class ActronApi:
    def __init__(self, username, password, device_id):
        self.username = username
        self.password = password
        self.device_id = device_id
        self.bearer_token = None

    async def authenticate(self):
        pairing_token = await self._request_pairing_token()
        self.bearer_token = await self._request_bearer_token(pairing_token)

    async def _request_pairing_token(self):
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": self.device_id,  # Use device_id as deviceName
            "deviceUniqueIdentifier": self.device_id
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                response.raise_for_status()
                json_response = await response.json()
                _LOGGER.debug(f"Pairing token response: {json_response}")
                return json_response["pairingToken"]

    async def _request_bearer_token(self, pairing_token):
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": pairing_token,
            "client_id": "app"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                _LOGGER.debug(f"Bearer token request data: {data}")
                _LOGGER.debug(f"Bearer token response status: {response.status}")
                _LOGGER.debug(f"Bearer token response text: {await response.text()}")
                response.raise_for_status()
                json_response = await response.json()
                _LOGGER.debug(f"Bearer token response: {json_response}")
                return json_response["access_token"]

    async def list_ac_systems(self):
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                systems = await response.json()
                _LOGGER.debug(f"List AC systems response: {systems}")

                # Extract relevant data
                ac_systems = []
                if '_embedded' in systems and 'acSystems' in systems['_embedded']:
                    for system in systems['_embedded']['acSystems']:
                        ac_systems.append({
                            'name': system.get('name', 'Unknown'),
                            'serial': system.get('serial', 'Unknown')
                        })
                _LOGGER.debug(f"Extracted AC systems: {ac_systems}")
                return ac_systems

    async def get_ac_status(self, serial):
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()

    async def send_command(self, serial, command):
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json={"command": command}) as response:
                response.raise_for_status()
                return await response.json()

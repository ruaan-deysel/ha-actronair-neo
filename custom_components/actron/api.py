import aiohttp
import logging
from typing import Dict, Any, List
from .const import API_URL, CMD_SET_SETTINGS

_LOGGER = logging.getLogger(__name__)

class ActronApi:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.bearer_token = None
        self.session = None

    async def authenticate(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        try:
            pairing_token = await self._request_pairing_token()
            self.bearer_token = await self._request_bearer_token(pairing_token)
        except Exception as e:
            await self.close()
            raise e

    async def _request_pairing_token(self) -> str:
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": "HomeAssistant",
            "deviceUniqueIdentifier": "HomeAssistant"
        }
        try:
            async with self.session.post(url, headers=headers, data=data) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Failed to get pairing token: %s, %s", response.status, text)
                    raise AuthenticationError(f"Failed to get pairing token: {response.status}, {text}")
                json_response = await response.json()
                _LOGGER.debug("Pairing token response: %s", json_response)
                return json_response["pairingToken"]
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while requesting pairing token: %s", err)
            raise AuthenticationError(f"Network error while requesting pairing token: {err}")

    async def _request_bearer_token(self, pairing_token: str) -> str:
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": pairing_token,
            "client_id": "app"
        }
        try:
            async with self.session.post(url, headers=headers, data=data) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Failed to get bearer token: %s, %s", response.status, text)
                    raise AuthenticationError(f"Failed to get bearer token: {response.status}, {text}")
                json_response = await response.json()
                _LOGGER.debug("Bearer token response: %s", json_response)
                return json_response["access_token"]
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while requesting bearer token: %s", err)
            raise AuthenticationError(f"Network error while requesting bearer token: {err}")

    async def get_devices(self) -> List[Dict[str, str]]:
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        try:
            systems = await self._authenticated_get(url)
            devices = []
            if '_embedded' in systems and 'ac-system' in systems['_embedded']:
                for system in systems['_embedded']['ac-system']:
                    devices.append({
                        'serial': system.get('serial', 'Unknown'),
                        'name': system.get('description', 'Unknown Device')
                    })
            return devices
        except ApiError as err:
            _LOGGER.error("Failed to get devices: %s", err)
            raise

    async def get_ac_status(self, serial: str) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        try:
            return await self._authenticated_get(url)
        except ApiError as err:
            _LOGGER.error("Failed to get AC status: %s", err)
            raise

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        data = {"command": {**command, "type": CMD_SET_SETTINGS}}
        try:
            async with self.session.post(url, headers=headers, json=data) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Failed to send command: %s, %s", response.status, text)
                    raise ApiError(f"Failed to send command: {response.status}, {text}")
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while sending command: %s", err)
            raise ApiError(f"Network error while sending command: {err}")

    async def _authenticated_get(self, url: str) -> Dict[str, Any]:
        if not self.bearer_token:
            _LOGGER.error("Not authenticated")
            raise AuthenticationError("Not authenticated")
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("API request failed: %s, %s", response.status, text)
                    raise ApiError(f"API request failed: {response.status}, {text}")
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during API request: %s", err)
            raise ApiError(f"Network error during API request: {err}")

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""
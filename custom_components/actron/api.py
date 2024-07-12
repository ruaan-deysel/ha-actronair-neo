import aiohttp
import logging
from typing import Dict, Any
from .const import API_URL

_LOGGER = logging.getLogger(__name__)

class ActronApi:
    def __init__(self, username: str, password: str, device_name: str, device_unique_id: str):
        self.username = username
        self.password = password
        self.device_name = device_name
        self.device_unique_id = device_unique_id
        self.bearer_token = None
        self.session = None

    async def authenticate(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        pairing_token = await self._request_pairing_token()
        self.bearer_token = await self._request_bearer_token(pairing_token)

    async def _request_pairing_token(self) -> str:
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": self.device_name,
            "deviceUniqueIdentifier": self.device_unique_id
        }
        async with self.session.post(url, headers=headers, data=data) as response:
            if response.status != 200:
                raise AuthenticationError(f"Failed to get pairing token: {response.status}")
            json_response = await response.json()
            _LOGGER.debug(f"Pairing token response: {json_response}")
            return json_response["pairingToken"]

    async def _request_bearer_token(self, pairing_token: str) -> str:
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": pairing_token,
            "client_id": "app"
        }
        async with self.session.post(url, headers=headers, data=data) as response:
            if response.status != 200:
                raise AuthenticationError(f"Failed to get bearer token: {response.status}")
            json_response = await response.json()
            _LOGGER.debug(f"Bearer token response: {json_response}")
            return json_response["access_token"]

    async def list_ac_systems(self) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        return await self._authenticated_get(url)

    async def get_ac_status(self, serial: str) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        return await self._authenticated_get(url)

    async def get_ac_events(self, serial: str) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/events/latest?serial={serial}"
        return await self._authenticated_get(url)

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }
        data = {"command": command}
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                raise ApiError(f"Failed to send command: {response.status}")
            return await response.json()

    async def _authenticated_get(self, url: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise ApiError(f"API request failed: {response.status}")
            return await response.json()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""
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
        _LOGGER.debug("ActronApi initialized for username: %s", username)

    async def authenticate(self):
        _LOGGER.debug("Starting authentication process")
        if self.session is None:
            self.session = aiohttp.ClientSession()
            _LOGGER.debug("New aiohttp ClientSession created")

        try:
            _LOGGER.debug("Requesting pairing token")
            pairing_token = await self._request_pairing_token()
            _LOGGER.debug("Pairing token received")
            
            _LOGGER.debug("Requesting bearer token")
            self.bearer_token = await self._request_bearer_token(pairing_token)
            _LOGGER.debug("Bearer token received")
        except Exception as e:
            _LOGGER.error("Authentication failed: %s", str(e))
            await self.close()
            raise AuthenticationError(f"Authentication failed: {str(e)}")

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
        _LOGGER.debug("Sending request for pairing token to: %s", url)
        response = await self._make_request(url, "POST", headers=headers, data=data, auth_required=False)
        _LOGGER.debug("Pairing token request response received")
        return response["pairingToken"]

    async def _request_bearer_token(self, pairing_token: str) -> str:
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": pairing_token,
            "client_id": "app"
        }
        _LOGGER.debug("Sending request for bearer token to: %s", url)
        response = await self._make_request(url, "POST", headers=headers, data=data, auth_required=False)
        _LOGGER.debug("Bearer token request response received")
        return response["access_token"]

    async def get_devices(self) -> List[Dict[str, str]]:
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        _LOGGER.debug("Fetching devices from: %s", url)
        response = await self._make_request(url, "GET")
        devices = []
        if '_embedded' in response and 'ac-system' in response['_embedded']:
            for system in response['_embedded']['ac-system']:
                devices.append({
                    'serial': system.get('serial', 'Unknown'),
                    'name': system.get('description', 'Unknown Device'),
                    'type': system.get('type', 'Unknown')
                })
        _LOGGER.debug("Fetched %d devices", len(devices))
        return devices

    async def get_ac_status(self, serial: str) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        _LOGGER.debug("Fetching AC status from: %s", url)
        return await self._make_request(url, "GET")

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        data = {"command": {**command, "type": CMD_SET_SETTINGS}}
        _LOGGER.debug("Sending command to: %s, Command: %s", url, data)
        return await self._make_request(url, "POST", json=data)

    async def _make_request(self, url: str, method: str, headers: Dict[str, str] = None, data: Dict[str, Any] = None, json: Dict[str, Any] = None, auth_required: bool = True) -> Dict[str, Any]:
        if auth_required and not self.bearer_token:
            _LOGGER.error("Authentication required but no bearer token available")
            raise AuthenticationError("Not authenticated")

        if headers is None:
            headers = {}
        if auth_required:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        _LOGGER.debug("Making %s request to: %s", method, url)
        try:
            async with self.session.request(method, url, headers=headers, data=data, json=json) as response:
                if response.status == 200:
                    _LOGGER.debug("Request successful, status code: 200")
                    return await response.json()
                else:
                    text = await response.text()
                    _LOGGER.error("API request failed: %s, %s", response.status, text)
                    raise ApiError(f"API request failed: {response.status}, {text}")
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during API request: %s", err)
            raise ApiError(f"Network error during API request: {err}")

    async def close(self):
        _LOGGER.debug("Closing API session")
        if self.session:
            await self.session.close()
            self.session = None
        _LOGGER.debug("API session closed")

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""
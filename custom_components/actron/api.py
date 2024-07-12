import aiohttp
import logging
from typing import Dict, Any
from .const import API_URL

_LOGGER = logging.getLogger(__name__)

class ActronApi:
    def __init__(self, username: str, password: str, device_id: str):
        self.username = username
        self.password = password
        self.device_id = device_id
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
            "deviceName": f"HomeAssistant_{self.device_id}",
            "deviceUniqueIdentifier": self.device_id
        }
        async with self.session.post(url, headers=headers, data=data) as response:
            if response.status != 200:
                text = await response.text()
                raise AuthenticationError(f"Failed to get pairing token: {response.status}, {text}")
            json_response = await response.json()
            _LOGGER.debug(f"Pairing token response: {json_response}")
            return json_response["pairingToken"]

    # ... (rest of the methods remain the same)

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""
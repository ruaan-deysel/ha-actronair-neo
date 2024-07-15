import aiohttp
import asyncio
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
        response = await self._make_request(url, "POST", headers=headers, data=data, auth_required=False)
        _LOGGER.debug(f"Pairing token response: {response}")
        return response["pairingToken"]

    async def _request_bearer_token(self, pairing_token: str) -> str:
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": pairing_token,
            "client_id": "app"
        }
        response = await self._make_request(url, "POST", headers=headers, data=data, auth_required=False)
        _LOGGER.debug(f"Bearer token response: {response}")
        return response["access_token"]

    async def _make_request(self, url: str, method: str, headers: Dict[str, str] = None, data: Dict[str, Any] = None, json: Dict[str, Any] = None, auth_required: bool = True, retries: int = 3) -> Dict[str, Any]:
        if auth_required and not self.bearer_token:
            raise AuthenticationError("Not authenticated")

        if headers is None:
            headers = {}
        if auth_required:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        for attempt in range(retries):
            try:
                async with self.session.request(method, url, headers=headers, data=data, json=json) as response:
                    response_text = await response.text()
                    _LOGGER.debug(f"API response: {response.status}, {response_text}")
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401 and auth_required:
                        _LOGGER.warning("Authentication failed. Attempting to re-authenticate.")
                        await self.authenticate()
                        continue
                    else:
                        raise ApiError(f"API request failed: {response.status}, {response_text}")
            except aiohttp.ClientError as err:
                if attempt == retries - 1:
                    raise ApiError(f"Network error during API request: {err}")
                _LOGGER.warning(f"API request failed, retrying... (Attempt {attempt + 1}/{retries})")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise ApiError("Max retries reached")

    # ... (rest of the class methods)

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""
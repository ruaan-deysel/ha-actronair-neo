import aiohttp
import logging
from typing import Dict, Any, List
from .const import API_URL

_LOGGER = logging.getLogger(__name__)

class ActronAirNeoApi:
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
        return response["access_token"]

    async def get_devices(self) -> List[Dict[str, str]]:
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        response = await self._make_request(url, "GET")
        devices = []
        if '_embedded' in response and 'ac-systems' in response['_embedded']:
            devices = response['_embedded']['ac-systems']
        return devices

    async def _make_request(self, url: str, method: str, headers: Dict[str, str] = None, data: Dict[str, Any] = None, auth_required: bool = True):
        if headers is None:
            headers = {}
        if auth_required and self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        async with self.session.request(method, url, headers=headers, data=data) as response:
            if response.status not in [200, 201]:
                _LOGGER.error(f"Error {response.status}: {await response.text()}")
                response.raise_for_status()
            return await response.json()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

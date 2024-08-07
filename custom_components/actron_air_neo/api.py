import aiohttp
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .const import API_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""

class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

class ActronApi:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.token = None
        self.rate_limit = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
        self.request_times = []
        self.max_requests_per_minute = 20

    async def authenticate(self):
        """Authenticate and get the token."""
        try:
            url = f"{API_URL}/api/v0/oauth/token"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "client_id": "app"
            }
            _LOGGER.debug("Authenticating with Actron Air Neo API")
            response = await self._make_request(url, "POST", headers=headers, data=data, auth_required=False)
            self.token = response.get("access_token")
            if not self.token:
                raise AuthenticationError("No token received in the response")
            _LOGGER.debug("Authentication successful")
        except Exception as e:
            _LOGGER.error(f"Authentication failed: {e}")
            raise AuthenticationError(str(e))

    async def get_devices(self) -> List[Dict[str, str]]:
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        _LOGGER.debug(f"Fetching devices from: {url}")
        response = await self._make_request(url, "GET")
        devices = []
        if '_embedded' in response and 'ac-system' in response['_embedded']:
            for system in response['_embedded']['ac-system']:
                devices.append({
                    'serial': system.get('serial', 'Unknown'),
                    'name': system.get('description', 'Unknown Device'),
                    'type': system.get('type', 'Unknown')
                })
        _LOGGER.debug(f"Found devices: {devices}")
        return devices

    async def get_ac_status(self, serial: str) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        _LOGGER.debug(f"Fetching AC status from: {url}")
        return await self._make_request(url, "GET")

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        data = {"command": command}
        _LOGGER.debug(f"Sending command to: {url}, Command: {data}")
        return await self._make_request(url, "POST", json=data)

    async def _make_request(self, url: str, method: str, auth_required: bool = True, **kwargs) -> Dict[str, Any]:
        await self._wait_for_rate_limit()

        retries = 3
        for attempt in range(retries):
            try:
                headers = kwargs.get('headers', {})
                if auth_required:
                    if not self.token:
                        await self.authenticate()
                    headers['Authorization'] = f'Bearer {self.token}'
                kwargs['headers'] = headers

                _LOGGER.debug(f"Making {method} request to: {url}")
                async with self.session.request(method, url, timeout=API_TIMEOUT, **kwargs) as response:
                    self.request_times.append(datetime.now())
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401 and auth_required:
                        _LOGGER.warning("Token expired, re-authenticating...")
                        await self.authenticate()
                        continue
                    elif response.status == 429:
                        raise RateLimitError("Rate limit exceeded")
                    else:
                        text = await response.text()
                        raise ApiError(f"API request failed: {response.status}, {text}")

            except aiohttp.ClientError as err:
                _LOGGER.error(f"Network error on attempt {attempt + 1}: {err}")
                if attempt == retries - 1:
                    raise ApiError(f"Network error after {retries} attempts: {err}")
                await asyncio.sleep(5 * (2 ** attempt))  # Exponential backoff

            except asyncio.TimeoutError:
                _LOGGER.error(f"Timeout error on attempt {attempt + 1}")
                if attempt == retries - 1:
                    raise ApiError(f"Timeout error after {retries} attempts")
                await asyncio.sleep(5 * (2 ** attempt))  # Exponential backoff

        raise ApiError(f"Failed to make request after {retries} attempts")

    async def _wait_for_rate_limit(self):
        now = datetime.now()
        self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
        if len(self.request_times) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]).total_seconds()
            _LOGGER.warning(f"Rate limit approaching, waiting for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
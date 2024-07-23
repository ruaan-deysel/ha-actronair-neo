import aiohttp
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .const import API_URL

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
        self.max_requests_per_minute = 60  # Adjust as needed

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
        _LOGGER.debug(f"Requesting pairing token from: {url} with data: {data}")
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
        _LOGGER.debug(f"Requesting bearer token from: {url} with data: {data}")
        response = await self._make_request(url, "POST", headers=headers, data=data, auth_required=False)
        _LOGGER.debug(f"Bearer token response: {response}")
        return response["access_token"]

    async def _make_request(self, url: str, method: str, **kwargs) -> Dict[str, Any]:
        await self._wait_for_rate_limit()

        retries = 3
        for attempt in range(retries):
            try:
                if not self.token and kwargs.get("auth_required", True):
                    await self.authenticate()

                headers = kwargs.get('headers', {})
                if self.token and kwargs.get("auth_required", True):
                    headers['Authorization'] = f'Bearer {self.token}'
                kwargs['headers'] = headers

                async with self.session.request(method, url, **kwargs) as response:
                    self.request_times.append(datetime.now())
                    
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
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
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except RateLimitError:
                _LOGGER.warning(f"Rate limit hit on attempt {attempt + 1}, waiting before retry")
                await asyncio.sleep(60)  # Wait for 1 minute before retrying

            except ApiError as err:
                _LOGGER.error(f"API error on attempt {attempt + 1}: {err}")
                if self._is_retryable_error(err):
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise  # Re-raise if it's not a retryable error

    async def _wait_for_rate_limit(self):
        """Wait if we're approaching the rate limit."""
        now = datetime.now()
        self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
        if len(self.request_times) >= self.max_requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]).total_seconds()
            _LOGGER.warning(f"Rate limit approaching, waiting for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

    def _is_retryable_error(self, err: ApiError) -> bool:
        """Determine if an error is retryable."""
        retryable_statuses = [500, 502, 503, 504]  # Example retryable status codes
        return any(str(status) in str(err) for status in retryable_statuses)

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

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

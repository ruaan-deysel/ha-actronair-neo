import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from .const import API_URL, API_TIMEOUT, MAX_RETRIES, MAX_REQUESTS_PER_MINUTE

_LOGGER = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""

class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

class ActronApi:
    def __init__(self, username: str, password: str, session: aiohttp.ClientSession, storage_path: str):
        self.username = username
        self.password = password
        self.session = session
        self.storage_path = storage_path
        self.refresh_token = None
        self.access_token = None
        self.token_expires_at = None
        self.rate_limit = asyncio.Semaphore(5)  # Limit to 5 concurrent requests
        self.request_times = []
        self.actron_serial = ''
        self.actron_system_id = ''
        self.error_count = 0
        self.last_successful_request = None
        self.cached_status = None
        self.load_tokens()

    def load_tokens(self):
        try:
            with open(f"{self.storage_path}/tokens.json", "r") as f:
                data = json.load(f)
                self.refresh_token = data.get("refresh_token")
                self.access_token = data.get("access_token")
                self.token_expires_at = datetime.fromisoformat(data.get("expires_at", "2000-01-01"))
        except FileNotFoundError:
            pass

    def save_tokens(self):
        with open(f"{self.storage_path}/tokens.json", "w") as f:
            json.dump({
                "refresh_token": self.refresh_token,
                "access_token": self.access_token,
                "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None
            }, f)

    async def authenticate(self):
        """Authenticate and get the token."""
        if not self.refresh_token:
            await self._get_refresh_token()
        await self._get_access_token()

    async def _get_refresh_token(self):
        """Get the refresh token."""
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": "HomeAssistant",
            "deviceUniqueIdentifier": "HA-ActronNeo"
        }
        try:
            response = await self._make_request("POST", url, headers=headers, data=data, auth_required=False)
            self.refresh_token = response.get("pairingToken")
            if not self.refresh_token:
                raise AuthenticationError("No refresh token received")
            self.save_tokens()
        except Exception as e:
            raise AuthenticationError(f"Failed to get refresh token: {str(e)}")

    async def _get_access_token(self):
        """Get access token using refresh token."""
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": "app"
        }
        try:
            response = await self._make_request("POST", url, headers=headers, data=data, auth_required=False)
            self.access_token = response.get("access_token")
            expires_in = response.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # Refresh 5 minutes early
            if not self.access_token:
                raise AuthenticationError("No access token received")
            self.save_tokens()
        except Exception as e:
            raise AuthenticationError(f"Failed to get access token: {str(e)}")

    async def _make_request(self, method: str, url: str, auth_required: bool = True, **kwargs) -> Dict[str, Any]:
        await self._wait_for_rate_limit()

        retries = MAX_RETRIES
        for attempt in range(retries):
            try:
                headers = kwargs.get('headers', {})
                if auth_required:
                    if not self.access_token or datetime.now() >= self.token_expires_at:
                        await self._get_access_token()
                    headers['Authorization'] = f'Bearer {self.access_token}'
                kwargs['headers'] = headers

                _LOGGER.debug(f"Making {method} request to: {url}")
                async with self.session.request(method, url, timeout=API_TIMEOUT, **kwargs) as response:
                    self.request_times.append(datetime.now())
                    
                    if response.status == 200:
                        self.error_count = 0
                        self.last_successful_request = datetime.now()
                        return await response.json()
                    elif response.status == 401 and auth_required:
                        _LOGGER.warning("Token expired, re-authenticating...")
                        await self.authenticate()
                        continue
                    elif response.status == 429:
                        raise RateLimitError("Rate limit exceeded")
                    else:
                        text = await response.text()
                        _LOGGER.error(f"API request failed: {response.status}, {text}")
                        self.error_count += 1
                        raise ApiError(f"API request failed: {response.status}, {text}")

            except aiohttp.ClientError as err:
                _LOGGER.error(f"Network error on attempt {attempt + 1}: {err}")
                self.error_count += 1
                if attempt == retries - 1:
                    raise ApiError(f"Network error after {retries} attempts: {err}")
                await asyncio.sleep(5 * (2 ** attempt))  # Exponential backoff

            except asyncio.TimeoutError:
                _LOGGER.error(f"Timeout error on attempt {attempt + 1}")
                self.error_count += 1
                if attempt == retries - 1:
                    raise ApiError(f"Timeout error after {retries} attempts")
                await asyncio.sleep(5 * (2 ** attempt))  # Exponential backoff

        raise ApiError(f"Failed to make request after {retries} attempts")

    async def _wait_for_rate_limit(self):
        now = datetime.now()
        self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
        if len(self.request_times) >= MAX_REQUESTS_PER_MINUTE:
            sleep_time = 60 - (now - self.request_times[0]).total_seconds()
            _LOGGER.warning(f"Rate limit approaching, waiting for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)

    def is_api_healthy(self) -> bool:
        if self.error_count > 5:
            if self.last_successful_request and (datetime.now() - self.last_successful_request) < timedelta(minutes=15):
                return False
        return True

    async def get_devices(self) -> List[Dict[str, str]]:
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        _LOGGER.debug(f"Fetching devices from: {url}")
        response = await self._make_request("GET", url)
        _LOGGER.debug(f"Get devices response: {response}")
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
        if not self.is_api_healthy():
            _LOGGER.warning("API is not healthy, using cached status")
            return self.cached_status if self.cached_status else {}

        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        _LOGGER.debug(f"Fetching AC status from: {url}")
        response = await self._make_request("GET", url)
        _LOGGER.debug(f"AC status response: {response}")
        self.cached_status = response
        return response

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        data = {"command": command}
        _LOGGER.debug(f"Sending command to: {url}, Command: {data}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._make_request("POST", url, json=data)
                _LOGGER.debug(f"Command response: {response}")
                return response
            except ApiError as e:
                if "500" in str(e) and attempt < max_retries - 1:
                    _LOGGER.warning(f"Received 500 error, retrying (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    async def initializer(self):
        await self.authenticate()
        await self.get_ac_systems()

    async def get_ac_systems(self):
        devices = await self.get_devices()
        if devices:
            self.actron_serial = devices[0]['serial']
            self.actron_system_id = devices[0].get('id', '')
            _LOGGER.info(f"Located serial number {self.actron_serial} with ID of {self.actron_system_id}")
        else:
            _LOGGER.error("Could not identify target device from list of returned systems")

    def create_command(self, command_type: str, **params) -> Dict[str, Any]:
        commands = {
            "ON": lambda: {"UserAirconSettings.isOn": True, "type": "set-settings"},
            "OFF": lambda: {"UserAirconSettings.isOn": False, "type": "set-settings"},
            "CLIMATE_MODE": lambda mode: {"UserAirconSettings.Mode": mode, "type": "set-settings"},
            "FAN_MODE": lambda mode: {"UserAirconSettings.FanMode": mode, "type": "set-settings"},
            "SET_TEMP": lambda temp, is_cool: {
                f"UserAirconSettings.TemperatureSetpoint_{'Cool' if is_cool else 'Heat'}_oC": temp,
                "type": "set-settings"
            },
            "ZONE_ENABLE": lambda zone_index, zones: {
                "UserAirconSettings.EnabledZones": self._modify_zone_status(True, zone_index, zones),
                "type": "set-settings"
            },
            "ZONE_DISABLE": lambda zone_index, zones: {
                "UserAirconSettings.EnabledZones": self._modify_zone_status(False, zone_index, zones),
                "type": "set-settings"
            },
        }
        return {"command": commands[command_type](**params)}

    def _modify_zone_status(self, status: bool, zone_index: int, current_zones: List[bool]) -> List[bool]:
        modified_zones = current_zones.copy()
        modified_zones[zone_index] = status
        return modified_zones
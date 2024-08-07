import aiohttp
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .const import API_URL, API_TIMEOUT, HVAC_MODE_OFF, HVAC_MODE_COOL, HVAC_MODE_HEAT, HVAC_MODE_FAN, HVAC_MODE_AUTO

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
            _LOGGER.debug(f"Authentication response: {response}")
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
        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        _LOGGER.debug(f"Fetching AC status from: {url}")
        response = await self._make_request(url, "GET")
        _LOGGER.debug(f"AC status response: {response}")
        return response

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        data = {"command": command}
        _LOGGER.debug(f"Sending command to: {url}, Command: {data}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._make_request(url, "POST", json=data)
                _LOGGER.debug(f"Command response: {response}")
                return response
            except ApiError as e:
                if "500" in str(e) and attempt < max_retries - 1:
                    _LOGGER.warning(f"Received 500 error, retrying (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

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
                    elif response.status == 500:
                        text = await response.text()
                        _LOGGER.error(f"Server error (500): {text}")
                        raise ApiError(f"API request failed: {response.status}, {text}")
                    else:
                        text = await response.text()
                        _LOGGER.error(f"API request failed: {response.status}, {text}")
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

    async def set_power_state(self, serial: str, state: bool) -> Dict[str, Any]:
        command = {
            "UserAirconSettings.isOn": state,
            "type": "set-settings"
        }
        return await self.send_command(serial, command)

    async def set_hvac_mode(self, serial: str, mode: str) -> Dict[str, Any]:
        hvac_mode_map = {
            HVAC_MODE_OFF: "OFF",
            HVAC_MODE_COOL: "COOL",
            HVAC_MODE_HEAT: "HEAT",
            HVAC_MODE_FAN: "FAN",
            HVAC_MODE_AUTO: "AUTO"
        }
        command = {
            "UserAirconSettings.Mode": hvac_mode_map.get(mode, "AUTO"),
            "type": "set-settings"
        }
        return await self.send_command(serial, command)

    async def set_temperature(self, serial: str, temperature: float, is_cooling: bool) -> Dict[str, Any]:
        setting = "Cool" if is_cooling else "Heat"
        command = {
            f"UserAirconSettings.TemperatureSetpoint_{setting}_oC": temperature,
            "type": "set-settings"
        }
        return await self.send_command(serial, command)

    async def set_fan_mode(self, serial: str, fan_mode: str) -> Dict[str, Any]:
        command = {
            "UserAirconSettings.FanMode": fan_mode.upper(),
            "type": "set-settings"
        }
        return await self.send_command(serial, command)

    async def set_zone_state(self, serial: str, zone_index: int, is_on: bool) -> Dict[str, Any]:
        current_status = await self.get_ac_status(serial)
        enabled_zones = current_status['lastKnownState']['UserAirconSettings']['EnabledZones']
        enabled_zones[zone_index] = is_on
        command = {
            "UserAirconSettings.EnabledZones": enabled_zones,
            "type": "set-settings"
        }
        return await self.send_command(serial, command)
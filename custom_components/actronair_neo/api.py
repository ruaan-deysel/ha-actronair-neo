"""ActronAir Neo API"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import os
import aiohttp # type: ignore
import aiofiles # type: ignore

from .const import API_URL, API_TIMEOUT, MAX_RETRIES, MAX_REQUESTS_PER_MINUTE

_LOGGER = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Raised when authentication fails."""

class ApiError(Exception):
    """Raised when an API call fails."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

class RateLimiter:
    """Rate limiter to prevent overwhelming the API."""
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.semaphore = asyncio.Semaphore(calls_per_minute)
        self.call_times = []

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        self.release()

    async def acquire(self):
        """Acquire a slot for making an API call."""
        await self.semaphore.acquire()
        now = datetime.now()
        self.call_times = [t for t in self.call_times if now - t < timedelta(minutes=1)]
        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0]).total_seconds()
            await asyncio.sleep(sleep_time)
        self.call_times.append(now)

    def release(self):
        """Release the acquired slot."""
        self.semaphore.release()

class ActronApi:
    def __init__(
        self, 
        username: str, 
        password: str, 
        session: aiohttp.ClientSession, 
        config_path: str
    ) -> None:
        """Initialize the ActronApi class.
        
        Args:
            username: ActronAir Neo account username
            password: ActronAir Neo account password
            session: aiohttp client session for API requests
            config_path: Path to store configuration files
            
        Note:
            The class manages API authentication, rate limiting, and maintains
            state for the ActronAir Neo system including fan modes.
        """
        # Authentication credentials
        self.username = username
        self.password = password
        self.session = session
        
        # Token management
        self.token_file = os.path.join('/config', "actron_token.json")  # Use HA config dir
        self.refresh_token_value: str | None = None
        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None
        
        # Device identification
        self.actron_serial: str = ''
        self.actron_system_id: str = ''
        
        # API health tracking
        self.error_count: int = 0
        self.last_successful_request: datetime | None = None
        self.cached_status: dict | None = None
        
        # Rate limiting
        self.rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)
        
        # Fan mode management
        self._continuous_fan: bool = False
        self._last_fan_mode_change: datetime | None = None
        self._fan_mode_change_lock: asyncio.Lock = asyncio.Lock()
        self._min_fan_mode_interval: int = 5  # Minimum seconds between fan mode changes
        
        # Request tracking
        self._request_semaphore = asyncio.Semaphore(MAX_REQUESTS_PER_MINUTE)
        self._request_timestamps: list[datetime] = []

    def validate_fan_mode(self, mode: str, continuous: bool = False) -> str:
        """Validate and format fan mode.
        
        Args:
            mode: The fan mode to validate (LOW, MED, HIGH, AUTO)
            continuous: Whether to add continuous suffix
            
        Returns:
            Validated and formatted fan mode string
        """
        # First strip any existing continuous suffix
        base_mode = mode.split('-')[0] if '-' in mode else mode
        base_mode = base_mode.split('+')[0] if '+' in mode else base_mode
        
        valid_modes = ["LOW", "MED", "HIGH", "AUTO"]
        base_mode = base_mode.upper()
        
        if base_mode not in valid_modes:
            _LOGGER.warning(f"Invalid fan mode {mode}, defaulting to LOW")
            base_mode = "LOW"
                
        return f"{base_mode}+CONT" if continuous else base_mode

    async def load_tokens(self):
        """Load authentication tokens from storage."""
        try:
            if os.path.exists(self.token_file):
                async with aiofiles.open(self.token_file, mode='r') as f:
                    data = json.loads(await f.read())
                    self.refresh_token_value = data.get("refresh_token")
                    self.access_token = data.get("access_token")
                    self.token_expires_at = datetime.fromisoformat(data.get("expires_at", "2000-01-01"))
                _LOGGER.debug("Tokens loaded successfully")
            else:
                _LOGGER.debug("No token file found, will authenticate from scratch")
        except json.JSONDecodeError:
            _LOGGER.warning("Token file is corrupted, will authenticate from scratch")
        except (OSError, IOError) as e:
            _LOGGER.error("IO error loading tokens: %s", e)
        except ValueError as e:
            _LOGGER.error("Value error loading tokens: %s", e)

    async def save_tokens(self):
        """Save authentication tokens to storage."""
        try:
            async with aiofiles.open(self.token_file, mode='w') as f:
                await f.write(json.dumps({
                    "refresh_token": self.refresh_token_value,
                    "access_token": self.access_token,
                    "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None
                }))
            _LOGGER.debug("Tokens saved successfully")
        except (OSError, IOError) as e:
            _LOGGER.error("IO error saving tokens: %s", e)
        except TypeError as e:
            _LOGGER.error("JSON encoding error saving tokens: %s", e)

    async def clear_tokens(self):
        """Clear stored tokens when they become invalid."""
        self.refresh_token_value = None
        self.access_token = None
        self.token_expires_at = None
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        _LOGGER.info("Cleared stored tokens due to authentication failure")

    async def authenticate(self):
        """Authenticate and get the token."""
        _LOGGER.debug("Starting authentication process")
        try:
            if not self.refresh_token_value:
                _LOGGER.debug("No refresh token, getting a new one")
                await self._get_refresh_token()
            await self._get_access_token()
        except AuthenticationError:
            _LOGGER.warning("Failed to authenticate with refresh token, trying to get a new one")
            await self._get_refresh_token()
            await self._get_access_token()
        _LOGGER.debug("Authentication process completed")

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
            _LOGGER.debug("Requesting new refresh token")
            response = await self._make_request("POST", url, headers=headers, data=data, auth_required=False)
            self.refresh_token_value = response.get("pairingToken")
            if not self.refresh_token_value:
                raise AuthenticationError("No refresh token received in response")
            await self.save_tokens()
            _LOGGER.info("New refresh token obtained and saved")
        except Exception as e:
            _LOGGER.error("Failed to get new refresh token: %s", str(e))
            raise AuthenticationError(f"Failed to get new refresh token: {str(e)}") from e

    async def _get_access_token(self):
        """Get access token using refresh token."""
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token_value,
            "client_id": "app"
        }
        try:
            _LOGGER.debug("Requesting new access token")
            response = await self._make_request("POST", url, headers=headers, data=data, auth_required=False)
            self.access_token = response.get("access_token")
            expires_in = response.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # Refresh 5 minutes early
            if not self.access_token:
                _LOGGER.error("No access token received in the response")
                raise AuthenticationError("No access token received in response")
            await self.save_tokens()
            _LOGGER.info("New access token obtained and valid until: %s", self.token_expires_at)
        except AuthenticationError as e:
            _LOGGER.error("Authentication failed: %s", e)
            raise
        except Exception as e:
            _LOGGER.error("Failed to get new access token: %s", e)
            raise AuthenticationError(f"Failed to get new access token: {e}") from e

    MAX_REFRESH_RETRIES = 3
    REFRESH_RETRY_DELAY = 5  # seconds

    async def refresh_access_token(self):
        for attempt in range(self.MAX_REFRESH_RETRIES):
            try:
                await self._get_access_token()
                return
            except AuthenticationError as e:
                _LOGGER.warning("Token refresh failed (attempt %s/%s): %s", attempt + 1, self.MAX_REFRESH_RETRIES, e)
                if attempt < self.MAX_REFRESH_RETRIES - 1:
                    await asyncio.sleep(self.REFRESH_RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    _LOGGER.error("All token refresh attempts failed. Attempting to re-authenticate.")
                    await self.clear_tokens()
                    try:
                        await self._get_refresh_token()
                        await self._get_access_token()
                        return
                    except AuthenticationError as auth_err:
                        _LOGGER.error("Re-authentication failed: %s", auth_err)
                        raise
        raise AuthenticationError("Failed to refresh token and re-authentication failed")

    async def _make_request(self, method: str, url: str, auth_required: bool = True, **kwargs) -> Dict[str, Any]:
        """Make an API request with rate limiting and error handling."""
        async with self.rate_limiter:
            for attempt in range(MAX_RETRIES):
                try:
                    headers = kwargs.get('headers', {})
                    if auth_required:
                        if not self.access_token or datetime.now() >= self.token_expires_at:
                            await self.refresh_access_token()
                        headers['Authorization'] = f'Bearer {self.access_token}'
                    kwargs['headers'] = headers

                    # Log request details
                    _LOGGER.debug("Making %s request to: %s", method, url)
                    if 'json' in kwargs and kwargs['json'] is not None:
                        _LOGGER.debug("Request payload:\n%s", json.dumps(kwargs['json'], indent=2))

                    async with self.session.request(method, url, timeout=API_TIMEOUT, **kwargs) as response:
                        response_text = await response.text()
                        _LOGGER.debug("Response status: %s", response.status)
                        try:
                            response_json = json.loads(response_text)
                            _LOGGER.debug("Response body:\n%s", json.dumps(response_json, indent=2))
                        except json.JSONDecodeError:
                            _LOGGER.debug("Non-JSON response body:\n%s", response_text)

                        if response.status == 200:
                            self.error_count = 0
                            self.last_successful_request = datetime.now()
                            return response_json if 'response_json' in locals() else response_text
                        elif response.status == 401 and auth_required:
                            _LOGGER.warning("Token expired, refreshing...")
                            await self.refresh_access_token()
                            continue
                        else:
                            _LOGGER.error("API request failed: %s, %s", response.status, response_text)
                            self.error_count += 1
                            raise ApiError(f"API request failed: {response.status}, {response_text}", status_code=response.status)

                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    _LOGGER.error("Request error on attempt %s: %s", attempt + 1, err)
                    self.error_count += 1
                    if attempt == MAX_RETRIES - 1:
                        raise ApiError(f"Request failed after {MAX_RETRIES} attempts: {err}") from err
                    await asyncio.sleep(5 * (2 ** attempt))  # Exponential backoff

        raise ApiError(f"Failed to make request after {MAX_RETRIES} attempts")

    def is_api_healthy(self) -> bool:
        """Check if the API is healthy based on recent errors and successful requests."""
        if self.error_count > 5:
            if self.last_successful_request and (datetime.now() - self.last_successful_request) < timedelta(minutes=15):
                return False
        return True

    async def get_devices(self) -> List[Dict[str, str]]:
        """Fetch the list of devices from the API."""
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        _LOGGER.debug("Fetching devices from: %s", url)
        response = await self._make_request("GET", url)
        _LOGGER.debug("Get devices response: %s", response)
        devices = []
        if '_embedded' in response and 'ac-system' in response['_embedded']:
            for system in response['_embedded']['ac-system']:
                devices.append({
                    'serial': system.get('serial', 'Unknown'),
                    'name': system.get('description', 'Unknown Device'),
                    'type': system.get('type', 'Unknown')
                })
        _LOGGER.debug("Found devices: %s", devices)
        return devices

    async def get_ac_status(self, serial: str) -> Dict[str, Any]:
        """Get the current status of the AC system."""
        if not self.is_api_healthy():
            _LOGGER.warning("API is not healthy, using cached status")
            return self.cached_status if self.cached_status else {}

        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        _LOGGER.debug("Fetching AC status from: %s", url)
        response = await self._make_request("GET", url)
        _LOGGER.debug("AC status response: %s", response)
        self.cached_status = response
        return response

    async def send_command(self, serial: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to the AC system."""
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        _LOGGER.debug("Sending command to: %s", url)
        _LOGGER.debug("Command payload:\n%s", json.dumps(command, indent=2))

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._make_request("POST", url, json=command)
                _LOGGER.debug("Command response:\n%s", json.dumps(response, indent=2))
                return response
            except ApiError as e:
                if (attempt < MAX_RETRIES - 1) and (e.status_code in [500, 502, 503, 504]):
                    wait_time = 2 ** attempt  # exponential backoff
                    _LOGGER.warning("Received %s error, retrying in %s seconds (attempt %s/%s)", e.status_code, wait_time, attempt + 1, MAX_RETRIES)
                    await asyncio.sleep(wait_time)
                else:
                    _LOGGER.error("API error: %s", e)
                    raise
            except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as err:
                _LOGGER.error("Unexpected error in send_command: %s", err)
                if attempt == MAX_RETRIES - 1:
                    raise

        raise ApiError(f"Failed to send command after {MAX_RETRIES} attempts")

    async def get_zone_statuses(self) -> List[bool]:
        """Get the current status of all zones."""
        status = await self.get_ac_status(self.actron_serial)
        return status['lastKnownState']['UserAirconSettings']['EnabledZones']

    async def set_zone_state(self, zone_index: int, enable: bool) -> None:
        """Set the state of a specific zone."""
        current_zone_status = await self.get_zone_statuses()
        modified_statuses = current_zone_status.copy()
        modified_statuses[zone_index] = enable
        command = self.create_command("SET_ZONE_STATE", zones=modified_statuses)
        await self.send_command(self.actron_serial, command)

    async def set_zone_temperature(self, zone_index: int, temperature: float, is_cooling: bool) -> None:
        """Set the temperature for a specific zone."""
        command = self.create_command("SET_ZONE_TEMP", zone=zone_index, temp=temperature, is_cool=is_cooling)
        await self.send_command(self.actron_serial, command)

    async def initializer(self):
        """Initialize the ActronApi by loading tokens and authenticating."""
        _LOGGER.debug("Initializing ActronApi")
        await self.load_tokens()
        if not self.access_token or not self.refresh_token_value:
            _LOGGER.debug("No valid tokens found, authenticating from scratch")
            await self.authenticate()
        else:
            _LOGGER.debug("Tokens found, validating")
            try:
                await self.get_devices()  # This will trigger re-authentication if tokens are invalid
            except AuthenticationError:
                _LOGGER.warning("Stored tokens are invalid, re-authenticating")
                await self.authenticate()
        await self.get_ac_systems()
        _LOGGER.debug("ActronApi initialization completed")

    async def get_ac_systems(self):
        """Get the AC systems and set the serial number and system ID."""
        devices = await self.get_devices()
        if devices:
            self.actron_serial = devices[0]['serial']
            self.actron_system_id = devices[0].get('id', '')
            _LOGGER.info("Located serial number %s with ID of %s", self.actron_serial, self.actron_system_id)
        else:
            _LOGGER.error("Could not identify target device from list of returned systems")

    def create_command(self, command_type: str, **params) -> Dict[str, Any]:
        """Create a command based on the command type and parameters."""
        commands = {
            "ON": lambda: {
                "command": {
                    "UserAirconSettings.isOn": True,
                    "type": "set-settings"
                }
            },
            "OFF": lambda: {
                "command": {
                    "UserAirconSettings.isOn": False,
                    "type": "set-settings"
                }
            },
            "CLIMATE_MODE": lambda mode: {
                "command": {
                    "UserAirconSettings.isOn": True,
                    "UserAirconSettings.Mode": mode,
                    "type": "set-settings"
                }
            },
            "FAN_MODE": lambda mode: {
                "command": {
                    "UserAirconSettings.FanMode": mode,
                    "type": "set-settings"
                }
            },
            "SET_TEMP": lambda temp, is_cool: {
                "command": {
                    f"UserAirconSettings.TemperatureSetpoint_{'Cool' if is_cool else 'Heat'}_oC": temp,
                    "type": "set-settings"
                }
            },
            "AWAY_MODE": lambda state: {
                "command": {
                    "UserAirconSettings.AwayMode": state,
                    "type": "set-settings"
                }
            },
            "QUIET_MODE": lambda state: {
                "command": {
                    "UserAirconSettings.QuietMode": state,
                    "type": "set-settings"
                }
            },
            "SET_ZONE_TEMP": lambda zone, temp, temp_key: {
                "command": {
                    f"RemoteZoneInfo[{zone}].{temp_key}": temp,
                    "type": "set-settings"
                }
            },
            "SET_ZONE_STATE": lambda zones: {
                "command": {
                    "UserAirconSettings.EnabledZones": zones,
                    "type": "set-settings"
                }
            },
        }
        return commands[command_type](**params)

    async def set_climate_mode(self, mode: str) -> None:
        """Set the climate mode."""
        command = self.create_command("CLIMATE_MODE", mode=mode)
        await self.send_command(self.actron_serial, command)

    async def set_fan_mode(self, mode: str, continuous: bool | None = None) -> None:
        """Set fan mode with state tracking, validation and retry logic.
        
        Args:
            mode: The fan mode to set (LOW, MED, HIGH, AUTO)
            continuous: Whether to enable continuous fan mode. If None, maintains current state.
        
        Raises:
            ApiError: If communication with the API fails
            ValueError: If the fan mode is invalid
            RateLimitError: If too many requests are made in a short period
        """
        try:
            # If continuous is not specified, maintain current state
            if continuous is None:
                current_mode = self.data["main"].get("fan_mode", "")
                continuous = current_mode.endswith("+CONT")
                _LOGGER.debug("Maintaining current continuous state: %s", continuous)
            
            # Rate limiting check
            async with self._fan_mode_change_lock:
                if self._last_fan_mode_change:
                    elapsed = (datetime.now() - self._last_fan_mode_change).total_seconds()
                    if elapsed < self._min_fan_mode_interval:
                        wait_time = self._min_fan_mode_interval - elapsed
                        _LOGGER.debug("Rate limiting: waiting %.1f seconds", wait_time)
                        await asyncio.sleep(wait_time)

                # Validate fan mode
                validated_mode = self.validate_fan_mode(mode, continuous)
                _LOGGER.debug("Setting fan mode: %s (original mode: %s, continuous: %s)", 
                            validated_mode, mode, continuous)

                # Add retry logic for API timeouts
                for attempt in range(MAX_RETRIES):
                    try:
                        command = self.create_command("FAN_MODE", mode=validated_mode)
                        _LOGGER.debug("Sending fan mode command (attempt %d/%d): %s", 
                                    attempt + 1, MAX_RETRIES, command)
                        
                        await self.send_command(self.actron_serial, command)
                        
                        # Update state tracking
                        self._last_fan_mode_change = datetime.now()
                        self._continuous_fan = continuous
                        
                        _LOGGER.info("Successfully set fan mode to: %s", validated_mode)
                        break
                        
                    except ApiError as e:
                        if e.status_code in [500, 502, 503, 504] and attempt < MAX_RETRIES - 1:
                            wait_time = 2 ** attempt  # exponential backoff
                            _LOGGER.warning("Received %s error, retrying in %s seconds (attempt %d/%d)", 
                                        e.status_code, wait_time, attempt + 1, MAX_RETRIES)
                            await asyncio.sleep(wait_time)
                            continue
                        _LOGGER.error("API error setting fan mode: %s", e)
                        raise
                    except Exception as err:
                        _LOGGER.error("Unexpected error setting fan mode: %s", err)
                        raise

        except Exception as err:
            _LOGGER.error("Failed to set fan mode %s (continuous=%s): %s", 
                        mode, continuous, err, exc_info=True)
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set the temperature."""
        command = self.create_command("SET_TEMP", temp=temperature, is_cool=is_cooling)
        await self.send_command(self.actron_serial, command)

    async def set_away_mode(self, state: bool) -> None:
        """Set away mode."""
        command = self.create_command("AWAY_MODE", state=state)
        await self.send_command(self.actron_serial, command)

    async def set_quiet_mode(self, state: bool) -> None:
        """Set quiet mode."""
        command = self.create_command("QUIET_MODE", state=state)
        await self.send_command(self.actron_serial, command)

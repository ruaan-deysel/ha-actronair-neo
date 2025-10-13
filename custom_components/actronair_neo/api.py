"""
ActronAir Neo API client for Home Assistant integration.

This module provides a comprehensive API client for ActronAir Neo air conditioning
systems, featuring response caching, request deduplication, rate limiting, and
robust error handling.

Classes:
    RateLimiter: Manages API request rate limiting with semaphore-based control.
    ResponseCache: TTL-based response caching for API optimization.
    ActronApi: Main API client with authentication and device management.

Exceptions:
    ApiError: General API communication errors.
    AuthenticationError: Authentication-specific errors.

Example:
    ```python
    async with aiohttp.ClientSession() as session:
        api = ActronApi("user@example.com", "password", session)
        await api.authenticate()
        devices = await api.get_devices()
        status = await api.get_ac_status(devices[0]["serial"])
    ```

"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, TypeVar, cast

import aiofiles  # type: ignore
import aiohttp  # type: ignore

from .const import (
    ADVANCE_FAN_MODES,
    ADVANCE_SERIES_MODELS,
    API_TIMEOUT,
    API_URL,
    BASE_FAN_MODES,
    DEFAULT_CACHE_TTL,
    MAX_REQUESTS_PER_MINUTE,
    MAX_RETRIES,
    MAX_TEMP,
    MAX_ZONES,
    MIN_TEMP,
)
from .types import (
    AcStatusResponse,
    ApiResponse,
    CommandData,
    CommandResponse,
    DeviceInfo,
    FanModeType,
    HvacModeType,
    ZoneCapabilities,
)

_LOGGER = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ApiError(Exception):
    """Raised when an API call fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

    @property
    def is_temporary(self) -> bool:
        """Check if this is a temporary error that might resolve with retry."""
        return (
            self.status_code in [429, 500, 502, 503, 504] if self.status_code else False
        )

    @property
    def is_client_error(self) -> bool:
        """Check if this is a client error (4xx)."""
        return 400 <= self.status_code < 500 if self.status_code else False

    @property
    def is_server_error(self) -> bool:
        """Check if this is a server error (5xx)."""
        return 500 <= self.status_code < 600 if self.status_code else False


class RateLimitError(ApiError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, status_code=429, retry_after=retry_after)


class DeviceOfflineError(ApiError):
    """Raised when device is offline or unreachable."""

    def __init__(self, message: str, device_id: str):
        super().__init__(message, status_code=503)
        self.device_id = device_id


class ConfigurationError(Exception):
    """Raised when there's a configuration issue."""

    def __init__(self, message: str, config_key: str | None = None):
        super().__init__(message)
        self.config_key = config_key


class ZoneError(Exception):
    """Raised when there's a zone-specific error."""

    def __init__(
        self, message: str, zone_id: str | None = None, zone_index: int | None = None
    ):
        super().__init__(message)
        self.zone_id = zone_id
        self.zone_index = zone_index


class RateLimiter:
    """Rate limiter to prevent overwhelming the API."""

    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.semaphore = asyncio.Semaphore(calls_per_minute)
        self.call_times = []

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, *_: object) -> None:
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


class ResponseCache:
    """Response cache with TTL for API optimization."""

    def __init__(self, default_ttl: timedelta = timedelta(seconds=30)):
        """
        Initialize response cache.

        Args:
            default_ttl: Default time-to-live for cached responses

        """
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str, ttl: timedelta | None = None) -> Any | None:
        """
        Get cached response if still valid.

        Args:
            key: Cache key
            ttl: Custom TTL, uses default if None

        Returns:
            Cached response or None if expired/missing

        """
        async with self._lock:
            if key not in self._cache:
                return None

            data, timestamp = self._cache[key]
            cache_ttl = ttl or self._default_ttl

            if datetime.now() - timestamp > cache_ttl:
                del self._cache[key]
                return None

            return data

    async def set(self, key: str, value: Any) -> None:
        """
        Set cached response.

        Args:
            key: Cache key
            value: Response data to cache

        """
        async with self._lock:
            self._cache[key] = (value, datetime.now())

    async def clear(self) -> None:
        """Clear all cached responses."""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key
                for key, (_, timestamp) in self._cache.items()
                if now - timestamp > self._default_ttl
            ]
            for key in expired_keys:
                del self._cache[key]


class ActronApi:
    """ActronAir Neo API class."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        config_path: str | None = None,
    ) -> None:
        """
        Initialize the ActronApi class.

        Args:
            username: ActronAir Neo account username
            password: ActronAir Neo account password
            session: aiohttp client session for API requests
            config_path: Path to store configuration files (defaults to /config)

        Note:
            The class manages API authentication, rate limiting, and maintains
            state for the ActronAir Neo system including fan modes.

        """
        # Authentication credentials
        self.username = username
        self.password = password
        self.session = session

        # Token management
        # Use provided config_path or default to /config for backward compatibility
        token_dir = config_path if config_path else "/config"
        self.token_file = os.path.join(token_dir, "actron_token.json")
        self.refresh_token_value: str | None = None
        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None

        # Device identification
        self.actron_serial: str = ""
        self.actron_system_id: str = ""

        # API health tracking
        self.error_count: int = 0
        self.last_successful_request: datetime | None = None
        self.cached_status: dict | None = None

        # Rate limiting and caching
        self.rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)
        self.response_cache = ResponseCache(
            default_ttl=timedelta(seconds=DEFAULT_CACHE_TTL)
        )

        # Request deduplication
        self._pending_requests: dict[str, asyncio.Future] = {}

        # Document the rate limiting strategy
        _LOGGER.debug(
            "Initializing rate limiter with %s requests per minute",
            MAX_REQUESTS_PER_MINUTE,
        )

        # Fan mode management
        self._continuous_fan: bool = False
        self._last_fan_mode_change: datetime | None = None
        self._fan_mode_change_lock: asyncio.Lock = asyncio.Lock()
        self._min_fan_mode_interval: int = 5  # Minimum seconds between fan mode changes

        # Zone locks
        self._zone_locks: dict[int, asyncio.Lock] = {}

        # Request tracking
        self._request_timestamps: list[datetime] = []

        # Refresh token lock
        self._refresh_lock = asyncio.Lock()

    def _get_model_series_capabilities(self, model: str) -> frozenset[str]:
        """
        Determine supported fan modes based on model series.

        Args:
            model: The model number of the AC unit

        Returns:
            Frozenset of supported fan modes for this model series

        """
        model_base = model.split("-")[0] if "-" in model else model

        if model_base in ADVANCE_SERIES_MODELS:
            return ADVANCE_FAN_MODES
        return BASE_FAN_MODES

    def _is_advance_series(self, model: str | None) -> bool:
        """Check if model is from Advance series."""
        if not model:
            return False
        model_base = model.split("-")[0] if "-" in model else model
        return model_base in ADVANCE_SERIES_MODELS

    def validate_fan_mode(self, mode: str, continuous: bool = False) -> str:
        """
        Validate and format fan mode.

        Args:
            mode: The fan mode to validate (LOW, MED, HIGH, AUTO)
            continuous: Whether to add continuous suffix

        Returns:
            Validated and formatted fan mode string

        Raises:
            ValueError: If the provided mode is None or empty

        """
        try:
            if not mode:
                _LOGGER.warning("Empty fan mode provided, defaulting to LOW")
                return "LOW+CONT" if continuous else "LOW"

            # First strip any existing continuous suffix
            base_mode = mode.strip().upper()
            base_mode = base_mode.split("-")[0] if "-" in base_mode else base_mode
            base_mode = base_mode.split("+")[0] if "+" in base_mode else base_mode

            # Validate against known modes
            valid_modes = ["LOW", "MED", "HIGH", "AUTO"]
            if base_mode not in valid_modes:
                _LOGGER.warning(
                    "Invalid fan mode '%s' (derived from '%s'), defaulting to LOW",
                    base_mode,
                    mode,
                )
                base_mode = "LOW"

            _LOGGER.debug(
                "Fan mode validation - Input: %s, Base: %s, Continuous: %s",
                mode,
                base_mode,
                continuous,
            )

            return f"{base_mode}+CONT" if continuous else base_mode

        except (ValueError, KeyError, TypeError) as err:
            _LOGGER.error("Error validating fan mode '%s': %s", mode, str(err))
            return "LOW+CONT" if continuous else "LOW"

    async def load_tokens(self) -> None:
        """Load authentication tokens from storage."""
        try:
            if os.path.exists(self.token_file):
                async with aiofiles.open(self.token_file) as f:
                    data = json.loads(await f.read())
                    self.refresh_token_value = data.get("refresh_token")
                    self.access_token = data.get("access_token")
                    expires_at_str = data.get("expires_at")
                    if expires_at_str:
                        self.token_expires_at = datetime.fromisoformat(expires_at_str)
                    else:
                        # If no expiry time, set to past to force refresh
                        self.token_expires_at = datetime(2000, 1, 1)
                _LOGGER.debug("Tokens loaded successfully")
            else:
                _LOGGER.debug("No token file found, will authenticate from scratch")
        except json.JSONDecodeError:
            _LOGGER.warning("Token file is corrupted, will authenticate from scratch")
        except OSError as e:
            _LOGGER.error("IO error loading tokens: %s", e)
        except ValueError as e:
            _LOGGER.error("Value error loading tokens: %s", e)

    async def save_tokens(self) -> None:
        """Save authentication tokens to storage."""
        try:
            async with aiofiles.open(self.token_file, mode="w") as f:
                token_data = {
                    "refresh_token": self.refresh_token_value,
                    "access_token": self.access_token,
                    "expires_at": (
                        self.token_expires_at.isoformat()
                        if self.token_expires_at
                        else None
                    ),
                }
                await f.write(json.dumps(token_data))
            _LOGGER.debug("Tokens saved successfully")
        except OSError as e:
            _LOGGER.error("IO error saving tokens: %s", e)
        except TypeError as e:
            _LOGGER.error("JSON encoding error saving tokens: %s", e)

    async def clear_tokens(self) -> None:
        """Clear stored tokens when they become invalid."""
        self.refresh_token_value = None
        self.access_token = None
        self.token_expires_at = None
        if os.path.exists(self.token_file):
            os.remove(self.token_file)
        _LOGGER.info("Cleared stored tokens due to authentication failure")

    async def authenticate(self) -> None:
        """Authenticate and get the token."""
        _LOGGER.debug("Starting authentication process")
        try:
            if not self.refresh_token_value:
                _LOGGER.debug("No refresh token, getting a new one")
                await self._get_refresh_token()
            await self._get_access_token()
        except AuthenticationError:
            _LOGGER.info(
                "Authentication token expired, automatically refreshing credentials. This is normal operation and requires no user action."
            )
            _LOGGER.debug(
                "Failed to authenticate with refresh token, trying to get a new one"
            )
            await self._get_refresh_token()
            await self._get_access_token()
        _LOGGER.debug("Authentication process completed")

    async def _get_refresh_token(self) -> None:
        """Get the refresh token."""
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": "HomeAssistant",
            "deviceUniqueIdentifier": "HA-ActronNeo",
        }
        try:
            _LOGGER.debug("Requesting new refresh token")
            response = await self._make_request(
                "POST", url, headers=headers, data=data, auth_required=False
            )
            self.refresh_token_value = response.get("pairingToken")
            if not self.refresh_token_value:
                raise AuthenticationError("No refresh token received in response")
            await self.save_tokens()
            _LOGGER.info("New refresh token obtained and saved")
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid_grant" in error_msg or "400" in error_msg:
                _LOGGER.warning(
                    "ActronAir credentials need to be refreshed. The integration will automatically retry authentication. If this persists, check your username and password in the integration configuration."
                )
                _LOGGER.debug(
                    "Failed to get new refresh token (credential issue): %s", str(e)
                )
            elif "timeout" in error_msg or "connection" in error_msg:
                _LOGGER.info(
                    "Temporary connection issue with ActronAir servers. The integration will automatically retry. No user action required."
                )
                _LOGGER.debug(
                    "Failed to get new refresh token (connection issue): %s", str(e)
                )
            else:
                _LOGGER.error(
                    "Unable to authenticate with ActronAir servers. Please check your internet connection and integration configuration. Error: %s",
                    str(e),
                )
                _LOGGER.debug(
                    "Failed to get new refresh token (unknown error): %s", str(e)
                )
            raise AuthenticationError(f"Failed to get new refresh token: {e!s}") from e

    async def _get_access_token(self) -> None:
        """Get access token using refresh token."""
        url = f"{API_URL}/api/v0/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token_value,
            "client_id": "app",
        }
        try:
            _LOGGER.debug("Requesting new access token")
            response = await self._make_request(
                "POST", url, headers=headers, data=data, auth_required=False
            )
            self.access_token = response.get("access_token")
            expires_in = response.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(
                seconds=expires_in - 300
            )  # Refresh 5 minutes early
            if not self.access_token:
                _LOGGER.error("No access token received in the response")
                raise AuthenticationError("No access token received in response")
            await self.save_tokens()
            _LOGGER.info(
                "New access token obtained and valid until: %s", self.token_expires_at
            )
        except AuthenticationError as e:
            error_msg = str(e).lower()
            if "invalid_grant" in error_msg:
                _LOGGER.info(
                    "Authentication token expired, automatically refreshing credentials. This is normal operation and requires no user action."
                )
                _LOGGER.debug("Authentication failed (token expired): %s", e)
            else:
                _LOGGER.warning(
                    "Authentication issue detected. The integration will automatically retry. If this persists, check your ActronAir account credentials."
                )
                _LOGGER.debug("Authentication failed: %s", e)
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "connection" in error_msg:
                _LOGGER.info(
                    "Temporary connection issue with ActronAir servers. The integration will automatically retry. No user action required."
                )
                _LOGGER.debug(
                    "Failed to get new access token (connection issue): %s", e
                )
            else:
                _LOGGER.warning(
                    "Unable to refresh authentication token. The integration will automatically retry. If this persists, restart the integration."
                )
                _LOGGER.debug("Failed to get new access token: %s", e)
            raise AuthenticationError(f"Failed to get new access token: {e}") from e

    MAX_REFRESH_RETRIES = 3
    REFRESH_RETRY_DELAY = 5  # seconds

    async def refresh_access_token(self) -> None:
        """
        Refreshes the access token using exponential backoff strategy.

        This method attempts to refresh the access token up to a maximum number of retries
        defined by `MAX_REFRESH_RETRIES`. If all attempts fail, it will attempt to re-authenticate
        by clearing the tokens and obtaining a new refresh token and access token.

        Raises:
            AuthenticationError: If all token refresh attempts and re-authentication attempts fail.

        """
        for attempt in range(self.MAX_REFRESH_RETRIES):
            try:
                await self._get_access_token()
                return
            except AuthenticationError as e:
                if attempt == 0:
                    _LOGGER.info(
                        "Authentication token refresh in progress. This is normal operation and requires no user action."
                    )
                _LOGGER.debug(
                    "Token refresh failed (attempt %s/%s): %s",
                    attempt + 1,
                    self.MAX_REFRESH_RETRIES,
                    e,
                )
                if attempt < self.MAX_REFRESH_RETRIES - 1:
                    await asyncio.sleep(
                        self.REFRESH_RETRY_DELAY * (2**attempt)
                    )  # Exponential backoff
                else:
                    _LOGGER.warning(
                        "Multiple authentication attempts failed. Trying fresh authentication with your credentials."
                    )
                    _LOGGER.debug(
                        "All token refresh attempts failed. Attempting to re-authenticate."
                    )
                    await self.clear_tokens()
                    try:
                        await self._get_refresh_token()
                        await self._get_access_token()
                        return
                    except AuthenticationError as auth_err:
                        _LOGGER.error(
                            "Unable to authenticate with ActronAir servers. Please verify your username and password in the integration configuration, check your internet connection, and ensure your ActronAir account is active. If the problem persists, try restarting Home Assistant."
                        )
                        _LOGGER.debug("Re-authentication failed: %s", auth_err)
                        raise
        raise AuthenticationError(
            "Failed to refresh token and re-authentication failed"
        )

    T = TypeVar("T")

    async def _make_request(
        self, method: str, url: str, auth_required: bool = True, **kwargs
    ) -> ApiResponse | str:
        """Make an API request with rate limiting and error handling."""
        async with self.rate_limiter:
            for attempt in range(MAX_RETRIES):
                try:
                    headers = kwargs.get("headers", {})
                    if auth_required:
                        async with self._refresh_lock:
                            if (
                                not self.access_token
                                or datetime.now() >= self.token_expires_at
                            ):
                                await self.refresh_access_token()
                        headers["Authorization"] = f"Bearer {self.access_token}"
                    kwargs["headers"] = headers

                    # Log request details
                    _LOGGER.debug("Making %s request to: %s", method, url)
                    if "json" in kwargs and kwargs["json"] is not None:
                        _LOGGER.debug(
                            "Request payload:\n%s", json.dumps(kwargs["json"], indent=2)
                        )

                    async with self.session.request(
                        method, url, timeout=API_TIMEOUT, **kwargs
                    ) as response:
                        response_text = await response.text()
                        _LOGGER.debug("Response status: %s", response.status)
                        try:
                            response_json = json.loads(response_text)
                            _LOGGER.debug(
                                "Response body:\n%s",
                                json.dumps(response_json, indent=2),
                            )
                        except json.JSONDecodeError:
                            _LOGGER.debug("Non-JSON response body:\n%s", response_text)

                        if response.status == 200:
                            self.error_count = 0
                            self.last_successful_request = datetime.now()
                            return (
                                response_json
                                if "response_json" in locals()
                                else response_text
                            )
                        if response.status == 401 and auth_required:
                            _LOGGER.info(
                                "Authentication token expired, automatically refreshing credentials. This is normal operation and requires no user action."
                            )
                            _LOGGER.debug("Token expired, refreshing...")
                            await self.refresh_access_token()
                            continue
                        if response.status == 429:
                            # Rate limit exceeded
                            retry_after = int(response.headers.get("Retry-After", 60))
                            _LOGGER.warning(
                                "Rate limit exceeded, retry after %s seconds",
                                retry_after,
                            )
                            self.error_count += 1
                            raise RateLimitError(
                                f"Rate limit exceeded, retry after {retry_after} seconds",
                                retry_after=retry_after,
                            )
                        if response.status == 503:
                            # Service unavailable - could be device offline
                            _LOGGER.warning("Service unavailable: %s", response_text)
                            self.error_count += 1
                            if (
                                "device" in response_text.lower()
                                or "offline" in response_text.lower()
                            ):
                                raise DeviceOfflineError(
                                    f"Device appears to be offline: {response_text}",
                                    device_id=getattr(self, "actron_serial", "unknown"),
                                )
                            raise ApiError(
                                f"Service unavailable: {response_text}",
                                status_code=response.status,
                                retry_after=30,
                            )
                        if 400 <= response.status < 500:
                            # Client error - don't retry
                            if (
                                response.status == 400
                                and "invalid_grant" in response_text.lower()
                            ):
                                _LOGGER.info(
                                    "Authentication credentials expired, automatically refreshing. This is normal operation and requires no user action."
                                )
                                _LOGGER.debug(
                                    "Client error (invalid_grant): %s, %s",
                                    response.status,
                                    response_text,
                                )
                            elif response.status == 403:
                                _LOGGER.warning(
                                    "Access denied by ActronAir servers. Please check your account permissions and ensure your ActronAir account is active."
                                )
                                _LOGGER.debug(
                                    "Client error (forbidden): %s, %s",
                                    response.status,
                                    response_text,
                                )
                            elif response.status == 404:
                                _LOGGER.warning(
                                    "ActronAir device or endpoint not found. This may indicate a temporary server issue or device configuration problem."
                                )
                                _LOGGER.debug(
                                    "Client error (not found): %s, %s",
                                    response.status,
                                    response_text,
                                )
                            else:
                                _LOGGER.warning(
                                    "Communication issue with ActronAir servers (error %s). The integration will continue to retry automatically.",
                                    response.status,
                                )
                                _LOGGER.debug(
                                    "Client error: %s, %s",
                                    response.status,
                                    response_text,
                                )
                            self.error_count += 1
                            raise ApiError(
                                f"Client error: {response.status}, {response_text}",
                                status_code=response.status,
                            )
                        if 500 <= response.status < 600:
                            # Server error - retry with backoff
                            _LOGGER.warning(
                                "Server error: %s, %s", response.status, response_text
                            )
                            self.error_count += 1
                            if attempt < MAX_RETRIES - 1:
                                wait_time = min(
                                    5 * (2**attempt), 60
                                )  # Cap at 60 seconds
                                _LOGGER.info(
                                    "Retrying in %s seconds due to server error",
                                    wait_time,
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            raise ApiError(
                                f"Server error after {MAX_RETRIES} attempts: {response.status}, {response_text}",
                                status_code=response.status,
                            )
                        # Unexpected status code
                        _LOGGER.error(
                            "Unexpected status code: %s, %s",
                            response.status,
                            response_text,
                        )
                        self.error_count += 1
                        raise ApiError(
                            f"Unexpected status code: {response.status}, {response_text}",
                            status_code=response.status,
                        )

                except (TimeoutError, aiohttp.ClientError) as err:
                    if attempt == 0:
                        _LOGGER.info(
                            "Temporary connection issue with ActronAir servers. The integration will automatically retry. No user action required."
                        )
                    _LOGGER.debug("Request error on attempt %s: %s", attempt + 1, err)
                    self.error_count += 1
                    if attempt == MAX_RETRIES - 1:
                        _LOGGER.warning(
                            "Unable to connect to ActronAir servers after multiple attempts. Please check your internet connection. The integration will continue to retry automatically."
                        )
                        raise ApiError(
                            f"Request failed after {MAX_RETRIES} attempts: {err}"
                        ) from err
                    await asyncio.sleep(5 * (2**attempt))  # Exponential backoff

        raise ApiError(f"Failed to make request after {MAX_RETRIES} attempts")

    def is_api_healthy(self) -> bool:
        """Check if the API is healthy based on recent errors and successful requests."""
        if self.error_count > 5:
            if self.last_successful_request and (
                datetime.now() - self.last_successful_request
            ) < timedelta(minutes=15):
                return False
        return True

    async def get_devices(self) -> list[DeviceInfo]:
        """Fetch the list of devices from the API."""
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        _LOGGER.debug("Fetching devices from: %s", url)
        response = await self._make_request("GET", url)
        _LOGGER.debug("Get devices response: %s", response)
        devices: list[DeviceInfo] = []
        if "_embedded" in response and "ac-system" in response["_embedded"]:
            for system in response["_embedded"]["ac-system"]:
                devices.append(
                    {
                        "serial": system.get("serial", "Unknown"),
                        "name": system.get("description", "Unknown Device"),
                        "type": system.get("type", "Unknown"),
                        "id": system.get("id", "Unknown"),
                    }
                )
        _LOGGER.debug("Found devices: %s", devices)
        return devices

    async def get_ac_status(
        self, serial: str, use_cache: bool = True
    ) -> AcStatusResponse:
        """
        Get the current status of the AC system with optional caching.

        Args:
            serial: Device serial number
            use_cache: Whether to use response caching (default: True)

        Returns:
            AC status response data

        """
        # Check API health first
        if not self.is_api_healthy():
            _LOGGER.warning("API is not healthy, using cached status")
            return cast(
                "AcStatusResponse", self.cached_status if self.cached_status else {}
            )

        # Try cache first if enabled
        cache_key = f"ac_status_{serial}"
        if use_cache:
            cached_response = await self.response_cache.get(cache_key)
            if cached_response is not None:
                _LOGGER.debug("Using cached AC status for %s", serial)
                return cast("AcStatusResponse", cached_response)

        # Check for pending request (deduplication)
        request_key = f"get_ac_status_{serial}"
        if request_key in self._pending_requests:
            _LOGGER.debug("Waiting for pending AC status request for %s", serial)
            try:
                response = await self._pending_requests[request_key]
                return cast("AcStatusResponse", response)
            except Exception:
                # If pending request failed, continue with new request
                pass

        # Create new request future
        future = asyncio.Future()
        self._pending_requests[request_key] = future

        try:
            # Fetch from API
            url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
            _LOGGER.debug("Fetching AC status from: %s", url)
            response = await self._make_request("GET", url)
            _LOGGER.debug("AC status response: %s", response)

            # Update both caches
            self.cached_status = response
            if use_cache:
                await self.response_cache.set(cache_key, response)

            # Complete the future for other waiting requests
            if not future.done():
                future.set_result(response)

            return cast("AcStatusResponse", response)

        except Exception as e:
            # Fail the future for other waiting requests
            if not future.done():
                future.set_exception(e)
            raise
        finally:
            # Clean up pending request
            self._pending_requests.pop(request_key, None)

    async def send_command(self, serial: str, command: CommandData) -> CommandResponse:
        """Send a command to the AC system and invalidate cache."""
        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        _LOGGER.debug("Sending command to: %s", url)
        _LOGGER.debug("Command payload:\n%s", json.dumps(command, indent=2))

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._make_request("POST", url, json=command)
                _LOGGER.debug("Command response:\n%s", json.dumps(response, indent=2))

                # Invalidate cache after successful command to ensure fresh data
                await self._invalidate_status_cache(serial)

                return cast("CommandResponse", response)
            except ApiError as e:
                if (attempt < MAX_RETRIES - 1) and (
                    e.status_code in [500, 502, 503, 504]
                ):
                    wait_time = 2**attempt  # exponential backoff
                    _LOGGER.warning(
                        "Received %s error, retrying in %s seconds (attempt %s/%s)",
                        e.status_code,
                        wait_time,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    _LOGGER.error("API error: %s", e)
                    raise
            except (TimeoutError, aiohttp.ClientError, json.JSONDecodeError) as err:
                _LOGGER.error("Unexpected error in send_command: %s", err)
                if attempt == MAX_RETRIES - 1:
                    raise

        raise ApiError(f"Failed to send command after {MAX_RETRIES} attempts")

    async def _invalidate_status_cache(self, serial: str) -> None:
        """
        Invalidate cached status data after commands.

        Args:
            serial: Device serial number

        """
        cache_key = f"ac_status_{serial}"
        # Remove from response cache
        async with self.response_cache._lock:
            if cache_key in self.response_cache._cache:
                del self.response_cache._cache[cache_key]

        # Clear legacy cached status
        self.cached_status = None
        _LOGGER.debug("Invalidated status cache for %s", serial)

    async def clear_all_caches(self) -> None:
        """Clear all cached data."""
        await self.response_cache.clear()
        self.cached_status = None
        _LOGGER.debug("Cleared all API caches")

    async def cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries."""
        await self.response_cache.cleanup_expired()
        _LOGGER.debug("Cleaned up expired cache entries")

    async def get_zone_statuses(
        self, cached_status: AcStatusResponse | None = None
    ) -> list[bool]:
        """
        Get the current status of all zones.

        Args:
            cached_status: Optional pre-fetched status to avoid duplicate API calls

        Returns:
            List of zone enabled states

        """
        if cached_status is not None:
            status = cached_status
        else:
            status = await self.get_ac_status(self.actron_serial)
        return status["lastKnownState"]["UserAirconSettings"]["EnabledZones"]

    async def set_zone_state(self, zone_index: int, enable: bool) -> None:
        """Set the state of a specific zone."""
        current_zone_status = await self.get_zone_statuses()
        modified_statuses = current_zone_status.copy()
        modified_statuses[zone_index] = enable
        command = self.create_command("SET_ZONE_STATE", zones=modified_statuses)
        await self.send_command(self.actron_serial, command)

    def get_zone_capabilities(
        self, zone_data: dict[str, str | int | bool | float]
    ) -> ZoneCapabilities:
        """
        Extract zone capabilities from zone data.

        Args:
            zone_data: Raw zone data from the API

        Returns:
            ZoneCapabilities containing processed zone capabilities

        """
        return cast(
            "ZoneCapabilities",
            {
                "can_operate": zone_data.get("CanOperate", False),
                "exists": zone_data.get("NV_Exists", False),
                "has_temp_control": (
                    zone_data.get("NV_VAV", False) and zone_data.get("NV_ITC", False)
                ),
                "has_separate_targets": bool(
                    zone_data.get("TemperatureSetpoint_Cool_oC") is not None
                    and zone_data.get("TemperatureSetpoint_Heat_oC") is not None
                ),
                "target_temp_cool": zone_data.get("TemperatureSetpoint_Cool_oC"),
                "target_temp_heat": zone_data.get("TemperatureSetpoint_Heat_oC"),
                "peripheral_capabilities": None,
            },
        )

    async def set_zone_temperature(
        self,
        zone_index: int,
        temperature: float | None = None,
        target_cool: float | None = None,
        target_heat: float | None = None,
    ) -> None:
        """
        Set zone temperature with comprehensive validation and error handling.

        Args:
            zone_index: Zero-based zone index
            temperature: Single target temperature (for non-separate mode)
            target_cool: Cooling target temperature
            target_heat: Heating target temperature

        Raises:
            ValueError: If temperature values are invalid or missing
            IndexError: If zone_index is out of bounds

        """
        # Validate zone index
        if not 0 <= zone_index < MAX_ZONES:
            raise IndexError(f"Zone index {zone_index} out of bounds")

        # Validate temperature values
        for temp in [
            t for t in [temperature, target_cool, target_heat] if t is not None
        ]:
            if not MIN_TEMP <= temp <= MAX_TEMP:
                raise ValueError(
                    f"Temperature {temp} outside valid range {MIN_TEMP}-{MAX_TEMP}"
                )

        # Use a lock to prevent concurrent updates to the same zone
        async with self._zone_locks.setdefault(zone_index, asyncio.Lock()):
            if temperature is not None:
                # Single target mode
                command = self.create_command(
                    "SET_ZONE_TEMP",
                    zone=zone_index,
                    temp=temperature,
                    temp_key="TemperatureSetpoint_oC",
                )
            elif target_cool is not None and target_heat is not None:
                # Separate targets mode
                await self.send_command(
                    self.actron_serial,
                    self.create_command(
                        "SET_ZONE_TEMP",
                        zone=zone_index,
                        temp=target_cool,
                        temp_key="TemperatureSetpoint_Cool_oC",
                    ),
                )
                command = self.create_command(
                    "SET_ZONE_TEMP",
                    zone=zone_index,
                    temp=target_heat,
                    temp_key="TemperatureSetpoint_Heat_oC",
                )
            else:
                raise ValueError(
                    "Must provide either temperature or both target_cool and target_heat"
                )

            await self.send_command(self.actron_serial, command)

    async def initializer(self) -> None:
        """Initialize the ActronApi by loading tokens and authenticating."""
        _LOGGER.debug("Initializing ActronApi")
        await self.load_tokens()
        if not self.access_token or not self.refresh_token_value:
            _LOGGER.debug("No valid tokens found, authenticating from scratch")
            await self.authenticate()
        else:
            _LOGGER.debug("Tokens found, validating")
            try:
                # This will trigger re-authentication if tokens are invalid
                await self.get_devices()
            except AuthenticationError:
                _LOGGER.info(
                    "Stored authentication tokens have expired, automatically refreshing credentials. This is normal operation and requires no user action."
                )
                _LOGGER.debug("Stored tokens are invalid, re-authenticating")
                await self.authenticate()
        _LOGGER.debug("ActronApi initialization completed")

    async def set_system(self, serial_number: str, system_id: str = "") -> None:
        """Set the system to use for API calls."""
        self.actron_serial = serial_number
        self.actron_system_id = system_id
        _LOGGER.info(
            "Using system with serial number %s and ID %s",
            self.actron_serial,
            self.actron_system_id,
        )

    def create_command(self, command_type: str, **params) -> CommandData:
        """Create a command based on the command type and parameters."""
        commands = {
            "ON": lambda: {
                "command": {"UserAirconSettings.isOn": True, "type": "set-settings"}
            },
            "OFF": lambda: {
                "command": {"UserAirconSettings.isOn": False, "type": "set-settings"}
            },
            "CLIMATE_MODE": lambda mode: {
                "command": {
                    "UserAirconSettings.isOn": True,
                    "UserAirconSettings.Mode": mode,
                    "type": "set-settings",
                }
            },
            "FAN_MODE": lambda mode: {
                "command": {"UserAirconSettings.FanMode": mode, "type": "set-settings"}
            },
            "SET_TEMP": lambda temp, is_cool: {
                "command": {
                    f"UserAirconSettings.TemperatureSetpoint_{'Cool' if is_cool else 'Heat'}_oC": temp,
                    "type": "set-settings",
                }
            },
            "AWAY_MODE": lambda state: {
                "command": {
                    "UserAirconSettings.AwayMode": state,
                    "type": "set-settings",
                }
            },
            "QUIET_MODE": lambda state: {
                "command": {
                    "UserAirconSettings.QuietMode": state,
                    "type": "set-settings",
                }
            },
            "SET_ZONE_TEMP": lambda zone, temp, temp_key: {
                "command": {
                    f"RemoteZoneInfo[{zone}].{temp_key}": temp,
                    "type": "set-settings",
                }
            },
            "SET_ZONE_STATE": lambda zones: {
                "command": {
                    "UserAirconSettings.EnabledZones": zones,
                    "type": "set-settings",
                }
            },
        }
        return cast("CommandData", commands[command_type](**params))

    async def set_climate_mode(self, mode: HvacModeType) -> None:
        """Set the climate mode."""
        command = self.create_command("CLIMATE_MODE", mode=mode)
        await self.send_command(self.actron_serial, command)

    async def set_fan_mode(
        self, mode: FanModeType, continuous: bool | None = None
    ) -> None:
        """
        Set fan mode with state tracking, validation and retry logic.

        Args:
            mode: The fan mode to set (LOW, MED, HIGH, AUTO)
            continuous: Whether to enable continuous fan mode. If None, maintains current state.

        Raises:
            ApiError: If communication with the API fails after all retries
            ValueError: If the fan mode is invalid or unsupported
            RateLimitError: If too many requests are made in a short period

        """
        try:
            # If continuous is not specified, maintain current state
            if continuous is None:
                current_mode = self.data["main"].get("fan_mode", "")
                continuous = "+CONT" in current_mode
                _LOGGER.debug("Maintaining current continuous state: %s", continuous)

            # Acquire lock for rate limiting
            async with self._fan_mode_change_lock:
                # Check rate limiting
                if self._last_fan_mode_change:
                    elapsed = (
                        datetime.now() - self._last_fan_mode_change
                    ).total_seconds()
                    if elapsed < self._min_fan_mode_interval:
                        wait_time = self._min_fan_mode_interval - elapsed
                        _LOGGER.debug("Rate limiting: waiting %.1f seconds", wait_time)
                        await asyncio.sleep(wait_time)

                # Get current model and validate mode against capabilities
                model = (
                    self.data["main"].get("model") if hasattr(self, "data") else None
                )
                validated_mode = self.validate_fan_mode(mode, continuous)

                if (
                    model
                    and validated_mode.startswith("AUTO")
                    and model not in ADVANCE_SERIES_MODELS
                ):
                    raise ValueError(f"AUTO fan mode not supported on model {model}")

                _LOGGER.debug(
                    "Setting fan mode: %s (original: %s, continuous: %s, model: %s)",
                    validated_mode,
                    mode,
                    continuous,
                    model,
                )

                # Retry logic for API timeouts
                last_error = None
                for attempt in range(MAX_RETRIES):
                    try:
                        command = self.create_command("FAN_MODE", mode=validated_mode)
                        _LOGGER.debug(
                            "Sending fan mode command (attempt %d/%d): %s",
                            attempt + 1,
                            MAX_RETRIES,
                            command,
                        )

                        await self.send_command(self.actron_serial, command)

                        # Update state tracking on success
                        self._last_fan_mode_change = datetime.now()
                        self._continuous_fan = continuous

                        _LOGGER.info(
                            "Successfully set fan mode to: %s (continuous: %s)",
                            validated_mode,
                            continuous,
                        )
                        return  # Success, exit the retry loop

                    except ApiError as api_err:
                        last_error = api_err
                        if (
                            api_err.status_code in [500, 502, 503, 504]
                            and attempt < MAX_RETRIES - 1
                        ):
                            wait_time = min(
                                2**attempt, 30
                            )  # Cap exponential backoff at 30 seconds
                            _LOGGER.warning(
                                "API error %s, retrying in %s seconds (attempt %d/%d)",
                                api_err.status_code,
                                wait_time,
                                attempt + 1,
                                MAX_RETRIES,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        raise  # Re-raise if we're out of retries or it's not a retriable error

                    except Exception as err:
                        _LOGGER.error(
                            "Unexpected error setting fan mode: %s", err, exc_info=True
                        )
                        raise

                # If we get here, all retries failed
                if last_error:
                    raise ApiError(
                        f"Failed to set fan mode after {MAX_RETRIES} attempts: {last_error}"
                    )

        except ValueError as val_err:
            _LOGGER.error(
                "Invalid fan mode request: %s (mode: %s, continuous: %s)",
                val_err,
                mode,
                continuous,
            )
            raise

        except Exception as err:
            _LOGGER.error(
                "Failed to set fan mode %s (continuous=%s): %s",
                mode,
                continuous,
                err,
                exc_info=True,
            )
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

"""Exceptions for the ActronAir Neo integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_HTTP_CLIENT_ERROR_MIN = 400
_HTTP_CLIENT_ERROR_MAX = 500
_HTTP_SERVER_ERROR_MIN = 500
_HTTP_SERVER_ERROR_MAX = 600


class ActronAirNeoError(HomeAssistantError):
    """Base exception for all ActronAir Neo errors."""

    translation_domain: str = DOMAIN
    translation_key: str = "unknown_error"

    def __init__(self, message: str, *args: object) -> None:
        """Initialize the base error."""
        super().__init__(message, *args)


class ApiError(ActronAirNeoError):
    """Raised when an API call fails."""

    translation_key: str = "api_error"

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        """Initialize API error."""
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after

    @property
    def is_temporary(self) -> bool:
        """Check if this is a temporary error that might resolve with retry."""
        if self.status_code is None:
            return False
        return self.status_code in {429, 500, 502, 503, 504}

    @property
    def is_client_error(self) -> bool:
        """Check if this is a client error (4xx)."""
        if self.status_code is None:
            return False
        return _HTTP_CLIENT_ERROR_MIN <= self.status_code < _HTTP_CLIENT_ERROR_MAX

    @property
    def is_server_error(self) -> bool:
        """Check if this is a server error (5xx)."""
        if self.status_code is None:
            return False
        return _HTTP_SERVER_ERROR_MIN <= self.status_code < _HTTP_SERVER_ERROR_MAX


class AuthenticationError(ActronAirNeoError):
    """Raised when authentication fails."""

    translation_key: str = "authentication_error"

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Initialize authentication error."""
        super().__init__(message)
        self.retry_after = retry_after


class RateLimitError(ApiError):
    """Raised when rate limit is exceeded."""

    translation_key: str = "rate_limit_error"

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        """Initialize rate limit error."""
        super().__init__(message, status_code=429, retry_after=retry_after)


class DeviceOfflineError(ApiError):
    """Raised when device is offline or unreachable."""

    translation_key: str = "device_offline_error"

    def __init__(self, message: str, device_id: str = "") -> None:
        """Initialize device offline error."""
        super().__init__(message, status_code=503)
        self.device_id = device_id


class ConfigurationError(ActronAirNeoError):
    """Raised when there is a configuration issue."""

    translation_key: str = "configuration_error"

    def __init__(self, message: str, config_key: str | None = None) -> None:
        """Initialize configuration error."""
        super().__init__(message)
        self.config_key = config_key


class ZoneError(ActronAirNeoError):
    """Raised when there is a zone-specific error."""

    translation_key: str = "zone_error"

    def __init__(
        self,
        message: str,
        zone_id: str | None = None,
        zone_index: int | None = None,
    ) -> None:
        """Initialize zone error."""
        super().__init__(message)
        self.zone_id = zone_id
        self.zone_index = zone_index

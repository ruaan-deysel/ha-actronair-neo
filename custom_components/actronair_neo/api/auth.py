"""
Authentication manager for the ActronAir Neo API.

Implements OAuth2 Device Code Flow (RFC 8628) for user authorization
and token lifecycle management (refresh, expiry, persistence via callback).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from custom_components.actronair_neo.exceptions import AuthenticationError

from .const import (
    API_URL,
    CLIENT_ID,
    DEVICE_CODE_GRANT_TYPE,
    DEVICE_CODE_POLL_INTERVAL,
    DEVICE_CODE_SCOPE,
    ENDPOINT_OAUTH_TOKEN,
    MAX_REFRESH_RETRIES,
    REFRESH_RETRY_DELAY,
    TOKEN_EXPIRY_BUFFER,
)

_LOGGER = logging.getLogger(__name__)

# Type alias for the token-refresh callback.
# Signature: (access_token, refresh_token, expires_at_timestamp) -> None
type TokenRefreshCallback = Any  # Callable[[str, str, float], Awaitable[None]]


@dataclass(frozen=True)
class DeviceCodeResponse:
    """Data returned when requesting a device code."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


class ActronAirNeoAuth:
    """
    Manages authentication tokens for the ActronAir Neo API.

    Supports two workflows:
    1. **Device Code Flow** (config flow):
       ``request_device_code()`` → ``poll_for_token()``
    2. **Token restore** (integration setup):
       ``set_tokens()`` → ``ensure_valid_token()`` (auto-refreshes)

    Token persistence is handled externally via the
    ``set_token_refresh_callback`` hook.
    """

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """
        Initialize the authentication manager.

        Args:
            session: aiohttp client session for HTTP requests.

        """
        self.session = session

        self.access_token: str | None = None
        self.refresh_token_value: str | None = None
        self.token_expires_at: datetime | None = None

        self._refresh_lock = asyncio.Lock()
        self._token_refresh_callback: TokenRefreshCallback | None = None

    # ── Callback management ──────────────────────────────────────

    def set_token_refresh_callback(
        self,
        callback: TokenRefreshCallback,
    ) -> None:
        """
        Register a callback invoked after every successful token refresh.

        The callback receives ``(access_token, refresh_token, expires_at)``
        where *expires_at* is a POSIX timestamp (``float``).
        """
        self._token_refresh_callback = callback

    async def _notify_token_refreshed(self) -> None:
        """Invoke the token-refresh callback if one is registered."""
        if (
            self._token_refresh_callback
            and self.access_token
            and self.refresh_token_value
            and self.token_expires_at
        ):
            await self._token_refresh_callback(
                self.access_token,
                self.refresh_token_value,
                self.token_expires_at.timestamp(),
            )

    # ── Token state helpers ──────────────────────────────────────

    @property
    def is_token_valid(self) -> bool:
        """Return True if the current access token has not expired."""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at  # noqa: DTZ005

    def set_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_at: float,
    ) -> None:
        """
        Restore tokens from persistent storage (config entry data).

        Args:
            access_token: The stored access token.
            refresh_token: The stored refresh token.
            expires_at: POSIX timestamp of token expiry.

        """
        self.access_token = access_token
        self.refresh_token_value = refresh_token
        self.token_expires_at = datetime.fromtimestamp(expires_at)  # noqa: DTZ006

    # ── Device Code Flow (used by config_flow) ───────────────────

    async def request_device_code(self) -> DeviceCodeResponse:
        """
        Request a device code to start the authorization flow.

        Returns:
            A ``DeviceCodeResponse`` with the device code, user code,
            verification URI, expiry, and poll interval.

        Raises:
            AuthenticationError: If the API rejects the request.

        """
        url = f"{API_URL}{ENDPOINT_OAUTH_TOKEN}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_id": CLIENT_ID,
            "scope": DEVICE_CODE_SCOPE,
        }

        response = await self._make_auth_request(
            "POST", url, headers=headers, data=data
        )

        try:
            verification_uri = response.get("verification_uri", f"{API_URL}/connect")
            return DeviceCodeResponse(
                device_code=response["device_code"],
                user_code=response["user_code"],
                verification_uri=verification_uri,
                verification_uri_complete=response.get(
                    "verification_uri_complete", verification_uri
                ),
                expires_in=response.get("expires_in", 300),
                interval=response.get("interval", DEVICE_CODE_POLL_INTERVAL),
            )
        except KeyError as err:
            msg = f"Incomplete device code response: {err}"
            raise AuthenticationError(msg) from err

    async def poll_for_token(
        self,
        device_code: str,
        interval: int = DEVICE_CODE_POLL_INTERVAL,
        expires_in: int = 300,
    ) -> dict[str, Any]:
        """
        Poll the token endpoint until the user authorizes.

        Args:
            device_code: The device code from ``request_device_code``.
            interval: Seconds between poll attempts.
            expires_in: Maximum seconds to poll before timing out.

        Returns:
            The raw token response dict from the API.

        Raises:
            AuthenticationError: On timeout, denial, or connection error.

        """
        url = f"{API_URL}{ENDPOINT_OAUTH_TOKEN}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": DEVICE_CODE_GRANT_TYPE,
            "device_code": device_code,
            "client_id": CLIENT_ID,
        }

        deadline = datetime.now() + timedelta(seconds=expires_in)  # noqa: DTZ005
        poll_interval = interval

        while datetime.now() < deadline:  # noqa: DTZ005
            try:
                async with self.session.post(
                    url,
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    body = await resp.text()

                    if resp.status == 200:  # noqa: PLR2004
                        result: dict[str, Any] = json.loads(body)
                        self._store_token_response(result)
                        return result

                    if resp.status == 400:  # noqa: PLR2004
                        error_data = json.loads(body)
                        error = error_data.get("error", "")

                        if error == "authorization_pending":
                            await asyncio.sleep(poll_interval)
                            continue
                        if error == "slow_down":
                            poll_interval += 5
                            await asyncio.sleep(poll_interval)
                            continue
                        if error == "expired_token":
                            msg = "Device code expired"
                            raise AuthenticationError(msg)  # noqa: TRY301
                        if error == "access_denied":
                            msg = "Authorization denied by user"
                            raise AuthenticationError(msg)  # noqa: TRY301

                        msg = f"Authorization failed: {error}"
                        raise AuthenticationError(msg)  # noqa: TRY301

                    msg = f"Unexpected response status: {resp.status}"
                    raise AuthenticationError(msg)  # noqa: TRY301

            except AuthenticationError:
                raise
            except (TimeoutError, aiohttp.ClientError):
                await asyncio.sleep(poll_interval)

        msg = "Device code authorization timed out"
        raise AuthenticationError(msg)

    # ── Token refresh (used at runtime) ──────────────────────────

    async def ensure_valid_token(self) -> None:
        """Ensure a valid access token is available, refreshing if needed."""
        async with self._refresh_lock:
            if not self.is_token_valid:
                await self.refresh_access_token()

    async def get_auth_headers(self) -> dict[str, str]:
        """Get authorization headers with a valid token."""
        await self.ensure_valid_token()
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using the stored refresh token."""
        if not self.refresh_token_value:
            msg = "No refresh token available"
            raise AuthenticationError(msg)

        url = f"{API_URL}{ENDPOINT_OAUTH_TOKEN}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token_value,
            "client_id": CLIENT_ID,
        }

        response = await self._make_auth_request(
            "POST", url, headers=headers, data=data
        )

        self._store_token_response(response)
        await self._notify_token_refreshed()

    async def refresh_access_token(self) -> None:
        """Refresh the access token with exponential backoff retry."""
        for attempt in range(MAX_REFRESH_RETRIES):
            try:
                await self._refresh_access_token()
            except AuthenticationError:
                if attempt < MAX_REFRESH_RETRIES - 1:
                    await asyncio.sleep(REFRESH_RETRY_DELAY * (2**attempt))
                else:
                    _LOGGER.warning(
                        "All token refresh attempts failed. Re-authentication required."
                    )
                    raise
            else:
                return

    # ── Internal helpers ─────────────────────────────────────────

    def _store_token_response(self, response: dict[str, Any]) -> None:
        """Extract and store tokens from an API response."""
        access_token = response.get("access_token")
        if not access_token:
            msg = "No access token in response"
            raise AuthenticationError(msg)

        expires_in = response.get("expires_in", 3600)
        self.access_token = access_token
        self.refresh_token_value = response.get(
            "refresh_token", self.refresh_token_value
        )
        self.token_expires_at = datetime.now() + timedelta(  # noqa: DTZ005
            seconds=expires_in - TOKEN_EXPIRY_BUFFER
        )

    async def _make_auth_request(
        self, method: str, url: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an unauthenticated request for token operations."""
        try:
            async with self.session.request(
                method,
                url,
                timeout=aiohttp.ClientTimeout(total=30),
                **kwargs,
            ) as response:
                response_text = await response.text()

                if response.status == 200:  # noqa: PLR2004
                    return json.loads(response_text)

                error_msg = f"Auth request failed: {response.status}, {response_text}"
                raise AuthenticationError(error_msg)  # noqa: TRY301

        except AuthenticationError:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            msg = f"Auth request failed: {err}"
            raise AuthenticationError(msg) from err

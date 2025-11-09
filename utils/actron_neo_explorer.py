#!/usr/bin/env python3
"""
ActronAir Neo API Explorer.

This tool connects to the ActronAir Neo cloud API and allows exploration of the API responses.
It can be used to better understand the API structure for documentation purposes.

Usage:
    python actron_neo_explorer.py [options]

Options:
    -u, --username  ActronAir Neo account username
    -p, --password  ActronAir Neo account password
    -d, --debug     Enable debug logging
    -t, --token-file Path to token file (default: actron_token.json in script directory)
    -g, --generate-diagnostics Generate diagnostics.md file based on system information

Examples:
    python actron_neo_explorer.py                     # Interactive mode with prompts
    python actron_neo_explorer.py -u user@email.com   # Provide username, prompt for password
    python actron_neo_explorer.py -d                  # Enable debug mode
    python actron_neo_explorer.py -g                  # Generate diagnostics.md file

NOTE: Credentials are never stored, only authentication tokens are saved locally.

"""

import argparse
import asyncio
import contextlib
import getpass
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

import aiofiles
import aiohttp

# Rich imports for beautiful UI
try:
    from rich.box import ROUNDED, Box
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.pretty import Pretty
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, Prompt
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    # Define custom theme
    actron_theme = Theme(
        {
            "info": "cyan",
            "warning": "yellow",
            "success": "green bold",
            "error": "red bold",
            "title": "blue bold",
            "highlight": "magenta",
            "menu_header": "cyan bold",
            "menu_item": "green",
            "menu_desc": "dim white",
            "button": "cyan reverse",
            "panel.border": "cyan",
        }
    )

    # Initialize rich console
    console = Console(theme=actron_theme)
    RICH_AVAILABLE = True
except ImportError:
    # Fall back to standard output if rich is not available
    RICH_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
_LOGGER = logging.getLogger("actron_neo_explorer")

# API Constants
API_URL = "https://nimbus.actronair.com.au"
API_TIMEOUT = 30
MAX_RETRIES = 3
MAX_REQUESTS_PER_MINUTE = 20


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class ApiError(Exception):
    """Raised when an API call fails."""

    def __init__(self, message, status_code=None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""


class RateLimiter:
    """Rate limiter to prevent overwhelming the API."""

    def __init__(self, calls_per_minute: int) -> None:
        self.calls_per_minute = calls_per_minute
        self.semaphore = asyncio.Semaphore(calls_per_minute)
        self.call_times = []

    async def __aenter__(self):
        await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        self.release()

    async def acquire(self) -> None:
        """Acquire a slot for making an API call."""
        await self.semaphore.acquire()
        now = datetime.now()
        self.call_times = [t for t in self.call_times if now - t < timedelta(minutes=1)]
        if len(self.call_times) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0]).total_seconds()
            await asyncio.sleep(sleep_time)
        self.call_times.append(now)

    def release(self) -> None:
        """Release the acquired slot."""
        self.semaphore.release()


class ActronNeoExplorer:
    """ActronAir Neo API Explorer class."""

    def __init__(
        self,
        username: str,
        password: str,
        token_file_path: str | None = None,
        debug: bool = False,
    ) -> None:
        # Set log level
        if debug:
            _LOGGER.setLevel(logging.DEBUG)

        # Authentication credentials
        self.username = username
        self.password = password

        # Token management
        self.token_file = token_file_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "actron_token.json"
        )
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

        # Rate limiting
        self.rate_limiter = RateLimiter(MAX_REQUESTS_PER_MINUTE)

        # Request tracking
        self._request_timestamps: list[datetime] = []

        # Refresh token lock
        self._refresh_lock = asyncio.Lock()

        # Session
        self.session = None

    async def __aenter__(self):
        # Create aiohttp session
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Close the session
        if self.session:
            await self.session.close()

    async def load_tokens(self) -> None:
        """Load authentication tokens from storage."""
        try:
            if os.path.exists(self.token_file):
                async with aiofiles.open(self.token_file) as f:
                    data = json.loads(await f.read())
                    self.refresh_token_value = data.get("refresh_token")
                    self.access_token = data.get("access_token")
                    expires_at_str = data.get("expires_at", "2000-01-01")
                    self.token_expires_at = datetime.fromisoformat(expires_at_str)

                # Verify token data is valid
                if (
                    not self.refresh_token_value
                    or not self.access_token
                    or not self.token_expires_at
                ):
                    _LOGGER.warning(
                        "Token file contains incomplete data, will authenticate from scratch"
                    )
                    await self.clear_tokens()
                else:
                    _LOGGER.debug("Tokens loaded successfully")
            else:
                _LOGGER.debug("No token file found, will authenticate from scratch")
        except json.JSONDecodeError:
            _LOGGER.warning("Token file is corrupted, will authenticate from scratch")
            await self.clear_tokens()
        except OSError as e:
            _LOGGER.exception("IO error loading tokens: %s", e)
        except ValueError as e:
            _LOGGER.exception("Value error loading tokens: %s", e)
            await self.clear_tokens()

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
            _LOGGER.exception("IO error saving tokens: %s", e)
        except TypeError as e:
            _LOGGER.exception("JSON encoding error saving tokens: %s", e)

    async def clear_tokens(self) -> None:
        """Clear stored tokens when they become invalid."""
        self.refresh_token_value = None
        self.access_token = None
        self.token_expires_at = None
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
                _LOGGER.info("Cleared stored tokens due to authentication failure")
            except OSError as e:
                _LOGGER.exception("Error removing token file: %s", e)

    async def authenticate(self) -> None:
        """Authenticate and get the token."""
        _LOGGER.info("Starting authentication process")
        try:
            if not self.refresh_token_value:
                _LOGGER.debug("No refresh token, getting a new one")
                await self._get_refresh_token()
            await self._get_access_token()
        except AuthenticationError:
            _LOGGER.warning(
                "Failed to authenticate with refresh token, trying to get a new one"
            )
            # Clear existing tokens as they failed
            await self.clear_tokens()
            # Try with a fresh token
            await self._get_refresh_token()
            await self._get_access_token()
        _LOGGER.info("Authentication process completed")

    async def _get_refresh_token(self) -> None:
        """Get the refresh token."""
        url = f"{API_URL}/api/v0/client/user-devices"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "username": self.username,
            "password": self.password,
            "client": "ios",
            "deviceName": "ActronExplorer",
            "deviceUniqueIdentifier": "ActronNeoExplorer",
        }
        try:
            _LOGGER.debug("Requesting new refresh token")
            response = await self._make_request(
                "POST", url, headers=headers, data=data, auth_required=False
            )
            self.refresh_token_value = response.get("pairingToken")
            if not self.refresh_token_value:
                msg = "No refresh token received in response"
                raise AuthenticationError(msg)
            await self.save_tokens()
            _LOGGER.info("New refresh token obtained and saved")
        except Exception as e:
            _LOGGER.exception("Failed to get new refresh token: %s", str(e))
            msg = f"Failed to get new refresh token: {e!s}"
            raise AuthenticationError(msg) from e

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
                msg = "No access token received in response"
                raise AuthenticationError(msg)
            await self.save_tokens()
            _LOGGER.info(
                "New access token obtained and valid until: %s", self.token_expires_at
            )
        except AuthenticationError as e:
            _LOGGER.exception("Authentication failed: %s", e)
            raise
        except Exception as e:
            _LOGGER.exception("Failed to get new access token: %s", e)
            msg = f"Failed to get new access token: {e}"
            raise AuthenticationError(msg) from e

    async def refresh_access_token(self) -> None:
        """Refresh the access token when it's expired."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self._get_access_token()
                return
            except AuthenticationError as e:
                _LOGGER.warning(
                    "Token refresh failed (attempt %s/%s): %s",
                    attempt + 1,
                    max_retries,
                    e,
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(5 * (2**attempt))  # Exponential backoff
                else:
                    _LOGGER.exception(
                        "All token refresh attempts failed. Attempting to re-authenticate."
                    )
                    await self.clear_tokens()
                    try:
                        await self._get_refresh_token()
                        await self._get_access_token()
                        return
                    except AuthenticationError as auth_err:
                        _LOGGER.exception("Re-authentication failed: %s", auth_err)
                        raise
        msg = "Failed to refresh token and re-authentication failed"
        raise AuthenticationError(msg)

    async def _make_request(
        self, method: str, url: str, auth_required: bool = True, **kwargs
    ) -> dict[str, Any]:
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
                        except json.JSONDecodeError:
                            _LOGGER.debug("Non-JSON response body:\n%s", response_text)
                            return response_text

                        if response.status == 200:
                            self.error_count = 0
                            self.last_successful_request = datetime.now()
                            return response_json
                        if response.status == 401 and auth_required:
                            _LOGGER.warning("Token expired, refreshing...")
                            await self.refresh_access_token()
                            continue
                        _LOGGER.error(
                            "API request failed: %s, %s",
                            response.status,
                            response_text,
                        )
                        self.error_count += 1
                        msg = f"API request failed: {response.status}, {response_text}"
                        raise ApiError(
                            msg,
                            status_code=response.status,
                        )

                except (TimeoutError, aiohttp.ClientError) as err:
                    _LOGGER.exception(
                        "Request error on attempt %s: %s", attempt + 1, err
                    )
                    self.error_count += 1
                    if attempt == MAX_RETRIES - 1:
                        msg = f"Request failed after {MAX_RETRIES} attempts: {err}"
                        raise ApiError(msg) from err
                    await asyncio.sleep(5 * (2**attempt))  # Exponential backoff

        msg = f"Failed to make request after {MAX_RETRIES} attempts"
        raise ApiError(msg)

    async def initialize(self) -> None:
        """Initialize the explorer by loading tokens and authenticating."""
        _LOGGER.info("Initializing ActronNeoExplorer")
        await self.load_tokens()
        if not self.access_token or not self.refresh_token_value:
            _LOGGER.debug("No valid tokens found, authenticating from scratch")
            await self.authenticate()
        else:
            _LOGGER.debug("Tokens found, validating")
            try:
                # This will trigger re-authentication if tokens are invalid
                cached_devices = await self.get_devices()
                if not cached_devices:
                    msg = "No devices found"
                    raise ValueError(msg)
            except AuthenticationError:
                _LOGGER.warning("Stored tokens are invalid, re-authenticating")
                await self.authenticate()
                cached_devices = await self.get_devices()
                if not cached_devices:
                    msg = "No devices found"
                    raise ValueError(msg)

        # Get devices and let user select one
        if not hasattr(self, "actron_serial") or not self.actron_serial:
            if not cached_devices:  # Use cached devices if available
                cached_devices = await self.get_devices()
            if not cached_devices:
                msg = "No devices found in your ActronAir Neo account"
                raise ValueError(msg)
            await self.select_device(cached_devices)

    async def get_devices(self) -> list[dict[str, str]]:
        """Fetch the list of devices from the API."""
        url = f"{API_URL}/api/v0/client/ac-systems?includeNeo=true"
        _LOGGER.info("Fetching devices from API")
        response = await self._make_request("GET", url)

        devices = []
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

        if not devices:
            _LOGGER.warning("No devices found")

        return devices

    async def select_device(self, devices: list[dict[str, str]]) -> dict[str, str]:
        """Allow the user to select a device from the list."""
        if not devices:
            msg = "No devices available to select from"
            raise ValueError(msg)

        if len(devices) == 1:
            selected_device = devices[0]
            _LOGGER.info(
                "Only one device found, automatically selecting %s (%s)",
                selected_device["name"],
                selected_device["serial"],
            )
        # Display devices for selection
        elif RICH_AVAILABLE:
            console.print("\n[title]Multiple ActronAir Neo systems found:[/title]")
            table = Table(show_header=True, header_style="menu_header")
            table.add_column("#", style="dim")
            table.add_column("Name")
            table.add_column("Serial")
            table.add_column("Type")

            for i, device in enumerate(devices):
                table.add_row(
                    str(i + 1), device["name"], device["serial"], device["type"]
                )

            console.print(table)

            # Prompt for selection
            selection = Prompt.ask(
                "[menu_header]Select a device[/menu_header]",
                choices=[str(i + 1) for i in range(len(devices))],
                default="1",
            )
            selected_device = devices[int(selection) - 1]
        else:
            for i, device in enumerate(devices):
                pass

            # Prompt for selection
            while True:
                try:
                    selection = input("Select a device (enter number): ")
                    index = int(selection) - 1
                    if 0 <= index < len(devices):
                        selected_device = devices[index]
                        break
                except ValueError:
                    pass

        # Set the selected device
        self.actron_serial = selected_device["serial"]
        self.actron_system_id = selected_device.get("id", "")
        _LOGGER.info(
            "Using device: %s with serial number %s and ID %s",
            selected_device["name"],
            self.actron_serial,
            self.actron_system_id,
        )

        return selected_device

    async def get_ac_status(self, serial: str | None = None) -> dict[str, Any]:
        """Get the current status of the AC system."""
        serial = serial or self.actron_serial
        if not serial:
            msg = "No serial number available. Call get_devices() first."
            raise ValueError(msg)

        url = f"{API_URL}/api/v0/client/ac-systems/status/latest?serial={serial}"
        _LOGGER.info("Fetching AC status")
        return await self._make_request("GET", url)

    async def get_ac_events(
        self,
        serial: str | None = None,
        event_id: str | None = None,
        newer: bool = True,
    ) -> dict[str, Any]:
        """Get AC system events."""
        serial = serial or self.actron_serial
        if not serial:
            msg = "No serial number available. Call get_devices() first."
            raise ValueError(msg)

        if event_id:
            # Replace | with % for API requests
            event_id = event_id.replace("|", "%")
            if newer:
                url = f"{API_URL}/api/v0/client/ac-systems/events/newer?serial={serial}&newerThanEventId={event_id}"
            else:
                url = f"{API_URL}/api/v0/client/ac-systems/events/older?serial={serial}&olderThanEventId={event_id}"
        else:
            url = f"{API_URL}/api/v0/client/ac-systems/events/latest?serial={serial}"

        _LOGGER.info("Fetching AC events")
        return await self._make_request("GET", url)

    async def send_command(
        self, command: dict[str, Any], serial: str | None = None
    ) -> dict[str, Any]:
        """Send a command to the AC system."""
        serial = serial or self.actron_serial
        if not serial:
            msg = "No serial number available. Call get_devices() first."
            raise ValueError(msg)

        url = f"{API_URL}/api/v0/client/ac-systems/cmds/send?serial={serial}"
        _LOGGER.info("Sending command: %s", json.dumps(command, indent=2))

        return await self._make_request("POST", url, json=command)

    async def set_climate_mode(self, mode: str) -> dict[str, Any]:
        """Set the climate mode."""
        command = {
            "command": {
                "UserAirconSettings.isOn": True,
                "UserAirconSettings.Mode": mode,
                "type": "set-settings",
            }
        }
        return await self.send_command(command)

    async def set_fan_mode(self, mode: str, continuous: bool = False) -> dict[str, Any]:
        """Set the fan mode."""
        # Format mode
        if continuous:
            if "+" not in mode and "-" not in mode:
                mode = f"{mode}+CONT"
        else:
            # Strip any continuous suffix
            mode = mode.split("+")[0].split("-")[0]

        command = {
            "command": {"UserAirconSettings.FanMode": mode, "type": "set-settings"}
        }
        return await self.send_command(command)

    async def set_temperature(
        self, temperature: float, is_cooling: bool = True
    ) -> dict[str, Any]:
        """Set the temperature."""
        temp_key = (
            "UserAirconSettings.TemperatureSetpoint_Cool_oC"
            if is_cooling
            else "UserAirconSettings.TemperatureSetpoint_Heat_oC"
        )
        command = {"command": {temp_key: temperature, "type": "set-settings"}}
        return await self.send_command(command)

    async def set_zone_state(self, zone_index: int, enable: bool) -> dict[str, Any]:
        """Set the state of a specific zone."""
        command = {
            "command": {
                f"UserAirconSettings.EnabledZones[{zone_index}]": enable,
                "type": "set-settings",
            }
        }
        return await self.send_command(command)

    async def set_zone_temperature(
        self,
        zone_index: int,
        temperature: float | None = None,
        target_cool: float | None = None,
        target_heat: float | None = None,
    ) -> dict[str, Any]:
        """Set zone temperature."""
        if temperature is not None:
            command = {
                "command": {
                    f"RemoteZoneInfo[{zone_index}].TemperatureSetpoint_oC": temperature,
                    "type": "set-settings",
                }
            }
            return await self.send_command(command)
        if target_cool is not None and target_heat is not None:
            # Send cooling command first
            cool_command = {
                "command": {
                    f"RemoteZoneInfo[{zone_index}].TemperatureSetpoint_Cool_oC": target_cool,
                    "type": "set-settings",
                }
            }
            await self.send_command(cool_command)

            # Then send heating command
            heat_command = {
                "command": {
                    f"RemoteZoneInfo[{zone_index}].TemperatureSetpoint_Heat_oC": target_heat,
                    "type": "set-settings",
                }
            }
            return await self.send_command(heat_command)
        msg = "Must provide either temperature or both target_cool and target_heat"
        raise ValueError(msg)

    async def turn_on(self) -> dict[str, Any]:
        """Turn the AC system on."""
        command = {"command": {"UserAirconSettings.isOn": True, "type": "set-settings"}}
        return await self.send_command(command)

    async def turn_off(self) -> dict[str, Any]:
        """Turn the AC system off."""
        command = {
            "command": {"UserAirconSettings.isOn": False, "type": "set-settings"}
        }
        return await self.send_command(command)

    # Helper method to pretty print JSON responses
    def pretty_print(self, data: dict | list | str) -> None:
        """Pretty print API response data using Rich if available."""
        if RICH_AVAILABLE:
            if isinstance(data, (dict, list)):
                console.print(
                    Panel(
                        Pretty(data, indent_guides=True, expand_all=True),
                        title="API Response",
                        border_style="panel.border",
                        padding=(1, 2),
                        title_align="center",
                    )
                )
            else:
                console.print(str(data), style="info")
        # Fallback to standard printing
        elif isinstance(data, (dict, list)):
            pass
        else:
            pass


async def interactive_session(explorer: ActronNeoExplorer) -> None:
    """Run an interactive session with the explorer."""
    try:
        if RICH_AVAILABLE:
            console.print(
                Panel(
                    "Welcome to the ActronAir Neo API Explorer",
                    title="Device Discovery",
                    border_style="panel.border",
                    title_align="center",
                    subtitle="Finding your connected AC systems",
                    subtitle_align="center",
                    width=70,
                )
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[info]Fetching available devices from your account..."),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching...", total=None)
                devices = await explorer.get_devices()
                progress.update(task, completed=True)

            if not devices:
                console.print(
                    "[error]No devices found in your account. Please check your credentials.[/error]"
                )
                return

            console.print(f"[success]✓ Found {len(devices)} device(s)[/success]")
        else:
            devices = await explorer.get_devices()

            if not devices:
                return

        # Set default device if there's only one
        if len(devices) == 1:
            explorer.actron_serial = devices[0]["serial"]
            explorer.actron_system_id = devices[0].get("id", "")

            if RICH_AVAILABLE:
                device_panel = Panel(
                    f"Name: [highlight]{devices[0]['name']}[/highlight]\n"
                    f"Serial: [info]{explorer.actron_serial}[/info]\n"
                    f"Type: {devices[0].get('type', 'Unknown')}",
                    title="Using the only available device",
                    border_style="panel.border",
                    padding=(1, 2),
                )
                console.print(device_panel)
            else:
                pass

        # If multiple devices, let user select one
        elif RICH_AVAILABLE:
            # Create a table for device selection
            table = Table(
                title="Available Devices", box=ROUNDED, border_style="panel.border"
            )
            table.add_column("ID", style="menu_item", justify="center")
            table.add_column("Name", style="title")
            table.add_column("Serial", style="info")
            table.add_column("Type", style="menu_desc")

            for i, device in enumerate(devices):
                table.add_row(
                    f"[{i}]",
                    device["name"],
                    device["serial"],
                    device.get("type", "Unknown"),
                )

            console.print(table)

            # Device selection with rich prompt
            console.print("\n[title]Please select your ActronAir device:[/title]")

            # Create styled choices for selection
            choices = {}
            for i, device in enumerate(devices):
                choices[str(i)] = (
                    f"[menu_item]{device['name']}[/menu_item] ([info]{device['serial']}[/info])"
                )

            # Use Rich prompt with styled options
            idx_str = Prompt.ask(
                "Select device", choices=list(choices.keys()), default="0"
            )

            try:
                idx = int(idx_str)
                if 0 <= idx < len(devices):
                    explorer.actron_serial = devices[idx]["serial"]
                    explorer.actron_system_id = devices[idx].get("id", "")

                    # Show selection confirmation with a panel
                    device_panel = Panel(
                        f"[highlight]Name:[/highlight] {devices[idx]['name']}\n"
                        f"[highlight]Serial:[/highlight] [info]{explorer.actron_serial}[/info]\n"
                        f"[highlight]Type:[/highlight] {devices[idx].get('type', 'Unknown')}",
                        title="✓ Selected Device",
                        border_style="success",
                        padding=(1, 2),
                        width=60,
                    )
                    console.print(device_panel)
                else:
                    console.print(
                        Panel(
                            f"[error]Invalid selection. Please enter a number between 0 and {len(devices) - 1}.[/error]",
                            title="Selection Error",
                            border_style="error",
                        )
                    )
            except ValueError:
                console.print(
                    Panel(
                        "[error]Please enter a valid number.[/error]",
                        title="Input Error",
                        border_style="error",
                    )
                )
        else:
            for i, device in enumerate(devices):
                if (
                    i < len(devices) - 1
                ):  # Add separator between devices except after the last one
                    pass

            while True:
                try:
                    idx = int(input(f"\nSelect a device (0-{len(devices) - 1}): "))
                    if 0 <= idx < len(devices):
                        explorer.actron_serial = devices[idx]["serial"]
                        explorer.actron_system_id = devices[idx].get("id", "")
                        break
                except ValueError:
                    pass
    except Exception:
        return

    # Main interactive loop
    while True:
        if RICH_AVAILABLE:
            # Create a beautiful menu with Rich
            menu = Panel(
                """
[menu_header]Status & Information:[/menu_header]
  [menu_item]1.[/menu_item] [highlight]Get AC Status[/highlight]      - View current AC system status
  [menu_item]2.[/menu_item] [highlight]Get AC Events[/highlight]     - Retrieve system events & history

[menu_header]Basic Controls:[/menu_header]
  [menu_item]3.[/menu_item] [highlight]Turn AC On[/highlight]        - Power on the AC system
  [menu_item]4.[/menu_item] [highlight]Turn AC Off[/highlight]       - Power off the AC system
  [menu_item]5.[/menu_item] [highlight]Set Climate Mode[/highlight]  - Change between COOL, HEAT, FAN, AUTO
  [menu_item]6.[/menu_item] [highlight]Set Fan Mode[/highlight]      - Change fan speed & continuous operation

[menu_header]Advanced Controls:[/menu_header]
  [menu_item]7.[/menu_item] [highlight]Set Temperature[/highlight]   - Adjust temperature setpoint
  [menu_item]8.[/menu_item] [highlight]Control Zone[/highlight]      - Enable/disable individual zones
  [menu_item]9.[/menu_item] [highlight]Send Custom Command[/highlight] - Send raw JSON commands

[menu_header]Diagnostics & Tools:[/menu_header]
  [menu_item]D.[/menu_item] [highlight]Generate Diagnostics[/highlight] - Create diagnostics.md for system

  [menu_item]0.[/menu_item] [error]Exit[/error]             - Quit the API Explorer
                """,
                title="ActronAir Neo API Explorer",
                title_align="center",
                border_style="panel.border",
                padding=(1, 2),
                width=70,
            )
            console.print(menu)
            choice = Prompt.ask(
                "Enter command",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "d", "D"],
                default="1",
            )
        else:
            choice = input("\nEnter command (0-9, D): ")

        try:
            if choice == "1":
                response = await explorer.get_ac_status()
                explorer.pretty_print(response)

                # Save to file option
                if input("\nSave this response to file? (y/n): ").lower() == "y":
                    filename = (
                        input("Enter filename (default: ac_status.json): ")
                        or "ac_status.json"
                    )
                    await save_response_to_file(response, filename)

            elif choice == "2":
                event_choice = input("\nSelect option (1-3): ")

                try:
                    if event_choice == "1":
                        response = await explorer.get_ac_events()
                    elif event_choice in ["2", "3"]:
                        event_id = input("Enter event ID: ")
                        if not event_id:
                            continue

                        response = await explorer.get_ac_events(
                            event_id=event_id, newer=(event_choice == "2")
                        )
                    else:
                        continue

                except Exception:
                    continue

                explorer.pretty_print(response)

                # Save to file option
                if input("\nSave this response to file? (y/n): ").lower() == "y":
                    filename = (
                        input("Enter filename (default: ac_events.json): ")
                        or "ac_events.json"
                    )
                    await save_response_to_file(response, filename)

            elif choice == "3":
                try:
                    response = await explorer.turn_on()
                    explorer.pretty_print(response)

                    # Save to file option
                    if input("\nSave this response to file? (y/n): ").lower() == "y":
                        filename = (
                            input("Enter filename (default: turn_on_response.json): ")
                            or "turn_on_response.json"
                        )
                        await save_response_to_file(response, filename)
                except Exception:
                    pass

            elif choice == "4":
                try:
                    response = await explorer.turn_off()
                    explorer.pretty_print(response)

                    # Save to file option
                    if input("\nSave this response to file? (y/n): ").lower() == "y":
                        filename = (
                            input("Enter filename (default: turn_off_response.json): ")
                            or "turn_off_response.json"
                        )
                        await save_response_to_file(response, filename)
                except Exception:
                    pass

            elif choice == "5":
                mode = input("\nEnter mode: ").upper()

                if mode in ["AUTO", "COOL", "HEAT", "FAN"]:
                    try:
                        response = await explorer.set_climate_mode(mode)
                        explorer.pretty_print(response)

                        # Save to file option
                        if (
                            input("\nSave this response to file? (y/n): ").lower()
                            == "y"
                        ):
                            filename = (
                                input(
                                    "Enter filename (default: climate_mode_response.json): "
                                )
                                or "climate_mode_response.json"
                            )
                            await save_response_to_file(response, filename)
                    except Exception:
                        pass
                else:
                    pass

            elif choice == "6":
                mode = input("\nEnter fan mode: ").upper()
                continuous = (
                    input("Enable continuous fan operation? (y/n): ").lower() == "y"
                )

                if mode in ["AUTO", "LOW", "MED", "HIGH"]:
                    try:
                        response = await explorer.set_fan_mode(mode, continuous)
                        explorer.pretty_print(response)

                        # Save to file option
                        if (
                            input("\nSave this response to file? (y/n): ").lower()
                            == "y"
                        ):
                            filename = (
                                input(
                                    "Enter filename (default: fan_mode_response.json): "
                                )
                                or "fan_mode_response.json"
                            )
                            await save_response_to_file(response, filename)
                    except Exception:
                        pass
                else:
                    pass

            elif choice == "7":
                try:
                    temp_input = input("Enter temperature (°C): ")
                    if not temp_input:
                        continue

                    temp = float(temp_input)
                    if temp < 16 or temp > 30:
                        continue

                    mode = input("Is this for cooling mode? (y/n): ").lower()
                    is_cooling = mode == "y"

                    response = await explorer.set_temperature(temp, is_cooling)
                    explorer.pretty_print(response)

                    # Save to file option
                    if input("\nSave this response to file? (y/n): ").lower() == "y":
                        filename = (
                            input(
                                "Enter filename (default: temperature_response.json): "
                            )
                            or "temperature_response.json"
                        )
                        await save_response_to_file(response, filename)
                except ValueError:
                    pass
                except Exception:
                    pass

            elif choice == "8":
                try:
                    zone_input = input("Enter zone index (0-7): ")
                    if not zone_input:
                        continue

                    zone = int(zone_input)
                    if not 0 <= zone <= 7:
                        continue

                    action = input("Enable or disable zone? (e/d): ").lower()
                    if action not in ["e", "d"]:
                        continue

                    enable = action == "e"
                    response = await explorer.set_zone_state(zone, enable)
                    explorer.pretty_print(response)

                    # Save to file option
                    if input("\nSave this response to file? (y/n): ").lower() == "y":
                        filename = (
                            input(
                                "Enter filename (default: zone_control_response.json): "
                            )
                            or "zone_control_response.json"
                        )
                        await save_response_to_file(response, filename)
                except ValueError:
                    pass
                except Exception:
                    pass

            elif choice == "9":
                command_str = input("\nEnter JSON command: ")
                if not command_str:
                    continue

                try:
                    command = json.loads(command_str)
                    response = await explorer.send_command(command)
                    explorer.pretty_print(response)

                    # Save to file option
                    if input("\nSave this response to file? (y/n): ").lower() == "y":
                        filename = (
                            input("Enter filename (default: custom_command.json): ")
                            or f"custom_command_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        )
                        await save_response_to_file(response, filename)
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass

            elif choice.lower() == "d":
                with contextlib.suppress(Exception):
                    await generate_diagnostics_file(explorer)

            # Exit
            elif choice == "0":
                break

            # Invalid choice
            else:
                pass

        except KeyboardInterrupt:
            break
        except Exception:
            pass


async def main() -> None:
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="ActronAir Neo API Explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "This tool allows you to explore the ActronAir Neo cloud API.\n"
            "Credentials are used for authentication only and are never stored.\n"
            "For more information, see README_EXPLORER.md\n"
        ),
    )
    parser.add_argument("-u", "--username", help="ActronAir Neo account username")
    parser.add_argument("-p", "--password", help="ActronAir Neo account password")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "-t", "--token-file", help="Path to token file (default: actron_token.json)"
    )
    parser.add_argument(
        "--docs", action="store_true", help="Show API documentation structure"
    )
    parser.add_argument(
        "-g",
        "--generate-diagnostics",
        action="store_true",
        help="Generate diagnostics.md file based on system information",
    )

    args = parser.parse_args()

    # Show documentation if requested
    if args.docs:
        docs_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "actron_api_structure.md"
        )
        if os.path.exists(docs_path):
            try:
                if RICH_AVAILABLE:
                    # Display a header for the documentation
                    console.print(
                        Panel(
                            "[title]ActronAir Neo API Documentation[/title]\n\n"
                            "This documentation outlines the structure and endpoints of the ActronAir Neo API.",
                            title="Documentation",
                            border_style="panel.border",
                            padding=(1, 2),
                            width=100,
                        )
                    )

                    # Read and display the markdown content
                    with open(docs_path) as f:
                        md_content = f.read()
                        console.print(Markdown(md_content))

                    # Add a footer
                    console.print(
                        Panel(
                            "For more details on using this explorer tool, see [highlight]README_EXPLORER.md[/highlight]",
                            border_style="panel.border",
                            padding=(1, 1),
                        )
                    )
                else:
                    with open(docs_path) as f:
                        pass
            except Exception as e:
                if RICH_AVAILABLE:
                    console.print(
                        Panel(
                            f"[error]Failed to read documentation: {e}[/error]",
                            title="Error",
                            border_style="error",
                        )
                    )
                else:
                    pass
        elif RICH_AVAILABLE:
            console.print(
                Panel(
                    "[warning]Documentation file not found![/warning]\n\n"
                    "Please see [highlight]README_EXPLORER.md[/highlight] for more information about this tool.",
                    title="Documentation Not Found",
                    border_style="warning",
                    padding=(1, 2),
                )
            )
        else:
            pass
        return

    # Display welcome message
    if RICH_AVAILABLE:
        # Create a beautiful welcome header
        welcome_panel = Panel(
            """[title]Welcome to the ActronAir Neo API Explorer[/title]

This tool allows you to [highlight]explore the ActronAir Neo cloud API responses[/highlight].
You can view device status, send commands, and save responses for documentation.

[info]Note: Your credentials are only used for authentication and are never stored.[/info]
            """,
            title="ActronAir Neo Explorer",
            subtitle="Version 1.0",
            border_style="panel.border",
            padding=(1, 2),
            title_align="center",
            subtitle_align="center",
            width=70,
        )
        console.print(welcome_panel)
    else:
        pass

    # Prompt for credentials if not provided
    username = args.username
    password = args.password

    if not username:
        if RICH_AVAILABLE:
            username = Prompt.ask(
                "[info]Enter ActronAir Neo username[/info]", console=console
            )
        else:
            username = input("Enter ActronAir Neo username: ")

    if not password:
        if RICH_AVAILABLE:
            console.print("[info]Enter ActronAir Neo password[/info]", end="")
        password = getpass.getpass(
            "" if RICH_AVAILABLE else "Enter ActronAir Neo password: "
        )

    if not username or not password:
        if RICH_AVAILABLE:
            console.print(
                Panel(
                    "[error]Username and password are required[/error]",
                    title="Error",
                    border_style="error",
                )
            )
        else:
            pass
        return

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[info]Initializing connection to ActronAir Neo API...[/info]"),
            console=console,
        ) as progress:
            task = progress.add_task("Connecting...", total=None)
            # Keep the spinner visible for a moment
            await asyncio.sleep(0.5)
    else:
        pass

    # Create and initialize explorer
    async with ActronNeoExplorer(
        username=username,
        password=password,
        token_file_path=args.token_file,
        debug=args.debug,
    ) as explorer:
        try:
            await explorer.initialize()

            if RICH_AVAILABLE:
                console.print(
                    Panel(
                        "[success]Successfully connected to the ActronAir Neo cloud services![/success]",
                        title="Authentication Success",
                        border_style="success",
                        padding=(1, 2),
                    )
                )
            else:
                pass

            # Handle the generate-diagnostics flag
            if args.generate_diagnostics:
                if RICH_AVAILABLE:
                    console.print(
                        "\n[info]Generating diagnostics.md file based on your system...[/info]"
                    )
                    with Progress(
                        SpinnerColumn(),
                        TextColumn(
                            "[info]Fetching system information and generating report...[/info]"
                        ),
                        console=console,
                    ) as progress:
                        task = progress.add_task("Generating...", total=None)
                        diagnostics_path = await generate_diagnostics_file(explorer)
                        progress.update(task, completed=True)

                    console.print(
                        Panel(
                            f"Diagnostics file has been created at:\n[highlight]{diagnostics_path}[/highlight]",
                            title="Diagnostics Generated Successfully",
                            border_style="success",
                            padding=(1, 2),
                        )
                    )

                    if Confirm.ask("Would you like to run interactive mode now?"):
                        await interactive_session(explorer)
                    else:
                        console.print("[info]Exiting...[/info]")
                else:
                    diagnostics_path = await generate_diagnostics_file(explorer)

                    run_interactive = (
                        input(
                            "\nWould you like to run interactive mode now? (y/n): "
                        ).lower()
                        == "y"
                    )
                    if run_interactive:
                        await interactive_session(explorer)
                    else:
                        pass
            else:
                await interactive_session(explorer)
        except AuthenticationError as e:
            if RICH_AVAILABLE:
                console.print(
                    Panel(
                        f"[error]Authentication failed: {e}[/error]\n\n"
                        "[title]Troubleshooting Tips:[/title]\n"
                        "  • [info]Check your username and password[/info]\n"
                        "  • [info]If you recently changed your password, delete the token file and try again[/info]\n"
                        "  • [info]Try again in a few minutes if too many auth attempts have been made[/info]",
                        title="Authentication Error",
                        border_style="error",
                        padding=(1, 2),
                    )
                )
            else:
                pass
        except ApiError as e:
            if RICH_AVAILABLE:
                error_msg = (
                    "\n[warning]Rate limit exceeded. Please wait a few minutes and try again.[/warning]"
                    if hasattr(e, "status_code") and e.status_code == 429
                    else ""
                )
                console.print(
                    Panel(
                        f"[error]API Error: {e}[/error]{error_msg}",
                        title="API Communication Error",
                        border_style="error",
                        padding=(1, 2),
                    )
                )
            elif hasattr(e, "status_code") and e.status_code == 429:
                pass
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(
                    Panel(
                        f"[error]An error occurred: {e}[/error]",
                        title="Unexpected Error",
                        border_style="error",
                        padding=(1, 2),
                    )
                )
            else:
                pass

        if RICH_AVAILABLE:
            console.print(
                Panel(
                    "Thank you for using the ActronAir Neo API Explorer\n"
                    "[info]Goodbye![/info]",
                    title="Session Complete",
                    border_style="panel.border",
                    padding=(1, 2),
                    width=50,
                )
            )
        else:
            pass


async def save_response_to_file(response: dict, filename: str) -> None:
    """
    Save API response to a file in a dedicated responses directory.

    Args:
        response: The API response data to save
        filename: The name of the file to save

    """
    try:
        # Create a responses directory if it doesn't exist
        responses_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "responses"
        )
        if not os.path.exists(responses_dir):
            os.makedirs(responses_dir)
            if RICH_AVAILABLE:
                console.print(
                    f"[info]Created responses directory at {responses_dir}[/info]"
                )
            else:
                pass

        # Add timestamp to filename for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name, ext = os.path.splitext(filename)
        if not ext:  # Default to .json if no extension provided
            ext = ".json"
        timestamped_filename = f"{base_name}_{timestamp}{ext}"

        # Prepare the full file path
        filepath = os.path.join(responses_dir, timestamped_filename)

        # Save the response as JSON
        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(response, indent=2))

        if RICH_AVAILABLE:
            console.print(
                Panel(
                    f"File: [highlight]{timestamped_filename}[/highlight]\n"
                    f"Path: [info]{filepath}[/info]",
                    title="Response Saved Successfully",
                    border_style="success",
                    padding=(1, 2),
                )
            )
        else:
            pass
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(
                Panel(
                    f"[error]{e!s}[/error]",
                    title="Error Saving Response",
                    border_style="error",
                    padding=(1, 2),
                )
            )
        else:
            pass


async def generate_diagnostics_file(
    explorer: ActronNeoExplorer, output_path: str | None = None
) -> str:
    """
    Generate a diagnostics.md file with system-specific information.

    Args:
        explorer: Initialized ActronNeoExplorer instance
        output_path: Optional path where to save the file (default: project root)

    Returns:
        Path to the generated file

    """
    try:
        # Fetch required data from API
        status_data = await explorer.get_ac_status()

        # Extract relevant system information
        last_known_state = status_data.get("lastKnownState", {})
        aircon_system = last_known_state.get("AirconSystem", {})
        indoor_unit = aircon_system.get("IndoorUnit", {})
        outdoor_unit = aircon_system.get("OutdoorUnit", {})
        master_info = last_known_state.get("MasterInfo", {})
        peripherals = aircon_system.get("Peripherals", [])
        remote_zone_info = last_known_state.get("RemoteZoneInfo", [])
        user_settings = last_known_state.get("UserAirconSettings", {})

        # Extract controller information
        controller_model = aircon_system.get("MasterWCModel", "Unknown")
        controller_serial = aircon_system.get("MasterSerial", "Unknown")
        firmware_version = aircon_system.get("MasterWCFirmwareVersion", "Unknown")

        # Extract indoor/outdoor unit information
        indoor_model = indoor_unit.get("NV_ModelNumber", "Unknown")
        indoor_serial = indoor_unit.get("SerialNumber", "Unknown")
        indoor_fw = indoor_unit.get("IndoorFW", "Unknown")
        outdoor_family = outdoor_unit.get("Family", "Unknown")
        outdoor_unit.get("ModelNumber", "Unknown")
        outdoor_serial = outdoor_unit.get("SerialNumber", "Unknown")
        outdoor_fw = outdoor_unit.get("SoftwareVersion", "Unknown")

        # Extract zone sensors information
        wireless_sensors = []
        wired_sensors = []

        # Process sensors for each zone
        zone_data = {}
        for i, zone in enumerate(remote_zone_info):
            if i >= 8:  # Max 8 zones
                break

            zone_id = f"zone_{i + 1}"
            zone_name = zone.get("NV_Title", f"Zone {i + 1}")

            if not zone.get("NV_Exists", False):
                continue

            # Add to zone data
            zone_data[zone_id] = {
                "name": zone_name,
                "temp": zone.get("LiveTemp_oC", "Unknown"),
                "humidity": zone.get("LiveHumidity_pc", "Unknown"),
                "enabled": user_settings.get("EnabledZones", [])[i]
                if i < len(user_settings.get("EnabledZones", []))
                else False,
            }

            # Find matching sensor in peripherals
            sensor_found = False
            for peripheral in peripherals:
                if peripheral.get("ZoneAssignment", []) == [i + 1]:
                    sensor_found = True
                    sensor_type = peripheral.get("DeviceType", "Unknown")
                    battery_level = peripheral.get("RemainingBatteryCapacity_pc")

                    peripheral_data = {
                        "zone_id": zone_id,
                        "zone_name": zone_name,
                        "type": sensor_type,
                        "serial": peripheral.get("SerialNumber", "Unknown"),
                        "battery_level": battery_level,
                        "signal_strength": peripheral.get("RSSI", {}).get(
                            "Local", "Unknown"
                        ),
                        "connection_state": peripheral.get(
                            "ConnectionState", "Unknown"
                        ),
                        "temperature": peripheral.get("SensorInputs", {})
                        .get("Thermistors", {})
                        .get("Ambient_oC", "Unknown"),
                        "humidity": peripheral.get("SensorInputs", {})
                        .get("SHTC1", {})
                        .get("RelativeHumidity_pc", "Unknown"),
                    }

                    # If it has battery level, it's a wireless sensor
                    if battery_level is not None:
                        wireless_sensors.append(peripheral_data)
                    else:
                        wired_sensors.append(peripheral_data)

                    # Update zone data with sensor info
                    zone_data[zone_id]["sensor_type"] = sensor_type
                    zone_data[zone_id]["sensor_serial"] = peripheral.get(
                        "SerialNumber", "Unknown"
                    )
                    zone_data[zone_id]["sensor_battery"] = battery_level
                    zone_data[zone_id]["wireless"] = battery_level is not None
                    break

            # If no sensor found for zone, check if main controller is the sensor
            if not sensor_found:
                for sensor in aircon_system.get("Sensors", []):
                    if sensor.get("Designator") == "C1" and sensor.get(
                        "Detected", False
                    ):
                        zone_data[zone_id]["sensor_type"] = "Main Controller"
                        zone_data[zone_id]["wireless"] = False
                        break

        # Generate markdown content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        markdown_content = f"""# ActronAir Neo Integration Diagnostics Guide

This document provides information to help troubleshoot and diagnose issues with the ActronAir Neo integration for Home Assistant, particularly focusing on sensor detection, wired vs. wireless sensors, and data retrieval.

*Generated on: {timestamp}*

## System Identification

The following hardware information was detected from your ActronAir system:

### Controller Information
* **Wall Controller Model**: {controller_model}
* **Serial Number**: {controller_serial}
* **Firmware Version**: {firmware_version}

### HVAC Equipment
* **Indoor Unit Model**: {indoor_model}
* **Indoor Unit Serial**: {indoor_serial}
* **Indoor Unit Firmware**: {indoor_fw}
* **Outdoor Unit Family**: {outdoor_family}
* **Outdoor Unit Serial**: {outdoor_serial}
* **Outdoor Unit Firmware**: {outdoor_fw}

## Zone and Sensor Detection

### Configured Zones
"""

        # Add zone details
        if zone_data:
            for zone_id, zone in zone_data.items():
                markdown_content += f"""
#### {zone["name"]}
* **Temperature**: {zone["temp"]}°C
* **Humidity**: {zone["humidity"]}%
* **Enabled**: {"Yes" if zone["enabled"] else "No"}
"""
                if "wireless" in zone:
                    markdown_content += f"* **Sensor Type**: {'Wireless' if zone['wireless'] else 'Wired'}\n"
                if "sensor_type" in zone:
                    markdown_content += f"* **Sensor Model**: {zone['sensor_type']}\n"
                if "sensor_serial" in zone:
                    markdown_content += (
                        f"* **Sensor Serial**: {zone['sensor_serial']}\n"
                    )
                if zone.get("sensor_battery") is not None:
                    markdown_content += (
                        f"* **Battery Level**: {zone['sensor_battery']}%\n"
                    )
        else:
            markdown_content += "\nNo zones configured or detected.\n"

        # Add section for wireless sensors
        markdown_content += """
### Wireless Sensors

The following wireless sensors were detected in your system:
"""
        if wireless_sensors:
            for sensor in wireless_sensors:
                markdown_content += f"""
* **{sensor["zone_name"]}**:
  - Type: {sensor["type"]}
  - Serial: {sensor["serial"]}
  - Battery Level: {sensor["battery_level"]}%
  - Signal Strength: {sensor["signal_strength"]}
  - Connection State: {sensor["connection_state"]}
"""
        else:
            markdown_content += "\nNo wireless sensors detected in your system.\n"

        # Add section for wired sensors
        markdown_content += """
### Wired Sensors

The following wired sensors were detected in your system:
"""
        if wired_sensors:
            for sensor in wired_sensors:
                markdown_content += f"""
* **{sensor["zone_name"]}**:
  - Type: {sensor["type"]}
  - Connection State: {sensor["connection_state"]}
"""
        else:
            markdown_content += "\nNo wired sensors detected in your system apart from the main controller.\n"

        # Add system capabilities section
        fan_modes = user_settings.get("FanMode", "LOW").split("+")[0]
        climate_mode = user_settings.get("Mode", "COOL")
        fan_continuous = "+CONT" in user_settings.get("FanMode", "")

        # Main controller sensor info
        main_temp = master_info.get("LiveTemp_oC", "Unknown")
        main_humidity = master_info.get("LiveHumidity_pc", "Unknown")

        markdown_content += f"""
## System Capabilities and Status

Based on the retrieved information, your system has the following capabilities and current settings:

* **Controller Temperature Sensor**: {main_temp}°C
* **Controller Humidity Sensor**: {main_humidity}%
* **Model Type**: {outdoor_family}
* **Current Mode**: {climate_mode}
* **Fan Mode**: {fan_modes}{" (Continuous)" if fan_continuous else ""}
* **System On**: {"Yes" if user_settings.get("isOn", False) else "No"}

## Integration Troubleshooting

### Sensor Type Detection

The ActronAir Neo Home Assistant integration detects sensors as follows:

1. **Wireless Sensors** will have:
   * Battery level (RemainingBatteryCapacity_pc)
   * Signal strength (Signal_of3)
   * Last connection time
   * Connection state

2. **Wired Sensors** will have:
   * No battery information
   * No signal strength information
   * Will be directly connected to the controller

### Battery Information
For wireless sensors, battery level is reported as a percentage. Wired sensors do not report battery level as they receive power from the unit.

## Debugging Common Issues

### Sensor Not Appearing
If a zone sensor isn't appearing in Home Assistant:

1. Verify the sensor is correctly paired with the ActronAir system
2. Check the API response in Raw JSON to confirm the sensor appears in the "Peripherals" list
3. Verify the sensor has a valid "ZoneAssignment" value that corresponds to an existing zone

### Battery Information Not Showing
For wireless sensors:

1. Confirm the sensor appears in the "Peripherals" list in API data
2. Check if "RemainingBatteryCapacity_pc" is present in the peripheral data
3. If present but not showing, check logs for decoding errors

### Missing Temperature Data
If temperature readings are missing:

1. Check if the sensor is correctly assigned to a zone
2. Verify the sensor is marked as "Connected" in the connection state
3. For wireless sensors, check battery level - low battery can cause intermittent readings

## Integration Data Details

The integration parses zone data in the following structure:

```python
zone_data = {{
    "name": zone.get("NV_Title", f"Zone {{i+1}}"),
    "temp": zone.get("LiveTemp_oC"),
    "humidity": zone.get("LiveHumidity_pc"),
    "is_enabled": parsed_data["main"]["EnabledZones"][i],
    "capabilities": capabilities,
}}

# For wireless sensors, additional data is added:
peripheral_data = {{
    "battery_level": peripheral.get("RemainingBatteryCapacity_pc"),
    "signal_strength": peripheral.get("Signal_of3"),
    "peripheral_type": peripheral.get("DeviceType"),
    "last_connection": peripheral.get("LastConnectionTime"),
    "connection_state": peripheral.get("ConnectionState"),
}}
```

When troubleshooting, verify all these fields exist in the diagnostic data.
"""

        # Determine output file path
        if output_path is None:
            # Default to project root (two directories up from the script)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            output_path = os.path.join(project_root, "diagnostics.md")

        # Write the markdown file
        async with aiofiles.open(output_path, "w") as f:
            await f.write(markdown_content)

        return output_path

    except Exception as e:
        _LOGGER.error("Error generating diagnostics file: %s", str(e), exc_info=True)
        msg = f"Failed to generate diagnostics file: {e!s}"
        raise ValueError(msg)


if __name__ == "__main__":
    asyncio.run(main())

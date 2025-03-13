"""Coordinator for the ActronAir Neo integration."""

import asyncio
from datetime import timedelta
import datetime
from typing import Any, Dict, Optional, Union
import logging

from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed  # type: ignore
from homeassistant.exceptions import ConfigEntryAuthFailed  # type: ignore
from homeassistant.components.climate.const import HVACMode  # type: ignore

from .api import ActronApi, AuthenticationError, ApiError
from .const import (
    DOMAIN,
    MAX_RETRIES,
    MAX_ZONES,
    MIN_FAN_MODE_INTERVAL,
    VALID_FAN_MODES,
    FAN_MODE_SUFFIX_CONT,
)

_LOGGER = logging.getLogger(__name__)


class ActronDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ActronAir Neo data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ActronApi,
        device_id: str,
        update_interval: int,
        enable_zone_control: bool,
    ):
        """Initialize the data coordinator.

        Args:
            hass: HomeAssistant instance
            api: ActronApi instance for API communication
            device_id: Unique identifier for the device
            update_interval: Update interval in seconds
            enable_zone_control: Whether zone control is enabled
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_id = device_id
        self.enable_zone_control = enable_zone_control
        self.last_data = None

        # Fan mode control attributes
        self._continuous_fan = False
        self._fan_mode_change_lock = asyncio.Lock()
        self._last_fan_mode_change = None
        self._min_fan_mode_interval = MIN_FAN_MODE_INTERVAL

    def validate_fan_mode(self, mode: str, continuous: bool = False) -> str:
        """Validate and format fan mode.

        Args:
            mode: The fan mode to validate (LOW, MED, HIGH, AUTO)
            continuous: Whether to add continuous suffix

        Returns:
            Validated and formatted fan mode string

        Raises:
            ValueError: If fan mode is invalid
        """
        try:
            # Get supported modes from coordinator data
            supported_modes = self.data["main"].get(
                "supported_fan_modes", ["LOW", "MED", "HIGH"]
            )

            # First strip any existing continuous suffix
            base_mode = mode.split("+")[0] if "+" in mode else mode
            base_mode = base_mode.split("-")[0] if "-" in base_mode else base_mode
            base_mode = base_mode.upper()

            # Validate against supported modes
            if base_mode not in supported_modes:
                _LOGGER.warning(
                    "Fan mode %s not supported by device. Supported modes: %s. Defaulting to LOW",
                    mode,
                    supported_modes,
                )
                base_mode = "LOW"

            # Validate against known valid modes as a safety check
            if base_mode not in VALID_FAN_MODES:
                _LOGGER.warning("Invalid fan mode %s, defaulting to LOW", mode)
                base_mode = "LOW"

            _LOGGER.debug(
                "Fan mode validation - Input: %s, Base: %s, Continuous: %s, Supported: %s",
                mode,
                base_mode,
                continuous,
                supported_modes,
            )

            return f"{base_mode}{FAN_MODE_SUFFIX_CONT}" if continuous else base_mode

        except (KeyError, AttributeError, ValueError) as err:
            _LOGGER.error(
                "Error validating fan mode '%s': %s", mode, str(err), exc_info=True
            )
            return "LOW+CONT" if continuous else "LOW"

    def _validate_fan_mode_response(
        self, requested_mode: str, continuous: bool, actual_mode: str
    ) -> bool:
        """Validate that the fan mode was set correctly.

        Args:
            requested_mode: The requested fan mode
            continuous: The requested continuous state
            actual_mode: The actual mode returned by the API

        Returns:
            bool: True if the mode was set correctly
        """
        base_requested = requested_mode.split("+")[0].split("-")[0].upper()
        base_actual = actual_mode.split("+")[0].split("-")[0].upper()

        is_continuous = "+CONT" in actual_mode

        mode_correct = base_requested == base_actual
        continuous_correct = continuous == is_continuous

        if not mode_correct:
            _LOGGER.warning(
                "Fan mode mismatch - Requested: %s, Got: %s",
                base_requested,
                base_actual,
            )

        if not continuous_correct:
            _LOGGER.warning(
                "Continuous state mismatch - Requested: %s, Got: %s",
                continuous,
                is_continuous,
            )

        return mode_correct and continuous_correct

    @property
    def continuous_fan(self) -> bool:
        """Get continuous fan state."""
        return self._continuous_fan

    @continuous_fan.setter
    def continuous_fan(self, value: bool):
        """Set continuous fan state."""
        self._continuous_fan = value

    async def set_enable_zone_control(self, enable: bool):
        """Update the enable_zone_control status."""
        self.enable_zone_control = enable
        await self.async_request_refresh()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            if not self.api.is_api_healthy():
                _LOGGER.warning("API is not healthy, using cached data")
                return self.last_data if self.last_data else {}

            _LOGGER.debug("Fetching data for device %s", self.device_id)
            status = await self.api.get_ac_status(self.device_id)
            parsed_data = await self._parse_data(status)  # Add await here
            self.last_data = parsed_data
            _LOGGER.debug("Parsed data: %s", parsed_data)
            return parsed_data
        except AuthenticationError as err:
            _LOGGER.error("Authentication error: %s", err)
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            _LOGGER.error("Error communicating with API: %s", err)
            if self.last_data:
                _LOGGER.warning("Using cached data due to API error")
                return self.last_data
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error occurred: %s", err)
            if self.last_data:
                _LOGGER.warning("Using cached data due to unexpected error")
                return self.last_data
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _parse_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the data from the API into a format suitable for the climate entity.

        Args:
            data: Raw API response data

        Returns:
            Dict containing parsed data including raw data for diagnostics

        Raises:
            UpdateFailed: If parsing fails
        """
        try:
            last_known_state = data.get("lastKnownState", {})
            user_aircon_settings = last_known_state.get("UserAirconSettings", {})
            master_info = last_known_state.get("MasterInfo", {})
            live_aircon = last_known_state.get("LiveAircon", {})
            aircon_system = last_known_state.get("AirconSystem", {})
            indoor_unit = aircon_system.get("IndoorUnit", {})
            alerts = last_known_state.get("Alerts", {})

            # Get supported modes
            supported_fan_modes = self._validate_fan_modes(
                indoor_unit.get(
                    "NV_SupportedFanModes", 0
                )  # Default to 0 if not present
            )

            # Get fan mode and check for continuous state using '+CONT'
            fan_mode = user_aircon_settings.get("FanMode", "")
            is_continuous = fan_mode.endswith("+CONT")

            # Strip the continuous suffix for clean fan_mode storage
            base_fan_mode = fan_mode.split("+")[0] if "+" in fan_mode else fan_mode
            base_fan_mode = (
                base_fan_mode.split("-")[0] if "-" in base_fan_mode else base_fan_mode
            )

            parsed_data = {
                # Store raw data for diagnostics
                "raw_data": data,
                "main": {
                    "is_on": user_aircon_settings.get("isOn", False),
                    "mode": user_aircon_settings.get("Mode", "OFF"),
                    "fan_mode": fan_mode,  # Store complete fan mode string
                    "fan_continuous": is_continuous,  # Explicit continuous state tracking
                    "base_fan_mode": base_fan_mode,  # Store base fan mode without suffix
                    "supported_fan_modes": supported_fan_modes,
                    "temp_setpoint_cool": user_aircon_settings.get(
                        "TemperatureSetpoint_Cool_oC"
                    ),
                    "temp_setpoint_heat": user_aircon_settings.get(
                        "TemperatureSetpoint_Heat_oC"
                    ),
                    "indoor_temp": master_info.get("LiveTemp_oC"),
                    "indoor_humidity": master_info.get("LiveHumidity_pc"),
                    "compressor_state": live_aircon.get("CompressorMode", "OFF"),
                    "EnabledZones": user_aircon_settings.get("EnabledZones", []),
                    "away_mode": user_aircon_settings.get("AwayMode", False),
                    "quiet_mode": user_aircon_settings.get("QuietMode", False),
                    "model": aircon_system.get("MasterWCModel"),
                    "serial_number": aircon_system.get("MasterSerial"),
                    "firmware_version": aircon_system.get("MasterWCFirmwareVersion"),
                    # Add alert statuses
                    "filter_clean_required": alerts.get("CleanFilter", False),
                    "defrosting": alerts.get("Defrosting", False),
                },
                "zones": {},
            }

            # Update continuous fan state based on actual mode
            self._continuous_fan = is_continuous

            _LOGGER.debug(
                "Fan mode status - Raw: %s, Base: %s, Continuous: %s",
                fan_mode,
                base_fan_mode,
                is_continuous,
            )

            # Parse zone data with enhanced capabilities and peripheral information
            remote_zone_info = last_known_state.get("RemoteZoneInfo", [])
            peripherals = aircon_system.get("Peripherals", [])

            for i, zone in enumerate(remote_zone_info):
                if i < MAX_ZONES:
                    zone_id = f"zone_{i+1}"

                    # Get zone capabilities including existence check
                    capabilities = self.api.get_zone_capabilities(zone)

                    if capabilities["exists"]:
                        zone_data = {
                            "name": zone.get("NV_Title", f"Zone {i+1}"),
                            "temp": zone.get("LiveTemp_oC"),
                            "humidity": zone.get("LiveHumidity_pc"),
                            "is_enabled": (
                                parsed_data["main"]["EnabledZones"][i]
                                if i < len(parsed_data["main"]["EnabledZones"])
                                else False
                            ),
                            "capabilities": capabilities,
                            # Add temperature setpoints from capabilities
                            "temp_setpoint_cool": capabilities.get("target_temp_cool"),
                            "temp_setpoint_heat": capabilities.get("target_temp_heat"),
                        }

                        # Find matching peripheral for battery info
                        for peripheral in peripherals:
                            if peripheral.get("ZoneAssignment", []) == [i + 1]:
                                peripheral_data = {
                                    "battery_level": peripheral.get(
                                        "RemainingBatteryCapacity_pc"
                                    ),
                                    "signal_strength": peripheral.get("Signal_of3"),
                                    "peripheral_type": peripheral.get("DeviceType"),
                                    "last_connection": peripheral.get(
                                        "LastConnectionTime"
                                    ),
                                    "connection_state": peripheral.get(
                                        "ConnectionState"
                                    ),
                                }
                                # Add peripheral data to zone_data
                                zone_data.update(peripheral_data)

                                # Add peripheral capabilities if present
                                if peripheral.get("ControlCapabilities"):
                                    zone_data["capabilities"].update(
                                        {
                                            "peripheral_capabilities": peripheral.get(
                                                "ControlCapabilities"
                                            )
                                        }
                                    )
                                break

                        parsed_data["zones"][zone_id] = zone_data

            return parsed_data

        except Exception as e:
            _LOGGER.error("Failed to parse API response: %s", e, exc_info=True)
            raise UpdateFailed(f"Failed to parse API response: {e}") from e

    def _validate_fan_modes(self, modes: Any) -> list[str]:
        """Validate and normalize supported fan modes.

        Note on Actron Quirks:
        - NV_SupportedFanModes is a bitmap where:
            1=LOW, 2=MED, 4=HIGH, 8=AUTO
        - Some devices omit HIGH from NV_SupportedFanModes even though
            they support it. If we detect HIGH mode in current settings,
            we add it to supported modes regardless of bitmap.
        - When in doubt, we fall back to [LOW, MED, HIGH] as safe defaults.
        """
        valid_modes = {"LOW", "MED", "HIGH", "AUTO"}
        default_modes = ["LOW", "MED", "HIGH"]

        try:
            _LOGGER.debug(
                "Starting fan mode validation with input: %s (type: %s)",
                modes,
                type(modes),
            )

            # Handle integer case - API returns a bitmap
            if isinstance(modes, int):
                # Binary mapping: 1=LOW, 2=MED, 4=HIGH, 8=AUTO (bitmap)
                _LOGGER.debug(
                    "Processing bitmap value: %d (binary: %s, hex: 0x%X)",
                    modes,
                    bin(modes),
                    modes,
                )

                # Get current fan mode to check for HIGH support
                current_mode = None
                if hasattr(self, "data") and self.data is not None:
                    user_settings = (
                        self.data.get("raw_data", {})
                        .get("lastKnownState", {})
                        .get(f"<{self.device_id.upper()}>", {})
                        .get("UserAirconSettings", {})
                    )
                    current_mode = user_settings.get("FanMode", "")
                    _LOGGER.debug("Current device fan mode: %s", current_mode)
                else:
                    _LOGGER.debug("No data available yet, skipping current mode check")

                # Detailed bitmap analysis
                _LOGGER.debug("Bitmap analysis:")
                _LOGGER.debug("- LOW  (0x1): %s", bool(modes & 1))
                _LOGGER.debug("- MED  (0x2): %s", bool(modes & 2))
                _LOGGER.debug("- HIGH (0x4): %s", bool(modes & 4))
                _LOGGER.debug("- AUTO (0x8): %s", bool(modes & 8))

                # Process bitmap
                supported = []
                if modes & 1:
                    supported.append("LOW")
                    _LOGGER.debug("Added LOW mode (bit 0 set)")
                if modes & 2:
                    supported.append("MED")
                    _LOGGER.debug("Added MED mode (bit 1 set)")
                if modes & 4:
                    supported.append("HIGH")
                    _LOGGER.debug("Added HIGH mode (bit 2 set)")
                if modes & 8:
                    auto_enabled = False
                    if hasattr(self, "data") and self.data is not None:
                        indoor_unit = (
                            self.data.get("raw_data", {})
                            .get("lastKnownState", {})
                            .get(f"<{self.device_id.upper()}>", {})
                            .get("AirconSystem", {})
                            .get("IndoorUnit", {})
                        )
                        auto_enabled = indoor_unit.get("NV_AutoFanEnabled", False)
                    if auto_enabled:
                        supported.append("AUTO")
                        _LOGGER.debug("Added AUTO mode (bit 3 set and enabled)")

                # If actual mode is HIGH or device supports basic modes, use defaults
                if current_mode == "HIGH" or modes & 0x03:
                    _LOGGER.debug(
                        "Using default modes due to: Current mode=%s, Basic modes supported=%s",
                        current_mode,
                        bool(modes & 0x03),
                    )
                    return default_modes

                _LOGGER.debug(
                    "Bitmap decoding complete - Supported modes: %s", supported
                )

                if not supported:
                    _LOGGER.debug(
                        "No modes decoded from bitmap, using default modes: %s",
                        default_modes,
                    )
                    return default_modes

                return supported

            # Handle other cases
            if not modes:
                _LOGGER.debug(
                    "Empty/None input received, using default modes: %s", default_modes
                )
                return default_modes

            if isinstance(modes, str):
                _LOGGER.debug("Processing string input: %s", modes)
                modes = [m.strip().upper() for m in modes.split(",")]
                _LOGGER.debug("Parsed string into list: %s", modes)

            elif isinstance(modes, (list, tuple)):
                _LOGGER.debug("Processing list/tuple input: %s", modes)
                modes = [str(m).strip().upper() for m in modes]
                _LOGGER.debug("Normalized list values: %s", modes)

            supported = [m for m in modes if m in valid_modes]
            _LOGGER.debug(
                "Validated modes against valid set %s - Result: %s",
                valid_modes,
                supported,
            )

            if not supported:
                _LOGGER.debug("No valid modes found, using defaults: %s", default_modes)
                return default_modes

            return supported

        except Exception as err:
            _LOGGER.error(
                "Error validating fan modes: %s (input was: %s, type: %s)",
                err,
                modes,
                type(modes),
            )
            _LOGGER.debug("Returning default modes due to error: %s", default_modes)
            return default_modes

    def get_zone_peripheral(self, zone_id: str) -> Union[Dict[str, Any], None]:
        """Get peripheral data for a specific zone."""
        try:
            zone_index = int(zone_id.split("_")[1]) - 1
            peripherals = (
                self.data.get("raw_data", {})
                .get("AirconSystem", {})
                .get("Peripherals", [])
            )

            for peripheral in peripherals:
                if peripheral.get("ZoneAssignment", []) == [zone_index + 1]:
                    return peripheral

            return None
        except (KeyError, ValueError, IndexError) as ex:
            _LOGGER.error(
                "Error getting peripheral data for zone %s: %s", zone_id, str(ex)
            )
            return None

    def get_zone_last_updated(self, zone_id: str) -> Optional[str]:
        """Get last update time for a specific zone."""
        try:
            peripheral_data = self.get_zone_peripheral(zone_id)
            return (
                peripheral_data.get("LastConnectionTime") if peripheral_data else None
            )
        except (KeyError, ValueError, IndexError) as ex:
            _LOGGER.error(
                "Error getting last update time for zone %s: %s", zone_id, str(ex)
            )
            return None

    async def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        try:
            if hvac_mode == HVACMode.OFF:
                command = self.api.create_command("OFF")
            else:
                command = self.api.create_command("CLIMATE_MODE", mode=hvac_mode)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set HVAC mode to %s: %s", hvac_mode, err)
            raise

    async def set_temperature(self, temperature: float, is_cooling: bool) -> None:
        """Set temperature."""
        try:
            command = self.api.create_command(
                "SET_TEMP", temp=temperature, is_cool=is_cooling
            )
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(
                "Failed to set %s temperature to %s: %s",
                "cooling" if is_cooling else "heating",
                temperature,
                err,
            )
            raise

    async def set_fan_mode(self, mode: str, continuous: Optional[bool] = None) -> None:
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
                current_mode = self.coordinator.data["main"].get("fan_mode", "")
                continuous = current_mode.endswith("+CONT")
                _LOGGER.debug("Maintaining current continuous state: %s", continuous)

            # Rate limiting check
            async with self._fan_mode_change_lock:
                if self._last_fan_mode_change:
                    elapsed = (
                        datetime.datetime.now() - self._last_fan_mode_change
                    ).total_seconds()
                    if elapsed < self._min_fan_mode_interval:
                        wait_time = self._min_fan_mode_interval - elapsed
                        _LOGGER.debug("Rate limiting: waiting %.1f seconds", wait_time)
                        await asyncio.sleep(wait_time)

                # Validate fan mode
                validated_mode = self.validate_fan_mode(mode, continuous)
                _LOGGER.debug(
                    "Setting fan mode: %s (original mode: %s, continuous: %s)",
                    validated_mode,
                    mode,
                    continuous,
                )

                # Add retry logic for API timeouts
                for attempt in range(MAX_RETRIES):
                    try:
                        command = self.api.create_command(
                            "FAN_MODE", mode=validated_mode
                        )
                        _LOGGER.debug(
                            "Sending fan mode command (attempt %d/%d): %s",
                            attempt + 1,
                            MAX_RETRIES,
                            command,
                        )

                        await self.api.send_command(self.device_id, command)

                        # Update state tracking
                        self._last_fan_mode_change = datetime.datetime.now()
                        self._continuous_fan = continuous

                        # Force immediate refresh
                        await self.async_request_refresh()

                        # Verify the change
                        new_mode = self.data["main"].get("fan_mode", "")
                        _LOGGER.debug("New fan mode after update: %s", new_mode)

                        # Validate continuous mode was set correctly
                        if continuous and "+CONT" not in new_mode:
                            if attempt < MAX_RETRIES - 1:
                                _LOGGER.warning(
                                    "Continuous mode not set correctly, retrying (attempt %d/%d)",
                                    attempt + 1,
                                    MAX_RETRIES,
                                )
                                await asyncio.sleep(2**attempt)  # Exponential backoff
                                continue
                            else:
                                _LOGGER.error(
                                    "Failed to set continuous mode after %d attempts",
                                    MAX_RETRIES,
                                )

                        _LOGGER.info("Successfully set fan mode to: %s", validated_mode)
                        break

                    except ApiError as e:
                        if (
                            e.status_code in [500, 502, 503, 504]
                            and attempt < MAX_RETRIES - 1
                        ):
                            wait_time = 2**attempt  # exponential backoff
                            _LOGGER.warning(
                                "Received %s error, retrying in %s seconds (attempt %d/%d)",
                                e.status_code,
                                wait_time,
                                attempt + 1,
                                MAX_RETRIES,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        _LOGGER.error("API error setting fan mode: %s", e)
                        raise
                    except Exception as err:
                        _LOGGER.error("Unexpected error setting fan mode: %s", err)
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

    async def set_zone_temperature(
        self, zone_id: str, temperature: float, temp_key: str
    ) -> None:
        """Set temperature for a specific zone with comprehensive validation.

        Args:
            zone_id: Identifier for the zone
            temperature: Target temperature
            temp_key: Temperature key for heating or cooling

        Raises:
            ValueError: If zone control is disabled or validation fails
            ApiError: If API communication fails
        """
        if not self.enable_zone_control:
            _LOGGER.error(
                "Attempted to set zone temperature while zone control is disabled"
            )
            raise ValueError("Zone control is not enabled")

        if not self.last_data:
            _LOGGER.error("No data available for zone temperature control")
            raise ValueError("No system data available")

        zones_data = self.last_data.get("zones", {})
        zone_data = zones_data.get(zone_id)

        if not zone_data:
            _LOGGER.error(
                "Zone %s not found in available zones: %s",
                zone_id,
                list(zones_data.keys()),
            )
            raise ValueError(f"Zone {zone_id} not found")

        if not zone_data.get("is_enabled", False):
            _LOGGER.error("Cannot set temperature for disabled zone %s", zone_id)
            raise ValueError(f"Zone {zone_id} is not enabled")

        try:
            zone_index = int(zone_id.split("_")[1]) - 1
            command = self.api.create_command(
                "SET_ZONE_TEMP", zone=zone_index, temp=temperature, temp_key=temp_key
            )
            await self.api.send_command(self.device_id, command)
            _LOGGER.info(
                "Successfully set zone %s temperature to %s", zone_id, temperature
            )
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error(
                "Failed to set zone %s temperature to %s: %s", zone_id, temperature, err
            )
            raise

    async def set_zone_state(self, zone_id: Union[str, int], enable: bool) -> None:
        """Set zone state.
        Args:
            zone_id: Either a zone ID string (e.g. 'zone_1') or direct zone index (0-7)
            enable: True to enable zone, False to disable
        """
        try:
            # Handle both string zone_id and direct integer index
            if isinstance(zone_id, str):
                zone_index = int(zone_id.split("_")[1]) - 1
            else:
                zone_index = int(zone_id)  # Direct index from switch component

            current_zone_status = self.last_data["main"]["EnabledZones"]
            modified_statuses = current_zone_status.copy()

            # Ensure zone_index is within bounds
            if 0 <= zone_index < len(modified_statuses):
                modified_statuses[zone_index] = enable
                command = self.api.create_command(
                    "SET_ZONE_STATE", zones=modified_statuses
                )
                await self.api.send_command(self.device_id, command)
                await self.async_request_refresh()
            else:
                raise ValueError(f"Zone index {zone_index} out of range")

        except Exception as err:
            _LOGGER.error(
                "Failed to set zone %s state to %s: %s",
                zone_id,
                "on" if enable else "off",
                err,
            )
            raise

    async def set_climate_mode(self, mode: str) -> None:
        """Set climate mode for all zones."""
        try:
            command = self.api.create_command("CLIMATE_MODE", mode=mode)
            await self.api.send_command(self.device_id, command)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set climate mode to %s: %s", mode, err)
            raise

    async def set_away_mode(self, state: bool) -> None:
        """Set away mode."""
        try:
            await self.api.set_away_mode(state)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set away mode to %s: %s", state, err)
            raise

    async def set_quiet_mode(self, state: bool) -> None:
        """Set quiet mode."""
        try:
            await self.api.set_quiet_mode(state)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set quiet mode to %s: %s", state, err)
            raise

    async def force_update(self) -> None:
        """Force an immediate update of the device data."""
        await self.async_refresh()

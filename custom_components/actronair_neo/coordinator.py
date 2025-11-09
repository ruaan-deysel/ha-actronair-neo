"""Coordinator for the ActronAir Neo integration."""

import asyncio
import datetime
import logging
from datetime import timedelta
from typing import Any, cast

from homeassistant.components.climate.const import HVACMode  # type: ignore
from homeassistant.core import HomeAssistant  # type: ignore
from homeassistant.exceptions import ConfigEntryAuthFailed  # type: ignore
from homeassistant.helpers.update_coordinator import (  # type: ignore
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    ActronApi,
    ApiError,
    AuthenticationError,
    ConfigurationError,
    DeviceOfflineError,
    RateLimitError,
    ZoneError,
)
from .const import (
    ADVANCE_FAN_MODES,
    DOMAIN,
    FAN_MODE_SUFFIX_CONT,
    MAX_RETRIES,
    MAX_TEMP,
    MAX_ZONES,
    MIN_FAN_MODE_INTERVAL,
    MIN_TEMP,
    NEO_SERIES_WC,
    VALID_FAN_MODES,
)
from .types import (
    AcStatusResponse,
    CoordinatorData,
    FanModeType,
    MainData,
    PeripheralData,
    ZoneData,
)
from .zone_presets import ZonePresetManager

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
    ) -> None:
        """
        Initialize the data coordinator.

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

        # Cache management
        self._last_cache_cleanup: datetime.datetime | None = None

        # Enhanced zone management
        self.zone_preset_manager = ZonePresetManager(hass, device_id)

        # Performance optimization: data processing cache
        self._parsed_data_cache: CoordinatorData | None = None
        self._raw_data_hash: int | None = None

        # Memory optimization: track cache sizes and cleanup
        self._cache_hit_count = 0
        self._cache_miss_count = 0
        self._last_memory_cleanup: datetime.datetime | None = None

    def validate_fan_mode(self, mode: str, continuous: bool = False) -> str:
        """
        Validate and format fan mode.

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
        """
        Validate that the fan mode was set correctly.

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
    def continuous_fan(self, value: bool) -> None:
        """Set continuous fan state."""
        self._continuous_fan = value

    async def set_enable_zone_control(self, enable: bool) -> None:
        """Update the enable_zone_control status."""
        self.enable_zone_control = enable
        await self.async_request_refresh()

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from API endpoint with enhanced caching and error handling."""
        try:
            # Check API health first - this leverages the API client's health monitoring
            if not self.api.is_api_healthy():
                _LOGGER.debug("API is not healthy, using cached data")
                if self.last_data:
                    return self.last_data
                # If no cached data and API unhealthy, try one request anyway
                _LOGGER.warning(
                    "No cached data available, attempting API request despite health status"
                )

            _LOGGER.debug("Fetching data for device %s", self.device_id)

            # Use the enhanced API client with caching and deduplication
            status = await self.api.get_ac_status(self.device_id, use_cache=True)

            # Parse data using optimized approach with caching
            parsed_data = await self._parse_data_optimized(status)

            # Update last known good data
            self.last_data = parsed_data

            # Periodic cache cleanup (every 5 minutes)
            await self._maybe_cleanup_cache()

            _LOGGER.debug(
                "Successfully updated coordinator data for device %s", self.device_id
            )
            return parsed_data

        except AuthenticationError as err:
            _LOGGER.exception("Authentication error: %s", err)
            # Clear any cached data on auth failure
            await self.api.clear_all_caches()
            raise ConfigEntryAuthFailed from err

        except RateLimitError as err:
            _LOGGER.warning("Rate limit exceeded: %s", err)
            if self.last_data:
                _LOGGER.info("Using cached coordinator data due to rate limiting")
                return self.last_data
            # Don't raise UpdateFailed for rate limits if we have cached data
            msg = f"Rate limit exceeded: {err}"
            raise UpdateFailed(msg) from err

        except DeviceOfflineError as err:
            _LOGGER.warning("Device appears to be offline: %s", err)
            if self.last_data:
                _LOGGER.info("Using cached coordinator data while device is offline")
                return self.last_data
            msg = f"Device offline: {err}"
            raise UpdateFailed(msg) from err

        except ApiError as err:
            if err.is_temporary and self.last_data:
                _LOGGER.warning("Temporary API error, using cached data: %s", err)
                return self.last_data
            if err.is_client_error:
                _LOGGER.exception("Client error (configuration issue): %s", err)
                if self.last_data:
                    return self.last_data
                msg = f"Configuration error: {err}"
                raise UpdateFailed(msg) from err
            _LOGGER.exception("API error: %s", err)
            if self.last_data:
                _LOGGER.warning("Using cached coordinator data due to API error")
                return self.last_data
            msg = f"API communication error: {err}"
            raise UpdateFailed(msg) from err

        except Exception as err:
            _LOGGER.error("Unexpected error occurred: %s", err, exc_info=True)
            if self.last_data:
                _LOGGER.warning("Using cached coordinator data due to unexpected error")
                return self.last_data
            msg = f"Unexpected error: {err}"
            raise UpdateFailed(msg) from err

    async def _parse_data(self, data: AcStatusResponse) -> CoordinatorData:
        """
        Parse the data from the API into a format suitable for the climate entity.

        Args:
            data: Raw API response data

        Returns:
            Dict containing parsed data including raw data for diagnostics

        Raises:
            UpdateFailed: If parsing fails

        """
        try:
            # Extract main data sections for easier access
            last_known_state = data.get("lastKnownState", {})
            data_sections = self._extract_data_sections(last_known_state)

            # Parse main system data
            main_data = await self._parse_main_data(data_sections)

            # Parse zone data efficiently
            zones = await self._parse_zones_data(data_sections)

            # Update internal state
            self._continuous_fan = main_data["fan_continuous"]

            # Construct the final result
            result: CoordinatorData = {
                "main": main_data,
                "zones": zones,
                "raw_data": data,
            }

            return result

        except Exception as e:
            _LOGGER.error("Failed to parse API response: %s", e, exc_info=True)
            msg = f"Failed to parse API response: {e}"
            raise UpdateFailed(msg) from e

    async def _parse_data_optimized(self, data: AcStatusResponse) -> CoordinatorData:
        """
        Parse data with performance optimizations and caching.

        Args:
            data: Raw API response data

        Returns:
            Parsed coordinator data

        """
        # Calculate hash of raw data for change detection
        raw_data_str = str(sorted(data.items()) if isinstance(data, dict) else data)
        raw_data_hash = hash(raw_data_str)

        # Return cached parsed data if raw data hasn't changed
        if self._raw_data_hash == raw_data_hash and self._parsed_data_cache is not None:
            self._cache_hit_count += 1
            _LOGGER.debug(
                "Using cached parsed data (cache hit #%d)", self._cache_hit_count
            )
            return self._parsed_data_cache

        # Parse data using existing method
        self._cache_miss_count += 1
        parsed_data = await self._parse_data(data)

        # Cache the parsed result
        self._raw_data_hash = raw_data_hash
        self._parsed_data_cache = parsed_data

        _LOGGER.debug(
            "Parsed and cached new data (cache miss #%d)", self._cache_miss_count
        )

        # Periodic memory cleanup
        await self._maybe_cleanup_memory()

        return parsed_data

    def _extract_data_sections(self, last_known_state: dict) -> dict:
        """
        Extract and organize data sections from API response.

        Args:
            last_known_state: The lastKnownState section from API response

        Returns:
            Dictionary with organized data sections

        """
        return {
            "user_aircon_settings": last_known_state.get("UserAirconSettings", {}),
            "master_info": last_known_state.get("MasterInfo", {}),
            "live_aircon": last_known_state.get("LiveAircon", {}),
            "aircon_system": last_known_state.get("AirconSystem", {}),
            "indoor_unit": last_known_state.get("AirconSystem", {}).get(
                "IndoorUnit", {}
            ),
            "alerts": last_known_state.get("Alerts", {}),
            "remote_zone_info": last_known_state.get("RemoteZoneInfo", []),
            "peripherals": last_known_state.get("AirconSystem", {}).get(
                "Peripherals", []
            ),
        }

    async def _parse_main_data(self, data_sections: dict) -> MainData:
        """
        Parse main system data from API response sections.

        Args:
            data_sections: Organized data sections from API response

        Returns:
            MainData structure with parsed main system information

        """
        user_aircon_settings = data_sections["user_aircon_settings"]
        master_info = data_sections["master_info"]
        live_aircon = data_sections["live_aircon"]
        aircon_system = data_sections["aircon_system"]
        indoor_unit = data_sections["indoor_unit"]
        alerts = data_sections["alerts"]

        # Get supported modes
        if indoor_unit.get("NV_AutoFanEnabled", False):
            supported_fan_modes = ADVANCE_FAN_MODES
        else:
            supported_fan_modes = self._validate_fan_modes(
                indoor_unit.get("NV_SupportedFanModes", 0)
            )

        # Get fan mode and check for continuous state using '+CONT'
        fan_mode = user_aircon_settings.get("FanMode", "")
        is_continuous = fan_mode.endswith("+CONT")

        # Strip the continuous suffix for clean fan_mode storage
        base_fan_mode = fan_mode.split("+")[0] if "+" in fan_mode else fan_mode
        base_fan_mode = (
            base_fan_mode.split("-")[0] if "-" in base_fan_mode else base_fan_mode
        )

        # Get model number for specific handling of NEO Series WC
        model = aircon_system.get("MasterWCModel", "")
        if model in NEO_SERIES_WC:
            model = indoor_unit.get("NV_ModelNumber", "")

        # Create main data structure
        main_data: MainData = {
            "is_on": user_aircon_settings.get("isOn", False),
            "mode": user_aircon_settings.get("Mode", "OFF"),
            "fan_mode": fan_mode,
            "fan_continuous": is_continuous,
            "base_fan_mode": base_fan_mode,
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
            "model": model,
            "indoor_model": indoor_unit.get("NV_ModelNumber"),
            "serial_number": aircon_system.get("MasterSerial"),
            "firmware_version": aircon_system.get("MasterWCFirmwareVersion"),
            "filter_clean_required": alerts.get("CleanFilter", False),
            "defrosting": alerts.get("Defrosting", False),
        }

        _LOGGER.debug(
            "Fan mode status - Raw: %s, Base: %s, Continuous: %s",
            fan_mode,
            base_fan_mode,
            is_continuous,
        )

        return main_data

    async def _parse_zones_data(self, data_sections: dict) -> dict[str, ZoneData]:
        """
        Parse zone data from API response sections.

        Args:
            data_sections: Organized data sections from API response

        Returns:
            Dictionary of zone data indexed by zone_id

        """
        zones: dict[str, ZoneData] = {}
        remote_zone_info = data_sections["remote_zone_info"]
        peripherals = data_sections["peripherals"]
        user_aircon_settings = data_sections["user_aircon_settings"]

        for i, zone in enumerate(remote_zone_info):
            if i < MAX_ZONES:
                zone_id = f"zone_{i + 1}"

                # Get zone capabilities including existence check
                capabilities = self.api.get_zone_capabilities(zone)

                if capabilities["exists"]:
                    # Create base zone data
                    zone_data = {
                        "name": zone.get("NV_Title", f"Zone {i + 1}"),
                        "temp": zone.get("LiveTemp_oC"),
                        "setpoint": zone.get("TemperatureSetpoint_oC"),
                        "is_on": zone.get("CanOperate", False),
                        "capabilities": capabilities,
                        "humidity": zone.get("LiveHumidity_pc"),
                        "is_enabled": (
                            user_aircon_settings.get("EnabledZones", [])[i]
                            if i < len(user_aircon_settings.get("EnabledZones", []))
                            else False
                        ),
                        "temp_setpoint_cool": capabilities.get("target_temp_cool"),
                        "temp_setpoint_heat": capabilities.get("target_temp_heat"),
                        # Zone damper position (convert from 0-20 API scale to 0-100 percentage)
                        "damper_position": self._convert_damper_position(
                            zone.get("ZonePosition")
                        ),
                        # YourZone airflow control fields
                        "airflow_setpoint": zone.get("AirflowSetpoint"),
                        "airflow_control_enabled": zone.get(
                            "AirflowControlEnabled", False
                        ),
                        "airflow_control_locked": zone.get(
                            "AirflowControlLocked", False
                        ),
                        "zone_max_position": zone.get("ZoneMaxPosition"),
                        "zone_min_position": zone.get("ZoneMinPosition"),
                        # Initialize peripheral data
                        "battery_level": None,
                        "signal_strength": None,
                        "peripheral_type": None,
                        "last_connection": None,
                        "connection_state": None,
                    }

                    # Find and add matching peripheral data by sensor serial number
                    # Access sensor info from current zone (case-insensitive device ID lookup)
                    zone_sensors = zone.get("Sensors", {})
                    zone_sensor_kind = ""

                    # Find device ID with case-insensitive matching
                    for device_key, sensor_data in zone_sensors.items():
                        if device_key.lower() == self.device_id.lower():
                            zone_sensor_kind = sensor_data.get("NV_Kind", "")
                            break

                    # Extract serial number from NV_Kind (format: "ZS: 23E01206")
                    if zone_sensor_kind.startswith("ZS: "):
                        zone_serial = zone_sensor_kind.replace("ZS: ", "")

                        # Find matching peripheral by serial number
                        for peripheral in peripherals:
                            peripheral_serial = peripheral.get("SerialNumber", "")
                            if peripheral_serial == zone_serial:
                                peripheral_data = {
                                    "battery_level": peripheral.get(
                                        "RemainingBatteryCapacity_pc"
                                    ),
                                    "signal_strength": peripheral.get("RSSI", {}).get(
                                        "Local"
                                    ),
                                    "peripheral_type": peripheral.get("DeviceType"),
                                    "last_connection": peripheral.get(
                                        "LastConnectionTime"
                                    ),
                                    "connection_state": peripheral.get(
                                        "ConnectionState"
                                    ),
                                }
                                zone_data.update(peripheral_data)

                                # Add peripheral capabilities if present
                                if peripheral.get("ControlCapabilities"):
                                    # Create a new capabilities dict with peripheral capabilities
                                    updated_capabilities = capabilities.copy()
                                    updated_capabilities["peripheral_capabilities"] = (
                                        peripheral.get("ControlCapabilities")
                                    )
                                    zone_data["capabilities"] = updated_capabilities
                                break

                    zones[zone_id] = cast("ZoneData", zone_data)

        return zones

    async def _maybe_cleanup_cache(self) -> None:
        """Perform periodic cache cleanup if needed."""
        now = datetime.datetime.now()

        # Cleanup every 5 minutes
        if (
            self._last_cache_cleanup is None
            or (now - self._last_cache_cleanup).total_seconds() > 300
        ):
            await self.api.cleanup_expired_cache()
            self._last_cache_cleanup = now
            _LOGGER.debug("Performed periodic cache cleanup")

    async def _maybe_cleanup_memory(self) -> None:
        """Perform periodic memory optimization cleanup."""
        now = datetime.datetime.now()

        # Memory cleanup every 10 minutes
        if (
            self._last_memory_cleanup is None
            or (now - self._last_memory_cleanup).total_seconds() > 600
        ):
            # Clear parsed data cache if we have too many cache misses
            cache_hit_rate = self._cache_hit_count / max(
                1, self._cache_hit_count + self._cache_miss_count
            )

            if cache_hit_rate < 0.3:  # Less than 30% hit rate
                _LOGGER.debug(
                    "Low cache hit rate (%.1f%%), clearing parsed data cache",
                    cache_hit_rate * 100,
                )
                self._parsed_data_cache = None
                self._raw_data_hash = None

            # Reset counters periodically
            if self._cache_hit_count + self._cache_miss_count > 1000:
                self._cache_hit_count = 0
                self._cache_miss_count = 0

            self._last_memory_cleanup = now
            _LOGGER.debug("Performed periodic memory cleanup")

    def _validate_fan_modes(self, modes: Any) -> list[str]:
        """
        Validate and normalize supported fan modes.

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
            _LOGGER.exception(
                "Error validating fan modes: %s (input was: %s, type: %s)",
                err,
                modes,
                type(modes),
            )
            _LOGGER.debug("Returning default modes due to error: %s", default_modes)
            return default_modes

    def get_zone_peripheral(self, zone_id: str) -> PeripheralData | None:
        """Get peripheral data for a specific zone by matching serial numbers."""
        try:
            zone_index = int(zone_id.split("_")[1]) - 1

            # Get zone sensor info from RemoteZoneInfo
            remote_zone_info = self.data.get("raw_data", {}).get("RemoteZoneInfo", [])
            if zone_index >= len(remote_zone_info):
                return None

            zone_info = remote_zone_info[zone_index]
            zone_sensors = zone_info.get("Sensors", {})
            zone_sensor_kind = ""

            # Find device ID with case-insensitive matching
            for device_key, sensor_data in zone_sensors.items():
                if device_key.lower() == self.device_id.lower():
                    zone_sensor_kind = sensor_data.get("NV_Kind", "")
                    break

            # Extract serial number from NV_Kind (format: "ZS: 23E01206")
            if not zone_sensor_kind.startswith("ZS: "):
                return None  # Not a wireless sensor

            zone_serial = zone_sensor_kind.replace("ZS: ", "")

            # Find matching peripheral by serial number
            peripherals = (
                self.data.get("raw_data", {})
                .get("AirconSystem", {})
                .get("Peripherals", [])
            )

            for peripheral in peripherals:
                peripheral_serial = peripheral.get("SerialNumber", "")
                if peripheral_serial == zone_serial:
                    return cast("PeripheralData", peripheral)

            return None
        except (KeyError, ValueError, IndexError) as ex:
            _LOGGER.exception(
                "Error getting peripheral data for zone %s: %s", zone_id, str(ex)
            )
            return None

    def get_zone_last_updated(self, zone_id: str) -> str | None:
        """Get last update time for a specific zone."""
        try:
            peripheral_data = self.get_zone_peripheral(zone_id)
            return (
                peripheral_data.get("LastConnectionTime") if peripheral_data else None
            )
        except (KeyError, ValueError, IndexError) as ex:
            _LOGGER.exception(
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
            _LOGGER.exception("Failed to set HVAC mode to %s: %s", hvac_mode, err)
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
            _LOGGER.exception(
                "Failed to set %s temperature to %s: %s",
                "cooling" if is_cooling else "heating",
                temperature,
                err,
            )
            raise

    async def set_fan_mode(
        self, mode: FanModeType, continuous: bool | None = None
    ) -> None:
        """
        Set fan mode with state tracking, validation and retry logic.

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
                        _LOGGER.exception("API error setting fan mode: %s", e)
                        raise
                    except Exception as err:
                        _LOGGER.exception("Unexpected error setting fan mode: %s", err)
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
        """
        Set temperature for a specific zone with comprehensive validation.

        Args:
            zone_id: Identifier for the zone
            temperature: Target temperature
            temp_key: Temperature key for heating or cooling

        Raises:
            ZoneError: If zone-specific validation fails
            ConfigurationError: If zone control is disabled
            ApiError: If API communication fails

        """
        if not self.enable_zone_control:
            _LOGGER.error(
                "Attempted to set zone temperature while zone control is disabled"
            )
            msg = "Zone control is not enabled"
            raise ConfigurationError(msg, config_key="enable_zone_control")

        if not self.last_data:
            _LOGGER.error("No data available for zone temperature control")
            msg = "No system data available"
            raise ZoneError(msg, zone_id=zone_id)

        zones_data = self.last_data.get("zones", {})
        zone_data = zones_data.get(zone_id)

        if not zone_data:
            _LOGGER.error(
                "Zone %s not found in available zones: %s",
                zone_id,
                list(zones_data.keys()),
            )
            msg = f"Zone {zone_id} not found"
            raise ZoneError(msg, zone_id=zone_id)

        # Note: We allow setting temperature for disabled zones as the ActronAir API
        # supports this and it's useful for pre-setting temperatures before enabling zones

        # Validate temperature range
        if not (MIN_TEMP <= temperature <= MAX_TEMP):
            _LOGGER.error(
                "Temperature %s outside valid range [%s, %s] for zone %s",
                temperature,
                MIN_TEMP,
                MAX_TEMP,
                zone_id,
            )
            msg = f"Temperature {temperature} outside valid range [{MIN_TEMP}, {MAX_TEMP}]"
            raise ZoneError(
                msg,
                zone_id=zone_id,
            )

        # Check zone capabilities
        capabilities = zone_data.get("capabilities", {})
        if not capabilities.get("has_temp_control", False):
            _LOGGER.error("Zone %s does not support temperature control", zone_id)
            msg = f"Zone {zone_id} does not support temperature control"
            raise ZoneError(msg, zone_id=zone_id)

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
            _LOGGER.exception(
                "Failed to set zone %s temperature to %s: %s", zone_id, temperature, err
            )
            raise

    async def set_zone_state(self, zone_id: str | int, enable: bool) -> None:
        """
        Set zone state.

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

            # Use current data if available, otherwise fetch fresh
            if self.last_data and "main" in self.last_data:
                current_zone_status = self.last_data["main"]["EnabledZones"]
            else:
                # Fetch fresh data if no cached data available
                _LOGGER.debug("No cached data available, fetching fresh zone status")
                zone_statuses = await self.api.get_zone_statuses()
                current_zone_status = zone_statuses

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
                msg = f"Zone index {zone_index} out of range"
                raise ValueError(msg)

        except Exception as err:
            _LOGGER.exception(
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
            _LOGGER.exception("Failed to set climate mode to %s: %s", mode, err)
            raise

    async def set_away_mode(self, state: bool) -> None:
        """Set away mode."""
        try:
            await self.api.set_away_mode(state)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.exception("Failed to set away mode to %s: %s", state, err)
            raise

    async def set_quiet_mode(self, state: bool) -> None:
        """Set quiet mode."""
        try:
            await self.api.set_quiet_mode(state)
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.exception("Failed to set quiet mode to %s: %s", state, err)
            raise

    async def force_update(self) -> None:
        """Force an immediate update of the device data."""
        # Clear API cache to ensure fresh data
        await self.api.clear_all_caches()
        await self.async_refresh()

    async def invalidate_cache(self) -> None:
        """Invalidate cached data to force fresh API calls."""
        await self.api._invalidate_status_cache(self.device_id)
        _LOGGER.debug("Invalidated cache for device %s", self.device_id)

    async def cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries."""
        await self.api.cleanup_expired_cache()
        _LOGGER.debug("Cleaned up expired cache entries")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics

        """
        return {
            "api_health": self.api.is_api_healthy(),
            "last_successful_request": self.api.last_successful_request,
            "error_count": self.api.error_count,
            "has_cached_status": self.api.cached_status is not None,
            "coordinator_has_data": self.last_data is not None,
        }

    def get_performance_stats(self) -> dict:
        """
        Get performance statistics for monitoring.

        Returns:
            Dictionary with performance statistics

        """
        total_requests = self._cache_hit_count + self._cache_miss_count
        cache_hit_rate = (self._cache_hit_count / max(1, total_requests)) * 100

        return {
            "cache_hit_count": self._cache_hit_count,
            "cache_miss_count": self._cache_miss_count,
            "cache_hit_rate_percent": round(cache_hit_rate, 1),
            "total_parse_requests": total_requests,
            "has_parsed_cache": self._parsed_data_cache is not None,
            "last_cache_cleanup": self._last_cache_cleanup,
            "last_memory_cleanup": self._last_memory_cleanup,
            "zone_preset_count": len(self.zone_preset_manager.get_all_presets())
            if self.zone_preset_manager
            else 0,
        }

    # Enhanced Zone Management Methods

    async def async_initialize_zone_management(self) -> None:
        """Initialize zone management components."""
        try:
            await self.zone_preset_manager.async_load()
            _LOGGER.debug("Zone management initialized for device %s", self.device_id)
        except Exception as err:
            _LOGGER.exception("Failed to initialize zone management: %s", err)

    async def async_create_zone_preset_from_current(
        self, name: str, description: str = ""
    ) -> None:
        """
        Create a zone preset from current zone states.

        Args:
            name: Preset name
            description: Optional description

        Raises:
            ConfigurationError: If preset creation fails

        """
        if not self.last_data:
            msg = "No zone data available"
            raise ConfigurationError(msg)

        zones_config = {}
        for zone_id, zone_data in self.last_data["zones"].items():
            zones_config[zone_id] = {
                "enabled": zone_data["is_enabled"],
                "temp_cool": zone_data.get("temp_setpoint_cool"),
                "temp_heat": zone_data.get("temp_setpoint_heat"),
            }

        await self.zone_preset_manager.async_create_preset(
            name, zones_config, description
        )
        _LOGGER.info("Created zone preset '%s' from current state", name)

    async def async_apply_zone_preset(self, preset_name: str) -> None:
        """
        Apply a zone preset.

        Args:
            preset_name: Name of preset to apply

        Raises:
            ConfigurationError: If preset not found or application fails

        """
        preset = self.zone_preset_manager.get_preset(preset_name)
        if not preset:
            msg = f"Preset '{preset_name}' not found"
            raise ConfigurationError(msg)

        if not self.enable_zone_control:
            msg = "Zone control is not enabled"
            raise ConfigurationError(msg)

        # Apply zone states
        for zone_id, zone_config in preset.zones.items():
            try:
                # Set zone state
                if "enabled" in zone_config:
                    await self.set_zone_state(zone_id, zone_config["enabled"])

                # Set temperatures if zone supports it and values are provided
                if self.last_data and zone_id in self.last_data["zones"]:
                    zone_data = self.last_data["zones"][zone_id]
                    capabilities = zone_data.get("capabilities", {})

                    if capabilities.get("has_temp_control"):
                        if zone_config.get("temp_cool") is not None:
                            await self.set_zone_temperature(
                                zone_id, zone_config["temp_cool"], "temp_setpoint_cool"
                            )
                        if zone_config.get("temp_heat") is not None:
                            await self.set_zone_temperature(
                                zone_id, zone_config["temp_heat"], "temp_setpoint_heat"
                            )

            except Exception as err:
                _LOGGER.exception("Failed to apply preset to zone %s: %s", zone_id, err)

        await self.async_request_refresh()
        _LOGGER.info("Applied zone preset '%s'", preset_name)

    async def async_bulk_zone_operation(
        self, operation: str, zones: list[str], **kwargs
    ) -> None:
        """
        Perform bulk operations on multiple zones.

        Args:
            operation: Operation type ('enable', 'disable', 'set_temperature')
            zones: List of zone IDs
            **kwargs: Additional operation parameters

        Raises:
            ConfigurationError: If zone control disabled or invalid operation
            ZoneError: If zone operation fails

        """
        if not self.enable_zone_control:
            msg = "Zone control is not enabled"
            raise ConfigurationError(msg)

        if operation not in ["enable", "disable", "set_temperature"]:
            msg = f"Invalid operation: {operation}"
            raise ConfigurationError(msg)

        results = []
        for zone_id in zones:
            try:
                if operation == "enable":
                    await self.set_zone_state(zone_id, True)
                    results.append({"zone_id": zone_id, "status": "success"})
                elif operation == "disable":
                    await self.set_zone_state(zone_id, False)
                    results.append({"zone_id": zone_id, "status": "success"})
                elif operation == "set_temperature":
                    temperature = kwargs.get("temperature")
                    temp_key = kwargs.get("temp_key", "temp_setpoint_cool")
                    if temperature is not None:
                        await self.set_zone_temperature(zone_id, temperature, temp_key)
                        results.append({"zone_id": zone_id, "status": "success"})
                    else:
                        results.append(
                            {
                                "zone_id": zone_id,
                                "status": "error",
                                "error": "No temperature provided",
                            }
                        )

            except Exception as err:
                _LOGGER.exception("Bulk operation failed for zone %s: %s", zone_id, err)
                results.append(
                    {"zone_id": zone_id, "status": "error", "error": str(err)}
                )

        await self.async_request_refresh()
        _LOGGER.info("Bulk operation '%s' completed on %d zones", operation, len(zones))
        return results

    def _convert_damper_position(self, api_position: int | None) -> int:
        """
        Convert damper position from API scale (0-20) to percentage scale (0-100).

        The ActronAir Neo API returns damper positions in a 0-20 scale, but Home Assistant
        expects percentage values (0-100). This method converts the API value to the correct
        percentage representation.

        Args:
            api_position: Raw damper position from API (0-20 scale), or None

        Returns:
            Damper position as percentage (0-100), or 0 if input is None/invalid

        """
        if api_position is None:
            return 0

        try:
            # Convert from 0-20 scale to 0-100 percentage
            # Clamp to valid range to handle any unexpected values
            api_position = max(0, min(20, int(api_position)))
            percentage = (api_position * 100) // 20
            return min(100, percentage)  # Ensure we never exceed 100%
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid damper position value: %s", api_position)
            return 0

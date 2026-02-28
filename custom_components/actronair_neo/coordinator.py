"""Coordinator for the ActronAir Neo integration."""

from __future__ import annotations

import asyncio
import datetime
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from homeassistant.components.climate.const import (
    HVACMode,  # type: ignore[import-untyped]
)
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,  # type: ignore[import-untyped]
)
from homeassistant.helpers.update_coordinator import (  # type: ignore[import-untyped]
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api.const import MAX_RETRIES, MIN_FAN_MODE_INTERVAL, RETRYABLE_STATUS_CODES
from .const import (
    ADVANCE_FAN_MODES,
    DOMAIN,
    FAN_MODE_SUFFIX_CONT,
    MAX_TEMP,
    MAX_ZONES,
    MIN_TEMP,
    NEO_SERIES_WC,
    OUTDOOR_TEMP_UNAVAILABLE,
    VALID_FAN_MODES,
)
from .exceptions import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    DeviceOfflineError,
    RateLimitError,
    ZoneError,
)
from .zone_presets import ZonePresetManager

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant  # type: ignore[import-untyped]

    from .api import ActronAirNeoApiClient
    from .api.models import (
        AcStatusResponse,
        CoordinatorData,
        FanModeType,
        MainData,
        PeripheralData,
        ZoneCapabilities,
        ZoneData,
    )

_LOGGER = logging.getLogger(__name__)


class ActronDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ActronAir Neo data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ActronAirNeoApiClient,
        device_id: str,
        update_interval: int,
        *,
        enable_zone_control: bool,
    ) -> None:
        """
        Initialize the data coordinator.

        Args:
            hass: HomeAssistant instance
            api: ActronAirNeoApiClient instance for API communication
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
        self.last_data: CoordinatorData | None = None

        # Fan mode control attributes
        self._continuous_fan = False
        self._fan_mode_change_lock = asyncio.Lock()
        self._last_fan_mode_change: datetime.datetime | None = None
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

    def validate_fan_mode(self, mode: str, *, continuous: bool = False) -> str:
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
            base_mode = mode.split("+", maxsplit=1)[0] if "+" in mode else mode
            base_mode = base_mode.split("-")[0] if "-" in base_mode else base_mode
            base_mode = base_mode.upper()

            # Validate against supported modes
            if base_mode not in supported_modes:
                base_mode = "LOW"

            # Validate against known valid modes as a safety check
            if base_mode not in VALID_FAN_MODES:
                base_mode = "LOW"

        except (KeyError, AttributeError, ValueError):
            return "LOW+CONT" if continuous else "LOW"
        else:
            return f"{base_mode}{FAN_MODE_SUFFIX_CONT}" if continuous else base_mode

    def _validate_fan_mode_response(
        self, requested_mode: str, actual_mode: str, *, continuous: bool
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
        base_requested = (
            requested_mode.split("+", maxsplit=1)[0].split("-", maxsplit=1)[0].upper()
        )
        base_actual = (
            actual_mode.split("+", maxsplit=1)[0].split("-", maxsplit=1)[0].upper()
        )

        is_continuous = "+CONT" in actual_mode

        mode_correct = base_requested == base_actual
        continuous_correct = continuous == is_continuous

        return mode_correct and continuous_correct

    @property
    def continuous_fan(self) -> bool:
        """Get continuous fan state."""
        return self._continuous_fan

    @continuous_fan.setter
    def continuous_fan(self, value: bool) -> None:
        """Set continuous fan state."""
        self._continuous_fan = value

    async def set_enable_zone_control(self, *, enable: bool) -> None:
        """Update the enable_zone_control status."""
        self.enable_zone_control = enable
        await self.async_request_refresh()

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from API endpoint with enhanced caching and error handling."""
        try:
            # Check API health first
            if not self.api.is_api_healthy() and self.last_data:
                return self.last_data

            # Use the enhanced API client with caching and deduplication
            status = await self.api.get_ac_status(self.device_id, use_cache=True)

            # Parse data using optimized approach with caching
            parsed_data = await self._parse_data_optimized(status)  # type: ignore[arg-type]

            # Update last known good data
            self.last_data = parsed_data

            # Periodic cache cleanup (every 5 minutes)
            await self._maybe_cleanup_cache()

        except AuthenticationError:
            await self.api.clear_all_caches()
            raise ConfigEntryAuthFailed from None

        except RateLimitError as err:
            if self.last_data:
                return self.last_data
            msg = f"Rate limit exceeded: {err}"
            raise UpdateFailed(msg) from err

        except DeviceOfflineError as err:
            if self.last_data:
                return self.last_data
            msg = f"Device offline: {err}"
            raise UpdateFailed(msg) from err

        except ApiError as err:
            return self._handle_api_error(err)

        except Exception as err:
            if self.last_data:
                return self.last_data
            msg = f"Unexpected error: {err}"
            raise UpdateFailed(msg) from err

        else:
            return parsed_data

    def _handle_api_error(self, err: ApiError) -> CoordinatorData:
        """
        Handle API errors during data update.

        Args:
            err: The ApiError that occurred

        Returns:
            Cached coordinator data if available

        Raises:
            UpdateFailed: If no cached data is available

        """
        if err.is_temporary and self.last_data:
            return self.last_data
        if err.is_client_error:
            if self.last_data:
                return self.last_data
            msg = f"Configuration error: {err}"
            raise UpdateFailed(msg) from err
        if self.last_data:
            return self.last_data
        msg = f"API communication error: {err}"
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
            result: CoordinatorData = {  # type: ignore[assignment]
                "main": main_data,
                "zones": zones,
                "raw_data": data,
            }

        except Exception as e:
            msg = f"Failed to parse API response: {e}"
            raise UpdateFailed(msg) from e
        else:
            return result

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
            return self._parsed_data_cache

        # Parse data using existing method
        self._cache_miss_count += 1
        parsed_data = await self._parse_data(data)

        # Cache the parsed result
        self._raw_data_hash = raw_data_hash
        self._parsed_data_cache = parsed_data

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
        supported_fan_modes: list[str] | frozenset[str]
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
        main_data: MainData = {  # type: ignore[assignment]
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
            # Extended API coverage fields
            "turbo_mode_supported": user_aircon_settings.get("TurboMode", {}).get(
                "Supported", False
            ),
            "turbo_mode_enabled": user_aircon_settings.get("TurboMode", {}).get(
                "Enabled", False
            ),
            "after_hours_enabled": user_aircon_settings.get("AfterHours", {}).get(
                "Enabled", False
            ),
            "after_hours_duration": user_aircon_settings.get("AfterHours", {}).get(
                "Duration", 120
            ),
            "outdoor_temp": self._parse_outdoor_temp(
                master_info.get("LiveOutdoorTemp_oC"),
                live_aircon.get("OutdoorUnit", {}),
            ),
            "fast_heating": user_aircon_settings.get("isFastHeating", False),
            "quiet_mode_supported": user_aircon_settings.get("QuietModeEnabled", False),
            "quiet_mode_active": user_aircon_settings.get("QuietModeActive", False),
            "service_reminder_enabled": user_aircon_settings.get(
                "ServiceReminder", {}
            ).get("Enabled", False),
            "service_reminder_time": user_aircon_settings.get(
                "ServiceReminder", {}
            ).get("Time", "NA"),
            "warnings": self._parse_warnings(live_aircon),
        }

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

                if capabilities.exists:
                    # Create base zone data
                    zone_data = {
                        "name": zone.get("NV_Title", f"Zone {i + 1}"),
                        "temp": zone.get("LiveTemp_oC"),
                        "setpoint": zone.get("TemperatureSetpoint_oC"),
                        "is_on": zone.get("CanOperate", False),
                        "capabilities": capabilities,
                        "humidity": zone.get("LiveHumidity_pc"),
                        "is_enabled": self._get_zone_enabled(user_aircon_settings, i),
                        "temp_setpoint_cool": capabilities.target_temp_cool,
                        "temp_setpoint_heat": capabilities.target_temp_heat,
                        # Zone damper position
                        # (convert from 0-20 API scale to 0-100 percentage)
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

                    # Match peripheral data by sensor serial
                    self._enrich_zone_with_peripheral(
                        zone, zone_data, capabilities, peripherals
                    )

                    zones[zone_id] = cast("ZoneData", zone_data)

        return zones

    @staticmethod
    def _get_zone_enabled(user_aircon_settings: dict, zone_index: int) -> bool:
        """Check if a zone is enabled by index."""
        enabled_zones = user_aircon_settings.get("EnabledZones", [])
        if zone_index < len(enabled_zones):
            return enabled_zones[zone_index]
        return False

    def _enrich_zone_with_peripheral(
        self,
        zone: dict,
        zone_data: dict,
        capabilities: ZoneCapabilities,
        peripherals: list,
    ) -> None:
        """Enrich zone data with matching peripheral information."""
        zone_sensors = zone.get("Sensors", {})
        zone_sensor_kind = ""

        # Find device ID with case-insensitive matching
        for device_key, sensor_data in zone_sensors.items():
            if device_key.lower() == self.device_id.lower():
                zone_sensor_kind = sensor_data.get("NV_Kind", "")
                break

        # Extract serial from NV_Kind (format: "ZS: 23E01206")
        if not zone_sensor_kind.startswith("ZS: "):
            return

        zone_serial = zone_sensor_kind.replace("ZS: ", "")

        # Find matching peripheral by serial number
        for peripheral in peripherals:
            if peripheral.get("SerialNumber", "") != zone_serial:
                continue

            zone_data.update(
                {
                    "battery_level": peripheral.get("RemainingBatteryCapacity_pc"),
                    "signal_strength": peripheral.get("RSSI", {}).get("Local"),
                    "peripheral_type": peripheral.get("DeviceType"),
                    "last_connection": peripheral.get("LastConnectionTime"),
                    "connection_state": peripheral.get("ConnectionState"),
                }
            )

            # Add peripheral capabilities if present
            if peripheral.get("ControlCapabilities"):
                zone_data["capabilities"] = capabilities.model_copy(
                    update={
                        "peripheral_capabilities": peripheral.get("ControlCapabilities")
                    }
                )
            break

    async def _maybe_cleanup_cache(self) -> None:
        """Perform periodic cache cleanup if needed."""
        now = datetime.datetime.now()  # noqa: DTZ005

        # Cleanup every 5 minutes
        if (
            self._last_cache_cleanup is None
            or (now - self._last_cache_cleanup).total_seconds() > 300  # noqa: PLR2004
        ):
            await self.api.cleanup_expired_cache()
            self._last_cache_cleanup = now

    async def _maybe_cleanup_memory(self) -> None:
        """Perform periodic memory optimization cleanup."""
        now = datetime.datetime.now()  # noqa: DTZ005

        # Memory cleanup every 10 minutes
        if (
            self._last_memory_cleanup is None
            or (now - self._last_memory_cleanup).total_seconds() > 600  # noqa: PLR2004
        ):
            # Clear parsed data cache if we have too many cache misses
            cache_hit_rate = self._cache_hit_count / max(
                1, self._cache_hit_count + self._cache_miss_count
            )

            if cache_hit_rate < 0.3:  # noqa: PLR2004
                self._parsed_data_cache = None
                self._raw_data_hash = None

            # Reset counters periodically
            if self._cache_hit_count + self._cache_miss_count > 1000:  # noqa: PLR2004
                self._cache_hit_count = 0
                self._cache_miss_count = 0

            self._last_memory_cleanup = now

    def _validate_fan_modes(self, modes: Any) -> list[str]:
        """
        Validate and normalize supported fan modes.

        Note on Actron Quirks:
        - NV_SupportedFanModes is a bitmap where:
            1=LOW, 2=MED, 4=HIGH, 8=AUTO
        - Some devices omit HIGH from NV_SupportedFanModes even though
            they support it. If we detect HIGH mode in current settings,
            we add it to supported modes regardless of bitmap.
        - When in doubt, we fall back to [LOW, MED, HIGH] as defaults.
        """
        default_modes = ["LOW", "MED", "HIGH"]

        try:
            if isinstance(modes, int):
                return self._decode_fan_mode_bitmap(modes, default_modes)

            return self._parse_fan_mode_list(modes, default_modes)

        except (KeyError, TypeError, ValueError):
            return default_modes

    def _decode_fan_mode_bitmap(
        self, modes: int, default_modes: list[str]
    ) -> list[str]:
        """
        Decode fan mode bitmap value from the API.

        Args:
            modes: Bitmap integer (1=LOW, 2=MED, 4=HIGH, 8=AUTO)
            default_modes: Fallback modes if decoding fails

        Returns:
            List of supported fan mode strings

        """
        # Get current fan mode to check for HIGH support
        current_mode = self._get_current_fan_mode()

        # Process bitmap
        supported: list[str] = []
        if modes & 1:
            supported.append("LOW")
        if modes & 2:
            supported.append("MED")
        if modes & 4:
            supported.append("HIGH")
        if modes & 8:
            auto_enabled = self._is_auto_fan_enabled()
            if auto_enabled:
                supported.append("AUTO")

        # Use defaults if HIGH mode active or basic modes set
        if current_mode == "HIGH" or modes & 0x03:
            return default_modes

        return supported or default_modes

    def _get_current_fan_mode(self) -> str | None:
        """Get the current fan mode from coordinator data."""
        if not (hasattr(self, "data") and self.data is not None):
            return None

        user_settings = (
            self.data.get("raw_data", {})
            .get("lastKnownState", {})
            .get("UserAirconSettings", {})
        )
        return user_settings.get("FanMode", "")

    def _is_auto_fan_enabled(self) -> bool:
        """Check if AUTO fan mode is enabled on the indoor unit."""
        if not (hasattr(self, "data") and self.data is not None):
            return False
        indoor_unit = (
            self.data.get("raw_data", {})
            .get("lastKnownState", {})
            .get("AirconSystem", {})
            .get("IndoorUnit", {})
        )
        return indoor_unit.get("NV_AutoFanEnabled", False)

    @staticmethod
    def _parse_fan_mode_list(modes: Any, default_modes: list[str]) -> list[str]:
        """
        Parse fan modes from string, list, or other formats.

        Args:
            modes: Fan mode input (string, list, or other)
            default_modes: Fallback modes

        Returns:
            List of valid fan mode strings

        """
        valid_modes = {"LOW", "MED", "HIGH", "AUTO"}

        if not modes:
            return default_modes

        if isinstance(modes, str):
            modes = [m.strip().upper() for m in modes.split(",")]
        elif isinstance(modes, (list, tuple)):
            modes = [str(m).strip().upper() for m in modes]

        supported = [m for m in modes if m in valid_modes]
        return supported or default_modes

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

            # Extract serial from NV_Kind (format: "ZS: 23E01206")
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

        except (KeyError, ValueError, IndexError):
            pass
        return None

    def get_zone_last_updated(self, zone_id: str) -> str | None:
        """Get last update time for a specific zone."""
        try:
            peripheral_data = self.get_zone_peripheral(zone_id)
        except (KeyError, ValueError, IndexError):
            return None
        else:
            return (
                peripheral_data.get("LastConnectionTime") if peripheral_data else None
            )

    async def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            command = self.api.create_command("OFF")
        else:
            command = self.api.create_command("CLIMATE_MODE", mode=hvac_mode)
        await self.api.send_command(self.device_id, command)
        await self.async_request_refresh()

    async def set_temperature(self, temperature: float, *, is_cooling: bool) -> None:
        """Set temperature."""
        command = self.api.create_command(
            "SET_TEMP", temp=temperature, is_cool=is_cooling
        )
        await self.api.send_command(self.device_id, command)
        await self.async_request_refresh()

    async def set_fan_mode(
        self, mode: FanModeType, *, continuous: bool | None = None
    ) -> None:
        """
        Set fan mode with state tracking, validation and retry.

        Args:
            mode: The fan mode to set (LOW, MED, HIGH, AUTO)
            continuous: Whether to enable continuous fan mode.
                If None, maintains current state.

        Raises:
            ApiError: If communication with the API fails
            ValueError: If the fan mode is invalid
            RateLimitError: If too many requests are made

        """
        # If continuous is not specified, maintain current state
        if continuous is None:
            current_mode = self.data["main"].get("fan_mode", "")
            continuous = current_mode.endswith("+CONT")

        # Rate limiting check
        async with self._fan_mode_change_lock:
            await self._throttle_fan_mode_change()

            validated_mode = self.validate_fan_mode(mode, continuous=continuous)

            await self._send_fan_mode_with_retry(validated_mode, continuous=continuous)

    async def _throttle_fan_mode_change(self) -> None:
        """Apply rate limiting for fan mode changes."""
        if self._last_fan_mode_change:
            elapsed = (
                datetime.datetime.now()  # noqa: DTZ005
                - self._last_fan_mode_change
            ).total_seconds()
            if elapsed < self._min_fan_mode_interval:
                wait_time = self._min_fan_mode_interval - elapsed
                await asyncio.sleep(wait_time)

    async def _send_fan_mode_with_retry(
        self, validated_mode: str, *, continuous: bool
    ) -> None:
        """
        Send fan mode command with retry logic.

        Args:
            validated_mode: The validated fan mode string
            continuous: Whether continuous fan mode is enabled

        """
        for attempt in range(MAX_RETRIES):
            try:
                command = self.api.create_command("FAN_MODE", mode=validated_mode)

                await self.api.send_command(self.device_id, command)

                # Update state tracking
                self._last_fan_mode_change = (
                    datetime.datetime.now()  # noqa: DTZ005
                )
                self._continuous_fan = continuous

                # Force immediate refresh (blocking to ensure fresh data
                # before verification)
                await self.async_refresh()

                # Verify the change
                new_mode = self.data["main"].get("fan_mode", "")

                # Validate continuous mode was set correctly
                if continuous and "+CONT" not in new_mode:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    _LOGGER.warning(
                        "Failed to set continuous mode after %d attempts",
                        MAX_RETRIES,
                    )

                break

            except ApiError as e:
                if (
                    e.status_code in RETRYABLE_STATUS_CODES
                    and attempt < MAX_RETRIES - 1
                ):
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                    continue
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
            msg = "Zone control is not enabled"
            raise ConfigurationError(msg, config_key="enable_zone_control")

        if not self.last_data:
            msg = "No system data available"
            raise ZoneError(msg, zone_id=zone_id)

        zones_data = self.last_data.get("zones", {})
        zone_data = zones_data.get(zone_id)

        if not zone_data:
            msg = f"Zone {zone_id} not found"
            raise ZoneError(msg, zone_id=zone_id)

        # Note: We allow setting temperature for disabled zones as the
        # ActronAir API supports this. It's useful for pre-setting
        # temperatures before enabling zones.

        # Validate temperature range
        if not (MIN_TEMP <= temperature <= MAX_TEMP):
            msg = (
                f"Temperature {temperature} outside "
                f"valid range [{MIN_TEMP}, {MAX_TEMP}]"
            )
            raise ZoneError(
                msg,
                zone_id=zone_id,
            )

        # Check zone capabilities
        capabilities = zone_data.get("capabilities")
        if not capabilities or not capabilities.has_temp_control:
            msg = f"Zone {zone_id} does not support temperature control"
            raise ZoneError(msg, zone_id=zone_id)

        zone_index = int(zone_id.split("_")[1]) - 1
        command = self.api.create_command(
            "SET_ZONE_TEMP",
            zone=zone_index,
            temp=temperature,
            temp_key=temp_key,
        )
        await self.api.send_command(self.device_id, command)
        await self.async_request_refresh()

    async def set_zone_state(self, zone_id: str | int, *, enable: bool) -> None:
        """
        Set zone state.

        Args:
            zone_id: Zone ID string ('zone_1') or direct index (0-7)
            enable: True to enable zone, False to disable

        """
        # Handle both string zone_id and direct integer index
        if isinstance(zone_id, str):
            zone_index = int(zone_id.split("_")[1]) - 1
        else:
            zone_index = int(zone_id)

        # Use current data if available, otherwise fetch fresh
        if self.last_data and "main" in self.last_data:
            current_zone_status = self.last_data["main"]["EnabledZones"]
        else:
            current_zone_status = await self.api.get_zone_statuses()

        modified_statuses = current_zone_status.copy()

        # Ensure zone_index is within bounds
        self._validate_zone_index(zone_index, len(modified_statuses))
        modified_statuses[zone_index] = enable
        command = self.api.create_command("SET_ZONE_STATE", zones=modified_statuses)
        await self.api.send_command(self.device_id, command)
        await self.async_request_refresh()

    @staticmethod
    def _validate_zone_index(zone_index: int, max_zones: int) -> None:
        """
        Validate zone index is within bounds.

        Args:
            zone_index: The zone index to validate
            max_zones: Maximum number of zones

        Raises:
            ValueError: If zone index is out of range

        """
        if not (0 <= zone_index < max_zones):
            msg = f"Zone index {zone_index} out of range"
            raise ValueError(msg)

    async def set_zone_airflow(self, zone_index: int, airflow_percentage: int) -> None:
        """Set zone airflow percentage (YourZone control)."""
        await self.api.set_zone_airflow(zone_index, airflow_percentage)
        await self.async_request_refresh()

    async def set_climate_mode(self, mode: str) -> None:
        """Set climate mode for all zones."""
        command = self.api.create_command("CLIMATE_MODE", mode=mode)
        await self.api.send_command(self.device_id, command)
        await self.async_request_refresh()

    async def set_away_mode(self, *, state: bool) -> None:
        """Set away mode."""
        await self.api.set_away_mode(state=state)
        await self.async_request_refresh()

    async def set_quiet_mode(self, *, state: bool) -> None:
        """Set quiet mode."""
        await self.api.set_quiet_mode(state=state)
        await self.async_request_refresh()

    async def set_turbo_mode(self, *, state: bool) -> None:
        """Set turbo mode."""
        await self.api.set_turbo_mode(state=state)
        await self.async_request_refresh()

    async def set_after_hours(self, *, enabled: bool) -> None:
        """Set after hours mode."""
        await self.api.set_after_hours(enabled=enabled)
        await self.async_request_refresh()

    async def set_after_hours_duration(self, duration: int) -> None:
        """Set after hours duration in minutes."""
        await self.api.set_after_hours_duration(duration)
        await self.async_request_refresh()

    async def force_update(self) -> None:
        """Force an immediate update of the device data."""
        await self.api.clear_all_caches()
        await self.async_refresh()

    async def invalidate_cache(self) -> None:
        """Invalidate cached data to force fresh API calls."""
        await self.api._invalidate_status_cache(  # noqa: SLF001
            self.device_id
        )

    async def cleanup_expired_cache(self) -> None:
        """Clean up expired cache entries."""
        await self.api.cleanup_expired_cache()

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
        except Exception:
            _LOGGER.exception("Failed to initialize zone management")

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

    async def async_apply_zone_preset(self, preset_name: str) -> None:
        """
        Apply a zone preset.

        Args:
            preset_name: Name of preset to apply

        Raises:
            ConfigurationError: If preset not found or fails

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
                if "enabled" in zone_config:
                    await self.set_zone_state(zone_id, enable=zone_config["enabled"])

                # Set temperatures if zone supports it
                if self.last_data and zone_id in self.last_data["zones"]:
                    await self._apply_zone_preset_temps(zone_id, zone_config)

            except Exception:
                _LOGGER.exception("Failed to apply preset to zone %s", zone_id)

        await self.async_request_refresh()

    async def _apply_zone_preset_temps(self, zone_id: str, zone_config: dict) -> None:
        """
        Apply temperature settings from a zone preset.

        Args:
            zone_id: The zone to apply temperatures to
            zone_config: Zone configuration from preset

        """
        if not self.last_data:
            return

        zone_data = self.last_data["zones"].get(zone_id)
        if not zone_data:
            return

        capabilities = zone_data.get("capabilities")
        if not capabilities or not capabilities.has_temp_control:
            return

        if zone_config.get("temp_cool") is not None:
            await self.set_zone_temperature(
                zone_id,
                zone_config["temp_cool"],
                "temp_setpoint_cool",
            )
        if zone_config.get("temp_heat") is not None:
            await self.set_zone_temperature(
                zone_id,
                zone_config["temp_heat"],
                "temp_setpoint_heat",
            )

    async def async_bulk_zone_operation(
        self,
        operation: str,
        zones: list[str],
        **kwargs: Any,
    ) -> list[dict[str, str]]:
        """
        Perform bulk operations on multiple zones.

        Args:
            operation: Operation type ('enable', 'disable', 'set_temperature')
            zones: List of zone IDs
            **kwargs: Additional operation parameters

        Raises:
            ConfigurationError: If zone control disabled or invalid op
            ZoneError: If zone operation fails

        Returns:
            List of result dicts with zone_id and status

        """
        if not self.enable_zone_control:
            msg = "Zone control is not enabled"
            raise ConfigurationError(msg)

        valid_operations = {"enable", "disable", "set_temperature"}
        if operation not in valid_operations:
            msg = f"Invalid operation: {operation}"
            raise ConfigurationError(msg)

        results: list[dict[str, str]] = []
        for zone_id in zones:
            try:
                result = await self._execute_bulk_zone_op(operation, zone_id, **kwargs)
                results.append(result)
            except Exception:  # noqa: BLE001
                results.append(
                    {
                        "zone_id": zone_id,
                        "status": "error",
                        "error": "operation failed",
                    }
                )

        await self.async_request_refresh()
        return results

    async def _execute_bulk_zone_op(
        self,
        operation: str,
        zone_id: str,
        **kwargs: Any,
    ) -> dict[str, str]:
        """
        Execute a single bulk zone operation.

        Args:
            operation: The operation to perform
            zone_id: Target zone ID
            **kwargs: Additional parameters

        Returns:
            Result dict with zone_id and status

        """
        if operation == "enable":
            await self.set_zone_state(zone_id, enable=True)
        elif operation == "disable":
            await self.set_zone_state(zone_id, enable=False)
        elif operation == "set_temperature":
            temperature = kwargs.get("temperature")
            temp_key = kwargs.get("temp_key", "temp_setpoint_cool")
            if temperature is None:
                return {
                    "zone_id": zone_id,
                    "status": "error",
                    "error": "No temperature provided",
                }
            await self.set_zone_temperature(zone_id, temperature, temp_key)
        return {"zone_id": zone_id, "status": "success"}

    def _convert_damper_position(self, api_position: int | None) -> int:
        """
        Convert damper position from API scale (0-20) to percentage.

        The ActronAir Neo API returns damper positions in a 0-20
        scale. This converts to 0-100 percentage for Home Assistant.

        Args:
            api_position: Raw damper position from API (0-20), or None

        Returns:
            Damper position as percentage (0-100), or 0 if invalid

        """
        if api_position is None:
            return 0

        try:
            # Clamp to valid range to handle unexpected values
            api_position = max(0, min(20, int(api_position)))
            percentage = (api_position * 100) // 20
            return min(100, percentage)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_outdoor_temp(
        raw_value: float | None,
        outdoor_unit: dict | None = None,
    ) -> float | None:
        """
        Parse outdoor temperature, filtering sentinel values.

        The API returns 3000.0 for LiveOutdoorTemp_oC when the outdoor
        temperature sensor is unavailable (common on Classic series units).
        In that case, fall back to OutdoorUnit.AmbTemp from LiveAircon,
        but only when the outdoor unit's ambient sensor is healthy
        (AmbientSensErr is False).

        Args:
            raw_value: Raw temperature from MasterInfo.LiveOutdoorTemp_oC
            outdoor_unit: LiveAircon.OutdoorUnit dict (contains AmbTemp
                and AmbientSensErr)

        Returns:
            Temperature in Celsius, or None if unavailable

        """
        if raw_value is not None and raw_value < OUTDOOR_TEMP_UNAVAILABLE:
            return raw_value
        # Fall back to outdoor unit ambient sensor only if no sensor error
        if outdoor_unit and not outdoor_unit.get("AmbientSensErr", True):
            amb_temp = outdoor_unit.get("AmbTemp")
            if amb_temp is not None:
                return amb_temp
        return None

    @staticmethod
    def _parse_warnings(live_aircon: dict) -> list[str]:
        """
        Parse active warnings from LiveAircon data.

        Checks outdoor unit error codes and other warning indicators.

        Args:
            live_aircon: LiveAircon section from API response

        Returns:
            List of active warning descriptions

        """
        warnings: list[str] = []
        outdoor_unit = live_aircon.get("OutdoorUnit", {})

        for key in ("ErrCode_1", "ErrCode_2", "ErrCode_3", "ErrCode_4", "ErrCode_5"):
            code = outdoor_unit.get(key, 0)
            if code and code != 0:
                warnings.append(f"{key}: {code}")

        if outdoor_unit.get("LPErr", 0) != 0:
            warnings.append(f"Low Pressure Error: {outdoor_unit['LPErr']}")
        if outdoor_unit.get("HPErr", 0) != 0:
            warnings.append(f"High Pressure Error: {outdoor_unit['HPErr']}")

        # Check main error code
        err_code = live_aircon.get("ErrCode", 0)
        if err_code and err_code != 0:
            warnings.append(f"System Error: {err_code}")

        return warnings

"""
Data models for the ActronAir Neo API.

All API response structures and internal data types are defined here
as Pydantic BaseModel classes with full validation and coercion.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

FALLBACK_SUPPORTED_MODES: tuple[str, ...] = ("COOL", "HEAT", "FAN", "AUTO")
_SENTINEL_THRESHOLD = 1000.0
_MAX_HUMIDITY = 100.0


def _coerce_optional_str(value: Any) -> str | None:
    """Coerce numeric firmware/model/serial fields (e.g. ModelNumber=561) to str."""
    if value is None or isinstance(value, bool):
        return None
    return str(value)


def _coerce_str(value: Any) -> str:
    """Coerce non-None scalar values to string."""
    if value is None or isinstance(value, bool):
        return ""
    return str(value)


def _filter_sentinel_temp(value: Any) -> float | None:
    """Filter Actron API sentinel values (>= 1000.0, e.g. 3000.0) for temperatures."""
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num >= _SENTINEL_THRESHOLD:
        return None
    return num


def _filter_sentinel_humidity(value: Any) -> float | None:
    """Filter Actron API sentinel values and out-of-range readings for humidity."""
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num < 0.0 or num > _MAX_HUMIDITY:
        return None
    return num


def _coerce_signal(value: Any) -> int | None:
    """Coerce Signal_of3 (int or string like '2' or 'NA') to int | None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


# --- API response models ---


class TokenResponse(BaseModel):
    """Response from the OAuth token endpoint."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    access_token: str
    token_type: str = Field(default="Bearer")
    expires_in: int = 3600
    refresh_token: str | None = None


class ActronAirUserInfo(BaseModel):
    """User account information from /api/v0/client/account."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    id: str = Field(default="", validation_alias=AliasChoices("id", "sub", "userId"))
    email: str = Field(default="")
    name: str = Field(default="")


class DeviceInfo(BaseModel):
    """Device information returned from the AC systems endpoint."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    serial: str
    name: str
    type: str
    id: str
    base_url: str = ""
    links: dict[str, str] = Field(default_factory=dict)

    @field_validator("serial", "name", "type", "id", mode="before")
    @classmethod
    def _coerce_strings(cls, value: Any) -> str:
        return _coerce_str(value)


class ModeSupport(BaseModel):
    """Hardware HVAC mode support flags from UserAirconSettings.ModeSupport."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    cool: bool = Field(default=True, alias="Cool")
    heat: bool = Field(default=True, alias="Heat")
    fan: bool = Field(default=True, alias="Fan")
    auto: bool = Field(default=True, alias="Auto")
    dry: bool = Field(default=False, alias="Dry")

    @property
    def supported_modes(self) -> list[str]:
        """Return list of enabled Actron HVAC modes."""
        modes: list[str] = []
        if self.cool:
            modes.append("COOL")
        if self.heat:
            modes.append("HEAT")
        if self.fan:
            modes.append("FAN")
        if self.auto:
            modes.append("AUTO")
        if self.dry:
            modes.append("DRY")
        return modes or list(FALLBACK_SUPPORTED_MODES)


class UserSetpointLimits(BaseModel):
    """Hardware temperature setpoint limits and Que/NX-Gen signed zone variances."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    set_cool_min: float = Field(default=16.0, alias="setCool_Min")
    set_cool_max: float = Field(default=30.0, alias="setCool_Max")
    set_heat_min: float = Field(default=16.0, alias="setHeat_Min")
    set_heat_max: float = Field(default=30.0, alias="setHeat_Max")
    variance_above_cool: float | None = Field(
        default=None, alias="VarianceAboveMasterCool"
    )
    variance_below_cool: float | None = Field(
        default=None, alias="VarianceBelowMasterCool"
    )
    variance_above_heat: float | None = Field(
        default=None, alias="VarianceAboveMasterHeat"
    )
    variance_below_heat: float | None = Field(
        default=None, alias="VarianceBelowMasterHeat"
    )


# --- Zone-related models ---


class ZoneCapabilities(BaseModel):
    """Capabilities for a single zone."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    exists: bool = False
    can_operate: bool = False
    has_temp_control: bool = False
    has_separate_targets: bool = False
    target_temp_cool: float | None = None
    target_temp_heat: float | None = None
    peripheral_capabilities: dict[str, bool] | None = None
    nv_vav: bool = False
    nv_itc: bool = False
    nv_itd: bool = False
    nv_ihd: bool = False
    nv_iac: bool = False


class ZoneData(BaseModel):
    """Parsed zone data used by the coordinator and entities."""

    model_config = ConfigDict(frozen=False, populate_by_name=True, extra="ignore")

    name: str
    temp: float | None = None
    setpoint: float | None = None
    is_on: bool = False
    capabilities: ZoneCapabilities = Field(default_factory=ZoneCapabilities)
    humidity: float | None = None
    is_enabled: bool = False
    temp_setpoint_cool: float | None = None
    temp_setpoint_heat: float | None = None
    battery_level: int | None = None
    signal_strength: int | None = None
    peripheral_type: str | None = None
    last_connection: str | None = None
    connection_state: str | None = None
    damper_position: int | None = None
    # YourZone airflow control fields
    airflow_setpoint: int | None = None
    airflow_control_enabled: bool = False
    airflow_control_locked: bool = False
    zone_max_position: int | None = None
    zone_min_position: int | None = None
    # Controller-published zone setpoint limits
    min_cool_setpoint: float | None = Field(default=None, alias="MinCoolSetpoint")
    max_cool_setpoint: float | None = Field(default=None, alias="MaxCoolSetpoint")
    min_heat_setpoint: float | None = Field(default=None, alias="MinHeatSetpoint")
    max_heat_setpoint: float | None = Field(default=None, alias="MaxHeatSetpoint")

    @field_validator(
        "temp",
        "min_cool_setpoint",
        "max_cool_setpoint",
        "min_heat_setpoint",
        "max_heat_setpoint",
        mode="before",
    )
    @classmethod
    def _validate_temp(cls, value: Any) -> float | None:
        return _filter_sentinel_temp(value)

    @field_validator("humidity", mode="before")
    @classmethod
    def _validate_humidity(cls, value: Any) -> float | None:
        return _filter_sentinel_humidity(value)

    @field_validator("signal_strength", mode="before")
    @classmethod
    def _validate_signal(cls, value: Any) -> int | None:
        return _coerce_signal(value)


# --- Main AC data model ---


class MainData(BaseModel):
    """Main AC system data parsed from the API response."""

    model_config = ConfigDict(frozen=False, populate_by_name=True, extra="ignore")

    is_on: bool = False
    mode: str = "OFF"
    fan_mode: str = "LOW"
    fan_continuous: bool = False
    base_fan_mode: str = "LOW"
    supported_fan_modes: list[str] | frozenset[str] = Field(
        default_factory=lambda: ["LOW", "MED", "HIGH"]
    )
    temp_setpoint_cool: float | None = None
    temp_setpoint_heat: float | None = None
    indoor_temp: float | None = None
    indoor_humidity: float | None = None
    compressor_state: str = "OFF"
    enabled_zones: list[bool] = Field(default_factory=list[bool], alias="EnabledZones")
    model: str = ""
    firmware_version: str = ""
    away_mode: bool = False
    quiet_mode: bool = False
    indoor_model: str | None = None
    serial_number: str | None = None
    filter_clean_required: bool = False
    defrosting: bool = False
    # Extended API coverage fields
    turbo_mode_supported: bool = False
    turbo_mode_enabled: bool = False
    after_hours_enabled: bool = False
    after_hours_duration: int = 120
    outdoor_temp: float | None = None
    fast_heating: bool = False
    quiet_mode_supported: bool = False
    quiet_mode_active: bool = False
    service_reminder_enabled: bool = False
    service_reminder_time: str = "NA"
    warnings: list[str] = Field(default_factory=list)
    dry_mode_supported: bool = False
    supported_hvac_modes: list[str] = Field(
        default_factory=lambda: list(FALLBACK_SUPPORTED_MODES)
    )
    min_temp_cool: float = 16.0
    max_temp_cool: float = 30.0
    min_temp_heat: float = 16.0
    max_temp_heat: float = 30.0
    zone_temp_variance: float = 0.0
    variance_above_cool: float | None = None
    variance_below_cool: float | None = None
    variance_above_heat: float | None = None
    variance_below_heat: float | None = None

    @field_validator("model", "firmware_version", mode="before")
    @classmethod
    def _coerce_required_str(cls, value: Any) -> str:
        return _coerce_str(value)

    @field_validator("indoor_model", "serial_number", mode="before")
    @classmethod
    def _coerce_opt_str(cls, value: Any) -> str | None:
        return _coerce_optional_str(value)

    @field_validator("indoor_temp", "outdoor_temp", mode="before")
    @classmethod
    def _validate_temps(cls, value: Any) -> float | None:
        return _filter_sentinel_temp(value)

    @field_validator("indoor_humidity", mode="before")
    @classmethod
    def _validate_humidity(cls, value: Any) -> float | None:
        return _filter_sentinel_humidity(value)


class LiveAirconData(BaseModel):
    """Live aircon operational data."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    system_on: bool = False
    compressor_capacity: int = 0
    compressor_mode: str = "OFF"
    am_running_fan: bool = False
    fan_rpm: int = 0
    fan_pwm: int = 0
    coil_inlet: float | None = None
    err_code: int = 0
    compressor_chasing_temp: float | None = None
    compressor_live_temp: float | None = None


class OutdoorUnitData(BaseModel):
    """Outdoor unit live and system data."""

    model_config = ConfigDict(frozen=False, populate_by_name=True, extra="ignore")

    comp_power: float = 0.0
    compressor_on: bool = False
    comp_speed: int = 0
    coil_temp: float | None = None
    amb_temp: float | None = None
    supply_voltage: float = 0.0
    supply_current: float = 0.0
    supply_power: float = 0.0
    reverse_valve_position: str = "Unknown"
    defrost_mode: int = 0
    drm: bool = False
    err_codes: list[int] = Field(default_factory=lambda: [0, 0, 0, 0, 0])
    family: str = ""
    ctrl_board_type: str = ""
    capacity_kw: float = 0.0
    model_number: str = ""
    software_version: str = ""
    serial_number: str = Field(default="", alias="SerialNumber")

    @field_validator(
        "family",
        "ctrl_board_type",
        "model_number",
        "software_version",
        "serial_number",
        mode="before",
    )
    @classmethod
    def _coerce_strings(cls, value: Any) -> str:
        return _coerce_str(value)


class SystemStatusData(BaseModel):
    """Device system status data."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    uptime_seconds: int = 0
    board_temp: float | None = None
    wifi_strength: int | None = None
    wifi_ssid: str = "Unknown"
    wifi_channel: str = "Unknown"
    wifi_firmware: str = "Unknown"
    wifi_hw_errors: int = 0


class CloudConnectionData(BaseModel):
    """Cloud connection data."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    connection_state: str = "Unknown"
    session_uptime: int = 0
    sent_packets: int = 0
    received_packets: int = 0
    failed_sent_packets: int = 0
    session_count_since_reset: int = 0
    dns_failures: int = 0
    aborted_sockets: int = 0


class ServicingData(BaseModel):
    """Servicing and error history data."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    error_history: list[Any] = Field(default_factory=list)
    event_history: list[Any] = Field(default_factory=list)


class ConnectionMetadata(BaseModel):
    """Top-level connection metadata."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    is_online: bool = False
    last_status_update: str = "Unknown"
    time_since_last_contact: str = "Unknown"


class VFTData(BaseModel):
    """Variable fan technology data."""

    model_config = ConfigDict(frozen=False, extra="ignore")

    supported: bool = False
    airflow: float = 0.0


class CoordinatorData(BaseModel):
    """Top-level data structure held by the coordinator."""

    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    main: MainData = Field(default_factory=MainData)
    zones: dict[str, ZoneData] = Field(default_factory=dict)
    live_aircon: LiveAirconData = Field(default_factory=LiveAirconData)
    outdoor_unit: OutdoorUnitData = Field(default_factory=OutdoorUnitData)
    system_status: SystemStatusData = Field(default_factory=SystemStatusData)
    cloud: CloudConnectionData = Field(default_factory=CloudConnectionData)
    servicing: ServicingData = Field(default_factory=ServicingData)
    connection_meta: ConnectionMetadata = Field(default_factory=ConnectionMetadata)
    vft: VFTData = Field(default_factory=VFTData)


# --- Raw API response type-hint models ---


class MasterSensorInfo(BaseModel):
    """Master sensor information from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    live_temp: float | None = Field(None, alias="LiveTemp_oC")
    live_humidity: float | None = Field(None, alias="LiveHumidity_pc")


class LiveAirconInfo(BaseModel):
    """Live aircon information from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    compressor_mode: str = Field("OFF", alias="CompressorMode")
    filter_info: dict[str, bool | int] = Field(default_factory=dict, alias="Filter")


class UserAirconSettings(BaseModel):
    """User aircon settings from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    is_on: bool = Field(default=False, alias="isOn")
    mode: str = Field(default="OFF", alias="Mode")
    fan_mode: str = Field(default="LOW", alias="FanMode")
    temp_setpoint_cool: float = Field(default=24.0, alias="TemperatureSetpoint_Cool_oC")
    temp_setpoint_heat: float = Field(default=22.0, alias="TemperatureSetpoint_Heat_oC")
    enabled_zones: list[bool] = Field(default_factory=list[bool], alias="EnabledZones")
    away_mode: bool = Field(default=False, alias="AwayMode")
    quiet_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("QuietMode", "QuietModeEnabled"),
    )


class LastKnownState(BaseModel):
    """Last known state of the AC system from API."""

    model_config = ConfigDict(frozen=False, populate_by_name=True, extra="ignore")

    master_info: dict[str, Any] = Field(default_factory=dict, alias="MasterInfo")
    live_aircon: dict[str, Any] = Field(default_factory=dict, alias="LiveAircon")
    user_aircon_settings: dict[str, Any] = Field(
        default_factory=dict, alias="UserAirconSettings"
    )
    remote_zone_info: list[dict[str, Any]] = Field(
        default_factory=list[dict[str, Any]], alias="RemoteZoneInfo"
    )
    aircon_system: dict[str, Any] = Field(default_factory=dict, alias="AirconSystem")
    alerts: dict[str, bool] = Field(default_factory=dict, alias="Alerts")


class AcStatusResponse(BaseModel):
    """AC status response from the API."""

    model_config = ConfigDict(frozen=False, populate_by_name=True, extra="ignore")

    last_known_state: LastKnownState = Field(
        default_factory=LastKnownState, alias="lastKnownState"
    )


class CommandResponse(BaseModel):
    """Response from sending a command to the AC system."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    success: bool = True
    message: str | None = None


class PeripheralData(BaseModel):
    """Peripheral device data from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    remaining_battery_capacity: int | None = Field(
        None, alias="RemainingBatteryCapacity_pc"
    )
    signal_of3: int | None = Field(None, alias="Signal_of3")
    device_type: str | None = Field(None, alias="DeviceType")
    last_connection_time: str | None = Field(None, alias="LastConnectionTime")
    connection_state: str | None = Field(None, alias="ConnectionState")
    zone_assignment: list[int] = Field(
        default_factory=list[int], alias="ZoneAssignment"
    )
    control_capabilities: dict[str, bool] | None = Field(
        None, alias="ControlCapabilities"
    )
    serial_number: str | None = Field(None, alias="SerialNumber")

    @field_validator("signal_of3", mode="before")
    @classmethod
    def _validate_signal(cls, value: Any) -> int | None:
        return _coerce_signal(value)

    @field_validator("serial_number", mode="before")
    @classmethod
    def _validate_serial(cls, value: Any) -> str | None:
        return _coerce_optional_str(value)


class CommandData(BaseModel):
    """Command data structure for API requests."""

    model_config = ConfigDict(frozen=False)

    command: dict[str, Any] = Field(default_factory=dict)


# --- Literal types for fan and HVAC modes ---

FanModeType = Literal["LOW", "MED", "HIGH", "AUTO"]
HvacModeType = Literal["COOL", "HEAT", "FAN", "AUTO", "DRY", "OFF"]

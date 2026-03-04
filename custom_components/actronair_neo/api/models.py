"""
Data models for the ActronAir Neo API.

All API response structures and internal data types are defined here
as Pydantic BaseModel classes with full validation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# --- API response models ---


class TokenResponse(BaseModel):
    """Response from the OAuth token endpoint."""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str = Field(default="Bearer")
    expires_in: int = 3600
    refresh_token: str | None = None


class DeviceInfo(BaseModel):
    """Device information returned from the AC systems endpoint."""

    model_config = ConfigDict(frozen=True)

    serial: str
    name: str
    type: str
    id: str
    base_url: str = ""


# --- Zone-related models ---


class ZoneCapabilities(BaseModel):
    """Capabilities for a single zone."""

    model_config = ConfigDict(frozen=True)

    exists: bool = False
    can_operate: bool = False
    has_temp_control: bool = False
    has_separate_targets: bool = False
    target_temp_cool: float | None = None
    target_temp_heat: float | None = None
    peripheral_capabilities: dict[str, bool] | None = None


class ZoneData(BaseModel):
    """Parsed zone data used by the coordinator and entities."""

    model_config = ConfigDict(frozen=False)

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


# --- Main AC data model ---


class MainData(BaseModel):
    """Main AC system data parsed from the API response."""

    model_config = ConfigDict(frozen=False, populate_by_name=True)

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
    enabled_zones: list[bool] = Field(default_factory=list, alias="EnabledZones")
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


class LiveAirconData(BaseModel):
    """Live aircon operational data."""

    model_config = ConfigDict(frozen=False)

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

    model_config = ConfigDict(frozen=False)

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


class SystemStatusData(BaseModel):
    """Device system status data."""

    model_config = ConfigDict(frozen=False)

    uptime_seconds: int = 0
    board_temp: float | None = None
    wifi_strength: int | None = None
    wifi_ssid: str = "Unknown"
    wifi_channel: str = "Unknown"
    wifi_firmware: str = "Unknown"
    wifi_hw_errors: int = 0


class CloudConnectionData(BaseModel):
    """Cloud connection data."""

    model_config = ConfigDict(frozen=False)

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

    model_config = ConfigDict(frozen=False)

    error_history: list[Any] = Field(default_factory=list)
    event_history: list[Any] = Field(default_factory=list)


class ConnectionMetadata(BaseModel):
    """Top-level connection metadata."""

    model_config = ConfigDict(frozen=False)

    is_online: bool = False
    last_status_update: str = "Unknown"
    time_since_last_contact: str = "Unknown"


class VFTData(BaseModel):
    """Variable fan technology data."""

    model_config = ConfigDict(frozen=False)

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

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    live_temp: float | None = Field(None, alias="LiveTemp_oC")
    live_humidity: float | None = Field(None, alias="LiveHumidity_pc")


class LiveAirconInfo(BaseModel):
    """Live aircon information from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    compressor_mode: str = Field("OFF", alias="CompressorMode")
    filter_info: dict[str, bool | int] = Field(default_factory=dict, alias="Filter")


class UserAirconSettings(BaseModel):
    """User aircon settings from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    is_on: bool = Field(default=False, alias="isOn")
    mode: str = Field(default="OFF", alias="Mode")
    fan_mode: str = Field(default="LOW", alias="FanMode")
    temp_setpoint_cool: float = Field(default=24.0, alias="TemperatureSetpoint_Cool_oC")
    temp_setpoint_heat: float = Field(default=22.0, alias="TemperatureSetpoint_Heat_oC")
    enabled_zones: list[bool] = Field(default_factory=list, alias="EnabledZones")
    away_mode: bool = Field(default=False, alias="AwayMode")
    quiet_mode: bool = Field(default=False, alias="QuietMode")


class LastKnownState(BaseModel):
    """Last known state of the AC system from API."""

    model_config = ConfigDict(frozen=False, populate_by_name=True)

    master_info: dict[str, Any] = Field(default_factory=dict, alias="MasterInfo")
    live_aircon: dict[str, Any] = Field(default_factory=dict, alias="LiveAircon")
    user_aircon_settings: dict[str, Any] = Field(
        default_factory=dict, alias="UserAirconSettings"
    )
    remote_zone_info: list[dict[str, Any]] = Field(
        default_factory=list, alias="RemoteZoneInfo"
    )
    aircon_system: dict[str, Any] = Field(default_factory=dict, alias="AirconSystem")
    alerts: dict[str, bool] = Field(default_factory=dict, alias="Alerts")


class AcStatusResponse(BaseModel):
    """AC status response from the API."""

    model_config = ConfigDict(frozen=False, populate_by_name=True)

    last_known_state: LastKnownState = Field(
        default_factory=LastKnownState, alias="lastKnownState"
    )


class CommandResponse(BaseModel):
    """Response from sending a command to the AC system."""

    model_config = ConfigDict(frozen=True)

    success: bool = True
    message: str | None = None


class PeripheralData(BaseModel):
    """Peripheral device data from API."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    remaining_battery_capacity: int | None = Field(
        None, alias="RemainingBatteryCapacity_pc"
    )
    signal_of3: int | None = Field(None, alias="Signal_of3")
    device_type: str | None = Field(None, alias="DeviceType")
    last_connection_time: str | None = Field(None, alias="LastConnectionTime")
    connection_state: str | None = Field(None, alias="ConnectionState")
    zone_assignment: list[int] = Field(default_factory=list, alias="ZoneAssignment")
    control_capabilities: dict[str, bool] | None = Field(
        None, alias="ControlCapabilities"
    )
    serial_number: str | None = Field(None, alias="SerialNumber")


class CommandData(BaseModel):
    """Command data structure for API requests."""

    model_config = ConfigDict(frozen=False)

    command: dict[str, Any] = Field(default_factory=dict)


# --- Literal types for fan and HVAC modes ---

FanModeType = Literal["LOW", "MED", "HIGH", "AUTO"]
HvacModeType = Literal["COOL", "HEAT", "FAN", "AUTO", "OFF"]

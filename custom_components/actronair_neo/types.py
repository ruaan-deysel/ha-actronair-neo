"""Type definitions for ActronAir Neo integration."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class TokenResponse(TypedDict):
    """Response from token endpoint."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None


class DeviceInfo(TypedDict):
    """Device information."""

    serial: str
    name: str
    type: str
    id: str


class ZoneData(TypedDict):
    """Zone data structure."""

    name: str
    temp: float | None
    setpoint: float | None
    is_on: bool
    capabilities: ZoneCapabilities
    humidity: float | None
    is_enabled: bool
    temp_setpoint_cool: float | None
    temp_setpoint_heat: float | None
    battery_level: int | None
    signal_strength: int | None
    peripheral_type: str | None
    last_connection: str | None
    connection_state: str | None
    damper_position: int | None
    # YourZone airflow control fields
    airflow_setpoint: int | None
    airflow_control_enabled: bool
    airflow_control_locked: bool
    zone_max_position: int | None
    zone_min_position: int | None


class MainData(TypedDict):
    """Main AC data structure."""

    is_on: bool
    mode: str
    fan_mode: str
    fan_continuous: bool
    base_fan_mode: str
    supported_fan_modes: list[str]
    temp_setpoint_cool: float | None
    temp_setpoint_heat: float | None
    indoor_temp: float | None
    indoor_humidity: float | None
    compressor_state: str
    EnabledZones: list[bool]
    model: str
    firmware_version: str
    away_mode: bool
    quiet_mode: bool
    indoor_model: str | None
    serial_number: str | None
    filter_clean_required: bool
    defrosting: bool
    # Extended API coverage fields
    turbo_mode_supported: bool
    turbo_mode_enabled: bool
    after_hours_enabled: bool
    after_hours_duration: int
    outdoor_temp: float | None
    fast_heating: bool
    quiet_mode_supported: bool
    quiet_mode_active: bool
    service_reminder_enabled: bool
    service_reminder_time: str
    warnings: list[str]


class LiveAirconData(TypedDict):
    """Live aircon operational data."""

    system_on: bool
    compressor_capacity: int
    compressor_mode: str
    am_running_fan: bool
    fan_rpm: int
    fan_pwm: int
    coil_inlet: float | None
    err_code: int
    compressor_chasing_temp: float | None
    compressor_live_temp: float | None


class OutdoorUnitData(TypedDict):
    """Outdoor unit live and system data."""

    comp_power: float
    compressor_on: bool
    comp_speed: int
    coil_temp: float | None
    amb_temp: float | None
    supply_voltage: float
    supply_current: float
    supply_power: float
    reverse_valve_position: str
    defrost_mode: int
    drm: bool
    err_codes: list[int]
    family: str
    ctrl_board_type: str
    capacity_kw: float


class SystemStatusData(TypedDict):
    """Device system status data."""

    uptime_seconds: int
    board_temp: float | None
    wifi_strength: int | None
    wifi_ssid: str
    wifi_channel: str
    wifi_firmware: str
    wifi_hw_errors: int


class CloudConnectionData(TypedDict):
    """Cloud connection data."""

    connection_state: str
    session_uptime: int
    sent_packets: int
    received_packets: int
    failed_sent_packets: int
    session_count_since_reset: int
    dns_failures: int
    aborted_sockets: int


class ServicingData(TypedDict):
    """Servicing and error history data."""

    error_history: list[Any]
    event_history: list[Any]


class ConnectionMetadata(TypedDict):
    """Top-level connection metadata."""

    is_online: bool
    last_status_update: str
    time_since_last_contact: str


class VFTData(TypedDict):
    """Variable fan technology data."""

    supported: bool
    airflow: float


class CoordinatorData(TypedDict):
    """Data structure for coordinator."""

    main: MainData
    zones: dict[str, ZoneData]
    live_aircon: LiveAirconData
    outdoor_unit: OutdoorUnitData
    system_status: SystemStatusData
    cloud: CloudConnectionData
    servicing: ServicingData
    connection_meta: ConnectionMetadata
    vft: VFTData


class MasterSensorInfo(TypedDict):
    """Master sensor information."""

    LiveTemp_oC: float | None
    LiveHumidity_pc: float | None


class LiveAirconInfo(TypedDict):
    """Live aircon information."""

    CompressorMode: str
    Filter: dict[str, bool | int]


class UserAirconSettings(TypedDict):
    """User aircon settings."""

    isOn: bool
    Mode: str
    FanMode: str
    TemperatureSetpoint_Cool_oC: float
    TemperatureSetpoint_Heat_oC: float
    EnabledZones: list[bool]


class LastKnownState(TypedDict):
    """Last known state of the AC system."""

    MasterInfo: MasterSensorInfo
    LiveAircon: LiveAirconInfo
    UserAirconSettings: UserAirconSettings
    RemoteZoneInfo: list[dict[str, str | int | bool | float]]
    AirconSystem: dict[str, str | int | bool | dict[str, Any] | list[dict[str, Any]]]
    Alerts: dict[str, bool]


class AcStatusResponse(TypedDict):
    """AC status response."""

    lastKnownState: LastKnownState


class CommandResponse(TypedDict):
    """Command response."""

    success: bool
    message: str | None


class ZoneCapabilities(TypedDict):
    """Zone capabilities structure."""

    exists: bool
    can_operate: bool
    has_temp_control: bool
    has_separate_targets: bool
    target_temp_cool: float | None
    target_temp_heat: float | None
    peripheral_capabilities: dict[str, bool] | None


class PeripheralData(TypedDict):
    """Peripheral device data structure."""

    battery_level: int | None
    signal_strength: int | None
    peripheral_type: str | None
    last_connection: str | None
    connection_state: str | None
    ZoneAssignment: list[int]
    DeviceType: str | None
    RemainingBatteryCapacity_pc: int | None
    Signal_of3: int | None
    LastConnectionTime: str | None
    ConnectionState: str | None
    ControlCapabilities: dict[str, bool] | None


class CommandData(TypedDict):
    """Command data structure for API requests."""

    UserAirconSettings: dict[str, bool | str | float | list[bool]]


class ApiResponse(TypedDict, total=False):
    """Generic API response structure."""

    # Common response fields
    success: bool
    message: str | None
    # Embedded data for device listing
    _embedded: dict[str, list[dict[str, str | int | bool]]]
    # Status response fields
    lastKnownState: LastKnownState
    # Other possible fields
    error: str | None
    status: int | None


# Fan mode types
FanModeType = Literal["LOW", "MED", "HIGH", "AUTO"]
HvacModeType = Literal["COOL", "HEAT", "FAN", "AUTO", "OFF"]

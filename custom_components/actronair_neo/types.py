"""Type definitions for ActronAir Neo integration."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, Union, Literal


class TokenResponse(TypedDict):
    """Response from token endpoint."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str]


class DeviceInfo(TypedDict):
    """Device information."""
    serial: str
    name: str
    type: str
    id: str


class ZoneData(TypedDict):
    """Zone data structure."""
    name: str
    temp: Optional[float]
    setpoint: Optional[float]
    is_on: bool
    capabilities: ZoneCapabilities
    humidity: Optional[float]
    is_enabled: bool
    temp_setpoint_cool: Optional[float]
    temp_setpoint_heat: Optional[float]
    battery_level: Optional[int]
    signal_strength: Optional[int]
    peripheral_type: Optional[str]
    last_connection: Optional[str]
    connection_state: Optional[str]


class MainData(TypedDict):
    """Main AC data structure."""
    is_on: bool
    mode: str
    fan_mode: str
    fan_continuous: bool
    base_fan_mode: str
    supported_fan_modes: List[str]
    temp_setpoint_cool: Optional[float]
    temp_setpoint_heat: Optional[float]
    indoor_temp: Optional[float]
    indoor_humidity: Optional[float]
    compressor_state: str
    EnabledZones: List[bool]
    model: str
    firmware_version: str
    away_mode: bool
    quiet_mode: bool
    indoor_model: Optional[str]
    serial_number: Optional[str]
    filter_clean_required: bool
    defrosting: bool


class CoordinatorData(TypedDict):
    """Data structure for coordinator."""
    main: MainData
    zones: Dict[str, ZoneData]
    raw_data: AcStatusResponse


class MasterSensorInfo(TypedDict):
    """Master sensor information."""
    LiveTemp_oC: Optional[float]
    LiveHumidity_pc: Optional[float]


class LiveAirconInfo(TypedDict):
    """Live aircon information."""
    CompressorMode: str
    Filter: Dict[str, Union[bool, int]]


class UserAirconSettings(TypedDict):
    """User aircon settings."""
    isOn: bool
    Mode: str
    FanMode: str
    TemperatureSetpoint_Cool_oC: float
    TemperatureSetpoint_Heat_oC: float
    EnabledZones: List[bool]


class LastKnownState(TypedDict):
    """Last known state of the AC system."""
    MasterInfo: MasterSensorInfo
    LiveAircon: LiveAirconInfo
    UserAirconSettings: UserAirconSettings
    RemoteZoneInfo: List[Dict[str, Union[str, int, bool, float]]]
    AirconSystem: Dict[str, Union[str, int, bool, Dict[str, Any], List[Dict[str, Any]]]]
    Alerts: Dict[str, bool]


class AcStatusResponse(TypedDict):
    """AC status response."""
    lastKnownState: LastKnownState


class CommandResponse(TypedDict):
    """Command response."""
    success: bool
    message: Optional[str]


class ZoneCapabilities(TypedDict):
    """Zone capabilities structure."""
    exists: bool
    can_operate: bool
    has_temp_control: bool
    has_separate_targets: bool
    target_temp_cool: Optional[float]
    target_temp_heat: Optional[float]
    peripheral_capabilities: Optional[Dict[str, bool]]


class PeripheralData(TypedDict):
    """Peripheral device data structure."""
    battery_level: Optional[int]
    signal_strength: Optional[int]
    peripheral_type: Optional[str]
    last_connection: Optional[str]
    connection_state: Optional[str]
    ZoneAssignment: List[int]
    DeviceType: Optional[str]
    RemainingBatteryCapacity_pc: Optional[int]
    Signal_of3: Optional[int]
    LastConnectionTime: Optional[str]
    ConnectionState: Optional[str]
    ControlCapabilities: Optional[Dict[str, bool]]


class CommandData(TypedDict):
    """Command data structure for API requests."""
    UserAirconSettings: Dict[str, Union[bool, str, float, List[bool]]]


class ApiResponse(TypedDict, total=False):
    """Generic API response structure."""
    # Common response fields
    success: bool
    message: Optional[str]
    # Embedded data for device listing
    _embedded: Dict[str, List[Dict[str, Union[str, int, bool]]]]
    # Status response fields
    lastKnownState: LastKnownState
    # Other possible fields
    error: Optional[str]
    status: Optional[int]


# Fan mode types
FanModeType = Literal["LOW", "MED", "HIGH", "AUTO"]
HvacModeType = Literal["COOL", "HEAT", "FAN", "AUTO", "OFF"]

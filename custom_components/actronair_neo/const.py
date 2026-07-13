"""Constants for the ActronAir Neo integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform  # type: ignore[import-untyped]

# ── Integration identifiers ─────────────────────────────────────

DOMAIN: Final = "actronair_neo"
DEVICE_MANUFACTURER: Final = "ActronAir"

# ── Configuration constants ─────────────────────────────────────
# Note: CONF_USERNAME / CONF_PASSWORD are no longer used (device code flow).

CONF_SERIAL_NUMBER: Final = "serial_number"
CONF_ENABLE_ZONE_CONTROL: Final = "enable_zone_control"
CONF_ENABLE_PUSH: Final = "enable_push"
CONF_BASE_URL: Final = "base_url"

# OAuth token storage keys (config entry data)
CONF_ACCESS_TOKEN: Final = "access_token"  # noqa: S105
CONF_REFRESH_TOKEN: Final = "refresh_token"  # noqa: S105
CONF_TOKEN_EXPIRES_AT: Final = "token_expires_at"  # noqa: S105

DEFAULT_REFRESH_INTERVAL: Final = 30  # seconds
DEFAULT_ENABLE_PUSH: Final = True

# ── Cache freshness ──────────────────────────────────────────────
# Maximum age of the coordinator's parsed-data cache before a full
# re-parse is forced, even when the raw API bytes are unchanged. This
# guards against the ActronAir cloud serving an unchanged (and possibly
# stale) lastKnownState indefinitely. See issue #112.
PARSE_CACHE_TTL: Final = 60  # seconds

# Maximum lifetime of an optimistic zone-enable override before it is
# discarded if the API never confirms the requested state.
ZONE_OVERRIDE_TTL: Final = 120  # seconds

# ── Platforms ────────────────────────────────────────────────────

PLATFORMS: Final[list[Platform]] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

# ── Temperature limits ───────────────────────────────────────────

MIN_TEMP: Final = 10
MAX_TEMP: Final = 30

# ── Fan modes (Actron API values) ───────────────────────────────

FAN_MODE_SUFFIX_CONT: Final = "+CONT"
VALID_FAN_MODES: Final[frozenset[str]] = frozenset({"LOW", "MED", "HIGH", "AUTO"})

# ── Zone constants ───────────────────────────────────────────────

MAX_ZONES: Final = 8

# ── Service names ────────────────────────────────────────────────

SERVICE_FORCE_UPDATE: Final = "force_update"
SERVICE_CREATE_ZONE_PRESET: Final = "create_zone_preset"
SERVICE_APPLY_ZONE_PRESET: Final = "apply_zone_preset"
SERVICE_BULK_ZONE_OPERATION: Final = "bulk_zone_operation"

# ── Entity attribute keys (used by sensor.py) ───────────────────

ATTR_BATTERY_LEVEL: Final = "battery_level"
ATTR_LAST_UPDATED: Final = "last_updated"
ATTR_ZONE_NAME: Final = "zone_name"
ATTR_ZONE_TYPE: Final = "zone_type"

# ── Icons ────────────────────────────────────────────────────────
# Note: Most icons are now defined in icons.json.
# Only kept here for programmatic use in entity constructors.

ICON_ZONE: Final = "mdi:air-conditioner"

# ── Model series definitions ────────────────────────────────────

ADVANCE_SERIES_MODELS: Final[frozenset[str]] = frozenset(
    {
        "CRV13AS",
        "CRV15AS",
        "CRV15AT",
        "CRV17AS",
        "CRV17AT",
        "CRV210T",
        "CRV240T",
        "EVV13AS-V",
        "EVV15AS",
        "EVV15AS-V",
        "EVV17AS",
        "EVV17AS-V",
        "EVV210S",
        "EVV240S",
    }
)

NEO_SERIES_WC: Final[frozenset[str]] = frozenset({"NTB-10", "NTW-10"})

# ── Fan mode capabilities ───────────────────────────────────────

BASE_FAN_MODES: Final[frozenset[str]] = frozenset({"LOW", "MED", "HIGH"})
ADVANCE_FAN_MODES: Final[frozenset[str]] = frozenset({"LOW", "MED", "HIGH", "AUTO"})

ADVANCED_FAN_MODE_ORDER: Final = ["AUTO", "LOW", "MED", "HIGH"]
BASE_FAN_MODE_ORDER: Final = ["LOW", "MED", "HIGH"]

# ── Sensor sentinel values ────────────────────────────────────────
# The ActronAir API returns 3000.0 when a sensor reading is unavailable
# (common on Classic series or zones without the respective sensor).

OUTDOOR_TEMP_UNAVAILABLE: Final = 3000.0
HUMIDITY_UNAVAILABLE: Final = 3000.0

# ── Outdoor-unit telemetry scaling factors ────────────────────────
# NTW-series (Advance/Inverter) units report telemetry at reduced scale
# in the raw API payload. These factors correct the values to real-world
# engineering units.
#
# SupplyVoltage_Vac: NTW-1000 evidence shows raw 23.0 -> actual 230 VAC
# (factor of 10). Confirmed via GitHub issue #133: supply_voltage x 10
# matches meter readings when cross-checked with supply_current.
#
# CompPower: Raw 45 -> actual ~4500 W (factor of 100). P ~= V x I gives
# 230 V x 19 A ~= 4370 W, consistent with 45 x 100 = 4500 W.
#
# SupplyPowerRMS_W / OutputPowerRMS_W: scaling not yet confirmed from a
# live payload with non-zero values; left unscaled pending further data.
# See utils/actron_api_structure.md (NTW-series Telemetry Scaling section)
# for details on sharing live payload data to confirm these factors.

SUPPLY_VOLTAGE_SCALE_FACTOR: Final = 10  # raw VAC x 10 = actual VAC (NTW-series)
COMP_POWER_SCALE_FACTOR: Final = 100  # raw W x 100 = actual W (NTW-series)

WATTS_PER_KILOWATT: Final = 1000  # W -> kW conversion for power display formatting

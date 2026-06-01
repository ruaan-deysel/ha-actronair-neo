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
CONF_BASE_URL: Final = "base_url"

# OAuth token storage keys (config entry data)
CONF_ACCESS_TOKEN: Final = "access_token"  # noqa: S105
CONF_REFRESH_TOKEN: Final = "refresh_token"  # noqa: S105
CONF_TOKEN_EXPIRES_AT: Final = "token_expires_at"  # noqa: S105

DEFAULT_REFRESH_INTERVAL: Final = 30  # seconds

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

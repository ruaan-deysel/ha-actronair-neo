"""Constants for the ActronAir Neo API client."""

from __future__ import annotations

from typing import Final

# API endpoints — Neo (Nimbus) and Que platforms
API_URL: Final = "https://nimbus.actronair.com.au"
API_URL_QUE: Final = "https://que.actronair.com.au"

# System type used by Que-platform (NX-Gen) devices
SYSTEM_TYPE_NXGEN: Final = "nxgen"

# Request configuration
API_TIMEOUT: Final = 30  # seconds
MAX_RETRIES: Final = 3
MAX_REQUESTS_PER_MINUTE: Final = 20
MIN_FAN_MODE_INTERVAL: Final = 5  # seconds between fan mode changes

# Cache configuration
DEFAULT_CACHE_TTL: Final = 15  # seconds
CACHE_CLEANUP_INTERVAL: Final = 300  # seconds (5 minutes)

# Circuit breaker: when the API is considered unhealthy, allow a single
# half-open recovery probe through after this cooldown so the integration
# can recover automatically rather than serving stale data for the full
# health window. See issue #112.
HEALTH_PROBE_COOLDOWN: Final = 60  # seconds

# OAuth2 Device Code Flow constants
CLIENT_ID: Final = "home_assistant"
DEVICE_CODE_GRANT_TYPE: Final = "urn:ietf:params:oauth:grant-type:device_code"
DEVICE_CODE_SCOPE: Final = "read write"
DEVICE_CODE_POLL_INTERVAL: Final = 5  # seconds

# API endpoints
ENDPOINT_OAUTH_TOKEN: Final = "/api/v0/oauth/token"  # noqa: S105
ENDPOINT_AC_SYSTEMS: Final = "/api/v0/client/ac-systems"
ENDPOINT_AC_STATUS: Final = "/api/v0/client/ac-systems/status/latest"
ENDPOINT_AC_COMMANDS: Final = "/api/v0/client/ac-systems/cmds/send"

# Token refresh constants
MAX_REFRESH_RETRIES: Final = 3
REFRESH_RETRY_DELAY: Final = 5  # seconds
TOKEN_EXPIRY_BUFFER: Final = 300  # Refresh 5 minutes early

# HTTP status codes used for retry logic
RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({500, 502, 503, 504})

# Realtime push (MQTT) — Neo platform
ENDPOINT_REALTIME_DETAILS: Final = "/api/v0/messaging/connection/details"
MQTT_KEEPALIVE: Final = 60  # seconds
MQTT_RECONNECT_INITIAL: Final = 0.5  # seconds
MQTT_RECONNECT_MAX: Final = 60.0  # seconds
MQTT_TOPIC_PREFIX: Final = "actron-cloud"
MQTT_PLATFORM_NEO: Final = "neo"
MQTT_TOPIC_FULL_STATUS: Final = "mwc/full-status"
MQTT_TOPIC_STATUS_CHANGE: Final = "mwc/status-change"
MQTT_TOPIC_HEART_BEAT: Final = "mwc/heart-beat"
# Command-response topic carries an ack/nack plus a status-change event. The
# broker publishes to .../mwc/cmd-response/{machine}/{commandId}, so the
# subscription needs two trailing single-level wildcards.
MQTT_TOPIC_CMD_RESPONSE: Final = "mwc/cmd-response"
# Heartbeat is treated as stale (push degraded) after this many seconds.
HEARTBEAT_STALE_AFTER: Final = 180

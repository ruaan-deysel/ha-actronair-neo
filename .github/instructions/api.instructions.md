---
applyTo: "custom_components/**/api/*.py"
---

# API Client Instructions

**Applies to:** `custom_components/actronair_neo/api/` (`auth.py`, `client.py`,
`const.py`, `models.py`)

## Integration Quality Scale (MANDATORY)

Always follow the official rules:
<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Three-Layer Architecture (CRITICAL)

**Entities → Coordinator → API Client** — Never skip layers

- **Entities:** Read `coordinator.data` only, never call API
- **Coordinator:** Calls `api/client.py`, transforms data, handles timing/errors
- **API package:** HTTP communication, auth, transport-level exception translation

## Module Responsibilities

- `auth.py`:
  - OAuth2 device-code flow (`request_device_code`, `poll_for_token`)
  - Token validation/refresh lifecycle
  - Token refresh callback for persistence
- `client.py`:
  - Core HTTP requests, retries, rate limiting, and response caching
  - Device/platform resolution and command dispatch
  - Transport/auth error translation to integration exceptions
- `models.py`:
  - Typed runtime models used by coordinator/API interactions
- `const.py`:
  - API endpoints, timeouts, retry constants, and OAuth constants

## API Client Rules

**Session management:**

- MUST accept `aiohttp.ClientSession` parameter
- NEVER create session (`aiohttp.ClientSession()`) inside the client
- Session comes from `async_get_clientsession(hass)` in `__init__.py`

**Timeout handling:**

- Use `aiohttp.ClientTimeout(...)` or `asyncio.timeout(...)`
- Set reasonable timeout per request (typically 10-30s)

**Return values:**

- Return API data that coordinator can parse into entity-ready state
- Keep Home Assistant entity semantics out of API layer
- Leave coordinator-level flattening/normalization in `coordinator.py`

## Exception Hierarchy

Defined in `exceptions.py`:

- `ApiError` — Base exception for all API errors
- `AuthenticationError` — Invalid or expired credentials (401/403)
- `ConfigurationError` — Configuration issues
- `ZoneError` — Zone-specific command failures
- `DeviceOfflineError` — Device unreachable / network failure
- `RateLimitError` — API rate limiting (429)

Always translate HTTP/network/auth failures to integration-specific exceptions.

## Coordinator Exception Mapping

| API Exception         | Coordinator Exception   | HA Behavior        |
| --------------------- | ----------------------- | ------------------ |
| `AuthenticationError` | `ConfigEntryAuthFailed` | Triggers reauth    |
| `DeviceOfflineError`  | `UpdateFailed(...)`     | Retry with backoff |
| `RateLimitError`      | `UpdateFailed(...)`     | Retry with backoff |
| `ApiError`            | `UpdateFailed(...)`     | Retry with backoff |

## Zone Commands

ActronAir Neo uses zone-based commands:

- Zone enable/disable: Pass zone index/serial
- Commands are sent to a specific AC serial number
- Always validate zone index before sending commands

## Common Mistakes

**❌ Don't:**

- Create `aiohttp.ClientSession()` in API client
- Call API directly from entities
- Raise `ConfigEntryAuthFailed` / `UpdateFailed` in API package
- Put Home Assistant-specific logic in API package

**✅ Do:**

- Accept session parameter in `__init__`
- Translate all HTTP/network exceptions to integration-specific types
- Keep transport/auth logic isolated from entity behavior
- Use specific exception types for different failure modes

---
applyTo: "custom_components/**/api_wrapper.py, custom_components/**/api.py"
---

# API Client Instructions

**Applies to:** `api_wrapper.py` (primary) and `api.py` (legacy)

## Three-Layer Architecture (CRITICAL)

**Entities → Coordinator → API Wrapper** — Never skip layers

- **Entities:** Read `coordinator.data` only, never call API
- **Coordinator:** Calls `api_wrapper.py`, transforms data, handles errors/timing
- **API Wrapper:** HTTP communication, auth, exception translation

## Prefer api_wrapper.py

`api_wrapper.py` is the primary API client. `api.py` is legacy and should not
receive new features. All new API functionality goes in `api_wrapper.py`.

## API Client Rules

**Session management:**

- MUST accept `aiohttp.ClientSession` parameter
- NEVER create session (`aiohttp.ClientSession()`) inside the client
- Session comes from `async_get_clientsession(hass)` in `__init__.py`

**Timeout handling:**

- Use `asyncio.timeout()` not `async_timeout`
- Set reasonable timeout per request (10-30s typical)

**Return values:**

- Return raw API response data
- Let coordinator transform data for entities
- Don't process/restructure in API client

## Exception Hierarchy

Defined in `exceptions.py`:

- `ApiError` — Base exception for all API errors
- `AuthenticationError` — Invalid or expired credentials (401/403)
- `ConfigurationError` — Configuration issues
- `ZoneError` — Zone-specific command failures
- `DeviceOfflineError` — Device unreachable / network failure
- `RateLimitError` — API rate limiting (429)

**Always translate HTTP errors to these integration-specific exceptions.**

## Coordinator Exception Mapping

| API Exception | Coordinator Exception | HA Behavior |
| ------------- | --------------------- | ----------- |
| `AuthenticationError` | `ConfigEntryAuthFailed` | Triggers reauth |
| `DeviceOfflineError` | `UpdateFailed(...)` | Retry with backoff |
| `RateLimitError` | `UpdateFailed(retry_after=60)` | Wait before retry |
| `ApiError` | `UpdateFailed(...)` | Retry with backoff |

## Zone Commands

ActronAir Neo uses zone-based commands:

- Zone enable/disable: Pass zone index/serial
- Commands are sent to a specific AC serial number
- Always validate zone index before sending commands

## Common Mistakes

**❌ Don't:**

- Create `aiohttp.ClientSession()` in API client
- Call API directly from entities
- Return transformed/restructured data from API client
- Implement retry logic in API client (coordinator does this)

**✅ Do:**

- Accept session parameter in `__init__`
- Translate all HTTP/network exceptions to integration-specific types
- Return raw data to coordinator
- Use specific exception types for different failure modes

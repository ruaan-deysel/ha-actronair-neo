---
applyTo: "**/*.py"
---

# Python Code Instructions

**Applies to:** All Python files in the integration

## File Structure

### Module Organization

- `__init__.py` — Platform setup with `async_setup_entry()`
- Individual platform files — One responsibility per file
- `const.py` — Module constants only (no logic)
- `types.py` — TypedDict definitions for API responses

**File size guidelines:**

- **Target:** 200-400 lines per file
- **Maximum:** ~500 lines before splitting

**Naming:**

- Files: `snake_case.py`
- Classes: `PascalCase` prefixed with `ActronAirNeo` for integration-specific classes
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Type Annotations

**Required for:**

- All function parameters and return values
- Class attributes (when not obvious)

**Import rules:**

- `from __future__ import annotations` (always first import)
- `collections.abc` for abstract base classes
- `typing` for complex types (Any, TYPE_CHECKING, etc.)

**Avoiding circular imports:**

Use `if TYPE_CHECKING:` block for type-only imports.

## Async Patterns

**All I/O operations must be async** — Network, file, database, blocking operations

**Core patterns:**

- `async def` for coroutines, `await` for async calls
- `asyncio.gather()` for concurrent operations
- `asyncio.timeout()` for timeouts (NOT `async_timeout` — deprecated)
- Never: `time.sleep()`, synchronous HTTP libraries, blocking operations

**Callback decorator:**

- `@callback` from `homeassistant.core` — For event loop functions without blocking
- Required for event listeners, state change callbacks
- Cannot do I/O, cannot call coroutines (only schedule them)

## Code Style

- Comments as complete sentences with capitalization and ending period
- Alphabetical sorting of constants/lists when order doesn't matter
- Ruff enforces import ordering, f-string usage, `__all__`/`__slots__` sorting

## Home Assistant Requirements

**Setup Failure Handling:**

- `ConfigEntryNotReady` — Device offline/unavailable (raises in `async_setup_entry()`)
- `ConfigEntryAuthFailed` — Expired credentials (triggers reauth flow)
- **Do NOT log setup failures manually** — Avoid log spam (HA logs at debug automatically)

**Constants:**

- Prefer `homeassistant.const` over defining new ones
- Only add to `const.py` if widely used internally

**Units of Measurement:**

- Always use constants from `homeassistant.const`
- Never hardcode strings like `"°C"` or `"%"`

**Time and Timestamps:**

- Always use UTC timestamps (`dt_util.utcnow()`)
- Never use relative time in state/attributes

## Imports

**Order (separated by blank lines):**

1. `from __future__ import annotations`
2. Standard library
3. Third-party packages
4. Home Assistant core (`homeassistant.*`)
5. Local integration imports (`.const`, `.coordinator`, etc.)

## Entity Classes

**Structure requirements:**

- Inherit from both platform entity and `ActronAirNeoBaseEntity` (order matters for MRO)
- Set `_attr_unique_id` in `__init__`
- Use coordinator data only — Never call API directly
- Handle unavailability via `_attr_available`

## Error Handling

**Logging levels:**

- `_LOGGER.exception()` — Errors with full traceback (in exception handlers)
- `_LOGGER.error()` — Errors affecting functionality
- `_LOGGER.warning()` — Recoverable issues
- `_LOGGER.info()` — Sparingly, user-facing only
- `_LOGGER.debug()` — Detailed troubleshooting

**Log message style:**

- No periods at end (syslog style)
- Never log credentials/tokens/API keys
- Use `%` formatting (enforced by Ruff G004)

## Testing Considerations

**Note: Only write tests when explicitly requested by the developer.**

## Validation

Run before submitting: `script/lint`

**When validation fails:**

- Look up error codes: [Ruff rules](https://docs.astral.sh/ruff/rules/)
- Fix root cause — Don't bypass checks

**Suppressing checks (use sparingly for false positives/library issues):**

- Specific: `# noqa: F401 - Reason` or `# type: ignore[attr-defined] - Reason`
- **Never use blanket:** `# noqa`, `# type: ignore`, `# ruff: noqa`

## Verify Current Patterns

Home Assistant APIs evolve — Always verify current patterns:

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Developer Blog](https://developers.home-assistant.io/blog/) for deprecations/changes

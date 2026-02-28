---
applyTo: "custom_components/**/coordinator.py"
---

# Coordinator Instructions

**Applies to:** `coordinator.py` (always read together with `api.instructions.md`)

## Using the Coordinator

✅ **Correct:** `self.coordinator.data["temperature"]` (in entity properties)

❌ **Wrong:** `await self.api_client.get_data()` (never fetch directly in entities)

## Pattern

```python
class ActronDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator fetching ActronAir Neo data."""

    def __init__(self, hass: HomeAssistant, api_wrapper: ActronApiWrapper) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api = api_wrapper

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            return await self.api.get_status()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except (ApiError, DeviceOfflineError) as err:
            raise UpdateFailed(str(err)) from err
```

## Error Handling in `_async_update_data()`

**Exception mapping:**

- `AuthenticationError` → `raise ConfigEntryAuthFailed from err` (triggers reauth)
- `ApiError` / `DeviceOfflineError` → `raise UpdateFailed("message") from err`
- `RateLimitError` → `raise UpdateFailed(retry_after=60) from err`

**Automatic handling:** `TimeoutError` and `aiohttp.ClientError` handled by base class

Do NOT log setup/update failures manually — HA handles it automatically.

## First Refresh

**In `async_setup_entry()` in `__init__.py`:**

```python
await coordinator.async_config_entry_first_refresh()
```

If `_async_update_data()` raises `UpdateFailed`, coordinator raises
`ConfigEntryNotReady` automatically.

## Update Interval

**Guidelines:** Cloud poll interval for ActronAir Neo is typically 30-60 seconds.
Don't poll faster than necessary — the ActronAir cloud API has rate limits.

## Data Transformation

**Coordinator responsibility:** Transform raw API response into a flat, typed dict
that entities can read directly. Entities should read `coordinator.data["key"]`, not
deeply nested API structures.

## Common Mistakes

**❌ Don't:**

- Call `api_wrapper` from entities
- Catch `TimeoutError`/`ClientError` in coordinator (base class handles)
- Log setup/update failures manually

**✅ Do:**

- Transform data in coordinator before storing
- Use specific exception types for different failures
- Let coordinator handle retries and timing

## Reference

[Home Assistant: Fetching Data](https://developers.home-assistant.io/docs/integration_fetching_data)

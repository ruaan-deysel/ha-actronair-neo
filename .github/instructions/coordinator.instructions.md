---
applyTo: "custom_components/**/coordinator.py"
---

# Coordinator Instructions

**Applies to:** `coordinator.py` (read together with `api.instructions.md`)

## Integration Quality Scale (MANDATORY)

Always follow the official rules:
<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Using the Coordinator

✅ **Correct:** `self.coordinator.data["temperature"]` (in entity properties)

❌ **Wrong:** `await self.api.get_ac_status(...)` in entity code

## Pattern

```python
class ActronDataCoordinator(DataUpdateCoordinator):
    """Coordinator fetching ActronAir Neo data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ActronAirNeoApiClient,
        device_id: str,
        update_interval: int,
        *,
        enable_zone_control: bool,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.api = api
        self.device_id = device_id
        self.enable_zone_control = enable_zone_control

    async def _async_update_data(self) -> CoordinatorData:
        """Fetch data from API."""
        try:
            status = await self.api.get_ac_status(self.device_id, use_cache=True)
            return await self._parse_data_optimized(status)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except (ApiError, DeviceOfflineError, RateLimitError) as err:
            raise UpdateFailed(str(err)) from err
```

## Error Handling in `_async_update_data()`

**Exception mapping:**

- `AuthenticationError` → `raise ConfigEntryAuthFailed from err` (triggers reauth)
- `ApiError` / `DeviceOfflineError` → `raise UpdateFailed("message") from err`
- `RateLimitError` → `raise UpdateFailed("message") from err`

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

Coordinator is responsible for parsing API payloads into `coordinator.data`:

- Keep `main`, `zones`, and `raw_data` keys stable for entities
- Keep entity-facing reads simple (`self.coordinator.data[...]`)
- Avoid pushing API shape complexity into entity classes

## Common Mistakes

**❌ Don't:**

- Call API methods from entities
- Catch `TimeoutError`/`ClientError` in coordinator (base class handles)
- Log setup/update failures manually

**✅ Do:**

- Transform data in coordinator before storing
- Use specific exception types for different failures
- Preserve last known good data when temporary failures occur
- Let coordinator handle retries and polling timing

## Reference

[Home Assistant: Fetching Data](https://developers.home-assistant.io/docs/integration_fetching_data)

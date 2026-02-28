---
applyTo: "custom_components/**/diagnostics.py"
---

# Diagnostics Instructions

**Applies to:** `diagnostics.py`

## Critical: Always Redact Sensitive Data

**Use `async_redact_data()` for all user data:**

```python
from homeassistant.helpers.redact import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "api_key",
    "token",
    "refresh_token",
    "access_token",
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "entry_options": async_redact_data(entry.options, TO_REDACT),
        "coordinator_data": coordinator.data,
    }
```

## Never Expose

The following must ALWAYS be redacted:

- Passwords and API keys/tokens
- OAuth credentials
- Location data (latitude/longitude)
- Personal information (email, phone, name)
- ActronAir account identifiers
- Serial numbers (if considered personally identifiable)

## When in Doubt

If you're unsure whether data is sensitive, **redact it**. Better to redact too much
than expose credentials.

## References

- [Diagnostics Platform](https://developers.home-assistant.io/docs/diagnostics/)

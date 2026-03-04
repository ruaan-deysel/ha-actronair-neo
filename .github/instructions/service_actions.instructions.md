---
applyTo: "custom_components/**/services.yaml"
---

# Service Actions Instructions

**Applies to:** `services.yaml`

**Official Documentation:** [Service Actions](https://developers.home-assistant.io/docs/dev_101_services/)

## Integration Quality Scale (MANDATORY)

Always follow the official rules:
<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Registration Pattern Used in This Integration

Services are registered once in integration-level `async_setup()` via
`_register_services(hass)` with an idempotency guard (`has_service(...)`).

**Pattern:**

```python
async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    _register_services(hass)
    return True

def _register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_FORCE_UPDATE):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_FORCE_UPDATE,
        _handle_force_update,
        schema=SERVICE_FORCE_UPDATE_SCHEMA,
    )
```

Do not switch to per-entry registration unless there is a clear architectural reason.

## Current Services (Keep in Sync)

- `force_update`
- `create_zone_preset`
- `apply_zone_preset`
- `bulk_zone_operation`

## services.yaml Structure

```yaml
force_update:
  name: Force Update
  description: Force an immediate update of ActronAir Neo data.
  target:
    entity:
      integration: actronair_neo
      domain: climate
  fields: {}

create_zone_preset:
  name: Create Zone Preset
  description: Save current zone settings as a preset.
  fields:
    device_id:
      name: Device ID
      description: The ActronAir device identifier.
      required: true
      selector:
        text:
    name:
      name: Preset Name
      description: Name for the new preset.
      required: true
      selector:
        text:
```

## Error Handling

| Error type               | Use when                                   |
| ------------------------ | ------------------------------------------ |
| `ServiceValidationError` | Bad user input (wrong device ID, etc.)     |
| `HomeAssistantError`     | Device error (API failure, device offline) |

```python
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

async def _handle_service(call: ServiceCall) -> None:
    device_id = call.data["device_id"]
    coordinator = _find_coordinator(hass, device_id)
    if coordinator is None:
        raise ServiceValidationError(f"Device '{device_id}' not found")
    try:
        await coordinator.async_request_refresh()
    except (ApiError, ZoneError, ConfigurationError) as err:
        raise HomeAssistantError(f"Service call failed: {err}") from err
```

## Key Rules

- Keep service names in `const.py`, `__init__.py`, and `services.yaml` aligned
- Register services in integration-level setup with idempotency guard
- Use voluptuous schema for input validation
- Use `ServiceValidationError` for user input errors
- Use `HomeAssistantError` for device/API errors
- Provide translations for all service names and descriptions in `strings.json`

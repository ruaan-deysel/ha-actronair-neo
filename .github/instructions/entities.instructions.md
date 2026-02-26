---
applyTo: "custom_components/**/climate.py, custom_components/**/sensor.py, custom_components/**/binary_sensor.py, custom_components/**/switch.py, custom_components/**/number.py, custom_components/**/base_entity.py"
---

# Entity Platform Instructions

**Applies to:** All entity platform implementations (climate, sensor, binary_sensor,
switch, number) and the base entity class.

## Shared Infrastructure

- **`base_entity.py`** — `ActronAirNeoBaseEntity` base class (inherit from this)
- **`coordinator.py`** — Data fetching (entities never call API directly)
- **`types.py`** — TypedDict definitions for coordinator data

## Base Entity Inheritance

**MUST inherit from:** `(PlatformEntity, ActronAirNeoBaseEntity)` — order matters for MRO

**Base class provides:** Coordinator integration, device info, unique ID, attribution,
entity naming

**You implement:** Platform-specific properties/methods (`native_value`, `is_on`,
`hvac_mode`, `async_set_temperature`, etc.)

**Constructor:** Call `super().__init__(coordinator, ...)` — base handles setup

## Entity Descriptions

Where applicable, use `EntityDescription` dataclasses defined at module level.

**Key fields:**

- `key` — Used in unique_id, must match coordinator data key
- `name` — Display name
- Platform-specific: `device_class`, `state_class`, `unit_of_measurement`, etc.

**Entity Categories:**

- `None` — Primary functionality (prominent display)
- `EntityCategory.DIAGNOSTIC` — Diagnostic info (signal strength, last update)
- `EntityCategory.CONFIG` — Configuration settings

## Coordinator Data Access

**MUST use coordinator only:**

```python
# In entity property
return self.coordinator.data.get("some_key")
```

**NEVER call API directly:** No `await api_client.get_data()` in entity methods

**Handle missing data:** Check for key existence before accessing

## Platform Setup

**Pattern:** `async_setup_entry()` creates entities from coordinator

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ActronDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MyEntity(coordinator)])
```

## Zone Entities

ActronAir Neo has per-zone entities (switches, climate control per zone):

- Create one entity instance per zone
- Use zone index in unique_id: `{entry.entry_id}_zone_{zone_index}_{key}`
- Zone data is in `coordinator.data["zones"][zone_index]`

## Platform-Required Methods

**Must implement per platform:**

- Sensors: `native_value`, `native_unit_of_measurement`
- Binary Sensors: `is_on`
- Switches: `is_on`, `async_turn_on()`, `async_turn_off()`
- Numbers: `native_value`, `async_set_native_value()`
- Climate: `hvac_mode`, `hvac_modes`, `current_temperature`,
  `async_set_hvac_mode()`, `async_set_temperature()`

## Custom State Attributes

**Use `extra_state_attributes` property** returning dict for supplemental data

**NEVER override `state_attributes`** — reserved for base platform components

## Type Hints

**Avoid circular imports:**

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .coordinator import ActronDataCoordinator
```

## Common Pitfalls

**❌ Don't:**

- Call API directly from entities
- Hardcode unique IDs
- Log in property getters (called frequently)
- Duplicate constants (use `homeassistant.const` or `const.py`)

**✅ Do:**

- Use coordinator data exclusively
- Generate unique IDs from `entry_id + description.key` (or zone index)
- Log only in async methods or `__init__`
- Consult HA docs for platform-specific patterns

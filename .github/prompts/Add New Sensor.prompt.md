---
agent: "agent"
tools: ["search/codebase", "edit", "search", "execute/runInTerminal"]
description: "Add a new sensor entity to ActronAir Neo"
---

# Add New Sensor

Add a sensor to `custom_components/actronair_neo/sensor.py`.

## Required implementation

1. Add a sensor entity class inheriting `ActronAirNeoEntity` and `SensorEntity`.
2. Define device class/state class/unit when applicable.
3. Read value from `self.coordinator.data` and handle missing data safely.
4. Register entity in `async_setup_entry()`.
5. Add translation keys for name/state text:
   - `custom_components/actronair_neo/strings.json`
   - `custom_components/actronair_neo/translations/en.json`
6. Add icon mapping in `icons.json` if needed.

## Rules

- No direct API calls from sensor entities.
- Use HA constants for units and states.
- Keep unique IDs stable.
- Follow HA Integration Quality Scale rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Validation

- Run: `script/lint`
- Run: `script/test` when requested or required by IQS impact

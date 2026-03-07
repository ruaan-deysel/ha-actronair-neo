---
agent: "agent"
tools: ["search/codebase", "edit", "search", "execute/runInTerminal"]
description: "Add a new entity platform to ActronAir Neo"
---

# Add Entity Platform

Add a new platform module under `custom_components/actronair_neo/`.

## Required implementation

1. Create platform file (for example `button.py`, `select.py`, etc.).
2. Implement `async_setup_entry()` and create entities from `entry.runtime_data`.
3. Ensure entities inherit from `ActronAirNeoEntity` + platform base class.
4. Read state from `self.coordinator.data` only.
5. Add platform to `PLATFORMS` in `custom_components/actronair_neo/const.py`.
6. Add translations for entity names:
   - `custom_components/actronair_neo/strings.json`
   - `custom_components/actronair_neo/translations/en.json`
7. Add icons to `custom_components/actronair_neo/icons.json` when relevant.

## Rules

- No direct API calls from entities.
- Keep unique IDs stable and deterministic.
- Preserve existing entity IDs unless explicitly approved.
- Follow HA Integration Quality Scale rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Validation

- Run: `script/lint`
- Run: `script/test` (or explain skip)

---
agent: "agent"
tools: ["search/codebase", "edit", "search", "execute/runInTerminal"]
description: "Add a new entity to an existing ActronAir Neo device"
---

# Add Entity to Device

Add a new entity to an existing `actronair_neo` platform while keeping device grouping consistent.

## Required implementation

1. Add entity class in the relevant platform file.
2. Register it in that platform’s `async_setup_entry()`.
3. Keep device grouping consistent via `ActronAirNeoEntity.device_info`.
4. Generate stable unique IDs (include device + entity purpose + zone context if needed).
5. Read from coordinator data only.
6. Add/update translation keys in:
   - `custom_components/actronair_neo/strings.json`
   - `custom_components/actronair_neo/translations/en.json`

## Rules

- Do not change unrelated entities’ unique IDs.
- Do not break existing automations/dashboard references.
- Keep availability behavior aligned with coordinator update success.
- Follow HA Integration Quality Scale rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Validation

- Run: `script/lint`
- Run: `script/test` (if requested or needed for IQS compliance)

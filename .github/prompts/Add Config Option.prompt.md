---
agent: "agent"
tools: ["search/codebase", "edit", "search", "runCommands"]
description: "Add a new config or options-flow setting to ActronAir Neo"
---

# Add Config Option

Add a new configuration option in `custom_components/actronair_neo/config_flow.py`.

## Required implementation

1. Add a `CONF_*` constant in `custom_components/actronair_neo/const.py` if reused.
2. Update config/reauth/options flow step schema in `config_flow.py`.
3. Validate user input and map errors to translation keys.
4. Persist value in either:
   - `entry.data` (credentials/core setup data), or
   - `entry.options` (user-tunable behavior).
5. Use the option where needed (coordinator/entities/setup).
6. Add translations in both:
   - `custom_components/actronair_neo/strings.json`
   - `custom_components/actronair_neo/translations/en.json`

## Rules

- Unique ID must stay stable (serial/account identifier).
- Reauth must update existing entry, never create a new one.
- Do not mutate config entries directly; use HA config-entry APIs.
- Follow HA Integration Quality Scale rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Validation

- Run: `script/lint`
- Run: `script/test` (or explain why skipped)

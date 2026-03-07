---
agent: "agent"
tools: ["search/codebase", "edit", "search", "execute/runInTerminal"]
description: "Add a new action (service action) to the ActronAir Neo integration"
---

# Add Action

Add a new Home Assistant action for `actronair_neo`.

## Required implementation

1. Update `custom_components/actronair_neo/const.py` with a new `SERVICE_*` constant.
2. Update `custom_components/actronair_neo/__init__.py`:
   - Add a voluptuous schema.
   - Register the action in `_register_services()`.
   - Add a handler using `ServiceValidationError` for bad input.
   - Raise `HomeAssistantError` for API/device failures.
3. Update `custom_components/actronair_neo/services.yaml` with selector-based fields.
4. Update both translation files:
   - `custom_components/actronair_neo/strings.json`
   - `custom_components/actronair_neo/translations/en.json`
5. Keep naming consistent:
   - User-facing text uses “action”.
   - Internal API may still use `services.yaml` and `hass.services`.

## Project rules

- Use entities -> coordinator -> API client flow. No direct API calls from entities.
- Use project scripts only: `script/lint`, `script/test`, `script/check`.
- Follow HA Integration Quality Scale rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Ask before starting if missing

- Action name
- Parameters and types
- Target scope (entity/device/integration-wide)
- Expected side effects

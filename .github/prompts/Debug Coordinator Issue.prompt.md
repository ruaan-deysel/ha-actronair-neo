---
agent: "agent"
tools:
  [
    "search/codebase",
    "search",
    "runCommands",
    "runCommands/terminalLastCommand",
  ]
description: "Diagnose coordinator update failures and stale data issues"
---

# Debug Coordinator Issue

Diagnose and fix issues in `custom_components/actronair_neo/coordinator.py`.

## Checkpoints

1. Validate exception mapping:
   - `AuthenticationError` -> `ConfigEntryAuthFailed`
   - API/rate/device errors -> `UpdateFailed`
2. Confirm `async_config_entry_first_refresh()` behavior at setup.
3. Confirm entities read only from `coordinator.data`.
4. Check fallback behavior with last known data.
5. Check API caching/rate-limit interactions in `api/client.py`.

## Local debugging steps

1. Set debug logging in `config/configuration.yaml`:
   - `custom_components.actronair_neo: debug`
2. Run Home Assistant with `script/develop`.
3. Inspect `config/home-assistant.log`.
4. Reproduce with a clear sequence and timestamps.

## Validation

- Run: `script/lint`
- Run targeted tests via: `script/test tests/test_coordinator.py -v`

## Rules

- Keep fixes inside existing architecture layers.
- Avoid direct API calls from entities.
- Keep behavior aligned with IQS rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

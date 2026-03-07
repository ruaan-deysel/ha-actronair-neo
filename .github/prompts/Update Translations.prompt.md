---
agent: "agent"
tools: ["edit", "search", "execute/runInTerminal"]
description: "Update translation keys for config flow, entities, and actions"
---

# Update Translations

Update translation content for `actronair_neo`.

## Required files

- `custom_components/actronair_neo/strings.json`
- `custom_components/actronair_neo/translations/en.json`

## Rules

1. Keep both files in sync.
2. Use valid placeholders (`{name}`), no single-quoted placeholders.
3. Reuse keys with `[%key:...%]` when appropriate.
4. Keep names concise and descriptions clear.
5. Do not auto-edit other language files unless explicitly requested.

## Common sections

- `config.step`, `config.error`, `config.abort`
- `options.step`
- `entity.<platform>.<translation_key>`
- `services` / action text keys used by `services.yaml`
- `issues` / repairs text where applicable

## Validation

- Run: `script/lint`
- Optionally run: `script/check` for broader validation

## Standards

- Follow HA localization rules and IQS requirements:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

---
applyTo: "**/*.yaml, **/*.yml"
---

# YAML Instructions

**Applies to:** All YAML files

## Formatting Standards

- **2 spaces** for indentation (never tabs)
- No trailing whitespace
- End files with a single newline
- Use lowercase for keys (except where case matters)
- Boolean values: `true`/`false` (lowercase)

## Home Assistant YAML Conventions

- Use modern HA configuration syntax (no legacy `platform:` style)
- Use `!secret` for sensitive values (passwords, API keys, tokens)

## services.yaml (Service Actions)

Service action definitions must include:

- `name` — Human-readable action name
- `description` — What the action does
- `fields` — Parameters with types and descriptions
- `target` — Optional; only required when the action targets specific entities

```yaml
set_zone_temperature:
  name: Set zone temperature
  description: Sets the target temperature for a specific zone.
  target:
    entity:
      integration: actronair_neo
      domain: climate
  fields:
    zone_id:
      name: Zone ID
      description: The zone identifier (0-indexed)
      required: true
      selector:
        number:
          min: 0
          max: 7
          mode: box
```

## configuration.yaml (Development Config)

The `config/configuration.yaml` file is for local development only:

- Set logger levels for debugging
- Configure Home Assistant for development use
- Never commit sensitive credentials

```yaml
logger:
  default: info
  logs:
    custom_components.actronair_neo: debug
```

## Common Mistakes

- ❌ Using tabs instead of spaces
- ❌ Trailing whitespace
- ❌ Hardcoded passwords in YAML (use `!secret`)
- ❌ Missing `name` or `description` in service definitions

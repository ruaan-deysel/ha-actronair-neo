---
applyTo: "**/manifest.json"
---

# Manifest Instructions

**Applies to:** `custom_components/actronair_neo/manifest.json`

## Integration Quality Scale (MANDATORY)

Always follow the official rules:
<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

## Current Baseline (Keep in Sync)

```json
{
  "domain": "actronair_neo",
  "name": "ActronAir Neo",
  "codeowners": ["@ruaan-deysel"],
  "config_flow": true,
  "documentation": "https://github.com/ruaan-deysel/ha-actronair-neo",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/ruaan-deysel/ha-actronair-neo/issues",
  "requirements": [],
  "version": "x.x.x"
}
```

Keep manifest values aligned with actual implementation and project strategy.

## Domain and Identity

- `domain` must always match `custom_components/actronair_neo`
- `name` should stay `ActronAir Neo`
- `config_flow` remains `true` (device-code OAuth setup flow)

## IoT Class

`iot_class` is `cloud_polling` and should only change if integration behavior changes.

## Requirements

Current manifest uses an empty `requirements` list.

If requirements are added in future:

- Pin versions explicitly
- Ensure runtime imports actually depend on those packages
- Validate setup and startup paths after changes

## Version

Use semantic versioning in this project's current scheme (`YYYY.MINOR.PATCH`),
for example `2026.3.0`.

## Common Mistakes

- ❌ Missing `version` (required for HACS)
- ❌ Missing `issue_tracker` (required for HACS)
- ❌ Wrong `domain` (must match directory name `actronair_neo`)
- ❌ Trailing commas in JSON
- ❌ Adding discovery keys (`zeroconf`, `ssdp`, `dhcp`, etc.) without implementing matching flow steps
- ❌ Changing `iot_class` without explicit behavior change

## References

- [Manifest Documentation](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [HACS Requirements](https://hacs.xyz/docs/publish/include)

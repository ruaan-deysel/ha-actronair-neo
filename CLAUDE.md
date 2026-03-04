# Claude Code Instructions

This repository uses a shared AI agent instruction system.
**All instructions are in [`AGENTS.md`](AGENTS.md).**

Read `AGENTS.md` completely before starting any work. It contains:

- Project overview and integration identifiers
- File structure and architectural rules
- Code style, validation commands, and quality expectations
- Home Assistant patterns (config flow, coordinator, entities, services)
- Error recovery strategy and breaking change policy
- Workflow rules (scope management, translations, documentation)

## Quick Reference

- **Domain:** `actronair_neo`
- **Title:** ActronAir Neo
- **Class prefix:** `ActronAirNeo`
- **Main code:** `custom_components/actronair_neo/`
- **Validate:** `script/lint` (ruff format + ruff check)
- **Test:** `script/test`
- **Run HA:** `script/develop`

## Path-Specific Instructions

Additional guidance is available in `.github/instructions/*.instructions.md`.
Consult the relevant file when working on specific file types:

- `python.instructions.md` — Python style, async patterns, HA imports
- `entities.instructions.md` — Entity platform patterns, inheritance
- `config_flow.instructions.md` — Config flow, reauth, discovery
- `coordinator.instructions.md` — DataUpdateCoordinator patterns
- `api.instructions.md` — API client, exception hierarchy
- `translations.instructions.md` — Translation file structure
- `manifest.instructions.md` — manifest.json fields and rules
- `diagnostics.instructions.md` — Sensitive data redaction
- `repairs.instructions.md` — Repair flow patterns
- `tests.instructions.md` — Test structure and fixtures

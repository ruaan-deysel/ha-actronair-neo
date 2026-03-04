# GitHub Copilot Instructions

> **Comprehensive docs:** See [`AGENTS.md`](../AGENTS.md) at the repository root for full AI agent documentation.
>
> **Why two files?** This file is loaded automatically by GitHub Copilot. `AGENTS.md` serves
> non-Copilot agents (Claude Code, Gemini, Cursor, etc.) who don't read this file. Some
> overlap is intentional. Path-specific `*.instructions.md` files provide detailed
> patterns per file type — avoid duplicating their content here.

## Project Identity

- **Domain:** `actronair_neo`
- **Title:** ActronAir Neo
- **Class prefix:** `ActronAirNeo`
- **Main code:** `custom_components/actronair_neo/`
- **iot_class:** `cloud_polling`
- **Validate:** `script/lint` (ruff format + ruff check --fix)
- **Start HA:** `script/develop`
- **Tests:** `script/test`

Use these exact identifiers throughout the codebase. Never hardcode different values.

## Integration Quality Scale Rules (MANDATORY)

Always comply with the official Home Assistant Integration Quality Scale rules:

- <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

Requirements:

1. Treat the rules page as source of truth for quality expectations
2. Apply all rules relevant to the files/behavior being changed
3. Do not introduce known rule violations
4. If a requested change conflicts with a rule, flag it and ask for explicit direction

## Code Quality Baseline

- **Python:** 4 spaces, 88 char lines, double quotes, full type hints, async for all I/O
- **YAML:** 2 spaces, modern Home Assistant syntax
- **JSON:** 2 spaces, no trailing commas, no comments

Before considering any coding task complete, the following **must** pass:

```bash
script/lint    # ruff format + ruff check --fix
```

Generate code that passes these checks on first run. Aim for zero validation errors.

## Architecture (Quick Reference)

**Data Flow:** Entities → Coordinator → API Client (never skip layers)

**Key files:**

- `coordinator.py` — `ActronDataCoordinator` (DataUpdateCoordinator subclass)
- `api/client.py` — `ActronAirNeoApiClient` transport/caching/rate limit handling
- `api/auth.py` — OAuth2 device-code authentication + token refresh
- `api/models.py` — API/coordinator models
- `entity.py` — `ActronAirNeoEntity` base class
- `exceptions.py` — Exception hierarchy (ApiError, AuthenticationError, etc.)
- `const.py` — All constants (DOMAIN, modes, features)
- `zone_presets.py` — Zone preset management

**Entity platforms:** `climate.py`, `sensor.py`, `binary_sensor.py`, `switch.py`, `number.py`, `cover.py`

**Exception → Coordinator mapping:**

- `AuthenticationError` → `ConfigEntryAuthFailed` (triggers reauth)
- `ApiError` / `DeviceOfflineError` / `RateLimitError` → `UpdateFailed` (retry/backoff)

## Workflow Rules

1. **Small, focused changes** — avoid large refactorings unless explicitly requested
2. **Implement features completely** — even if spanning multiple files
   - New sensor: entity class + platform init + const entries → implement all together
   - Bug fix touching coordinator + entity + error handling → do all at once
3. **Multiple independent features:** implement one at a time, suggest commit between each
4. **Large refactoring (>10 files or architectural changes):** propose plan first
5. **Validation:** run `script/lint` before considering task complete

**Important: Do NOT write tests unless explicitly requested.**

**Translation strategy:**

- Update `strings.json` and `translations/en.json` together
- NEVER update other language files automatically — extremely time-consuming
- Ask before creating new translation files

## Research First

**Don't guess — look it up:**

1. Search [Home Assistant Developer Docs](https://developers.home-assistant.io/)
2. Check the [developer blog](https://developers.home-assistant.io/blog/) for recent changes
3. Look at existing patterns in similar files in the integration
4. Run `script/lint` early and often — catch issues before they compound
5. Consult [Ruff rules](https://docs.astral.sh/ruff/rules/) when validation fails

**Home Assistant evolves rapidly** — verify current best practices.

## Local Development

**Always use the project's scripts** — do NOT craft your own `hass`, `pip`, `pytest`, or
similar commands.

**Start Home Assistant:**

```bash
script/develop
```

**Validate changes:**

```bash
script/lint    # Always run before considering task complete
```

**Run tests:**

```bash
script/test              # run all tests
script/test --cov        # with coverage
```

**Full pre-commit check:**

```bash
script/check   # type-check + lint-check + spell-check
```

**Other useful scripts:**

```bash
script/clean          # clean build artifacts
script/type-check     # Pyright type checking
script/spell          # spell check with auto-fix
script/help           # list all available scripts
script/setup/reset    # reset HA config to fresh state
```

**Logs:**

- Live: terminal where `script/develop` runs
- File: `config/home-assistant.log` (most recent), `config/home-assistant.log.1` (previous)
- Debug level: set `custom_components.actronair_neo: debug` in `config/configuration.yaml`

## Working With the Developer

**When requests conflict with these instructions:**

1. Clarify if deviation is intentional
2. Confirm you understood correctly
3. Suggest updating instructions if this is a permanent change
4. Proceed after confirmation

**Documentation rules:**

- ❌ **NEVER** create markdown files without explicit permission
- ❌ **NEVER** create "helpful" READMEs, GUIDE.md, NOTES.md, etc.
- ✅ **ALWAYS ask first** before creating permanent documentation
- ✅ **Prefer module/class/function docstrings** over separate markdown files
- ✅ **Use `.ai-scratch/`** for temporary planning and notes (never committed)

**Session management:**

- When task completes and developer moves on: suggest commit with message
- Suggest once, don't nag if declined

**Commit format:** [Conventional Commits](https://www.conventionalcommits.org/)

```text
type(scope): short summary (max 72 chars)

- Optional detailed points
- Reference issues if applicable
```

**Always check `git diff` first** — don't rely on session memory.

**Common types:**

- `feat:` — User-facing functionality (new sensor, service, config option)
- `fix:` — Bug fixes (user-facing issues)
- `chore:` — Dev tools, dependencies, devcontainer (NOT user-facing)
- `refactor:` — Code restructuring (no functional change)
- `docs:` — Documentation changes

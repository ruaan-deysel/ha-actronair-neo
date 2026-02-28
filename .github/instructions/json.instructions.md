---
applyTo: "**/*.json"
---

# JSON Instructions

**Applies to:** All JSON files

## Formatting Standards

- **2 spaces** for indentation
- No trailing commas
- No comments (JSON spec doesn't support them)
- Use double quotes for all strings
- End files with a single newline

## Validation

Use Python's json module to validate syntax:

```bash
python3 -m json.tool file.json > /dev/null
```

## File-Specific Rules

**`manifest.json`** — See `manifest.instructions.md` for required fields and values.

**`strings.json` / `translations/en.json`** — See `translations.instructions.md`.
Both files must be kept in sync.

**`hacs.json`** — HACS integration metadata. Do not modify `name` or `render_readme`
without explicit reason.

## Common Mistakes

- ❌ Trailing comma after last element
- ❌ Comments (`// ...` or `/* ... */`)
- ❌ Single quotes instead of double quotes
- ❌ Missing closing brace/bracket

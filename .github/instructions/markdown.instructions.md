---
applyTo: "**/*.md"
---

# Markdown Instructions

**Applies to:** All Markdown documentation files

## Formatting Standards

**Headers:**

- Use ATX-style (`#` not underlines)
- Don't skip heading levels (H1 → H2 → H3, not H1 → H3)

**Code blocks:**

- Always specify language: ` ```python `, ` ```bash `, ` ```yaml `
- Use `console` or `bash` for terminal commands
- Use `text` or `plain` for plain output

**Lists:**

- Unordered: Use `-` (dash)
- Consistent indentation (2 spaces for nested items)

**Tables:**

- Use proper alignment and spacing

## Documentation Structure

- `README.md` — User-facing overview and installation guide
- `CHANGELOG.md` — Version history
- `CONTRIBUTING.md` — Contribution guidelines
- `AGENTS.md` — AI agent instructions (root level)
- `CLAUDE.md`, `GEMINI.md` — Agent-specific pointers
- `.github/copilot-instructions.md` — GitHub Copilot compact instructions
- `.ai-scratch/` — Temporary AI notes (never committed)

## Documentation Rules

- ❌ **NEVER** create markdown files without explicit permission
- ❌ **NEVER** create "helpful" READMEs, GUIDE.md, NOTES.md, etc.
- ✅ **ALWAYS ask first** before creating permanent documentation
- ✅ **Prefer module/class/function docstrings** over separate markdown files
- ✅ **Use `.ai-scratch/`** for temporary planning and notes

## GitHub Copilot Instructions Files

Files in `.github/instructions/*.instructions.md`:

- Must have frontmatter with `applyTo` glob pattern
- Keep focused and concise (~50-300 lines)
- Enforce standards, not tutorials
- Use compact examples over verbose explanations

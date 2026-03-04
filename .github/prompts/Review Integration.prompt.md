---
agent: "agent"
tools: ["search/codebase", "search", "runCommands"]
description: "Perform a quality and architecture review of the integration"
---

# Review Integration

Run a practical quality review of `actronair_neo` with findings first.

## Review sequence

1. Run validation commands:
   - `script/lint`
   - `script/test`
   - `script/check`
2. Review architecture conformance:
   - entities -> coordinator -> API client
   - config flow unique ID and reauth behavior
   - diagnostics redaction safety
3. Review high-risk areas:
   - unique ID stability
   - service/action schemas and error handling
   - translation sync (`strings.json` and `translations/en.json`)
4. Summarize findings by severity with file/line references.

## Required standards

- Home Assistant Integration Quality Scale rules:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>
- Project agent guidance in `AGENTS.md` and `.github/instructions/*.instructions.md`

## Output format

1. Findings (highest severity first)
2. Open questions/assumptions
3. Brief change summary

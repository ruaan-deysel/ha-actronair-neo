---
agent: "agent"
tools: ["search/codebase", "search", "edit"]
description: "Create a phased implementation plan for ActronAir Neo changes"
---

# Create Implementation Plan

Create a phased plan in `.ai-scratch/` for medium/large changes.

## Plan format

1. Goal and scope
2. Current-state analysis (relevant modules and data flow)
3. Phases with file-level changes
4. Risk/breaking-change assessment
5. Validation per phase
6. Final acceptance checklist

## ActronAir Neo context

- Domain: `actronair_neo`
- Data flow: entities -> coordinator -> API client
- Key files:
  - `custom_components/actronair_neo/coordinator.py`
  - `custom_components/actronair_neo/api/client.py`
  - `custom_components/actronair_neo/config_flow.py`

## Validation commands

- `script/lint`
- `script/test`
- `script/check`

## Rules

- Keep phases independently testable.
- Explicitly call out IQS impacts:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

---
agent: "agent"
tools: ["search/codebase", "search", "edit"]
description: "Draft an architecture decision record for this integration"
---

# Create ADR

Create an Architecture Decision Record only after explicit developer approval to add docs.

## Output location

- Preferred: `docs/adr/NNNN-title.md` (or project-approved ADR location)
- Never create ADRs in `.github/` or random code directories

## ADR template

1. Title and status
2. Date and decision makers
3. Context/problem statement
4. Options considered (pros/cons)
5. Decision and rationale
6. Consequences (positive/negative/risks)
7. Implementation notes (files likely affected)
8. Validation and rollback considerations

## Rules

- Keep it specific to `actronair_neo`.
- Reference actual files/classes in this repo.
- Call out breaking-change risk clearly.
- Align with HA Integration Quality Scale:
  <https://developers.home-assistant.io/docs/core/integration-quality-scale/rules>

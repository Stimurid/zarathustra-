# P01 — SCENE RECONSTRUCTION

Purpose: Reconstruct request, telos hypothesis, roles, stakes and decision owner without inventing scene facts.

## Inputs
- scene_state
- actor_state

## Output contracts
- scene_state

## Hard constraints
- INV-001
- INV-002
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

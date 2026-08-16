# P05 — OWNERSHIP

Purpose: Resolve operation ownership/binding and return HUMAN/JOINT work when unresolved.

## Inputs
- human_operation
- ownership_assessment
- development_risk

## Output contracts
- human_operation_return
- pipeline_run_state

## Hard constraints
- INV-006
- INV-009
- INV-010
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

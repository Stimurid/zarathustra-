# P08 — SYNTHESIS RENDER

Purpose: Render user-facing answer from authorised state while keeping operational trace separate.

## Inputs
- pipeline_run_state
- epistemic_claim

## Output contracts
- user_facing_response
- pipeline_trace

## Hard constraints
- INV-004
- INV-016
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
May produce user-facing text only after the relevant output/state contract is satisfied.

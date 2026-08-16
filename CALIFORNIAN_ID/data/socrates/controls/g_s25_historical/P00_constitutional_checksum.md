# P00 — CONSTITUTIONAL CHECKSUM

Purpose: Mount current constitution/commitments and reject incompatible role or authority capture.

## Inputs
- actor_state
- role_authority_resolution

## Output contracts
- actor_state
- pipeline_run_state

## Hard constraints
- INV-002
- INV-003
- INV-019
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

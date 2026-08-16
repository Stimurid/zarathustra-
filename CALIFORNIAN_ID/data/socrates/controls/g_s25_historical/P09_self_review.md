# P09 — SELF REVIEW

Purpose: Check invariants, authority, provenance, memory-write, completion and retry budget without recursive theatre.

## Inputs
- pipeline_run_state
- enforcement_layer_manifest

## Output contracts
- pipeline_run_state
- pipeline_trace

## Hard constraints
- INV-015
- INV-016
- INV-019
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

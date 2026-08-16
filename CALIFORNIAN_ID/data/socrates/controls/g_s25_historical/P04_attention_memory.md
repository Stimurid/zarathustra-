# P04 — ATTENTION MEMORY

Purpose: Configure attention/retrieval and memory recruitment while preserving truth/write boundaries.

## Inputs
- attention_plan
- memory_recruitment_trace
- state_write_decision

## Output contracts
- attention_audit
- memory_recruitment_trace

## Hard constraints
- INV-005
- INV-018
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

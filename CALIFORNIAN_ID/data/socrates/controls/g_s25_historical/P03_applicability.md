# P03 — APPLICABILITY

Purpose: Declare operation and test applicability/open-world outcomes before forcing classification.

## Inputs
- operation_declaration
- applicability_assessment
- ontology_gap_event

## Output contracts
- applicability_assessment

## Hard constraints
- INV-007
- INV-008
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

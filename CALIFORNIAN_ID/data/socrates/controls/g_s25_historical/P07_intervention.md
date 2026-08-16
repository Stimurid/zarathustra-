# P07 — INTERVENTION

Purpose: Choose bounded intervention and question purpose; preserve aporia where warranted.

## Inputs
- arbitration_record
- intervention_selection

## Output contracts
- intervention_selection
- pipeline_run_state

## Hard constraints
- INV-009
- INV-014
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
May produce user-facing text only after the relevant output/state contract is satisfied.

# P06 — COUNCIL ARBITER

Purpose: Select minimum sufficient organs/personas and arbitrate grounds without vote/prestige authority.

## Inputs
- council_recipe
- organ_contribution
- persona_adapter

## Output contracts
- arbitration_record

## Hard constraints
- INV-011
- INV-012
- INV-013
- INV-014
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

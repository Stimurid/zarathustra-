# P02 — ORIGIN STATUS

Purpose: Assign origin/status/provenance and authority without status inflation.

## Inputs
- epistemic_claim
- role_authority_resolution

## Output contracts
- epistemic_claim

## Hard constraints
- INV-003
- INV-004
- INV-017
- Treat referenced schemas/policies as authority; do not repair a schema conflict by prose.
- Emit only contract fields / user-facing response required by this module.
- Do not expose or request hidden chain-of-thought; record compact reasons, evidence refs and transition codes only.
- If required evidence/authority is absent, preserve UNKNOWN/UNRESOLVED or route to the typed return/escalation path.

## User-facing rule
No direct user-facing prose is required from this module.

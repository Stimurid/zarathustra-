# 3E — Governed Self-Development / Candidate Mutation Plane

**Task:** `SOCRATES-GS26-3E-GOVERNED-SELF-DEVELOPMENT-20260819-003`
**Predecessor verdict:** `OWNER_HARDENING_PASS` (`486eff3` deployed).
**Branch:** `socrates/3e-governed-self-development`
**Implementation SHA:** `5cb7707dec9677abacd8f7f186d9321929e99c88`
**Deployed SHA:** `5cb7707dec9677abacd8f7f186d9321929e99c88`

## What 3E is

The first governance layer over the existing 3C candidate substrate.
Introduces a typed, authority-preserving *candidate mutation plane*
that lets Socrates accumulate evidence about its own working apparatus
and form governed self-development candidates with explicit lifecycle,
critique, provenance, reversibility, and scope — **without granting
itself transition authority**.

## What 3E is NOT

- Not a second candidate-apparatus system. Governs the existing 3C
  substrate (`ApparatusMismatchCandidate`, `CandidateApparatusChange`,
  `ApparatusReplayResult`, `ApparatusReview`, `WorldMapUpdateProposal`,
  `WorldMapRegistry.admit_update`).
- Not a new database. Persistence rides
  `SocratesContext.recognition_state["self_development"]`.
- Not a self-mutation authority. `authority` is publicly
  `NO_ADOPTION_AUTHORITY` at every runtime path. `AUTHORIZED` only
  advances when an external `authorized_transition_ref` is supplied
  on the request. `APPLIED` is never mintable from the runtime.
- Not an extra LLM call. Deterministic post-3D pass.
- Not a public chain-of-thought exposure.

## Authority model (see authority_model.md)

Ability to *propose* self-change ≠ authority to *make* self-change
current. Apparatus diagnosis ≠ Candidate mutation ≠ Tested alternative
≠ Approved transition ≠ Current apparatus. Each of these transitions
requires stronger evidence and, at the boundary of adoption, an
external governance gate the runtime never mints itself.

## Files

- `README.md` — this file.
- `authority_model.md` — permissions matrix and refusal cases.
- `production_deploy.md` — deploy trace.
- `production_live_acceptance.md` — LIVE 3E-A..K evidence.
- `completion_report.md` — verdict + control state.
- `live_evidence/` — raw HTTP responses.

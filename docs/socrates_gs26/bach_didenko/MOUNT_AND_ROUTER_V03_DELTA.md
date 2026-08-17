# MOUNT AND ROUTER v0.3 DELTA — G-BD.5

Delivered in `CALIFORNIAN_ID/data/socrates/candidate_v0_3/mount/semantic_mount_manifest_v0.3.yaml`. v0.2 mount policy remains frozen in `CALIFORNIAN_ID/data/socrates/current/mount/`.

## What v0.3 adds over v0.2

1. **BACH-local isolation** (§7 handoff). Donor-local operators (OP-07 FOLD, OP-08 UNFOLD_IN_MEDIUM) are admitted only when the current EpistemicSpace has a WorldModelMount with `ontology_ref` matching the donor AND `mount_mode ∈ {PRIMARY, OVERLAY, LENS}`. CONTRAST / NEGATIVE_CONTROL / ARCHIVAL mounts do not grant activation. Lexical mention has ZERO admission authority.

2. **Transferable-operator registry**. The 16 non-donor-local operators are available in every Space by default. Space policy may restrict but never mint authority.

3. **New v0.3 trigger causes** (all derived from typed state / authorized transitions per CTA discipline):

   - `REFLECTIVE_MISMATCH_PENDING` — admits B07 when `state.pending_diagnostic.mismatch`.
   - `MULTI_ONTOLOGY_MOUNT` — admits B08 when the Space carries more than one WorldModelMount.
   - `OPERATION_MISMATCH` — admits B08 when diagnostics carry the signal.
   - `REVISE_APPARATUS_INVOKED` — admits B08 when OP-10 dispatched.
   - `CROSS_SPACE_TRANSDUCTION_PENDING` — admits B07 when OP-04 dispatched.

4. **Historical fallback banned**. If a v0.3 body is unavailable, mount MUST fail explicitly (`SEMANTIC_MOUNT_MISSING`). No silent v0.2 substitution.

5. **Explicit budget failure semantics**. Mandatory contexts that exceed the hard byte budget → `SEMANTIC_CONTEXT_BUDGET_EXCEEDED`. Optional context degrades first in a declared order.

6. **WorldModelMount provenance ≠ activation** formalised as a mount-policy rule (§6.2 invariant).

## Phase mount matrix (v0.3)

Unchanged from v0.2 except for B07 (now admits reflective-mismatch cause) and B08 (now admits four new causes). CORE / B01–B06 / B09 / B10 phase bindings preserved.

## What v0.3 does NOT change

- CTA-001..008 discipline (typed state / authorized transition only).
- Summary substitution ban (every body).
- Phase jurisdiction (jurisdictions changed in G-BD.1 for S4 proposal; that change was to v0.2 defaults too).
- InterventionGovernor terminals (v0.2 authoritative).
- Human ownership INV-009.

## Router prompts

Existing router prompt files under `data/socrates/current/routers/P00_*..P09_*_v0.2_semantic.md` remain frozen. v0.3 candidate router prompts are drafted inline within each v0.3 body (§16 "Runtime-facing summary" of every body has the phase-facing distillation). A separate v0.3 router-prompt bundle is scope for a later pass — not needed to test the mount policy or the runtime object model.

## Test coverage

The mount manifest is a data file governed by policy semantics; runtime enforcement of the new trigger causes + BACH-local isolation lands in G-BD.6 (runtime consumers). The manifest itself is validated by:

- v0.3 body loading verified in G-BD.4 test `test_semantic_v0_3.py`.
- BACH operator library donor-local classification (G-BD.3) already asserts OP-07 / OP-08 as donor-local — the manifest's `bach_local_isolation.donor_local_operator_ids` must match.

## Non-goals

- v0.3 router prompts as separate files: deferred.
- Runtime enforcement of new mount-admission rules: G-BD.6.
- LIVE mode consumption of v0.3 policy: G-BD.11.

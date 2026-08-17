# V0.3 TRIGGER TYPE AUDIT — §0.2 GAP C

Per handoff §0.2 GAP C, each of the five cause names introduced by the candidate v0.3 mount manifest must be classified as ONE OF:

- **A. REGISTERED DISTINCT CAUSAL TYPE** — genuine new type; add to registry with definition + predicates + counterexamples + applicability boundary.
- **B. ALIAS / SUBTYPE / EVIDENCE FOR EXISTING CAUSAL TYPE** — synonym, refinement, or diagnostic pattern of an existing v0.2 type. Do NOT register as a distinct type.
- **C. STATE / EVENT INSTANCE** — a state fingerprint or transition indicator that MAY generate a `TriggerCandidate`, but is NOT itself a type.

Audit result: **all five are C** or (in one case) **B**. No new registered type is introduced by this pass.

---

## REFLECTIVE_MISMATCH_PENDING

**Classification: C — STATE / EVENT INSTANCE.**

**Structural basis**: a state fingerprint on `state.pending_diagnostic is not None AND state.pending_diagnostic.mismatch`. When true, `_seed_reflective_candidate_if_needed` produces a `TriggerCandidate` whose `proposed_trigger_type_id = "REFLECTIVE_EXIT_REQUIRED"` (an EXISTING v0.2 type in the B07 family). The state itself is not a type; it is a well-known state fingerprint that generates candidates.

**Near-duplication note**: `REFLECTIVE_MISMATCH_PENDING` sounded like it could be a distinct type separate from `REFLECTIVE_EXIT_REQUIRED`. It is not — the "pending" flag is a STATE description; the resulting causal type IS `REFLECTIVE_EXIT_REQUIRED`. Registering a separate type would fragment the v0.2 B07 vocabulary and violate the "no duplicate types to preserve names from a candidate YAML" invariant.

**Relation to existing type**: generates → `REFLECTIVE_EXIT_REQUIRED`.

**Runtime evidence**: `_seed_reflective_candidate_if_needed` in `pipeline.py`.

---

## MULTI_ONTOLOGY_MOUNT

**Classification: C — STATE / EVENT INSTANCE.**

**Structural basis**: a state fingerprint over `EpistemicSpace.world_model_mounts` cardinality. When more than one mount is active, this is a state indicator that B08 may become relevant. It is NOT a causal type on its own — the causal TYPES that a multi-ontology-mount state may generate are things like `ONTOLOGY_TRANSFER_PENDING` or state-derived candidates for B08 mount targeting.

**Near-duplication note**: distinct from the v0.2 concept "MULTI_ONTOLOGY" which was implicit in B08 v0.2 semantics; not a registered type in v0.2 either.

**Relation to existing types**: multi-mount state may generate candidates for existing B08-owning types when they exist. Currently no such registered type ships — a future pass may register one via `TriggerTypeCandidate` review.

**Runtime evidence**: none in this repair (deferred until a real B08 trigger type is registered). Presence of the state fingerprint remains visible on `state.space_registry.get(space_id).world_model_mounts` for future seeders.

---

## OPERATION_MISMATCH

**Classification: B — ALIAS / SUBTYPE / EVIDENCE.**

**Basis**: `OPERATION_MISMATCH` is one of the `DiagnosticSignal` enum values (`projection.py::DiagnosticSignal`). It appears as a member of `ProjectionDiagnostics.signals`. When a diagnostic carries this signal, `_seed_reflective_candidate_if_needed` uses that fact to ground a `REFLECTIVE_EXIT_REQUIRED` candidate.

`OPERATION_MISMATCH` is therefore **evidence for `REFLECTIVE_EXIT_REQUIRED`**, not a separate type. Registering it as a distinct type would create a false parallel to REFLECTIVE_EXIT_REQUIRED — both would compete to mount B07 for the same underlying cause.

**Relation to existing type**: evidence pattern for `REFLECTIVE_EXIT_REQUIRED`.

**Runtime evidence**: `state.pending_diagnostic.signals` inspected by the seeder + `_state_contradicts_type` in `trigger_lifecycle.py`.

---

## REVISE_APPARATUS_INVOKED

**Classification: C — STATE / EVENT INSTANCE.**

**Structural basis**: indicates that OP-10 REVISE_APPARATUS (from the BACH operator library, G-BD.3) was dispatched. Detectable via `state.pending_projection_proposal is not None` or `state.capability_resolutions[-1].kind == CUTTER_SPEC_SYNTHESIS`.

The apparatus-revision path is HANDLED BY the ADR-S26-023 `CapabilityResolver` (registered / synthesis / organ_gap), NOT by the trigger registry. Turning this state indicator into a trigger type would create a shadow authority that duplicates the resolver's work.

**Relation to existing types**: state indicator; no trigger type required. The resolver is the authority.

**Runtime evidence**: `state.pending_projection_proposal`, `state.capability_resolutions` on `PipelineState`.

---

## CROSS_SPACE_TRANSDUCTION_PENDING

**Classification: C — STATE / EVENT INSTANCE.**

**Structural basis**: indicates that an `emit_context_transduction` call was made (G-BD.6 runtime helper) or a proposal to make one is on state. Detectable via `state.context_transductions[-1]` presence + kind.

`ContextTransduction` is a first-class typed object (G-BD.2). The typed record IS the transition; adding a trigger type for "transduction pending" would create a shadow authority that duplicates the transition object.

**Relation to existing types**: state indicator; no trigger type required. `ContextTransduction` is the authority.

**Runtime evidence**: `state.context_transductions` on `PipelineState`.

---

## Summary

| v0.3 name | Class | Registered as new type? | Runtime path |
|---|---|---|---|
| `REFLECTIVE_MISMATCH_PENDING` | C — STATE | **No** | Seeded as `REFLECTIVE_EXIT_REQUIRED` candidate |
| `MULTI_ONTOLOGY_MOUNT` | C — STATE | **No** | State fingerprint on `EpistemicSpace.world_model_mounts` |
| `OPERATION_MISMATCH` | B — EVIDENCE | **No** (evidence for `REFLECTIVE_EXIT_REQUIRED`) | Signal on `ProjectionDiagnostics.signals` |
| `REVISE_APPARATUS_INVOKED` | C — STATE | **No** | Handled by `CapabilityResolver` (ADR-S26-023) |
| `CROSS_SPACE_TRANSDUCTION_PENDING` | C — STATE | **No** | Handled by `ContextTransduction` (G-BD.2) |

Zero new registered types added. v0.2 B07 + B09 + B02 causes preserved verbatim.

## Test coverage

`test_trigger_lifecycle.py::TestV03CauseNameAudit` — 5 parametrised tests, one per v0.3 name, each asserting the name is NOT present in the registry as a distinct type.

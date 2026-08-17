# D-S26-TRIG-001 CODE_GATE REPAIR — TRIGGER CAUSAL TYPING + ADMISSION

## Defect (recap)

At inherited HEAD `09421fc`:

- `pipeline._apply_delta` wrote `state.admitted_trigger_causes` DIRECTLY from `delta.triggers`. Model output that named `"COUNCIL_REQUIRED"` in a phase delta became an admitted mount authority immediately.
- `pipeline._run_phase_sequence` called `mount_policy.mount(router.module_id, phase)` with NO `proposed_triggers`, so the existing CTA gate in `mount.py::_gate_triggers` never fired on the production path.
- No governed conversion path from `ObservedSignal → TriggerCandidate → CausalTypingDecision → TriggerAdmissionDecision → AdmittedTriggerEvent` existed.
- Reflective S7 / P06 had no pre-mount route: even when `state.pending_diagnostic.mismatch` was true, the pipeline did not seed a REFLECTIVE_EXIT_REQUIRED candidate before P06 was mounted, so B07 was not physically present in the mount.

## Architecture (post-repair)

```
ObservedSignal
    ↓
TriggerCandidate           NO_MOUNT_AUTHORITY
    ↓
CausalTypingDecision       REGISTERED_TYPE | TYPE_GAP | REJECT
    ↓
TriggerAdmissionDecision   ADMIT | COALESCE | REJECT
    ↓
AdmittedTriggerEvent       SEMANTIC_CONDITIONAL_MOUNT (the ONLY authority)
    ↓
SemanticMountPolicy.mount(proposed_triggers=[adapted from admitted events])
```

Every stage is a distinct typed object on `PipelineState`:

- `pending_trigger_candidates: list[TriggerCandidate]`
- `trigger_typing_decisions: list[CausalTypingDecision]`
- `trigger_admission_decisions: list[TriggerAdmissionDecision]`
- `admitted_trigger_events: list[AdmittedTriggerEvent]`
- `rejected_trigger_candidates: list[TriggerCandidate]`
- `trigger_type_gaps: list[TriggerTypeGap]`

`state.admitted_trigger_causes` is preserved as a **compat projection** — `_recompute_admitted_causes_projection()` derives it from `admitted_trigger_events` after every drain. Governor + `_council_needed` continue to read the projection.

## Files changed

| File | Purpose |
|---|---|
| [`socrates_runtime/trigger_lifecycle.py`](../../CALIFORNIAN_ID/src/socrates_runtime/trigger_lifecycle.py) | **NEW** — full lifecycle: enums, `TriggerCandidate`, `CausalTyper`, `TriggerAdmitter`, `AdmittedTriggerEvent`, `TriggerTypeGap`, `TriggerTypeCandidate`, `TriggerTypeRegistry`, default registry with v0.2 B07 + B09 + B02 causes. |
| [`socrates_runtime/state.py`](../../CALIFORNIAN_ID/src/socrates_runtime/state.py) | Added six lifecycle partitions; `admitted_trigger_causes` now compat projection. |
| [`socrates_runtime/pipeline.py`](../../CALIFORNIAN_ID/src/socrates_runtime/pipeline.py) | `_apply_delta` for `triggers` routes to `pending_trigger_candidates` (never direct write). Added `_drain_pending_triggers`, `_seed_reflective_candidate_if_needed`, `_recompute_admitted_causes_projection`. Widened `_council_needed` to cover B07 family (S7 conditional on either B09 council OR B07 reflective causes). Adapter `_admitted_to_trigger_admission(event, router_id=...)` stamps router id so the CTA gate aligns. |
| [`data/socrates/current/routers/trigger_type_registry.yaml`](../../CALIFORNIAN_ID/data/socrates/current/routers/trigger_type_registry.yaml) | **NEW** — YAML mirror of the code-only registry, for Workbench inspection. Runtime does NOT consume it as authority. |
| [`tests/workbench/test_trigger_lifecycle.py`](../../CALIFORNIAN_ID/tests/workbench/test_trigger_lifecycle.py) | **NEW** — 45 tests covering §19 categories, metamorphic corpus, S7/P06/B07 physical pre-mount, v0.3 audit, negatives. |
| [`docs/socrates_gs26/trigger_lifecycle/`](.) | **NEW** — this file + audit docs. |

## GAP reconciliations (§0.2 of the handoff)

### GAP A — v0.3 mount manifest

**Decision: v0.3 candidate mount YAML stays NON-RUNTIME CANDIDATE metadata.**

The production `SemanticMountPolicy` continues to load `data/socrates/current/mount/semantic_mount_manifest.yaml` (v0.2). `data/socrates/candidate_v0_3/mount/semantic_mount_manifest_v0.3.yaml` is not consumed by any runtime code path — verified by `test_trigger_lifecycle.py::TestV03MountManifestIsNonRuntime`.

Rationale: making v0.3 executable in this repair would have required a schema adapter + a second SemanticMountPolicy instantiation, which is out of the bounded scope of D-S26-TRIG-001. The handoff §0.2 explicitly permits Option B (retain v0.3 as non-runtime candidate) provided no second/parallel trigger-authority path exists. Verified.

Any future pass that promotes v0.3 to executable MUST feed the same production admitted-event lifecycle — the lifecycle module is designed to be the single authority sink regardless of manifest version.

### GAP B — B07 / B09 reconciliation

**Decision: preserve v0.2 exactly.**

- **B07 causes**: `REFLECTIVE_EXIT_REQUIRED`, `ROLE_CAPTURE`, `FRAME_GENERATED_FAILURE`, `SELF_REVIEW_RECURSION` — all registered under `owning_body="B07"`.
- **B09 causes**: `COUNCIL_REQUIRED`, `TYPED_VETO`, `MINORITY_MATERIAL` — all registered under `owning_body="B09"`.
- **B02 causes**: `STATUS_DISPUTE` — preserved.
- No cause has `additional_mount_targets` that would double-mount B07 + B09 for the same trigger.
- Verified by `test_trigger_lifecycle.py::TestB07B09Reconciliation` (5 tests).

`REFLECTIVE_MISMATCH_PENDING` from the v0.3 manifest is NOT registered as a new type. It is treated as a **STATE/EVENT indicator**: `_seed_reflective_candidate_if_needed` converts a typed `pending_diagnostic.mismatch` state into a `REFLECTIVE_EXIT_REQUIRED` candidate (the existing v0.2 type). No duplicate types.

### GAP C — v0.3 cause name audit

**Decision: all five v0.3 names are STATE / EVENT / ALIAS indicators, none is a new registered type.**

| v0.3 name | Classification | Reason |
|---|---|---|
| `REFLECTIVE_MISMATCH_PENDING` | **STATE / EVENT INSTANCE** | State fingerprint on `state.pending_diagnostic.mismatch`. The runtime SEED converts it into a `REFLECTIVE_EXIT_REQUIRED` candidate. Not a distinct causal type. |
| `MULTI_ONTOLOGY_MOUNT` | **STATE / EVENT INSTANCE** | State fingerprint on `EpistemicSpace.world_model_mounts` cardinality. Not a causal type on its own. |
| `OPERATION_MISMATCH` | **ALIAS / SUBTYPE / EVIDENCE** for `REFLECTIVE_EXIT_REQUIRED` | One of the `DiagnosticSignal` values a `ProjectionDiagnostics` may carry. It is the evidence pattern that grounds `REFLECTIVE_EXIT_REQUIRED`, not a distinct type. |
| `REVISE_APPARATUS_INVOKED` | **STATE / EVENT INSTANCE** | Indicates OP-10 (BACH operator library) dispatched. The apparatus revision goes through the ADR-S26-023 `CapabilityResolver`, not the trigger registry. |
| `CROSS_SPACE_TRANSDUCTION_PENDING` | **STATE / EVENT INSTANCE** | Indicates a `ContextTransduction` has been proposed. The transition is a first-class object (G-BD.2), not a trigger. |

Verified by `test_trigger_lifecycle.py::TestV03CauseNameAudit` (5 parametrised tests).

## Physical B07 pre-mount for S7 / P06

Deterministic runtime proof at `test_trigger_lifecycle.py::TestReflectivePreMountP06B07::test_reflective_mismatch_leads_to_b07_admission_and_mount`:

```
state.pending_diagnostic = ProjectionDiagnostics(mismatch=True, ...)
    ↓
_seed_reflective_candidate_if_needed(state, "S7")
    ↓ (produces REFLECTIVE_EXIT_REQUIRED candidate from
    ↓  PROJECTION_DIAGNOSTIC source — authorised)
state.pending_trigger_candidates = [candidate]
    ↓
_drain_pending_triggers(state, "S7", trace=None)
    ↓ typing: REGISTERED_TYPE (predicate satisfied)
    ↓ admission: ADMIT
state.admitted_trigger_events = [event]
    event.trigger_type_id = "REFLECTIVE_EXIT_REQUIRED"
    event.owning_body = "B07"
    event.authority = "SEMANTIC_CONDITIONAL_MOUNT"
    ↓
mount_policy.mount("P06", "S7",
    proposed_triggers=[_admitted_to_trigger_admission(event,
                                                       router_id="P06")])
    ↓
MountedContext.body_ids() includes "B07"  ← physical presence proven
```

Ordinary S7 negative mirror at `test_ordinary_s7_does_not_mount_b07`: user text may contain `"exam obedience reflection status BACH council"` — B07 remains ABSENT because no typed reflective state exists.

## Public trace evidence

Every admitted event carries the full lineage in `event.to_public()`:

- `event_id`, `trigger_instance_id`, `trigger_type_id`, `owning_body`, `additional_mount_targets`
- `generating_state_ref`, `cause_object_ref`, `source_kind`, `source_status`
- `phase_relevance`, `materiality_reason`, `admitting_rule`
- `typed_basis_refs`, `registry_version`, `sequence`
- `candidate_ids` (lineage), `typing_id`, `admission_id`
- `authority = "SEMANTIC_CONDITIONAL_MOUNT"`

Verified by `TestTracePublicEvidence::test_admitted_event_carries_full_lineage`. No hidden chain-of-thought.

## Tests + regression

- **New**: 45 tests in `test_trigger_lifecycle.py` covering §19 items 1–30 + §0.2 GAPs A/B/C + coalescence + phase-boundary law + technical-retry-distinct.
- **Full backend**: 942 passed / 4 skipped (was 897/4 inherited floor; +45 lifecycle tests, zero regression).
- **UI**: `NOT_RERUN_UNCHANGED_SURFACE` — no UI surface touched.

## Success criteria (§24) — self-check

| # | Criterion | Status |
|---|---|---|
| 1 | Model output cannot create admitted mount authority directly | ✅ `TestModelSelfAdmissionNegatives` |
| 2 | Four lifecycle stages are distinct runtime records | ✅ `TestLifecycleStages` |
| 3 | `admitted_trigger_causes` no longer a model-write surface | ✅ Now compat projection only |
| 4 | Unknown grounded structure → TYPE_GAP | ✅ `TestOpenWorldTypeGap` |
| 5 | `TriggerTypeCandidate` cannot self-register | ✅ `TestLifecycleStages::test_type_candidate_cannot_self_register` |
| 6 | Full lineage test-visible | ✅ `TestTracePublicEvidence` |
| 7 | Conditional bodies consume admitted events only | ✅ Pipeline passes `admitted_for_phase` to `mount.mount(proposed_triggers=)` |
| 8 | Same structure survives surface mutation | ✅ `TestMetamorphicInvariance::test_same_structure_different_wording_yields_same_type` |
| 9 | Familiar words without structure don't trigger | ✅ `TestMetamorphicInvariance::test_familiar_words_without_structure_no_type` |
| 10 | S7 governed reflective state → valid REFLECTIVE_EXIT_REQUIRED admission | ✅ `TestReflectivePreMountP06B07` |
| 11 | Full B07 physically in MountedContext before P06 call | ✅ Same test |
| 12 | Ordinary S7 does not mount B07 | ✅ `test_ordinary_s7_does_not_mount_b07` |
| 13 | P06 cannot self-authorize its current mount | ✅ Drain runs at TOP of phase iteration, before mount; phase-N delta reaches phase-N+1 |
| 14 | B07 / B09 causal jurisdictions coherently reconciled | ✅ `TestB07B09Reconciliation` |
| 15 | v0.2 B07 semantics not silently lost | ✅ Same |
| 16 | 5 v0.3 cause names classified | ✅ `TestV03CauseNameAudit` |
| 17 | (v0.3 executable path uses same lifecycle) | N/A — v0.3 stays non-runtime candidate |
| 18 | v0.3 non-runtime boundary explicit; no falsely claimed PASS | ✅ `TestV03MountManifestIsNonRuntime` |
| 19 | Cue frequency ≠ authority | ✅ `TestCoalescence::test_same_cause_key_coalesces_into_one_event` |
| 20 | Same-phase retroactive mount impossible | ✅ `TestPhaseBoundaryLaw` |
| 21 | Technical retry distinct from ReflectiveReturn | ✅ `TestTechnicalRetryDistinct` |
| 22 | Direct-assistance path remains direct | ✅ `TestDirectAssistanceRegression` |
| 23 | BACH/Didenko inherited functionality does not regress | ✅ Full backend 942/4 (+45, zero regression) |
| 24 | Focused tests PASS | ✅ 45/45 |
| 25 | Full backend regression ≥ 897 | ✅ 942 |
| 26 | Committed + pushed | ✅ (see git log) |

**D-S26-TRIG-001 CODE_GATE = PASS.**

## Non-goals (carried forward per handoff §21/§22)

- No R9, no P001 Socratic Siege, no G-S27/G-S28, no Kvaqin.
- No production deploy. No Aiye/Sayena/Academy mutation.
- No Workbench/Arena work.
- BACH/Didenko LIVE L1–L8 remain NOT_RUN (env-blocked at previous pass); this repair did not run any live campaign.
- v0.3 mount manifest not made executable — deferred to a future pass with explicit scope.
- No self-modifying production type registration. `TriggerTypeRegistry.register` exists for test harnesses only; the pipeline never calls it from a phase-delta path.

## Carried nonclaims

- LIVE L1–L8: NOT_RUN (unchanged from BACH/Didenko pass; env-blocked).
- R9, P001, G-S27, G-S28, Kvaqin: NOT_RUN.
- Production: NOT_DEPLOYED. Aiye/Academy: NOT_MUTATED.
- No new BACH/Didenko expansion.

**`D-S26-TRIG-001` CLOSED** — CODE_GATE = PASS.

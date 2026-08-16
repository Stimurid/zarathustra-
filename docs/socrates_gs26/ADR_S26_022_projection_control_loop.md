# ADR-S26-022 — Projection-control loop / cutter governance

**Status:** ACCEPTED (implementation landed on `socrates/gs26-projection-control-loop`)
**Sibling artefact:** `docs/socrates_gs26/projection_control_loop/PESKOV_TRACE.json`
**Frozen R8 baseline:** `431fa77` — R8 = PARTIAL (unchanged by this ADR; see §12)

## Context

Semantic bodies **already** encode the loop:

- **B03** — operation-relative objects, applicability, ontology gaps, multiple projections, recognition criteria, residue, reversible local selection.
- **B07** — reflective retreat, changed return, changed operation, changed ontology, changed scene when necessary.
- **B08** — polyontology, object-genesis field mode.

But before this ADR, the **runtime** could not execute the loop. `PipelineExecutor.run` was a single linear `for phase in PHASE_ORDER` pass. S7 fired only in council mode. No phase actually looked at the source with a typed projection spec, so no phase could produce typed diagnostics about the CUT. `RETRY_PENDING` in `workbench_adapters/socrates_adapter.py:311` was a state-model projection node — not a reflective mechanism. The only "return" the runtime could execute was `Terminal.RETURN_OPERATION` — a return to the **human**, not an internal revision of the governing hypothesis.

Symptom: Socrates could name the residue in prose ("возможно, концептуальная резка здесь недостаточна") but could not **make the second look happen**. R8 semantic-arm score reflected the shape of the S-phase state machine, not this deeper architectural gap.

## Decision

Introduce a **projection-control loop** that wraps the linear S0..S10 pass. Three typed objects govern the loop; one control record links them; one small registry hands execution to Tinkuy; four deterministic guards bound the loop.

### 1. Typed objects (`src/socrates_runtime/projection.py`)

- **`SemanticProjectionSpec`** — the declaration of the current *look*. Fields: `projection_id`, `source_id`, `scene_ref`, `operation_id`, `ontology_id`, `target_object_family`, `recognition_criteria`, `segmentation_policy`, `evidence_requirements`, `applicability_assumptions`, `contraindications`, `parent_projection_id`, `revises`, `status`. Content-hashed to a `fingerprint()` the loop guards use.
- **`ProjectionResult`** — typed evidence about the CUT. `objects` (each anchored to `source_id` + `source_span`, both pointing at the ORIGINAL source), `residue` (first-class — what triggers reflection), `coverage`, `unclassified_spans`, `recognition_failures`, `counterexamples`, `internal_conflicts`, `status` (`exploratory | accepted_local | partial | rejected`).
- **`ProjectionDiagnostics`** — typed judgement about the LOOK itself, not only about the objects. Signals from a fixed vocabulary (`OPERATION_MISMATCH`, `ONTOLOGY_LIMIT`, `MULTI_ONTOLOGY`, `OBJECT_GENERATOR_LIMIT`, `RECOGNITION_FAILURE`, `FORCED_COMPLETENESS`, `SCENE_MISMATCH`, `APPLICABILITY_FAILURE`), plus a suggested covering operation when one exists.

### 2. Reflective return (distinct from three neighbours the runtime must keep non-overlapping)

**`ReflectiveReturn`** is the executable form of B07 reflective retreat. It carries `retreat_level` (R1..R6), `return_target` (S1 | S3 | S4), `reason`, `failed_assumption`, `what_remains_valid`, `what_changes`, `revised_operation_kind`, `revised_ontology_id`, `revised_scene_telos`, plus the diagnostic fingerprint that motivated it.

Distinctions (each is a first-class invariant, tested):

| Concept | Semantics | Layer |
|---|---|---|
| **`Terminal.RETURN_OPERATION`** | Return to the **HUMAN**. Terminal for the run. INV-009. | Governor. |
| **`ProviderStatus.RETRIES_EXHAUSTED`** | TECHNICAL retry ended without an OK response. The governing hypothesis did not change. | Phase executor. |
| **`ReflectiveReturn`** | The **governing hypothesis IS changing**. The run continues internally against the ORIGINAL source with a new spec. | Projection control loop. |

### 3. Cutter registry (`src/socrates_runtime/cutter_registry.py`)

Per ADR §8: Socrates never becomes the parser itself. It names the operation, ontology, and recognition policy; a `CutterCapability` executes the cut against the source. The registry is thin — capability metadata plus an `execute(source_text, spec) -> ProjectionResult` callable.

Two capabilities ship in this pass:

- `EXTRACT_CONCEPTS` — concept ontology; leaves non-concept fragments as residue.
- `DIFFERENTIATED_ACCOUNT` — concept + report + gesture + absence + future_work; covers the residue of the concept projection.

More capabilities plug into the same shape. Nothing about the loop mechanics is Peskov-specific: `compute_diagnostics` derives `OPERATION_MISMATCH` from typed evidence (residue families the current operation does not cover, another registered operation that does).

### 4. Immutable-source reprojection (`src/socrates_runtime/projection_step.py`)

`PipelineExecutor.projection_step` is a seam. Bound to a registry via `make_projection_step(registry)`, the step:

1. builds `SemanticProjectionSpec` from `state.operation` (honouring the last reflective return's `revised_ontology_id` on re-entry, preserving lineage via `parent_projection_id`);
2. resolves the operation to a `CutterCapability` — if none is registered, the step is a **no-op** (direct-assistance / non-projection runs are not affected);
3. executes the cutter against **`state.input_text`** — the ORIGINAL, immutable source — never against a prior projection's derived output;
4. records `ProjectionResult` + `ProjectionDiagnostics` in `state.projection_lineage`;
5. sets `state.pending_diagnostic` iff `diagnostics.mismatch`.

The immutable-source invariant is enforced BY CONSTRUCTION: `PipelineState.input_text` is set once at `PipelineExecutor.run` entry and never rewritten; `PipelineState.source_id` derives deterministically from that text; every `SemanticProjectionSpec` carries `source_id`, so P1 and P2 must share it. Test `test_peskov_p2_rereads_original_source_not_p1_units` verifies the invariant end-to-end.

### 5. Outer control loop (`src/socrates_runtime/pipeline.py`)

`PipelineExecutor.run` becomes two layers:

- **inner** `_run_phase_sequence` — the linear `for phase in PHASE_ORDER` from `state.reentry_from` (S0 on first pass; `PHASE_ORDER[return_target_index + 1]` on re-entry).
- **outer** — after each inner pass, `projection_step` runs; if `pending_diagnostic.mismatch`, `_invoke_reflective_epilogue` calls **S7 in reflective mode** (a dedicated call, distinct from the CONDITIONAL S7 inside the pass); the epilogue's delta MUST carry a `ReflectiveReturn`; `_record_reflective_context` records it, marks the failing projection `PARTIAL`, stashes it as public typed context on `state.pending_reflective_context`, and sets `reentry_from = return_target` for the next pass.

> **Historical note — defect D-S26-PROJ-002 (repaired in commit `ba8047f`).** An earlier draft of this ADR had `_apply_reflective_return` silently write the revised operation/scene into state, and had pass 2 start at `return_target + 1` to avoid stale-hint clobbering. Owner audit rejected this: it made `ReflectiveReturn` a side-channel state mutation instead of a governed revision. The repaired semantics (documented above) are: `_record_reflective_context` does NOT overwrite `state.operation`/`state.scene`; the target phase re-executes AT `return_target`, reads `state.pending_reflective_context` from its state snapshot (public typed context), and emits a NEW validated delta under its normal contract. `_apply_delta` clears the context once the target phase writes into its jurisdiction. The Peskov trace at `docs/socrates_gs26/projection_control_loop/PESKOV_TRACE.json` accordingly shows phase sequence `S0..S10 → S7 → S4..S10` (with S4 re-executed) rather than the pre-repair `S0..S10 → S7 → S5..S10` (with S4 skipped).

### 6. Loop guards (all deterministic, no LLM)

- **`MAX_PROJECTION_ITERATIONS = 3`** — P1 + P2 + P3 max. Reached → `projection_loop_bound_reached`.
- **Same-diagnosis fingerprint** — new diagnosis matches a previous pass's fingerprint → `projection_repeat_diagnosis`. Reflection would not add material information.
- **Epilogue produced no `ReflectiveReturn`** — S7 chose PRESERVE_APORIA-shaped silence → `reflective_epilogue_empty`. Not a technical retry; the loop stops and the governor picks a legitimate terminal.
- **Hard-stop terminals** — `SEMANTIC_MOUNT_MISSING`, `FAILED_EXPLICIT` — exit the outer loop immediately.

## Consequences

### Positive

- Semantics that already knew the loop can now execute it. The gap between B03/B07/B08 body text and runtime behaviour closes.
- P1 and P2 are both preserved with typed lineage. A projection can remain locally valid while globally insufficient.
- Provenance is projection-relative and queryable: every object records `projection_id`, `source_id`, `source_span`, `recognition_basis`.
- Direct-assistance / non-projection runs are not penalised: operations without a registered capability get a no-op projection step; the outer loop terminates after one pass exactly as before.
- Human ownership is unchanged: `Terminal.RETURN_OPERATION` remains the governor's terminal for INV-009 and for `operation.applicable=False`.

### Negative / cost

- Two new state fields (`pending_diagnostic`, `reentry_from`) and one new lineage record on `PipelineState` — the state grows.
- Every S-phase pass that emits an operation registered in the cutter registry now performs a projection execution. For symbolic marker cutters this is cheap; for a real NLP cutter this is a real cost.
- Re-entry semantics (start at `return_target + 1`) require the ReflectiveReturn to fully specify the revision; a partial return that leaves `revised_operation_kind` empty produces incoherent pass-2 state. Guarded by the schema's `required` list.

### Non-goals (this pass)

- Rewriting CORE / B01–B10 or P00–P09 body content. **Not touched.**
- Making R8's semantic-arm 7/10. R8 does not exercise the projection-control loop. See §12.
- Building a zoo of cutters. Two capabilities ship — enough to prove the loop on Peskov.
- P001 Socratic Siege. Explicitly deferred (ADR §21).

## Peskov acceptance (executable proof)

`tests/workbench/test_peskov_projection_loop.py::test_peskov_full_projection_control_loop` (and the ten sibling tests) prove the ADR §15 trajectory on Peskov-shaped source:

```
[concept]     Ontology is the study of what exists.
[report]      The team met last Thursday to review scope.
[gesture]     The lead nodded acknowledgement.
[absence]     Data for Q3 is not available.
[future_work] We plan to extend this analysis next quarter.
[concept]     Epistemology is the study of knowledge.
```

Trajectory:

1. Pass 1: `S0..S10` with `operation=EXTRACT_CONCEPTS`.
2. `projection_step` runs P1 → 2 concept objects + 4 residue lines.
3. `ProjectionDiagnostics` raises `OPERATION_MISMATCH` and `RECOGNITION_FAILURE`, suggests `DIFFERENTIATED_ACCOUNT`.
4. Reflective S7 epilogue → `ReflectiveReturn` (R1 → S4) with `revised_operation_kind=DIFFERENTIATED_ACCOUNT`, `revised_ontology_id=differentiated_v1`.
5. `_apply_reflective_return` marks P1 `partial`, writes revised operation into state, sets `reentry_from=S4`.
6. Pass 2 starts at S5 (S4 was the site of the revision). `state.operation.kind` remains `DIFFERENTIATED_ACCOUNT` through S5..S10.
7. `projection_step` runs P2 against the ORIGINAL source with the revised operation → covers all 6 lines, no residue.
8. Loop terminates. Governor picks `ANSWER`.
9. Lineage: 2 entries (P1 `partial`, P2 `accepted_local`), 1 revision linking them, 2 diagnostics.

Committed artefact: `docs/socrates_gs26/projection_control_loop/PESKOV_TRACE.json` (produced by the same test payload, with volatile ids stabilised).

## Tests

- **9 unit tests** in `tests/workbench/test_projection_control_loop.py` — control-flow of the outer loop with synthetic diagnostics + injected ReflectiveReturns. Cover happy path, re-entry, and all four guards, plus explicit "ReflectiveReturn is not RETURN_OPERATION" and "not RETRIES_EXHAUSTED" distinction tests.
- **11 integration tests** in `tests/workbench/test_peskov_projection_loop.py` — full end-to-end with the real CutterRegistry, plus negatives per ADR §17 and targeted regressions per ADR §20 (direct-assistance no-op, RETURN_OPERATION path, no-covering-op iteration bound).

Full suite: **730 passing, 4 skipped** (baseline 710 + 20 new: 9 loop + 11 Peskov).

## Rejected alternatives

- **Rewrite the S-phase state machine.** Rejected — the S0..S10 order encodes real ordering constraints (mount before triggers, ownership before execution). The loop is orthogonal.
- **Move S7 after S9 in the phase order.** Rejected — S7's council mode legitimately runs earlier. Instead we invoke S7 twice conceptually: CONDITIONAL council-mode inside the pass; explicit reflective-mode epilogue after the pass.
- **Universal `SemanticUnitExtractor` at boot.** Rejected — ADR §8. Extraction is capability-registered, operation-relative; there is no "canonical text atoms" surface.
- **Store P2 as a diff over P1.** Rejected — ADR §12. Would break the immutable-source invariant and make "P2 rereads original" impossible to prove.
- **Prose-only reflection ("Socrates says: maybe try again").** Rejected — ADR §17. Would leave residue silently unaddressed. The typed `ReflectiveReturn` contract is what makes the loop executable.

## R8 baseline (unchanged)

Per ADR §19, R8 evidence at `431fa77` remains **PRE-PROJECTION-LOOP BASELINE**:

```
R8 FINAL: PARTIAL
- request integrity: 33/33 PASS
- mandatory-body mount fail-close: 9/9 PASS
- behavioral ablation: NOT_DEMONSTRATED
- semantic improvement: 6/10 required B_BETTER (threshold=7) → FAIL
- extra C05 RETRIEVAL_ATTENTION: B_BETTER
- direct-assistance regression: NONE
- new fatal regressions: NONE
```

**Not rerun by this pass.** R8 does not exercise the projection-control loop; rerunning would measure a different property. `R8_FINAL_GATE.json` at `docs/socrates_gs26/live_acceptance/r8_closure/` is untouched. Semantic bodies were NOT modified.

## Claim boundary

This ADR delivers the smallest complete mechanism that makes Socrates able to:

1. notice a bad cut (typed `ProjectionDiagnostics.mismatch`);
2. change the cut (typed `ReflectiveReturn` with `revised_operation_kind`);
3. actually execute the new cut (`projection_step` reads ORIGINAL source, new `ProjectionSpec`, `CutterRegistry` executes).

It does **NOT** claim: real NLP-driven cutting (the shipped cutters are symbolic marker-scanners — enough to prove the loop; a fabric-parser / live-model cutter plugs into the same shape); LIVE-model Peskov acceptance on 302.ai (deterministic proof only in this pass); R8 semantic-arm gate closure; P001 Socratic Siege unblock.

## Follow-ups

- Wire a real NLP / fabric-parser cutter capability behind an operation kind Socrates already emits.
- LIVE Peskov acceptance: extend `LiveModelPhaseExecutor` support with an S7 router prompt that references the pending `ProjectionDiagnostics` in the mounted context, so a real model can emit the typed `ReflectiveReturn`.
- Extend `CutterRegistry` from Workbench (per-workspace registration) once a second Peskov-shaped case appears.

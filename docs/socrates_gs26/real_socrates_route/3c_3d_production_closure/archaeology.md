# 3C+3D production closure — archaeology

## Baseline

| Item | Value |
|---|---|
| Repo | `C:/projects/zarathustra-push` |
| Base branch | `socrates/3d-hybrid-dyad` |
| Base SHA | `f53b583e9e45ddc57d9cdc9f07f2834e6b11790f` |
| Repair branch | `socrates/3cd-production-closure` |
| Implementation SHA | `fe34f3dd11f398212db61457250ffaf9745707ab` |
| Production entry SHA | `b31b88f77197c0818437649f9e90660a5143bdac` |

## Question 1 — Scene identity across a context lifetime

* `SocratesContext.scene_id` exists (`socrates_runtime/context_store.py:41`) and is
  persisted to disk (`SQLiteContextStore.save`,
  `californian_id/socrates_context_store.py:68-83`).
* `snapshot_context()` sets `ctx.scene_id = state.scene_id` after every run
  (`socrates_runtime/context_continuity.py:108`).
* `hydrate_state_from_context()` sets `state.scene_id = ctx.scene_id` at
  request entry (`socrates_runtime/context_continuity.py:36`), so on turn 2
  and later of the same context, `state.scene_id` carries the persisted
  DAG-node id before 3D runs.
* `state.scene_id` is declared on `PipelineState` (`socrates_runtime/state.py:330`).

The stable identity for the whole scene lifetime exists, is written, and is
hydrated back in time for the 3D seam on turn 2. On turn 1 it is
empty because 3A+ recognition assigns it *after* the 3D pass.

## Question 2 — Telos vs continuation identity

* `hybrid_dyad.scene_scope_key(state)` (`socrates_runtime/hybrid_dyad.py:347-356`
  in the base commit) returned `f"telos:{state.scene.telos.lower().strip()}"`
  unconditionally. Its comment documented the choice as forced by turn-1
  timing (scene_id unassigned then).
* `runtime.py:362-364` in the base commit built `prior_scene_key = f"telos:{prior_ctx.last_telos.strip().lower()}"`.

Both seams keyed dyad scope on telos wording. When the runtime's own S1
phase rephrased a natural-language telos across turns (the production
symptom) the two derived scope keys disagreed and
`run_dyadic_pass` classified the turn as `SCENE_SHIFT`, which
* cleared `used_prior_record_ids`,
* set `causal_effect = "none"`,
* prevented `PredictionClass.REUSE_DISTINCTION`, and
* short-circuited the user-hypothesis-revision path (which requires
  `accept_hyps` to be visible — visibility is scoped by
  `_visible_records(session, scene_key, space_key)` at
  `hybrid_dyad.py:448-459`).

Test evidence that the persistence path itself worked:
`test_hybrid_dyad_3d.TestContextSnapshotHydration::test_dyad_rides_existing_context_store_not_a_new_db`
(`tests/workbench/test_hybrid_dyad_3d.py:424-443`) already exercised
two `SocratesRuntime` instances sharing one context and observed dyad
reuse — but only because the test used identical `_hints(telos="answer directly")`
on both calls. Production S1 rephrases telos naturally, so the same
hydration path was unreachable in the LIVE setting.

## Question 3 — Where repeated apparatus evidence should persist

* `_apparatus_repeat: dict[str, int]` initialised on the runtime instance
  (`socrates_runtime/runtime.py:180`) and passed to
  `run_apparatus_diagnostic(..., repeat_index=self._apparatus_repeat)`
  (`runtime.py:340` in the base commit).
* Key: `f"{state.space_id or 'space_default_workspace'}:{apparatus_ref}"`
  (`aporia_and_world_map.py:701-703`).
* Increment: `repeat_index[key] += 1` only when `mismatch` is true
  (`aporia_and_world_map.py:758-762`).
* No reset — the dict grows for the lifetime of the runtime instance.
* Consumer (`aporia_and_world_map.py:784-787`): `repeats >= 2 and mismatch`
  promotes classification to `APPARATUS_MISMATCH_CANDIDATE`.
* Downstream: `hybrid_dyad.py:917-927` maps classification to
  `FailureSource`; classification also flows to
  `SocratesRunResult.apparatus_diagnostic` (`runtime.py:96, 129, 561`),
  the HTTP bridge (`californian_id/socrates_bridge.py:142`), and the
  dialogue log (`californian_id/dialogue_log.py:75-78`).
* **World-map admission is proposal-only** (`aporia_and_world_map.py:277-329`
  `WorldMapRegistry.admit_update` requires a `REVISION_WARRANTED` review
  matching `triggered_by_review_id` or an `authorized_transition_ref`);
  the runtime never calls `admit_update`.

The context snapshot itself was the correct persistence carrier:
`SocratesContext.recognition_state` (`context_store.py:50`) is a free-form
dict already used to persist the dyad projection under key `dyad`
(`context_continuity.py:117-133`). Adding a sibling key
`apparatus_repeat` reuses the existing carrier, requires no new database,
no new authority path, and preserves per-context scoping (the counter
is bounded to the context that produced it and does not leak to unrelated
contexts).

## Question 4 — EVIDENCE_GAP vs GENUINE_APORIA

Full priority chain in `run_apparatus_diagnostic` at
`aporia_and_world_map.py:772-802` (first-match wins):

1. `organ_gap or type_gaps or (not applicable and why_not in EVIDENCE_WHY_NOT)`
   → `EVIDENCE_GAP` — `contributing:typed_source_or_organ_gap`.
2. `(not applicable) and (not open_world) and term_val == RETURN_OPERATION`
   → `OPERATION_GAP`.
3. `(not applicable) and (not open_world)` → `OPERATION_GAP`.
4. `"SCENE_MISMATCH" in signals` → `SPACE_MISMATCH`.
5. `repeats >= 2 and mismatch` → `APPARATUS_MISMATCH_CANDIDATE`.
6. Ontology signals → `ONTOLOGY_GAP`.
7. `mismatch` or projection-mismatch signals → `PROJECTION_GAP`.
8. `term_val == PRESERVE_APORIA or open_world or conflicts` → `GENUINE_APORIA`.
9. Default → `ORDINARY_UNRESOLVED`.

`PRESERVE_APORIA` is a terminal set *upstream* of `run_apparatus_diagnostic`
(the diagnostic only reads `outcome.terminal`). Terminal and classification
are independent decisions — no invariant aligns them.

The failure P3C-3 (`terminal = PRESERVE_APORIA`, `classification = EVIDENCE_GAP`)
happens when organ_gap is true and Order 1 wins before Order 8 is
considered. The specific gap is correct evidence but it is not the
primary diagnosis: `PRESERVE_APORIA` means the runtime already committed
to a genuine-aporia terminal. The dyad consumer
(`hybrid_dyad.py:917-927`) maps only `GENUINE_APORIA` to
`FailureSource.GENUINE_DISAGREEMENT`; a misclassified case loses that
mapping and returns `FailureSource.NONE`.

## Question 5 — One boundary or three roots?

* **D-S26-3D-LIVE-TELOS-001** and the user-hypothesis-revision failure
  (P3D-2b) are the **same** root: `scene_scope_key` and `prior_scene_key`
  both keyed on telos when a stable persisted `scene_id` was available.
* **D-S26-3C-LIVE-REPEAT-001** is a **coupled** root of the same broader
  theme "cross-HTTP state continuity" but with a distinct mechanism: not
  a scoping bug, but a missing persistence write for a state that
  already had the correct in-process semantics.
* **D-S26-3C-LIVE-ORGAN-PRIORITY-001** is **distinct**: pure classification
  priority in `aporia_and_world_map.run_apparatus_diagnostic`, no
  persistence angle, no dyad angle.

Classification: **COUPLED_ROOTS** overall, with ORGAN-PRIORITY-001 as a
separate defect that happens to fall inside the same LIVE
production-acceptance PARTIAL evidence set.

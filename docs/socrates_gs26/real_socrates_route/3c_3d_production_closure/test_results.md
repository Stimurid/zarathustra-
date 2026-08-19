# 3C+3D production closure — local test results

## Baseline (before repair, at `f53b583`)

`1276 passed / 4 skipped / 0 failed`

## Repair floor (after repair, at `fe34f3d`)

```
PYTHONPATH=src pytest tests/ --tb=short -q
...
1287 passed, 4 skipped in 111.04s (0:01:51)
```

**Delta:** exactly `+11` — the eleven new closure regression cases in
`tests/workbench/test_3c_3d_production_closure.py`. No unexplained
regression in the pre-existing 1276.

## Targeted suites (after repair)

| Suite | Result |
|---|---|
| `test_hybrid_dyad_3d.py` + `test_aporia_apparatus_3c.py` + `test_context_continuity_3a_plus.py` | 73 passed |
| `test_private_work_plane.py` + `test_socrates_api_endpoint.py` + `test_socrates_runtime.py` + `test_socrates_participant_and_http.py` + `test_aporia_and_world_map.py` | 107 passed |
| `test_3c_3d_production_closure.py` (new) | 11 passed |

## New closure regression cases (`test_3c_3d_production_closure.py`)

* **CASE A** — `TestCaseA_DistinctionReuseAcrossTelosRephrase.test_reuse_holds_when_telos_wording_drifts`  
  Two separate `SocratesRuntime` instances share one `SQLiteContextStore`
  context. Turn-1 telos "clarify the distinction requested" vs turn-2
  "apply the previously established distinction" — asserts no
  `SCENE_SHIFT`, `causal_effect == "reuse_prior_distinction"`,
  non-empty `used_prior_record_ids`, terminal `DISTINGUISH`.
* **CASE B** — `TestCaseB_GenuineSceneBoundaryStillIsolates.test_different_telos_without_context_id_still_shifts`  
  One in-process session (no context_id) with two explicitly different
  `_hints(telos)` values — asserts `SCENE_SHIFT` still fires and no
  reuse happens. Guards the `CASE4SceneBoundary` contract.
* **CASE C** — `TestCaseC_UserHypothesisRevisionAcrossHttp.test_explicit_reject_revises_across_runtime_instances`  
  Two runtime instances share one context. Turn 1 mints an epistemic
  hypothesis; turn 2 explicitly rejects it — asserts
  `user_hypothesis_revised == True`, `INFORMATIVE_SURPRISE`, terminal
  `CHALLENGE`.
* **CASE E** — `TestCaseE_RepeatedProjectionAcumulatesAcrossHttp.test_second_runtime_instance_promotes_to_mismatch_candidate`  
  Injected mismatch on two runtime instances sharing one context.
  Turn 1 → `PROJECTION_GAP`. Turn 2 → `APPARATUS_MISMATCH_CANDIDATE`.
  Guards D-S26-3C-LIVE-REPEAT-001 and confirms `durable_write_attempted
  == False`.
* **CASE F** — `TestCaseF_RepeatStateIsolatedFromFreshContext.test_new_context_gets_ordinary_projection_gap_not_mismatch`  
  Warms one context to `APPARATUS_MISMATCH_CANDIDATE`, then opens a
  fresh context — asserts fresh context returns `PROJECTION_GAP`, not
  `APPARATUS_MISMATCH_CANDIDATE`. Guards against cross-context leakage.
* **CASE J**
  * `test_preserve_aporia_plus_source_gap_yields_genuine_aporia` —
    `PRESERVE_APORIA` terminal + `SOURCE_GAP` operation → asserts
    `classification == GENUINE_APORIA` with
    `contributing:typed_source_or_organ_gap` and
    `preserve_aporia_terminal_promoted_over_evidence_gap` in grounds.
  * `test_non_preserve_aporia_source_gap_still_evidence_gap` — non-aporia
    terminal + `SOURCE_GAP` → asserts classification is still
    `EVIDENCE_GAP` (regression guard on the pre-repair chain).
* **CASE K** — `TestCaseK_NoNewStore.test_repeat_state_persists_on_recognition_state_not_a_new_db`  
  After an injected-mismatch LIVE `SocratesRuntime.run`, asserts the
  persisted `SocratesContext.recognition_state` contains a non-empty
  `apparatus_repeat` dict — confirms the carrier rides the existing
  context store, no new DB.
* **CASE L** — `TestCaseL_SceneScopeKeyPreference`
  * `test_scene_id_wins_over_telos` — with both set, key is
    `scene:<id>`.
  * `test_telos_fallback_when_no_scene_id` — with only telos, key is
    `telos:<lower-stripped>`.
  * `test_default_when_neither` — default `scene:default`.

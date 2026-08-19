# 3C+3D production closure — changed files manifest

Implementation commit: `fe34f3dd11f398212db61457250ffaf9745707ab`
Branch: `socrates/3cd-production-closure`
Parent: `f53b583e9e45ddc57d9cdc9f07f2834e6b11790f`

`git diff --stat f53b583..fe34f3d`:

```
 CALIFORNIAN_ID/src/socrates_runtime/aporia_and_world_map.py      |  13 ++
 CALIFORNIAN_ID/src/socrates_runtime/context_continuity.py        |  25 ++
 CALIFORNIAN_ID/src/socrates_runtime/hybrid_dyad.py               |  18 +-
 CALIFORNIAN_ID/src/socrates_runtime/runtime.py                   |  53 +++-
 CALIFORNIAN_ID/src/socrates_runtime/state.py                     |   7 +
 CALIFORNIAN_ID/tests/workbench/test_3c_3d_production_closure.py  | 316 +++++++++++++++++++++++
 6 files changed, 434 insertions(+), 7 deletions(-)
```

## File-by-file reason

| Path | Reason |
|---|---|
| `socrates_runtime/hybrid_dyad.py` | R1: `scene_scope_key` prefers persisted `state.scene_id`, falls back to telos. Preserves in-process turn-1 semantics and the `CASE4SceneBoundary` contract. |
| `socrates_runtime/runtime.py` | R2 + R3 + R4a/b: symmetric `prior_scene_key`; legacy `telos:` scope_id migration on dyad hydration; hydrate `_apparatus_repeat` from `prior_ctx`; publish `state.apparatus_repeat_projection` after diagnostic. |
| `socrates_runtime/context_continuity.py` | R4c: `snapshot_context` persists `state.apparatus_repeat_projection` into `ctx.recognition_state["apparatus_repeat"]` with per-key `max(int)` merge. |
| `socrates_runtime/state.py` | R4d: new field `apparatus_repeat_projection: dict[str, int] | None` on `PipelineState`. |
| `socrates_runtime/aporia_and_world_map.py` | R5: post-chain promotion — `PRESERVE_APORIA + EVIDENCE_GAP` → `GENUINE_APORIA` with `contributing:typed_source_or_organ_gap` in grounds. |
| `tests/workbench/test_3c_3d_production_closure.py` | Eleven new regression tests: CASE A/B/C exercise cross-runtime hydration + scope stability; CASE E/F prove cross-HTTP repeat accumulation + isolation; CASE J proves aporia promotion + non-terminal-aporia guard; CASE K + CASE L cover carrier persistence and unit-level scope-key priority. |

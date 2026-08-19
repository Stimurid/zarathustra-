# 3C+3D production closure — repair design

**Implementation SHA:** `fe34f3dd11f398212db61457250ffaf9745707ab`

Five source files touched. One new test file added. No new database, no
new authority path, no world-map admission bypass, no new dyad system.

## R1 — `scene_scope_key` prefers persisted `scene_id`
**File:** `CALIFORNIAN_ID/src/socrates_runtime/hybrid_dyad.py:347-364`

```python
def scene_scope_key(state):
    scene_id = (getattr(state, "scene_id", "") or "").strip()
    if scene_id:
        return f"scene:{scene_id}"
    telos = (state.scene.telos or "").strip().lower()
    return f"telos:{telos}" if telos else "scene:default"
```

Turn-1 fallback to telos is preserved (`scene_id` unassigned pre-recognition)
so the in-process `CASE4SceneBoundary` contract (two different telos hints
on the same runtime instance without a context store) still classifies
`SCENE_SHIFT`.

## R2 — `prior_scene_key` prefers `prior_ctx.scene_id`
**File:** `CALIFORNIAN_ID/src/socrates_runtime/runtime.py` (dyad seam)

```python
prior_scene_key = ""
if prior_ctx is not None:
    if prior_ctx.scene_id:
        prior_scene_key = f"scene:{prior_ctx.scene_id}"
    elif prior_ctx.last_telos:
        prior_scene_key = f"telos:{prior_ctx.last_telos.strip().lower()}"
```

Symmetric with R1: when the persisted `scene_id` exists, both keys agree
across turns regardless of natural S1-telos rephrasing.

## R3 — Legacy `telos:` scope_id migration on dyad hydration
**File:** `CALIFORNIAN_ID/src/socrates_runtime/runtime.py` (dyad hydration)

When turn 2 hydrates records from `prior_ctx.recognition_state.dyad`,
records written on turn 1 carry `scope_id = "telos:<wording>"` (because
`state.scene_id` was empty then). If `prior_ctx.scene_id` is now set, the
hydration block rewrites every SCENE-scoped record's `scope_id` to
`f"scene:{prior_ctx.scene_id}"`. Without this migration,
`_visible_records` would drop the prior records under the new key and
distinction reuse would still miss.

## R4 — `_apparatus_repeat` rides the context snapshot
**Files:** `runtime.py` (hydrate + publish),
`socrates_runtime/context_continuity.py` (persist with max-merge),
`socrates_runtime/state.py:376` (new field `apparatus_repeat_projection`).

* On request entry, if `prior_ctx.recognition_state["apparatus_repeat"]`
  is a dict, merge it into `self._apparatus_repeat` with `max(int)` per
  key.
* After `run_apparatus_diagnostic`, publish the (possibly incremented)
  dict onto `state.apparatus_repeat_projection`.
* `snapshot_context` writes `state.apparatus_repeat_projection` into
  `ctx.recognition_state["apparatus_repeat"]` with a per-key `max(int)`
  merge over any prior value; an empty projection retains the prior
  counter.

Keys remain `f"{space_id}:{apparatus_ref}"` (unchanged) so cross-context
leakage is impossible: a fresh `context_id` starts with an empty
`recognition_state`.

## R5 — `PRESERVE_APORIA + EVIDENCE_GAP` promotes to `GENUINE_APORIA`
**File:** `CALIFORNIAN_ID/src/socrates_runtime/aporia_and_world_map.py`
(post-chain guard, immediately after the novelty-demand guard):

```python
if term_val == Terminal.PRESERVE_APORIA and classification == GapKind.EVIDENCE_GAP:
    classification = GapKind.GENUINE_APORIA
    grade = AporiaGrade.APORIA
    grounds.append("contributing:typed_source_or_organ_gap")
    grounds.append("preserve_aporia_terminal_promoted_over_evidence_gap")
```

Scope limited to the specific failing combo:

* `PRESERVE_APORIA + APPARATUS_MISMATCH_CANDIDATE` → untouched (mismatch
  is warranted apparatus revision candidate, stronger than plain aporia).
* `PRESERVE_APORIA + OPERATION_GAP` → untouched (operation applicability
  failure is a specific structural claim).
* `PRESERVE_APORIA + SPACE_MISMATCH / ONTOLOGY_GAP / PROJECTION_GAP` →
  untouched.
* Non-`PRESERVE_APORIA` `EVIDENCE_GAP` → untouched.

The specific gap that was previously the primary classification is
retained as a grounds entry so downstream evidence readers see it.

## Alternatives rejected

* **New global process dict for apparatus repeat** — rejected: unbounded,
  leaks across contexts, contradicts handoff.
* **New second dyad DB or memory store** — rejected: reuse the existing
  `recognition_state` carrier.
* **Force scene_scope_key to always use `session_key = context_id`** —
  rejected: breaks the `CASE4SceneBoundary` in-process contract where
  two logical scenes coexist within one runtime without a store.
* **Fuzzy telos similarity threshold** — rejected: unreliable, hard to
  reproduce, ties dyadic reuse to a heuristic.
* **Enum extension `APORIA_WITH_EVIDENCE_GAP`** — rejected: new enum
  value ripples through consumers (dyad, dialogue_log, HTTP) with no
  added expressive power; `grounds` already carries the contributing
  evidence.
* **Priority inversion (move Order 8 above Order 1 for all cases)** —
  rejected: over-broad, would break `OPERATION_GAP` and
  `APPARATUS_MISMATCH_CANDIDATE` primary classifications when combined
  with `PRESERVE_APORIA`.

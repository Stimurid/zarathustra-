# 3C+3D Owner Hardening — evidence pack

**Task ID:** `SOCRATES-GS26-3CD-OWNER-HARDENING-20260819-002`
**Predecessor:** `SOCRATES_3C_3D_PRODUCTION_CLOSURE_PASS` (`fe34f3d` deployed).
**Owner finding:** Pass-1 LIVE C only proved *inter-context* isolation; the harder
invariant — *same context_id + genuine scene transition → no dyadic
reuse of scene-local state* — was not covered on LIVE.

**Repair branch:** `socrates/3cd-owner-hardening`
**Hardening SHA:** `486eff34baf338b0e8977ab03c5160f4c856944f`
**Deployed SHA (`/opt/tinkuy/DEPLOY_SHA`):** `486eff34baf338b0e8977ab03c5160f4c856944f`
**Rollback snapshot:** `/opt/tinkuy/rollback_snapshot_pre_486eff3.tar.gz`

## Repair summary (runtime.py, pre-3D)

The runtime already received `context_action` at line 199 (well before
3D). Recognition (which mints new scene identity) runs at line 520 —
AFTER 3D. That ordering meant a genuine same-context scene transition
could never be seen by 3D on the turn it was requested; the isolation
would land one turn late.

Hardening detects a typed pre-3D scene-transition signal:

```python
_pre3d_scene_boundary = (
    _act_kind in {"NEW_SCENE", "SPACE_TRANSITION"}
    and bool(_act.get("human_explicit_choice")))
```

When it fires:
1. Mint a fresh `scene_id` via `epistemic_model.new_scene_id`.
2. Register it in `state.scene_registry` with `parent_scene_id` = the
   prior scene (preserving lineage).
3. Set `state.scene_id = new_sid` before 3D runs.
4. Trace `pre_3d_scene_transition` for evidence.

Effect on the dyad:
- `scene_scope_key(state)` returns `scene:<new_sid>` — different from
  `prior_scene_key = "scene:" + prior_ctx.scene_id`, so `scene_shift`
  fires on THIS turn, not one turn late.
- Any new dyad records write under the new scene_id, giving clean
  turn-3+ isolation.

The trunk-inheritance semantics for non-explicit FORKs are preserved:
a fork branch inside a scene continues to see trunk distinctions.

## Files

- `README.md` — this file.
- `production_deploy.md` — deploy trace + verification.
- `production_live_acceptance.md` — LIVE HC-1/2/3 evidence.
- `completion_report.md` — verdict + control state.
- `live_evidence/` — raw JSON responses from real production HTTP.

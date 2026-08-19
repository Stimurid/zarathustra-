# 3C+3D production closure — root-cause decision

| Defect | Root | Verdict | Evidence |
|---|---|---|---|
| D-S26-3D-LIVE-TELOS-001 | Dyad scope keyed on volatile telos wording when a stable persisted `scene_id` is available. | **SAME_ROOT** with the user-hypothesis-revision failure P3D-2b (revision is blocked because visibility filter drops the prior hypothesis under the wrong scope key). | `hybrid_dyad.scene_scope_key` at base commit; `runtime.py:362-364` at base commit; `SocratesContext.scene_id` and `hydrate_state_from_context` at `context_continuity.py:36`. |
| P3D-2b (user-hypothesis revision) | (see above) | **SAME_ROOT** as TELOS-001. | `_visible_records` at `hybrid_dyad.py:448-459` filters records by `scope_id`; a scope mismatch prevents revision. |
| D-S26-3C-LIVE-REPEAT-001 | `_apparatus_repeat` state lives on the runtime instance; production builds a new `SocratesRuntime` per HTTP request; no persistence to `SocratesContext`. | **COUPLED_ROOT** with TELOS-001 under the broader "cross-HTTP state continuity" theme, but with a **distinct mechanism** (missing carrier write, not a scope selection bug). | `runtime.py:180`; grep-confirmed absence of `_apparatus_repeat` anywhere in the context save path. |
| D-S26-3C-LIVE-ORGAN-PRIORITY-001 | `run_apparatus_diagnostic` chain has Order 1 (organ_gap → `EVIDENCE_GAP`) fire before Order 8 (`PRESERVE_APORIA` → `GENUINE_APORIA`). | **DISTINCT** — pure classification-priority logic, no persistence angle, no dyad angle. | `aporia_and_world_map.py:772-802`, subagent-confirmed priority ordering table. |
| D-S26-QSEL-003 | Unrelated. | **OPEN** (nonblocking, unchanged). | Handoff. |

## Why not one shared repair for all three

The two theme-related roots (TELOS-001 + REPEAT-001) share the observation
that state that should survive across HTTP requests inside one context
must ride the persisted `SocratesContext` — which is the existing
architectural carrier. Each requires a distinct write, though: the dyad
projection is already persisted (the bug was in the scope-key selection,
not persistence), while the apparatus repeat counter was not persisted
at all (the bug was the missing carrier write).

ORGAN-PRIORITY-001 has no persistence angle: it is a bug in a
first-match if/elif chain. Combining it with the other two would
overload one commit and would not simplify the fix.

The user-facing defect ledger keeps all three IDs open until the
production LIVE acceptance confirms each was closed independently.

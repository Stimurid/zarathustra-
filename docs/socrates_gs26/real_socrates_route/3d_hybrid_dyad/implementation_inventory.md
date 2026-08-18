# 3D implementation inventory

Default: `create_new_store = false`. No new memory / persona / relationship / argument / fabric store.

| OBJECT | LOCATION | CURRENT/HISTORICAL/DONOR/DEAD | LIVE CALLER | STATE/PERSISTENCE | TEST COVERAGE | 3D REUSE DECISION |
|---|---|---|---|---|---|---|
| `UserEpistemicView`, `UserHypothesis`, `BaselinePredictor`, `SurpriseAssessment` | `context_governance.py` | CURRENT (SOC-PRED/USERMODEL/SCENEBIND types) | 3A+ tests; **not** previously in `SocratesRuntime.run` | ephemeral view | `test_context_governance.py` | REUSE types; 3D `DyadicSession.user_view` holds hypotheses |
| Hybrid audit P-HYBRID-1/2/3 | `docs/socrates_gs26/hybrid_dyad_audit/HYBRID_DYAD_TRANSFER_AUDIT.md` | HISTORICAL (doc-only 3D, zero code) | none | none | none | DONOR of questions; not authority to invent a store |
| Scene / Space / Branch | `epistemic_model.py`, `state.py` | CURRENT | 3A+ continuity | context store | `test_context_continuity_3a_plus.py` | REUSE; dyad scene scope = telos at 3D seam |
| `ConflictRegistry` / `ConflictHoldingState` | `epistemic_model.py` | CURRENT | 3A+/governor | in-run state | epistemic tests | REUSE for productive disagreement |
| Context snapshots | `context_store.py` / `context_continuity.py` | CURRENT | `SocratesRuntime.run` | SQLite via existing store | 3A+ | REUSE: `recognition_state["dyad"]` |
| 3B private work | `private_work_runtime.py` / `private_work_plane.py` | CURRENT | post-pipeline, pre-3C | ephemeral shadow | `test_private_work_plane.py` | REUSE orchestrator; 3D is deterministic, no extra LLM pass |
| 3C `run_apparatus_diagnostic` | `aporia_and_world_map.py` | CURRENT | after 3B | in-process WorldMapRegistry | `test_aporia_apparatus_3c.py` | CONSUME; no 3C↔3D reentry (`stop_reason=no_3c_reentry`) |
| WorldMapRegistry | `SocratesRuntime.world_map_registry` | CURRENT | 3C | in-process | 3C | PATTERN only for `DyadicSessionRegistry` |
| B05 / `_commit_memory_if_any` | `runtime.py` | CURRENT | end of run | WM deny without standing human authority | runtime tests | 3D never mints durable write |
| HTTP bridge | `socrates_bridge.py` | CURRENT | `/api/socrates/run` | new runtime per request | HTTP tests | Expose compact `dyad`; hydrate via context_id |
| Dialogue compact log | `dialogue_log.py` | CURRENT | API log | compact fields | `test_dialogue_log.py` | Add prediction/surprise/write/causal fields |
| Persona / Indago / Tinkuy home | neighbouring design line | UNRESOLVED; not 3D authority | — | — | — | **DO NOT IMPLEMENT** |
| Autoprompt / constitution rewrite | 3E | NOT STARTED | — | — | — | **DO NOT IMPLEMENT** |
| `DyadicSession` / `run_dyadic_pass` | `hybrid_dyad.py` | NEW this pass | `SocratesRuntime.run` after 3C | in-process registry + context snapshot | `test_hybrid_dyad_3d.py` | WIRE; not a second database |

## Duplicates not created

- No relationship store
- No user-profile database
- No persona ontology / residency
- No second private-work orchestrator
- No automatic prompt mutation

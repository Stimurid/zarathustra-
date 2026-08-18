# 3C implementation inventory

## Already existed (REUSE)

| Object | Path | Status |
|---|---|---|
| 3C types (AporiaObservation, open_apparatus_mismatch, WorldMapRegistry) | `CALIFORNIAN_ID/src/socrates_runtime/aporia_and_world_map.py` | SUBSTRATE, test-only before this pass |
| PRESERVE_APORIA terminal | `governor.py` / `state.py` | LIVE |
| ProjectionDiagnostics / lineage / residue | `projection.py` | LIVE |
| ReflectiveReturn / same-source reprojection | `pipeline.py` | LIVE |
| OrganGap / CapabilityResolver | `capability_resolution.py` | LIVE |
| 3B private work seam | `private_work_runtime.py` + `runtime.py` | LIVE |
| B05-shaped write | `SocratesRuntime._commit_memory_if_any` → WM deny | LIVE gate |
| Space/Scene registries | `epistemic_model.py` / `context_store.py` | LIVE |

## Not found (not invented)

- No `AporiaKeeper` class (B07 “Boundary Keeper” is prose)
- No `OntologyGapEvent` Python type (catalog/schema-only)
- No named `state_write_gate` (WM `commit_if_authorized` is the gate)

## Wired this pass (WIRE, not a second system)

- `run_apparatus_diagnostic` in the existing 3C module
- Invoked from `SocratesRuntime.run` after 3B, before B2Q-R
- `WorldMapRegistry` held on `SocratesRuntime` (in-memory, per process)
- 3B allowlist gained module `apparatus_diagnostic` / purpose `APPARATUS_DIAGNOSTIC` (registered; diagnostic itself is deterministic and does **not** auto-increment extra private passes)
- API: `apparatus_diagnostic` on `SocratesRunResult` / bridge / compact dialogue log

## Duplicates not created

- No second private orchestrator
- No new memory store / fabric store / argument store
- No silent world-map mutation
- 3D/3E not started

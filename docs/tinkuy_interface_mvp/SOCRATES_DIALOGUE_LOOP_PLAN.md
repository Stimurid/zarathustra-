# Socrates Dialogue Loop — Implementation Plan

**Base:** `a00e4e6` (vertical slice: Launchpad + Session + Run + Artifact + SQLite).
**Freeze:** ON — no new runtime, memory, persona layer, ontology engine, or agent framework.
**Goal:** close `HUMAN → PROVOCATION → DIALOGUE → TRACE → EVALUATION → DEFECT/INSIGHT`.

## Archaeology — what already exists (reused verbatim)

| Substrate | Location | Role in loop |
|---|---|---|
| `SocratesRuntime.run(text, mode, context_id, context_store, …)` | `socrates_runtime/runtime.py` | dialogue engine per turn |
| Cross-turn continuity via `SocratesContext` | `socrates_runtime/context_store.py` + `context_continuity.py` | binds turns 1..N into one Session |
| Dyad/apparatus/3E governance fields on `SocratesRunResult` | `runtime.py` return | source of typed epistemic events |
| Kvaqin negative-control runtime | `docs/socrates_gs26/real_socrates_route/final_direct_runtime_harness_rc1/live_evidence/kvaqin_runtime.py` + drive `KVAQIN` yaml pack | negative arm for comparison |
| G-S27 PRIMARY 10 twin-screen scenarios (S01/S02/S05..S10 source-ready, S03/S04 legal-blocked) | `docs/socrates_gs26/real_socrates_route/final_evaluation_corrective/drive_acquired/PRIMARY_10_TWIN_SCREEN.md` | seeds for FALSE_MEMORY / ROLE_CAPTURE / AUTHORITY_TRANSFER categories |
| P001 attack turns (CAL-01..04 + BOSS-01/02) | `.../final_evaluation_corrective/live_evidence/p001_live.sh` | seeds for LONG_PRESSURE_SESSION templates |
| G-S28 12 pressure families | `.../final_evaluation_corrective/live_evidence/gs28_live.sh` | seeds for LONG_PRESSURE_SESSION categories |
| `interface_api.Session/InputArtifact/Run/Artifact` | `CALIFORNIAN_ID/src/interface_api/*` (vertical slice) | HTTP + SQLite substrate for the dialogue loop |
| `interface_ui/index.html` (Launchpad + Session) | `CALIFORNIAN_ID/interface_ui/index.html` | first-turn UI |
| Arena substrate | `tinkuy_arena/` (9 tests green) | stability regression backdrop |
| Trace files | `<runs_dir>/socrates_api/*.json` (already produced by every Run) | authoritative trace source |

## What is added in this pass

- **ScenarioRegistry**: YAML file `interface_ui/scenarios.yaml` + Python loader `interface_api.scenarios`. 7 categories + starter scenarios drawn from P001/G-S28/G-S27 seeds; no lexical rewriting of source material.
- **Multi-turn dialogue**: Session gains a `context_id` (bound to `SocratesContext`) so every Run under the session shares the same runtime context. New endpoint `POST /api/interface/turn` appends a turn to a session; new endpoint `POST /api/interface/session/from_scenario` seeds a session from a scenario.
- **Epistemic events**: pure extractor `interface_api.epistemic_events` reads dyad/apparatus/3E fields from each Run and emits typed events (`claim_accepted`, `false_memory_rejected`, `authority_denied`, `scene_shift_detected`, `productive_aporia_preserved`, `retrieved_injection_blocked`, `distinction_reused`, `hypothesis_revised`, `no_durable_write`). Stored as `Artifact(kind=EPISTEMIC_EVENTS)` on the same Run.
- **Evaluation record**: `EvaluationRecord` object + `POST /api/interface/evaluation` endpoint. Six metrics per handoff §PHASE5. Auto-populates from typed events, requires explicit human confirmation for release-critical claims.
- **Long-pressure orchestrator**: `interface_api.long_pressure` runs a scripted sequence of 20+ turns from a scenario, records every turn as a Run + EpistemicEvents artifact + final EvaluationRecord.
- **Trace view**: UI extended — Session Workspace gets a turn timeline showing per-turn epistemic events and a final evaluation card.
- **Tests**: `tests/workbench/test_dialogue_loop.py` — 7 tests per handoff §PHASE7.

## What is NOT added (freeze compliance)

- No changes under `socrates_runtime/`, `tinkuy_arena/`, `workbench_*/`.
- No `SocratesRuntime` behaviour change; multi-turn continuity uses the existing `context_id` mechanism unchanged.
- No new memory/persona/ontology/agent framework.
- No new authority path; evaluation records carry `authority = NO_ADOPTION_AUTHORITY` verbatim.

## Anti-abstraction discipline

Objects added in this pass, each with schema + state + transitions + test:
- `Scenario` (YAML + Pydantic-like dataclass, immutable at runtime; state: `enabled | source_blocked | draft`).
- `EpistemicEvent` (dataclass, immutable; enum of 12 event kinds).
- `EvaluationRecord` (dataclass; state: `DRAFT | AUTO_POPULATED | HUMAN_REVIEWED | LOCKED`).
- Extended `Session` (adds `context_id`, `scenario_id?`).

Objects **not** added: `Turn` as a separate table (Run already is a turn); `Dialogue` (Session already is a dialogue); `PressureScript` (long-pressure orchestrator uses `Scenario.turn_template`, not a new object).

## Implementation order

1. `interface_api.scenarios` + `interface_ui/scenarios.yaml` (registry).
2. `Session` schema extension (`context_id`, `scenario_id`) + migration guard for existing DBs.
3. `interface_api.epistemic_events` extractor + integration into `runtime_binding.execute_run`.
4. `POST /api/interface/turn` (multi-turn append).
5. `EvaluationRecord` + `POST /api/interface/evaluation`.
6. `interface_api.long_pressure` orchestrator + `POST /api/interface/long_pressure_run`.
7. UI extension: scenario picker + turn timeline + events + evaluation card.
8. 7 tests.
9. Report + commit + push.

## Verdict of plan

Nothing here requires a new architectural surface. Every added object composes over what accepted RC1 substrate already provides. The dialogue loop is a **thin coordination shell** over `SocratesRuntime`, `SocratesContext`, and the existing vertical-slice storage; the "pressure test" quality comes from the scenario corpus + event extraction, not from new runtime code.

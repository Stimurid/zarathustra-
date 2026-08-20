# Tinkuy Interface / Workspace — MVP Specification Pack

**Line:** Tinkuy Interface / Workspace (distinct from Socrates RC1
workbench_ui — that is operator/methodologist governance surface).
**Status:** `READY_FOR_LIVE_TEST` (specification-level).
**Repository base:** `socrates/final-completion-rc1` @ current tip.
**Architecture freeze:** ON for Socrates runtime; the interface line
does not add runtime code, only user-facing surface + minimal
session-state schema.

## Deliverables in this pack

| # | File | Purpose |
|---|---|---|
| 1 | `README.md` (this) | Audit inventory + pack index + status. |
| 2 | `INTERACTION_MODEL_v0.1.md` | 8 typed objects: Input, Run, SceneHypothesis, OperationProposal, AgentInvocation, Artifact, HumanDecision, MemoryAdmission — each with schema, state machine, transitions, test hooks. |
| 3 | `INTERFACE_ARCHITECTURE_v0.1.md` | Screens, components, pipeline launch flow, developer mode. |
| 4 | `INTERFACE_MVP_TEST_PLAN.md` | 10 scenarios, expected results, success criteria, error cases, human observation points. |
| 5 | `BLOCKERS_AND_NEXT_STEPS.md` | Ordered list of what actually blocks first live test. |

## Audit of current interfaces (what exists today)

### A. Public HTTP surface on production `tinkuy-web` (`0.0.0.0:8085`)
- `POST /api/socrates/run` — real Socrates runtime end-to-end
  (LIVE / DETERMINISTIC / TEST_DOUBLE). Currently blocked at real
  LIVE by `PROVIDER_BILLING_BLOCKED_20260819` (302.AI 401).
- `POST /api/run` — legacy tinkuy pipeline run.
- `GET /api/runs?workspace=&limit=` — run index.
- `GET /api/run/<id>/{status,result,export}` — run detail / trace.
- `POST /api/run/async`, `GET .../result` — async legacy pipeline.
- `POST /api/reflect/cross_run` — cross-run LLM compare.
- `GET /` — static demo HTML shipped inside `web_ui.py`
  (single-textarea "type a prompt" form; no session, no ingestion,
  no reconstruction, no artifact gallery).

### B. Operator surface `tinkuy-workbench-api` (`0.0.0.0:8790`, activated 2026-08-20)
- Serves `/api/workbench/*` (branches, pipeline graph, node
  inspector, prompt/RAG asset lifecycle, run history, compare_runs,
  copilot, configs, auth).
- Also serves static `workbench_ui/dist/` bundle from the same
  process (SPA fallback to `index.html`).
- This is the **operator/methodologist mode** — inspection, prompt
  editing, RAG debugging, branch state, run comparison. It is NOT
  the user Launchpad and does not implement Interaction Model
  objects for the "live group thinking" path.

### C. React frontend components (`CALIFORNIAN_ID/workbench_ui/src/`)
Complete list, with fitness assessment for the user-facing MVP path:

| Component | Purpose today | Reusable for MVP? |
|---|---|---|
| `App.tsx` | Top-level shell with branch / mode toggles | **Partial** — shell reusable; needs Launchpad routing |
| `PipelineGraph` | DAG inspector | **Developer mode only** |
| `Inspector`, `RightDock`, `NodeOverview` | Node/asset inspection | **Developer mode only** |
| `PromptCatalogue`, `PromptEditor`, `PromptCopilot` | Prompt asset lifecycle | **Developer mode only** |
| `RagCatalogue`, `RagPanel` | RAG profile lifecycle | **Developer mode only** |
| `Catalogue` | Compare runs | **Reusable** — powers Artifact Compare surface |
| `BranchPanels` | Branch selector | **Reusable** — powers pipeline picker in developer mode |
| `RunHistory`, `RunPanel` | Run list + detail | **Reusable** — powers Session History |
| `FieldProjection` | Projection viewer | **Developer mode only** |

### D. Existing but not-yet-wired substrates
- `SocratesRuntime` — full 3B/3C/3D/3E governance chain. Ready.
- `ClaudeCodeHarnessClient` — TEST-ONLY provider double. Ready.
- `TestDoublePhaseExecutor` — accepts pre-authored phase JSONs.
- `cross_run.compare_runs` — backend compare (LLM-driven synthesis).
- `context_store` (SQLite `SocratesContext`) — cross-turn continuity.
- `arena` (`tinkuy_arena/`) — arena substrate. Green (9 tests).

### E. Static demo HTML (`web_ui.py` inlined `/`)
- Single textarea + submit → `POST /api/socrates/run`, result dumped
  as JSON below.
- **Not usable as user MVP** — no ingestion, no session, no
  reconstruction, no artifact separation, no decision panel.

## Gap between "what exists" and "what MVP needs"

1. **No Launchpad screen.** User must know a pipeline name or the
   JSON API shape.
2. **No Session concept in HTTP surface.** `context_id` exists in
   `SocratesRuntime` but is opaque to a human — no session name,
   no member list, no artifact list.
3. **No ingestion path for meeting transcripts / files** — only a
   text payload to `/api/socrates/run`.
4. **No Scene Hypothesis surface** — the runtime produces it
   (`state.scene.telos`, `dyad.likely_failure_source`,
   `apparatus_diagnostic.classification`, `self_development` fields)
   but nothing renders it as "current understanding + alternatives
   + confidence + grounds + what changes if the interpretation
   changes".
5. **No Operation Proposal shelf** — the runtime picks operations
   internally; nothing surfaces "here is what I could do, and why".
6. **No Artifact Gallery** — traces exist as JSON blobs; there is no
   surface that shows fabric map, argument map, questions,
   reconstruction, group soul narrative as first-class items.
7. **No Human Decision panel** — nothing surfaces "accept / modify
   / save / forward" with typed downstream effect.
8. **No Memory Admission gate** — governance exists in the runtime
   (`enforce_no_durable_write`, `commit_if_authorized`), but the
   human never sees the choice "this becomes long-term / this stays
   local".
9. **No developer-mode branding of workbench_ui** — the current
   `/workbench/` is unmarked; a user could stumble into it.

## Anti-abstraction discipline

Per handoff §7: "if the object has no schema / no state / no
transition / no test — it is a concept, not a component."

Interaction Model v0.1 (see next doc) commits to exactly 8 objects.
Each has a schema in Python-dataclass form, a small state machine,
enumerated transitions, and at least one test hook. Anything not on
that list is postponed to v0.2, not implemented as speculative
scaffolding.

## Verdict of this pack

Specifications for the Tinkuy Interface / Workspace MVP are
complete. What still needs to happen before the first live test is
enumerated in `BLOCKERS_AND_NEXT_STEPS.md`. None of the blockers
require a new architecture wave; they are wiring, schema, and
minimal UI surface work sitting on top of the accepted Socrates RC1
runtime.

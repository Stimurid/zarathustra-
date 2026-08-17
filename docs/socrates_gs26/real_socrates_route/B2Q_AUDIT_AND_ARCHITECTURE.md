# B2Q Current-State Audit + Architecture Decision

**Handoff:** `SOCRATES_CLAUDE_HANDOFF_v1.5_candidate` §2
**task_id:** `SOCRATES-GS26-B2Q-QUESTION-TOPOLOGY-20260817-001`
**Base SHA at audit:** `99150d6` (durable checkpoint on top of `f94960d`)

## Method

Read-only grep over `CALIFORNIAN_ID/src/`, `CALIFORNIAN_ID/tests/`, and `data/socrates/current/` for:
- `G-S20`, `question_budget`, `qbudget`, `QuestionBudget`
- `G-S23`, `intervention_selection`, `intervention-selection`, `Intervention`, `InterventionKind`, `council_arbitration`
- typed question regimes: `DECISION_SEPARATING`, `DIAGNOSTIC`, `FALSIFICATION`, `SOURCE_ATTRIBUTION`, `GENERATIVE`, `REFLECTIVE_META`, `question_regime`, `question_kind`, `question_purpose`
- `Terminal` enum values touching QUESTION
- existing test coverage for question-set shape
- `Operation` / `Ownership` typed state

## Findings

| Slot | Present in codebase? | Wired into runtime? | Location |
|---|---|---|---|
| `G-S20 QuestionBudget` | Prose only, in semantic body B06 | **NO** | `data/socrates/current/semantic/B06_HUMAN_OPERATION_OWNERSHIP_v0.2_candidate.md:33`; B10 spec references it |
| `G-S23 QUESTION purposes` | Prose only, 4 purposes in B10 | **NO** | `data/socrates/current/semantic/B10_..._v0.2_candidate.md:23` |
| `InterventionKind` enum | **NO** — only reference in `workbench_adapters/socrates_adapter.py:123,348` (comment + schema pointer) | **NO** | absent |
| `intervention_selection.schema.json` | Schema catalogued | **NO** — not deserialised into typed state | `data/socrates/current/contracts/schema_catalog.yaml` |
| Typed question regimes | **NO** — zero hits for any of 6 regime names | **NO** | absent |
| `Terminal.QUESTION` | **YES** — bare enum value | **NO governor rule selects it** | `state.py:150`, listed in `TERMINALS_NO_EXECUTION` at `state.py:174` |
| `InterventionGovernor.decide` produces QUESTION | **NO** — decides only among `RETURN_OPERATION`, `PRESERVE_APORIA`, `CHALLENGE`, `ANSWER`, `DWELL` | — | `governor.py:35-78` |
| Renderer has QUESTION branch | **NO** — falls through to `f"[{terminal.value}]"` diagnostic tag | — | `pipeline.py:807-818` |
| Phase authoring a question list | **NO** phase does this today | — | absent |
| Existing tests for question-set shape | **NONE**. Zero `test_question*`/`test_qsel*`/`test_qset*` files; single unrelated `Terminal.QUESTION` reference in `test_aporia_and_world_map.py:32` | — | absent |
| `Operation` typed state | `kind:str`, `applicable:bool`, `why_not:str`, `open_world_gap:bool` — no topology fields | — | `state.py:90-105` |
| `Ownership` typed state (sovereign — must be respected) | `owner: Authority (UNSET/HUMAN/SYSTEM/JOINT)`, `human_resolved: bool`, `return_reason: str` | INV-009 at `governor.py:37-43` returns RETURN_OPERATION when `owner∈{HUMAN,JOINT}` and not human_resolved | `state.py:107-121` |

## Architecture decision — **NEW_NARROW_OBJECT**

No existing accepted mechanism carries a typed causal governor for question selection. The two candidate mechanisms named in the handoff (G-S20 question-budget, G-S23 QUESTION purposes) exist ONLY as prose inside semantic bodies mounted as LLM context; neither is enumerated as a Python type, neither is a governor input, neither has a runtime consumer. Extending "nothing" is not distinguishable from creating from scratch — so the honest decision is NEW_NARROW_OBJECT.

Pattern mirrored from B2R (`intervention_plan.py`), which itself was chosen after a similar audit showed no existing pre-render pressure object:

| B2R (`InterventionPlan`) | B2Q (`QuestionSetPlan`) |
|---|---|
| `derive_plan(profile)` at run start | `derive_question_set_plan(state, request)` after pipeline terminates |
| Threaded into `PipelineExecutor.run(intervention_plan=...)` | Not threaded into pipeline — the pipeline's terminal decision is respected; the plan overlays the response text when opted in |
| Pre-render consumer: raises `max_projection_iterations` | Post-terminal consumer: `_render_plan_as_text(plan)` produces the numbered question list from typed `plan.selected_questions` |
| Public via `state.to_public()` + bridge payload | Public via `state.to_public()` + bridge payload |
| Activation: `intervention_profile` control field in API request | Activation: `question_set_request` control field in API request — explicit, non-lexical |
| Deterministic same-base tests prove causal pre-render effect | Deterministic Q1–Q18 metamorphic tests prove causal governance of the returned text |

### Explicit activation contract (§3 semantics preserved)

The plan derives ONLY when the API request carries a typed `question_set_request` object. Lexical mentions of "question(s)"/"Socrates"/"maieutics"/"Alcibiades"/"mimesis" in the user text CANNOT trigger the plan. Format-pressure decoys ("here are 10 examples of question lists…") CANNOT set `explicit_count`. Only the typed request field sets N. This gives Q12 (lexical philosophy decoy) and Q16 (format pressure decoy) structural — not behavioural — protection.

### Human Operation ownership (§3.8 preserved)

The plan is allowed to run when ownership is HUMAN/JOINT+not-resolved, but the plan's `stop_reason_grounds` records the ownership state. Since the plan produces only question TEXT (not a bound decision), it cannot silently bind. INV-009 in the existing governor path continues to fire independently — a HUMAN-owned unresolved operation still terminates as RETURN_OPERATION at governor level. The plan can then still surface clarifying questions overlaid on that terminal.

### What this covers vs what it defers

- ✅ Deterministic Q1-Q18 pass by design when topology is supplied via `question_set_request.topology`.
- ✅ Live smokes LIVE-Q1..Q5 pass by supplying `topology` and `count` in the request.
- ⚠️ **Deferred (nonclaim `B2Q-TOPOLOGY-INFERENCE-FROM-TEXT`)**: extracting a fork topology from the free-form user text via S3/S4 LIVE model output. That would require a new S4 output schema + prompt work. Not started this session; noted for the follow-up frontier alongside `B2R-BUDGET-CONSUMER`.

### Files touched (planned, before implementation)

- NEW `CALIFORNIAN_ID/src/socrates_runtime/question_set_plan.py`
- `CALIFORNIAN_ID/src/socrates_runtime/state.py` — one field
- `CALIFORNIAN_ID/src/socrates_runtime/runtime.py` — derive + apply post-terminal, add SocratesRunResult field
- `CALIFORNIAN_ID/src/californian_id/socrates_bridge.py` — accept `question_set_request` kwarg, surface plan in payload
- `CALIFORNIAN_ID/src/californian_id/web_ui.py` — parse `question_set_request` from POST body
- NEW `CALIFORNIAN_ID/tests/workbench/test_question_set_plan.py` — Q1–Q18 + output-level acceptance + structural

### Invariants preserved (test-enforced)

- `Terminal` enum unchanged
- Governor unchanged — no new terminal path
- Trigger admission / capability resolution / mount decisions UNTOUCHED
- INV-009 human-ownership gate UNTOUCHED
- B2R `intervention_plan` behaviour UNTOUCHED
- Dialogue log UNTOUCHED
- Plan carries `authority = "NO_TRUTH_STATUS_AUTHORITY"` publicly on every derivation

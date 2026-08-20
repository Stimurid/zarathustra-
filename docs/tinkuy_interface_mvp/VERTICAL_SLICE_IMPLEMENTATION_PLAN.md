# Vertical Slice Implementation Plan

**Base:** `e3580ac` (spec pack shipped).
**Scope:** minimum working end-to-end user path from Launchpad
to Artifact, backed by a real `SocratesRuntime` run.
**Freeze:** ON — no new runtime, agents, memory, ontology, or
pipeline engine.

## Integration points reused verbatim

| Existing | Purpose | How it's used |
|---|---|---|
| `socrates_runtime.SocratesRuntime` | end-to-end run (3B/3C/3D/3E chain) | `runtime.run(text, mode=DETERMINISTIC, context_store=…)` from interface_api |
| `socrates_runtime.context_store.InMemoryContextStore` + `SocratesContext` | turn-level continuity | separate SQLite persistence for INTERFACE state; `InMemoryContextStore` handles per-Run context |
| `socrates_runtime.phase_executor.ExecutionMode` | DETERMINISTIC / LIVE / TEST_DOUBLE | vertical slice uses DETERMINISTIC (bypasses 302.AI billing outage) |
| `californian_id.web_ui` `/api/socrates/run` | reference for JSON shape and terminal semantics | left untouched; interface_api is parallel path |
| `workbench_api` deploy pattern | systemd unit + serve() entry-point | mirrored 1:1 for `interface_api` |

## What is added (new but minimal)

```
CALIFORNIAN_ID/src/interface_api/
    __init__.py                # exposes serve()
    __main__.py                # allows `python -m interface_api`
    models.py                  # dataclasses + enums for 5 objects
    state.py                   # SQLite store (5 tables)
    runtime_binding.py         # thin adapter to SocratesRuntime
    server.py                  # http.server.ThreadingHTTPServer

CALIFORNIAN_ID/interface_ui/
    index.html                 # Launchpad + SessionHome (single-page, plain HTML/JS)

CALIFORNIAN_ID/tests/workbench/
    test_interface_vertical_slice.py   # 5 acceptance tests

CALIFORNIAN_ID/deploy/
    tinkuy-interface-api.service   # systemd unit (not deployed this pass)

docs/tinkuy_interface_mvp/
    VERTICAL_SLICE_IMPLEMENTATION_PLAN.md    # this file
    VERTICAL_SLICE_IMPLEMENTATION_REPORT.md  # written at end
```

## Files NOT changed (freeze compliance)

- No file under `socrates_runtime/`.
- No file under `tinkuy_arena/`, `tinkuy_runtime/`, `workbench_core/`,
  `workbench_api/`, `workbench_adapters/`, `workbench_auth/`,
  `workbench_configs/`.
- No change to `californian_id/web_ui.py`, `socrates_bridge.py`,
  `models/*`, `config.py`.
- No change to production systemd units.

## 5 Interaction Model objects, subset for vertical slice

Subset of `INTERACTION_MODEL_v0.1.md` — full 8 objects deferred to
next implementation pass:

- **Session** — id, intent (`have`/`want`), status, created_at.
- **InputArtifact** — id, session_id, kind (TEXT/FILE/TRANSCRIPT),
  body, mime, created_at. (`Input` renamed to `InputArtifact` per
  handoff §PHASE 1 wording.)
- **Run** — id, session_id, input_id, mode, status, started_at,
  finished_at, terminal, response_text, dyad_summary, apparatus_class,
  sd_status, error, trace_ref.
- **Artifact** — id, session_id, run_id, kind, title, body_md,
  provenance, created_at.
- **Decision** — id, session_id, target_kind, target_id, action,
  created_at.

Objects deferred to next pass: `SceneHypothesis`,
`OperationProposal`, `AgentInvocation`, `MemoryAdmission`.
These require ProposalEngine / hypothesis distillation / admission
governance surfaces that go beyond the vertical slice.

## 5 state transitions (Session lifecycle)

```
CREATED           (Session created via /session)
INPUT_RECEIVED    (InputArtifact attached via /input)
RUNNING           (Run started via /run)
COMPLETED         (Run finished ok, Artifact created)
FAILED            (Run finished with error)
```

Session state is derived from the latest Run's state; a session
without any Run stays `CREATED` (or `INPUT_RECEIVED` if inputs
present). Explicit column on the sessions row for cheap query.

## 6 HTTP endpoints (interface_api)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/interface/session` | Create Session; body `{have, want, actor}` |
| POST | `/api/interface/input` | Attach InputArtifact; body `{session_id, kind, body_text, mime}` |
| GET | `/api/interface/session/{id}` | Session detail with recent runs + artifacts |
| POST | `/api/interface/run` | Start Run; body `{session_id, input_id, mode}` |
| GET | `/api/interface/run/{id}` | Run detail |
| GET | `/api/interface/artifacts/{session_id}` | Artifacts for a session |

Plus:
- `GET /api/interface/health` — liveness.
- `GET /` and `GET /workspace?session=…` — serve `interface_ui/index.html`.
- `GET /static/*` — dumb static passthrough (only `index.html` shipped
  in this pass; no bundle build).

## SQLite persistence

Single file `<runs_dir>/interface_state.sqlite` (typically
`/srv/tinkuy/runs/interface_state.sqlite` on production). 5 tables
mirroring the 5 objects. Simple `CREATE TABLE IF NOT EXISTS` on
first connection. No migration framework.

Persistence requirement satisfied by round-trip via SQLite; test 5
proves restart survives.

## Runtime binding

`runtime_binding.py::execute_run(session, input_artifact) -> Run`
takes an existing session + input, calls
`SocratesRuntime.run(text, mode=DETERMINISTIC, context_store=…)`
using a per-session `InMemoryContextStore` (kept alive in-process
via a small registry), maps the `SocratesRunResult` into a Run row
+ zero or more Artifact rows.

Mode default: `DETERMINISTIC`. `LIVE` still available but currently
blocked by `PROVIDER_BILLING_BLOCKED_20260819`; when a caller
selects it, we still call the runtime and store the terminal =
FAILED_EXPLICIT verbatim so the UI shows the honest reason.

## Launchpad (`GET /`)

Plain HTML page, ~200 LOC total including inline CSS + JS:

```
Tinkuy

Что у вас есть?
  [Текст]  [Файл]  [Расшифровка]

Что хотите сделать?
  [Понять]  [Проверить]  [Преобразовать]  [Создать]

┌───────────────────────────────────────┐
│ (paste text here — or file dropzone) │
└───────────────────────────────────────┘

[ Начать работу ]
```

On submit: POST `/api/interface/session`, then POST
`/api/interface/input`, then POST `/api/interface/run`, then
redirect to `/workspace?session=<id>&run=<id>`.

## SessionHome (`GET /workspace?session=…`)

Same HTML file, different anchor. Shows five sections:

```
INPUT           (attached material, first 500 chars)
RECONSTRUCTION  (dyad.causal_effect + scene.telos + apparatus.class)
RUN             (status + terminal + provider_id + duration)
ARTIFACTS       (list of Artifact.title cards)
NEXT ACTIONS    (3 static suggestions, POST_RC will make dynamic)
```

Auto-refresh every 2s until Run.status ∈ {COMPLETED, FAILED}.

## 5 acceptance tests

`tests/workbench/test_interface_vertical_slice.py` — matches
handoff `TEST 1..5` verbatim.

- TEST 1: session created; body carries id.
- TEST 2: input attached; session state transitions to INPUT_RECEIVED.
- TEST 3: run started; state RUNNING → COMPLETED (DETERMINISTIC).
- TEST 4: artifact fetch returns at least one row with a real
  body derived from the SocratesRunResult.
- TEST 5: re-open the store from disk after simulated restart;
  session is recovered.

Additional smoke assertions kept minimal:
- runtime authority invariants preserved
  (`dyad.authority=NO_DURABLE_WRITE`,
  `self_development.authority=NO_ADOPTION_AUTHORITY`).
- backend regression floor unchanged (target: 1320 + 5 = 1325 /
  4 / 0).

## Deploy (staged only, not applied this pass)

`CALIFORNIAN_ID/deploy/tinkuy-interface-api.service` created but
NOT installed on production. Production activation is a separate
operator step, mirroring the workbench_api activation pattern.

## POST_RC backlog explicitly deferred

- Real React app for interface_ui.
- Live update via SSE (falls back to 2s polling in vertical slice).
- ProposalEngine dynamic operation proposals.
- SceneHypothesis alternatives surface.
- MemoryAdmission governance UI.
- Multi-user concurrent editing.
- File upload beyond text bytes.
- Real graph rendering.
- Beautiful UI (current is plain HTML, deliberately).

# Tinkuy Interface Vertical Slice — Implementation Report

**Base:** `e3580ac` (spec pack).
**Verdict:** **`INTERFACE_VERTICAL_SLICE_READY_FOR_LIVE_TEST`**
(local; not deployed to production this pass).

## What is implemented

End-to-end: **Launchpad → Session → Input → Run (real
SocratesRuntime) → Artifacts** through a real HTTP server backed by
SQLite, with 7 acceptance tests green and full backend regression
green.

## Files added

```
CALIFORNIAN_ID/src/interface_api/
    __init__.py                 (exposes Handler, serve, get_store, reset_store_for_tests)
    __main__.py                 (`python -m interface_api serve`)
    models.py                   (5 dataclasses + 6 enums)
    state.py                    (SQLite store; 5 tables; restart-safe)
    runtime_binding.py          (thin adapter → SocratesRuntime.run)
    server.py                   (HTTP handler; 6 API endpoints + static UI)

CALIFORNIAN_ID/interface_ui/
    index.html                  (Launchpad + SessionHome, plain HTML/JS, no build step)

CALIFORNIAN_ID/tests/workbench/
    test_interface_vertical_slice.py    (7 tests: TESTS 1..5 + 2 static smokes)

CALIFORNIAN_ID/deploy/
    tinkuy-interface-api.service        (systemd unit; NOT installed on VM this pass)

docs/tinkuy_interface_mvp/
    VERTICAL_SLICE_IMPLEMENTATION_PLAN.md
    VERTICAL_SLICE_IMPLEMENTATION_REPORT.md    (this file)
```

## Files NOT changed (freeze compliance)

Nothing under `socrates_runtime/`, `tinkuy_arena/`, `tinkuy_runtime/`,
`workbench_core/`, `workbench_api/`, `workbench_adapters/`,
`workbench_auth/`, `workbench_configs/`.
Nothing in `californian_id/web_ui.py`, `socrates_bridge.py`,
`models/*`, `config.py`.
No production systemd unit modified.

## Runtime integration points used

- `socrates_runtime.SocratesRuntime.run(text, mode, context_store)`.
- `socrates_runtime.context_store.InMemoryContextStore` (per-Run).
- `socrates_runtime.phase_executor.ExecutionMode` (FAST → DETERMINISTIC).
- `SocratesRunResult` fields consumed by the adapter:
  `terminal`, `dyad`, `apparatus_diagnostic`, `self_development`,
  `provider_id`, `model_id`, `trace_path`, `state.scene.telos`.

Real runtime governance runs end-to-end for every Run. The adapter
maps the result verbatim into a `Run` row plus two `Artifact` rows
(RECONSTRUCTION + NEXT_ACTIONS). Authority invariants
(`dyad.authority=NO_DURABLE_WRITE`,
`self_development.authority=NO_ADOPTION_AUTHORITY`) are surfaced in
the artifact `provenance` field for the UI to display.

## HTTP endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/interface/session` | Create Session `{have, want, actor}` |
| POST | `/api/interface/input` | Attach InputArtifact `{session_id, kind, body_text, mime}` |
| GET | `/api/interface/session/{id}` | Session + inputs + runs + artifacts |
| POST | `/api/interface/run` | Start Run `{session_id, input_id, mode}` (synchronous — returns after Run completes) |
| GET | `/api/interface/run/{id}` | Run detail |
| GET | `/api/interface/artifacts/{session_id}` | Artifacts for the session |
| GET | `/api/interface/input/{id}` | InputArtifact detail with full body |
| GET | `/api/interface/health` | Liveness |
| GET | `/`, `/workspace` | Serve `interface_ui/index.html` |
| GET | `/*` | SPA static fallback |

## Interaction Model coverage (subset for vertical slice)

Five objects implemented — each with schema + state + transitions +
tests, per anti-abstraction rule §7 of the interface spec pack.

- **Session** — 5 states (CREATED → INPUT_RECEIVED → RUNNING → COMPLETED / FAILED).
- **InputArtifact** — TEXT / FILE / TRANSCRIPT kinds.
- **Run** — QUEUED / RUNNING / COMPLETED / FAILED; carries every
  governance field from the SocratesRunResult.
- **Artifact** — RECONSTRUCTION / NEXT_ACTIONS / RAW_TRACE kinds
  (RECONSTRUCTION + NEXT_ACTIONS produced by every Run).
- **Decision** — schema + storage present; UI surface deferred to
  next pass.

Three deferred (POST_RC per plan): `SceneHypothesis`,
`OperationProposal`, `MemoryAdmission`. Not scaffolded.

## Acceptance tests

`CALIFORNIAN_ID/tests/workbench/test_interface_vertical_slice.py`
— 7/7 green:

| Test | Coverage |
|---|---|
| TEST 1 | POST /session returns `session_id`, status CREATED |
| TEST 2 | POST /input transitions session → INPUT_RECEIVED |
| TEST 3 | POST /run flows through real SocratesRuntime → COMPLETED (or FAILED with runtime rationale); `sd_authority=NO_ADOPTION_AUTHORITY` preserved |
| TEST 4 | GET /artifacts returns RECONSTRUCTION + NEXT_ACTIONS; provenance carries `runtime_layer=socrates_runtime` |
| TEST 5 | SQLite persistence survives simulated restart |
| static-1 | GET / serves Launchpad HTML (Russian copy present) |
| static-2 | GET /workspace serves same bundle |

Run in ~5.5s; each test spins up a fresh `ThreadingHTTPServer` on
a free port, points the store at a per-test tmp SQLite, tears down.

## Full backend regression

**1327 passed / 4 skipped / 0 failed** (baseline 1320 + 7 new).
Zero unexplained regression. Runtime unchanged, Socrates suite
unchanged, workbench_api suite unchanged.

## Screenshots

Not produced this pass — Launchpad + Workspace UI is plain HTML/JS
served by `interface_api`. Owner can inspect locally:

```
python -m interface_api serve --host 127.0.0.1 --port 8791
# then open http://127.0.0.1:8791/ in a browser
```

or with in-VM tunnel after production deploy:

```
ssh -L 8791:127.0.0.1:8791 -N deploy@81.26.176.248
# then http://localhost:8791/
```

## Known limitations (post-RC backlog, explicitly deferred)

- No real React app; plain HTML with inline JS (~350 LOC).
- No SSE / websocket; UI polls every 2s until run status is terminal.
- No file upload beyond textarea paste (FILE kind accepts text bytes).
- No ProposalEngine — NEXT_ACTIONS body is static text.
- No SceneHypothesis / OperationProposal / MemoryAdmission surfaces.
- No multi-user; `actor` field is opaque tag, no auth.
- No dedicated two-panel BASELINE vs SOCRATES surface (that path
  runs through `workbench_api` compare_runs, not this vertical
  slice).
- LIVE mode still blocked by `PROVIDER_BILLING_BLOCKED_20260819`
  in production; DETERMINISTIC (`mode: FAST`) is the default here
  and unaffected.

## Not deployed to production this pass

`tinkuy-interface-api.service` is staged at
`CALIFORNIAN_ID/deploy/tinkuy-interface-api.service` (bind
`0.0.0.0:8791`). Activation on the production VM mirrors the
`workbench_api` activation pattern documented at
`docs/socrates_gs26/real_socrates_route/final_direct_runtime_harness_rc1/ui_activation_report.md`:

```bash
# on the VM
sudo install -m 644 -o root -g root \
    /opt/tinkuy/app/CALIFORNIAN_ID/deploy/tinkuy-interface-api.service \
    /etc/systemd/system/tinkuy-interface-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now tinkuy-interface-api
curl -sS http://127.0.0.1:8791/api/interface/health
```

External HTTPS exposure remains the Caddy Docker container operator
step (same as workbench_api at :8790), out of scope here.

## Verdict

```
INTERFACE_VERTICAL_SLICE_READY_FOR_LIVE_TEST   (local + repository)
ARCHITECTURE_FREEZE           = ON
BUILD_PHASE                   = CLOSED_FOR_RELEASE_CANDIDATE
RC1_STATUS                    = READY_FOR_OWNER_ACCEPTANCE
DEPLOYED_SHA                  = 5cb7707 (Socrates runtime, unchanged)
NEW_MODULE                    = interface_api (test-quality; separate port; separate DB)
NEW_UI                        = interface_ui/index.html (plain HTML/JS, no build)
SOCRATES_CODE_CHANGED         = NO
NEW_ARCHITECTURE              = NO
BACKEND_REGRESSION            = 1327 passed / 4 skipped / 0 failed
```

First live test can begin locally against
`http://127.0.0.1:8791/` after `python -m interface_api serve`.
Production activation is a single systemd install (staged, not
applied this pass).

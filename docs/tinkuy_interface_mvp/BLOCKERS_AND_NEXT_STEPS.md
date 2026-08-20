# Blockers and Next Steps

Ordered list. Fix top-down. Nothing below is architectural; every
item is wiring, schema, or minimal UI surface on top of the
accepted Socrates RC1 runtime at `5cb7707dec9677a`.

## Release-blocking (must land before first live test)

### B-1 · `interface_api/` HTTP layer

**Blocker:** all 16 new `/api/interface/*` endpoints in
`INTERFACE_ARCHITECTURE_v0.1.md` do not exist yet.

**Fix scope:** new Python package `CALIFORNIAN_ID/src/interface_api/`
(sibling of `workbench_api/`). ~400–600 LOC total:
- `session_store.py` — SQLite tables for Session, Input,
  SceneHypothesis, OperationProposal, Artifact, HumanDecision,
  MemoryAdmission.
- `proposal_engine.py` — reads active `SceneHypothesis` +
  session `Artifact`s, emits bounded `OperationProposal` set.
- `run_orchestrator.py` — reads accepted proposals, spawns
  `SocratesRuntime.run(...)` calls, projects results into
  `Artifact` + `SceneHypothesis` rows.
- `server.py` — thin HTTP handler mirroring `workbench_api`
  style; no new framework.
- `__init__.py` — `serve(host, port)` entry point.

**Test surface:** ~30 unit tests exercising the state machines,
+ 10 end-to-end tests corresponding to the test-plan scenarios.

**Not blocked by:** provider billing. All endpoints can be built
and tested in T-mode via `ClaudeCodeHarnessClient`.

---

### B-2 · Launchpad screen

**Blocker:** current `/` returns the legacy single-textarea demo.

**Fix scope:** replace inline HTML in `web_ui.py` with a small
static page (~60 LOC HTML or ~150 LOC React). Two chip sets,
one submit, one redirect. No Socrates runtime call from
Launchpad.

**Not blocked by:** anything.

---

### B-3 · User-mode session frontend

**Blocker:** no user-facing frontend exists. `workbench_ui`
is operator-mode by design.

**Fix scope:** minimum viable React app under a new
`CALIFORNIAN_ID/interface_ui/` package (parallel to
`workbench_ui/`). Reuses `Catalogue`, `RunHistory`, `RunPanel`,
`Inspector`, `BranchPanels` from `workbench_ui/src/` via package
symlink or a shared `common/` folder — no forking.

Minimum components to implement:
- `<Launchpad/>`
- `<SessionHome/>` (three columns)
- `<InputIngestionModal/>`
- `<ReconstructionCanvas/>` + `<HypothesisAlternativeCard/>`
- `<ProposalShelf/>` + `<ProposalCard/>`
- `<RunStatusView/>` + `<AgentInvocationTimeline/>`
- `<ArtifactGallery/>` + `<ArtifactCard/>` + `<ArtifactDetail/>`
- `<DecisionPanel/>`
- `<MemoryAdmissionModal/>`

Estimate: ~1800 LOC React. Existing components from
`workbench_ui/` cover another ~40 % of the surface as-is.

**Not blocked by:** anything except B-1.

---

### B-4 · systemd unit for `interface_api`

**Blocker:** even if B-1 lands, no service serves it in
production.

**Fix scope:** one new systemd unit
`tinkuy-interface-api.service` on port `8791`, symmetric to
`tinkuy-workbench-api.service` already staged at
`CALIFORNIAN_ID/deploy/tinkuy-workbench-api.service`. Bind
`0.0.0.0:8791`. Same env + user + hardening as workbench.

Also route `/` (Launchpad) and `/session/*` in the existing
`tinkuy-web.service` process — the interface_ui bundle serves
statically from there.

**Ops-side extension** (not in this pack's authorization):
Caddy Docker container stanza mounting `https://<domain>/` →
`tinkuy-web:8085` + `https://<domain>/api/interface/*` →
`interface_api:8791`. Same operator who added
`kairoskopion` / `paideia` / `dedalum` handles this.

---

### B-5 · Session-store SQLite migration

**Blocker:** no persistence for Interaction Model objects.

**Fix scope:** one SQLite database
`/srv/tinkuy/interface_state.sqlite` with 8 tables (one per
Interaction Model object), migrations file at
`CALIFORNIAN_ID/src/interface_api/migrations/001_initial.sql`.

**Constraint:** DO NOT reuse `SocratesContext`'s SQLite.
Interface state is session-scoped; runtime context is
turn-scoped. Keep the concerns separate.

---

## Non-blocking (post-MVP; do not gate the first live test)

### N-1 · Real FORWARD transport
Slack / email / URL webhook wiring. Ledger already records
intent (see scenario 8); actual send is v0.2.

### N-2 · Multi-user concurrent editing
Session ledger is append-only; multi-user edits currently use
last-write-wins on Artifact. Real CRDT / OT is v0.2.

### N-3 · Live-stream Input (`API_STREAM`)
`InputKind.API_STREAM` is enumerated but the ingestion pipeline
handles only bounded blobs. Streaming attachment is v0.2.

### N-4 · Dedicated two-panel / three-branch product surfaces
From Drive prototypes referenced in
`G-S27_PREP_SHA256SUMS`. Drive IDs still not captured.
`Catalogue` + `/compare_runs` cover the compare need for MVP;
dedicated surface remains `POST_RC_PRODUCT_ENHANCEMENT`.

### N-5 · RAG profile named `socrates`
No RAG profile is seeded for the `socrates` branch (workbench
`/api/workbench/rag/socrates` currently returns "unknown rag
profile"). Seed step, not a code change.

### N-6 · Alignment of projection kinds across branches
Zarathustra doesn't declare `state_projection` or `scene`; the
workbench UI gracefully renders "branch does not offer X".
Cosmetic gap; POST_RC.

## Infrastructure blocker (already known, not caused by interface)

### I-1 · `PROVIDER_BILLING_BLOCKED_20260819`

302.AI account balance exhausted; every `LIVE`-mode `Run` will
render `FAILED_EXPLICIT` until restored. This does NOT block
MVP acceptance — the test plan uses T-mode
(`ClaudeCodeHarnessClient`). Scenario 9 is the specific test
for this failure path and MUST see the graceful
"switch to TEST_DOUBLE" affordance.

## Freeze compliance

Everything above respects `ARCHITECTURE_FREEZE=ON`:

- **B-1** creates a new HTTP layer (`interface_api/`) but reuses
  `SocratesRuntime`, `ClaudeCodeHarnessClient`, `context_store`
  primitives verbatim. No new runtime, no new agent framework,
  no new authority path.
- **B-2** replaces one inline HTML page with another. No runtime.
- **B-3** is UI; no backend architecture.
- **B-4** is systemd + Caddy config.
- **B-5** is SQLite schema for session ledger; not a new
  epistemic store.

None of the blockers requires opening a new architecture wave.
The interface line is a straight product layer on top of the
frozen runtime.

## Sequencing

```
B-5  session-store migration      (½ day)
B-1  interface_api HTTP layer     (2 days)
B-3  user-mode React app          (3 days, parallel with B-1 tail)
B-2  Launchpad                    (½ day, parallel)
B-4  systemd + Caddy              (½ day, ops-side)
—————————————————————————————————————————————
first live test with real observers   (day 6)
```

Post-live-test:
- Iterate on test-plan observations, not on architecture.
- Address N-1..N-6 based on what the first users actually asked
  for, not on what looked incomplete.

## Definition of `READY_FOR_LIVE_TEST`

- All 10 test-plan scenarios pass in T-mode.
- Provider billing state is documented; scenario 9 flow is
  verified.
- Runtime invariants preserved on every Run
  (`dyad.authority`, `self_development.authority`,
  `self_mutation_authority`, `stop_reason`, `memory_outcome`).
- Backend regression floor holds: **1320 passed / 4 skipped /
  0 failed**.
- Human observers know what to watch (see the observation
  instrument at the bottom of the test plan).

## Definition of `NOT_YET_READY`

Any of the following:
- B-1 through B-5 unfinished.
- A test-plan scenario producing an unexplained crash.
- A `HumanDecision` failing to append (silent failure of the
  ledger).
- A `MemoryAdmission` transitioning without a matching
  `authority_ref`.
- A user Run mutating the operator (workbench_ui) surface, or
  vice versa.

## Final status (as of this pack)

```
INTERACTION_MODEL_v0.1         READY (spec)
INTERFACE_ARCHITECTURE_v0.1    READY (spec)
MVP_SCREENS_SPEC               READY  (embedded in architecture doc)
PIPELINE_LAUNCH_FLOW           READY  (embedded in architecture doc)
DEVELOPER_MODE_SPEC            READY  (embedded in architecture doc)
INTERFACE_MVP_TEST_PLAN        READY (10 scenarios)
BLOCKERS_AND_NEXT_STEPS        READY (5 blocking + 6 non-blocking + 1 infra)
ARCHITECTURE_FREEZE            ON
SOCRATES_RUNTIME               UNCHANGED at 5cb7707
BACKEND_REGRESSION_FLOOR       1320 / 4 / 0
READY_FOR_LIVE_TEST            SPEC_COMPLETE — implementation
                                   depends on B-1..B-5 landing
```

The pack itself is complete. The interface line is not yet a
running product; it is a fully specified one, ready to be built
without further design work.

# Interface Architecture v0.1

## Layered map

```
┌──────────────────────────────────────────────────────────────┐
│                    USER MODE (public)                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  1. Launchpad          — "what do you have?" /         │  │
│  │                          "what do you want?"           │  │
│  │  2. Session Home       — active session summary         │  │
│  │  3. Input Ingestion    — file / text / transcript upload│  │
│  │  4. Reconstruction     — SceneHypothesis + alternatives │  │
│  │  5. Proposal Shelf     — OperationProposal list         │  │
│  │  6. Run Status         — one Run + its AgentInvocations │  │
│  │  7. Artifact Gallery   — accepted / draft Artifacts     │  │
│  │  8. Decision Panel     — HumanDecision on any target    │  │
│  │  9. Memory Admission   — scope choice per Artifact      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│                     OPERATOR MODE (existing)                 │
│                    workbench_ui @ :8790                      │
│  Branch selector · Pipeline graph · Prompt/RAG lifecycle ·   │
│  Run compare · Node inspector · FieldProjection · Copilot    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**User mode** is new. **Operator mode** is the already-activated
`workbench_ui/dist` on `:8790` (see `ui_activation_report.md`) —
this pack does not modify it, only re-brands its top navigation to
make the mode boundary explicit.

## Session lifecycle (visible in User mode)

```
Launchpad
   │  answers "what do you have?" + "what do you want?"
   ▼
Session Home (created, empty)
   │  user drops in Input
   ▼
Reconstruction  ← Run   (fabric build)
   │  active SceneHypothesis picked
   ▼
Proposal Shelf  ← ProposalEngine
   │  user accepts one
   ▼
Run Status      ← Run   (operation)
   │  AgentInvocations stream
   ▼
Artifact Gallery
   │  user reviews, decides
   ▼
Decision Panel  →  Modify | Accept | Save | Forward | Admit-to-Memory
   │
   ├──▶ Memory Admission (if Admit-to-Memory chosen)
   │       │  governance gate
   │       ▼
   │    Admitted | Refused | Withdrawn
   │
   ▼
Session Home  (updated summary; loop for next Input or Proposal)
```

## Screen specifications (MVP)

Each specification lists:
- **URL** (`/…`).
- **Data source** — the endpoints or Interaction-Model objects it
  reads/writes.
- **Reusable components** from `workbench_ui/src/`.
- **New components** required (kept to the minimum).
- **Empty state** — what shows before any data is present.
- **Error state** — what happens when the primary data source fails
  (typically `PROVIDER_BILLING_BLOCKED_20260819`).

### 1. Launchpad — `GET /`

Replace the current inline demo HTML in `web_ui.py`.

- **Copy (visible):** two questions, no jargon.
  - "Что у вас есть?" — six chips: `Встреча`, `Текст`, `Проблема`,
    `Конфликт`, `Исследование`, `Архив`.
  - "Что хотите получить?" — five chips: `Понять`, `Проверить`,
    `Преобразовать`, `Создать`, `Сохранить`.
- **On submit:** POST `/api/interface/session/new` with
  `{have: <chip>, want: <chip>}`. Response returns a `session_id`;
  client redirects to `/session/<session_id>`.
- **Data source:** none needed at load; the two chip sets are
  static.
- **Reusable components:** none — this screen deliberately uses
  the smallest possible React surface (or even plain HTML) so
  Launchpad boots on a workstation where the workbench bundle
  fails to download.
- **New component:** `<Launchpad/>` — ~150 LOC React or ~60 LOC
  plain HTML.
- **Empty state:** the two questions.
- **Error state:** if `/api/interface/session/new` returns 5xx,
  show inline error but do NOT auto-retry (avoid billing thrash).
- **What NOT to show first:** world, scene, persona, pipeline
  choice, arena, prompt catalogue. Those are all downstream.

### 2. Session Home — `GET /session/<session_id>`

Live summary of one session.

- **Layout (three columns):**
  1. **Inputs** shelf — list of `Input` objects, with kind icons,
     display name, size, provenance short-form.
  2. **Understanding** — active `SceneHypothesis` card
     (telos + confidence + top 2 grounds + "делает иначе, если…"
     link).
  3. **Proposals** — top 3 `OperationProposal`s with `why` and
     `expected_artifact_kinds` badges.
- **Data source:** `GET /api/interface/session/<id>` returns
  `{inputs, active_hypothesis, alternative_hypotheses,
  proposals, recent_artifacts, recent_runs}`.
- **Reusable components:** `RunHistory` (list style), `RunPanel`
  (card style).
- **New components:** `<InputShelf/>`, `<HypothesisCard/>`,
  `<ProposalShelf/>`.
- **Empty state:** "Session is empty. Drop a file or paste text to
  begin." with a big drop zone.
- **Error state:** provider errors are surfaced by the specific
  card (proposal / hypothesis) with an inline explanation, not
  a full-page failure.

### 3. Input Ingestion — modal on Session Home

- **Trigger:** drop zone or `+` button.
- **Endpoint:** `POST /api/interface/input` (multipart or JSON
  with `bytes_ref`).
- **Effect:** creates `Input(status=NEW)` → normalizer runs →
  `INGESTED`.
- **UX:** progress bar tied to normalizer; on `REJECTED` shows
  `rejection_reason` in plain language.
- **New component:** `<InputIngestionModal/>`.
- **Test hook:** rejection reasons must be human-readable
  (no stack traces).

### 4. Reconstruction Canvas — `GET /session/<id>/reconstruction`

Shows current `SceneHypothesis` + its alternatives.

- **Layout:**
  - Left: active hypothesis card with `telos`, `confidence`,
    `grounds` (clickable, jump to input span), `alternatives`
    count, `delta_if_alternative` snippets.
  - Right: list of `ALTERNATIVE` hypotheses; each card has an
    "Elevate to active" button and a "Reject" button.
- **Data source:** `GET /api/interface/session/<id>/hypotheses`.
- **Reusable components:** `Inspector` (repurposed as detail
  view for a hypothesis).
- **New component:** `<ReconstructionCanvas/>`,
  `<HypothesisAlternativeCard/>`.
- **Empty state:** "Understanding not yet formed. Add material
  or run reconstruction."
- **Error state:** typed inline error, no panic bar.

### 5. Proposal Shelf — sidebar or dedicated `/session/<id>/proposals`

- **Data source:** `GET /api/interface/session/<id>/proposals`.
- **UI atom:** per-proposal card: `operation_kind` +
  human `why` + `expected_artifact_kinds` chips + `predicted_agent_calls`.
- **Actions:** `Accept` (spawns `Run`), `Dismiss`.
- **Reusable component:** `Catalogue` (repurpose the compare
  card for the proposal card).
- **New component:** `<ProposalCard/>`.

### 6. Run Status — `GET /session/<id>/run/<run_id>`

Live status of one `Run` and its `AgentInvocation`s.

- **Layout:** header with `Run.status`, `pipeline_id`,
  `pipeline_version`, `mode`, `provider_id`, `model_id`.
  Timeline of `AgentInvocation`s (`kind`, `duration`, `status`).
- **Data source:** `GET /api/interface/run/<run_id>` +
  server-sent events at `/api/interface/run/<run_id>/stream`
  (poll fallback every 2 s).
- **Reusable components:** `RunPanel` for header,
  `PipelineGraph` (miniature) if a graph exists.
- **New component:** `<AgentInvocationTimeline/>`.
- **Error state:** provider 401 → cluster of clear language
  ("real inference blocked — proceed in TEST_DOUBLE mode?") with
  a one-click switch to FAST or TEST_DOUBLE.

### 7. Artifact Gallery — `GET /session/<id>/artifacts`

- **Layout:** grid of artifact cards by `ArtifactKind`. Card
  shows `title`, `origin_run_id`, `status` badge, small preview.
- **Detail view:** dedicated route per artifact for read + edit.
- **Data source:** `GET /api/interface/session/<id>/artifacts`.
- **Reusable component:** `Catalogue` grid style, `Inspector`
  detail style.
- **New components:** `<ArtifactCard/>`, `<ArtifactDetail/>`
  (Markdown + JSON viewer + edit toggle).
- **Empty state:** "No artifacts yet. Accept a proposal or run
  a pipeline."

### 8. Decision Panel — modal / dock on any target

- **Trigger:** any `HypothesisCard`, `ProposalCard`,
  `ArtifactCard`, `MemoryAdmissionCard`.
- **UI:** five buttons (`Accept`, `Modify`, `Save`, `Forward`,
  `Reject`) + optional `Admit to Memory` when target kind allows.
- **Endpoint:** `POST /api/interface/decision`
  `{target_kind, target_id, action, payload}`.
- **Guardrail:** all actions except `Modify` require a one-click
  confirm ("Undo" toast for 8 s).

### 9. Memory Admission — modal spawned by `Admit to Memory`

- **UI:** four scope options as radio (`SESSION_LOCAL`,
  `WORKSPACE`, `PROJECT`, `SHARED_FABRIC`); each with a
  one-line consequence description.
- **Endpoint:** `POST /api/interface/memory_admission` returns
  `MemoryAdmission(status=PENDING)` → gate resolves →
  `ADMITTED` / `REFUSED` (visible in the modal).
- **Governance:** `SHARED_FABRIC` and `PROJECT` require
  `human_explicit_choice=true` on the request; the runtime's
  existing `WriteAuthority.denied` path returns `REFUSED` for
  everything else.

## New HTTP endpoints for User mode

All new routes live under `/api/interface/*` so operator mode
(`/api/workbench/*`) and Socrates runtime (`/api/socrates/*`)
remain untouched.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/interface/session/new` | Create a new session; body carries `have`/`want`. |
| GET | `/api/interface/session/<id>` | Summary payload for Session Home. |
| POST | `/api/interface/input` | Create Input. |
| GET | `/api/interface/input/<id>` | Fetch Input metadata + normalized body. |
| GET | `/api/interface/session/<id>/hypotheses` | List `SceneHypothesis` rows. |
| GET | `/api/interface/session/<id>/proposals` | List `OperationProposal` rows. |
| GET | `/api/interface/session/<id>/artifacts` | List Artifacts. |
| GET | `/api/interface/artifact/<id>` | Fetch Artifact detail. |
| PATCH | `/api/interface/artifact/<id>` | Modify Artifact (bumps version). |
| POST | `/api/interface/proposal/<id>/accept` | Spawn Run from Proposal. |
| POST | `/api/interface/proposal/<id>/dismiss` | Dismiss. |
| GET | `/api/interface/run/<id>` | Run detail. |
| GET | `/api/interface/run/<id>/stream` | SSE stream of AgentInvocations. |
| POST | `/api/interface/decision` | Append `HumanDecision`. |
| POST | `/api/interface/memory_admission` | Propose Memory Admission. |
| GET | `/api/interface/memory_admission/<id>` | Fetch admission outcome. |

All endpoints validate a `session_id` at their top and refuse
cross-session mutation. All decision-writing endpoints require
a `X-Interface-Actor` header (user id) for the `HumanDecision`
ledger.

## Pipeline launch flow

Reference sequence for scenario 5 in the test plan (transcript
→ artifacts).

```
User → Launchpad     "У меня встреча" + "Понять"
      → POST /api/interface/session/new
        ← {session_id: "ses_X"}

User → SessionHome   drop transcript.vtt
      → POST /api/interface/input {session_id, kind: TRANSCRIPT, ...}
        ← Input(status=INGESTED)

Server (auto)        ProposalEngine.propose(session_id) after ingest
                      spawns default "reconstruct fabric" Run
      → Run(mode=FAST) executes SocratesRuntime.run(..., mode=DETERMINISTIC)
      → SceneHypothesis(status=CANDIDATE) minted from Run
      → Session.elect_active picks the top candidate
      → OperationProposal(status=OFFERED) rows emitted

User → SessionHome   sees 3 proposals
      → POST /api/interface/proposal/opp_1/accept
        ← Run(status=QUEUED) → RUNNING → OK
        ← Artifact(kind=FABRIC_MAP, status=DRAFT)
        ← Artifact(kind=QUESTION_SET, status=DRAFT)

User → ArtifactGallery   opens FABRIC_MAP
      → POST /api/interface/decision {target: Artifact, action: ACCEPT}
        ← Artifact.status → ACCEPTED

User → DecisionPanel   Admit to Memory
      → POST /api/interface/memory_admission {artifact_id, scope: WORKSPACE,
                                              authority_ref: "human_explicit_choice:user_1"}
        ← MemoryAdmission(status=ADMITTED)  (governance passes)
```

Any step that fails at the provider layer surfaces on the
originating card, not as a full-page collapse. `PROVIDER_BILLING_BLOCKED_20260819`
maps to: Run.status=FAILED, error="PROVIDER_UNAVAILABLE", visible
in Run Status; the user is offered "switch this run to
TEST_DOUBLE mode" (via `ClaudeCodeHarnessClient` in-process for
first live tests).

## Developer mode specification

- **URL prefix:** `/dev/`.
- **Implementation:** re-mounts the existing `workbench_ui/dist`
  bundle from `:8790` under `/dev/workbench/` and the
  `/api/workbench/*` API under `/api/dev/workbench/*` (a single
  reverse-proxy stanza; no React change).
- **Discoverability:** hidden from Launchpad by default.
  Accessible only by direct URL or via `/session/<id>?dev=1`.
- **Top-nav banner:** clearly marked "Developer mode — governance
  surface; changes propagate to production runtime".
- **Capabilities exposed:** everything workbench_ui already has —
  pipeline selection, prompt asset lifecycle, RAG profile
  lifecycle, run compare, node inspector, branches, copilot.
- **User mode ↔ developer mode isolation:** a User mode session
  never renders developer-mode components; a developer-mode
  screen never spawns a HumanDecision that mutates user
  Artifacts (developer decisions target assets, not artifacts).
- **Existing activation:** already deployed at `:8790` per
  `ui_activation_report.md`. The only new work here is the
  `/dev/` re-mount route + banner text.

## What this architecture does NOT introduce

- No new backend runtime beyond an `interface_api/` HTTP layer
  that reads/writes the Interaction Model objects and orchestrates
  `SocratesRuntime` runs.
- No new database. Sessions and their objects live in the same
  SQLite substrate as `SocratesContext` (add tables under a new
  `interface_state.sqlite` file or an `interface_*` prefix).
- No new provider adapter. Runs use the existing provider chain
  or the existing `ClaudeCodeHarnessClient` (TEST-ONLY).
- No new authority path. `MemoryAdmission` reuses
  `enforce_no_durable_write` + `WriteAuthority` from
  `socrates_runtime`.
- No new agent framework. `AgentInvocation` is a projection of
  existing model-call boundaries in `SocratesRuntime` +
  `LiveModelPhaseExecutor`.
- No new arena. The existing `tinkuy_arena` is invoked as a
  `Run.pipeline_id="tinkuy_arena"` when relevant.

# Interface MVP Test Plan

10 scenarios. Each is a whole session, not a unit test. Observers
watch human behaviour, not only backend logs.

For every scenario:
- **Setup** — starting state.
- **Steps** — actions the human performs.
- **Expected results** — what the UI and backend must show.
- **Success criteria** — objective checkpoints.
- **Error cases** — what happens when things go wrong.
- **Observation** — what to watch on the human, not the machine.

Two runtime modes for the plan:
- **T-mode** (`TEST_DOUBLE`) — uses `ClaudeCodeHarnessClient`.
  Envelopes are recorded; response comes from an isolated worker.
  Deterministic for the seams that need it. Recommended for first
  live tests while `PROVIDER_BILLING_BLOCKED_20260819` is open.
- **L-mode** (`LIVE`) — real provider chain. Runs only after 302.AI
  balance restores.

All 10 scenarios are executable in T-mode; scenarios marked `[L]`
additionally require L-mode for full acceptance.

---

## Scenario 1 · First-time visitor lands on Launchpad

**Setup:** empty workspace; new user.

**Steps:**
1. Open `/`.
2. Read the two questions.
3. Click `Встреча` + `Понять`.
4. Wait ≤2 s for redirect.

**Expected:**
- Launchpad renders in ≤500 ms.
- No world/scene/persona selector on screen.
- Redirect lands at `/session/<new_session_id>` with an empty
  Session Home.

**Success criteria:**
- `POST /api/interface/session/new` returns 201 with a
  `session_id`.
- Session Home renders empty state ("Drop a file or paste text").

**Error cases:**
- Backend 5xx → Launchpad shows inline error, does NOT retry.

**Observation:**
- Does the user hesitate on the chip choices? If yes, chip labels
  need to change (record which chip pair is chosen).
- Does the user try to click something before the two chips are
  answered? If yes, the "Continue" button state needs to be more
  visible.

---

## Scenario 2 · Meeting transcript ingestion

**Setup:** empty session created in scenario 1.

**Steps:**
1. On Session Home, drop `meeting_2026_08_18.vtt` (10 KB
   speaker-labelled transcript).
2. Wait ≤3 s for normalizer.

**Expected:**
- Input appears in the Inputs shelf, kind=TRANSCRIPT.
- `Input.status` transitions NEW → INGESTED visibly (progress
  bar).
- Speaker labels preserved and visible in the Input detail view.
- A default "reconstruct fabric" `Run` starts automatically
  (visible in Run Status).

**Success:**
- Session Home lists 1 Input, 1 Run, 0 Artifacts.
- Within 15 s (T-mode), Run.status = OK and at least one
  `SceneHypothesis(status=CANDIDATE)` exists.

**Error:**
- Provider error (L-mode) → Run.status = FAILED, error carries
  provider reason; UI offers "switch to TEST_DOUBLE".

**Observation:**
- Does the user understand that ingestion is separate from a
  pipeline run? (If not, name the intermediate state clearer.)

---

## Scenario 3 · Reconstruction canvas reveals alternatives

**Setup:** scenario 2 completed successfully.

**Steps:**
1. Navigate to Reconstruction Canvas.
2. Read the active `SceneHypothesis` card (telos, grounds,
   confidence).
3. Open one alternative; read `delta_if_alternative`.
4. Elevate that alternative to `ACTIVE`.

**Expected:**
- Active hypothesis shows at most 3 grounds; each is clickable
  and highlights the corresponding span in the Input.
- Alternatives list is ordered by descending confidence.
- Elevating an alternative supersedes the previous active
  hypothesis (its status → SUPERSEDED).

**Success:**
- Invariant holds: exactly one `ACTIVE` hypothesis at any time.
- Backend receives `POST /api/interface/decision
  {target_kind: SceneHypothesis, action: ACCEPT}`.

**Error:**
- Attempt to elevate a `REJECTED` hypothesis → server refuses
  with a typed error; UI shows inline.

**Observation:**
- Does the user believe the active hypothesis? Watch for
  hesitation before elevate/reject.
- Does `delta_if_alternative` help the user see what changes?

---

## Scenario 4 · Proposal shelf → accept operation

**Setup:** scenario 3 completed.

**Steps:**
1. Open Proposal Shelf.
2. Read three proposals with `operation_kind` + `why`.
3. Accept one.

**Expected:**
- Accepted proposal transitions to `ACCEPTED`; a new `Run`
  starts.
- Other proposals stay `OFFERED` (not auto-`SUPERSEDED`).
- Session Home updates: pending Run visible; proposal card
  shows "Accepted" badge.

**Success:**
- `Run.input_ids` includes the session's ingested Inputs.
- `Run.pipeline_id` matches the accepted `operation_kind`.

**Error:**
- Accept a proposal whose hypothesis has since been
  `SUPERSEDED` → server refuses; UI shows "hypothesis changed;
  refresh proposals".

**Observation:**
- Does the user pick the first proposal every time? (If yes,
  the proposals are not distinguishable enough.)

---

## Scenario 5 · Artifact gallery + accept + modify

**Setup:** scenario 4 Run completed, produced 2 artifacts.

**Steps:**
1. Open Artifact Gallery.
2. Open the `FABRIC_MAP` artifact.
3. Accept it (Decision Panel).
4. Edit one node in the map.
5. Save (bumps version).

**Expected:**
- Artifact.status transitions DRAFT → ACCEPTED → MODIFIED.
- `Artifact.version` increments; prior `body_ref` still fetchable
  under `/api/interface/artifact/<id>?version=<n-1>`.

**Success:**
- Two `HumanDecision` rows exist: one ACCEPT, one MODIFY.
- Modified artifact re-renders in the gallery with a "v2" badge.

**Error:**
- Edit conflict (rare in single-user MVP) → last-write-wins with
  a Toast, no data loss.

**Observation:**
- Does the user find the edit surface intuitive? Are they trying
  to edit inside the map or in a JSON blob? (Design decision:
  which is the canonical edit affordance for `FABRIC_MAP`?)

---

## Scenario 6 · Admit an artifact to workspace memory

**Setup:** scenario 5 completed.

**Steps:**
1. On the modified artifact, click "Admit to Memory".
2. Modal appears with four scope options + one-line
   consequence text.
3. Choose `WORKSPACE`.
4. Confirm.

**Expected:**
- `MemoryAdmission(status=PENDING)` created.
- Governance gate returns `ADMITTED` (workspace + human
  explicit choice → authority path passes).
- Modal shows result inline.

**Success:**
- Admission ledger row is append-only; visible via
  `GET /api/interface/memory_admission/<id>`.
- Artifact.status unchanged (admission does not mutate artifact
  state).

**Error:**
- Choose `SHARED_FABRIC` without canonical authority →
  `REFUSED` with human-readable reason; ledger records the
  refusal.

**Observation:**
- Does the user understand the four scopes without hovering
  the tooltip? (If not, the labels need to change.)

---

## Scenario 7 · Reject a hypothesis; watch downstream cascade

**Setup:** scenario 5 completed (artifacts exist bound to the
active hypothesis).

**Steps:**
1. Return to Reconstruction Canvas.
2. Reject the active hypothesis.
3. Observe how the Proposal Shelf and Artifact Gallery react.

**Expected:**
- Prior active hypothesis → `REJECTED`.
- No alternative is auto-elevated (invariant: system does not
  silently pick a new active without human).
- Existing `OperationProposal`s tied to the rejected hypothesis
  are marked `SUPERSEDED` on the shelf.
- Existing `Artifact`s remain (they were produced under the
  rejected hypothesis; their `provenance.scene_hypothesis_id`
  shows the rejected ref). No artifact is silently deleted.

**Success:**
- Session Home shows "No active understanding — pick an
  alternative or drop new material".
- No cascade of deletions.

**Error:**
- Attempt to accept a `SUPERSEDED` proposal fails typed error.

**Observation:**
- Does the user experience the rejection as safe? (Rejection
  should not feel like it destroys work.)

---

## Scenario 8 · Forward an artifact

**Setup:** scenario 6 completed; the modified artifact is
`ACCEPTED` + `ADMITTED WORKSPACE`.

**Steps:**
1. On artifact, choose "Forward".
2. Enter a downstream address (email / Slack / URL).
3. Confirm.

**Expected:**
- `HumanDecision(action=FORWARD, payload.address=...)` created.
- Forwarding side effect is stubbed for MVP: system records
  intent, does not actually send (v0.2 wires real transport).
- UI shows "Forwarded to <address>" with an Undo toast (8 s).

**Success:**
- Decision ledger has the FORWARD row.
- No email/slack was actually sent (stub).

**Error:**
- Malformed address → inline validation, no ledger row.

**Observation:**
- Does the user expect the send to be real? (Manage
  expectation with a "MVP: intent recorded" line.)

---

## Scenario 9 · Provider outage during a live run `[L]`

**Setup:** L-mode; provider is 302.AI in a state that returns
401 for at least one call.

**Steps:**
1. From Session Home, accept a proposal that requires LIVE.
2. Wait for Run to move RUNNING → FAILED.

**Expected:**
- Run Status shows `terminal=FAILED_EXPLICIT`, error =
  `PROVIDER_UNAVAILABLE: FallbackClient: all N providers
  failed. Last error: AuthenticationError: 401 Insufficient
  account balance…`.
- No `Artifact(status=DRAFT)` is produced (fail-closed).
- No `SceneHypothesis` is auto-updated.
- Runtime authority invariants preserved:
  `dyad.authority=NO_DURABLE_WRITE`,
  `self_development.authority=NO_ADOPTION_AUTHORITY`.
- UI offers a one-click "switch this run to TEST_DOUBLE mode".

**Success:**
- One-click switch spawns a fresh Run with `mode=TEST_DOUBLE`
  that completes OK.

**Error:**
- If TEST_DOUBLE responses are absent (isolated worker not
  authored), `ClaudeCodeHarnessClient` raises
  `HarnessResponseMissing`; UI surfaces the specific
  envelope id and asks the operator to produce a response.

**Observation:**
- Does the user panic at the failure? The failure must read as
  "provider blocked", not as "Socrates broke".

---

## Scenario 10 · Developer mode round-trip

**Setup:** the workbench_ui bundle activated on `:8790` per
`ui_activation_report.md`.

**Steps:**
1. From within a session, click "Developer mode" (hidden by
   default; accessible via `/session/<id>?dev=1`).
2. Land on `/dev/workbench/` — full operator UI loads.
3. Inspect the pipeline that produced the session's latest
   artifact (jump from artifact.origin_run.pipeline_id).
4. Modify a prompt asset via the accept lifecycle
   (clone → save → validate → smoke → accept).
5. Return to User mode.

**Expected:**
- Developer-mode banner clearly marks the mode boundary.
- No `HumanDecision` on user artifacts is produced by the
  developer-mode click.
- Prompt lifecycle changes are visible in `Catalogue` /
  `PromptEditor` — the acceptance chain works as documented
  in `workbench_ui/qa/screenshots/`.
- Round-trip back to User mode preserves the session state.

**Success:**
- User mode session state after the round-trip is unchanged
  except for whatever the pipeline change caused on the NEXT
  Run (which is the intended effect).

**Error:**
- Accidental promotion of a broken prompt asset — lifecycle
  rejects at `validate` or `smoke`, prevents `activate`.

**Observation:**
- Can the operator explain to a non-operator why they went
  into Developer mode? (The mode boundary needs to be a
  concept the operator can articulate.)

---

## Global success criteria (RC1 acceptance for the interface)

All 10 scenarios pass their success criteria in T-mode. Scenarios
1–8, 10 pass in L-mode when 302.AI billing restores. Scenario 9
by definition tests the L-mode failure path and must produce the
documented graceful degradation.

Runtime invariants (unchanged from Socrates RC1) hold on every
Run produced by the interface:

- `dyad.authority = NO_DURABLE_WRITE`
- `self_development.authority = NO_ADOPTION_AUTHORITY`
- `self_development.self_mutation_authority = "NO"`
- `self_development.stop_reason = "no_3e_reentry"`
- `memory_outcome = null` unless a `MemoryAdmission(status=ADMITTED)`
  with a matching `authority_ref` exists
- no hidden chain-of-thought exposed in Artifacts

Backend regression floor: **1320 passed / 4 skipped / 0 failed**
(current baseline). New tests added by the interface implementation
must extend this floor without touching the existing 1320.

## Observation instrument for human testers

For every scenario, the observer records:

- Time-to-first-action (from screen render to first user click).
- Number of hesitations (>2 s pause with cursor over one
  affordance).
- Frequency of tooltip / help-hover.
- Direct expressions of confusion (transcribed if verbal).
- Points at which the user tried to do something the UI does
  not expose (feature-request signal).
- Points at which the user tried to undo (record which target
  and which action).

These observations, not raw backend logs, decide whether the
interface is `READY_FOR_LIVE_TEST` graduate to `READY_FOR_BETA`.

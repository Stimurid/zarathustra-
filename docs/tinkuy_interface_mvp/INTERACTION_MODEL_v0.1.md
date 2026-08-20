# Interaction Model v0.1

Exactly 8 typed objects. No other first-class object may be added
without demonstrated need in a live-test trace.

Every object below has:
- **schema** — Python-dataclass form suitable for
  `dataclasses.dataclass(frozen=True)` and JSON `to_public()`.
- **state** — an enum of allowed states.
- **transitions** — allowed edges in the state machine.
- **test hooks** — the minimum tests required before the object may
  ship to a live test session.

Naming convention: fields snake_case, IDs prefixed with the object
short-tag (`inp_`, `run_`, `sch_`, `opp_`, `agn_`, `art_`, `dec_`,
`mem_`).

Objects live in a proposed new package `tinkuy_interface/` next to
`socrates_runtime/` and reuse existing runtime primitives where
possible. Nothing here rewrites `SocratesRuntime`.

---

## 1. Input

The raw material the user brings into a session — meeting
transcript, a note, a file, a live stream.

### Schema

```python
class InputKind(str, Enum):
    TEXT              = "TEXT"
    FILE              = "FILE"
    TRANSCRIPT        = "TRANSCRIPT"
    API_STREAM        = "API_STREAM"
    EXTERNAL_SOURCE   = "EXTERNAL_SOURCE"  # PLAUD, Otter, arbitrary

@dataclass(frozen=True)
class Input:
    input_id:        str                # "inp_<hex12>"
    session_id:      str                # session it belongs to
    kind:            InputKind
    display_name:    str                # user-visible label
    bytes_ref:       str                # blob store path or inline
    mime:            str                # "text/plain" | "text/vtt" | ...
    length_chars:    int                # cheap size for the shelf
    provenance:      dict[str, str]     # {source: str, capture_at: iso, uploader: user_id}
    created_at:      str                # iso
    checksum_sha256: str
```

### State

```
NEW              # object exists, bytes present, not indexed yet
INGESTED         # normalizer ran, `length_chars` set, ready for reconstruction
INDEXED          # RAG-visible if the session opts in
REJECTED         # too large / unsupported mime / provenance-blocked
```

### Transitions

```
NEW      → INGESTED    on `run normalizer(input_id)`
NEW      → REJECTED    on size/mime/policy failure (records rejection_reason)
INGESTED → INDEXED     on optional `index_for_rag(input_id, profile_id)`
INGESTED → REJECTED    on downstream normalization failure discovered later
```

`INDEXED → REJECTED` is intentionally forbidden — once indexed, an
input can only be withdrawn (a separate action outside this state
machine).

### Test hooks

- `test_input_text_roundtrip` — POST text → object at NEW → INGESTED.
- `test_input_transcript_vtt_normalises_speakers` — speaker labels
  survive `INGESTED`.
- `test_input_oversize_rejects_with_reason`.
- `test_input_mime_unsupported_rejects_with_reason`.

---

## 2. Run

A single pipeline execution against a session's inputs.

### Schema

```python
class RunMode(str, Enum):
    FAST         = "FAST"          # deterministic / cached path
    LIVE         = "LIVE"          # real provider
    TEST_DOUBLE  = "TEST_DOUBLE"   # ClaudeCodeHarnessClient etc.

class RunStatus(str, Enum):
    QUEUED    = "QUEUED"
    RUNNING   = "RUNNING"
    OK        = "OK"
    FAILED    = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass(frozen=True)
class Run:
    run_id:            str                  # "run_<hex12>"
    session_id:        str
    pipeline_id:       str                  # "socrates_runtime" | "californian_id.inner_council" | ...
    pipeline_version:  str                  # git sha of the runtime code
    input_ids:         tuple[str, ...]
    mode:              RunMode
    provider_id:       str                  # "302ai_chain" | "claude_code_harness" | "fallback"
    model_id:          str
    status:            RunStatus
    started_at:        str                  # iso
    finished_at:       str                  # iso
    duration_ms:       int
    terminal:          str                  # SocratesRuntime terminal name if applicable
    trace_ref:         str                  # path to on-disk trace
    context_id:        str                  # SocratesContext id when applicable
    error:             str                  # empty when OK
```

### State

```
QUEUED → RUNNING → OK
QUEUED → CANCELLED
RUNNING → FAILED
RUNNING → CANCELLED
```

### Transitions

- `RunStore.enqueue(session_id, pipeline_id, inputs, mode, params)`
  returns `Run(status=QUEUED)`.
- `RunOrchestrator.pump()` picks a `QUEUED` run and moves to
  `RUNNING`, then to `OK`/`FAILED` based on runtime result.
- `Run.cancel()` allowed from `QUEUED` and `RUNNING`.

### Test hooks

- `test_run_socrates_fast_deterministic_completes_ok`.
- `test_run_live_falls_to_failed_when_provider_401` —
  reproduces current `PROVIDER_BILLING_BLOCKED_20260819` state,
  proves the Run object records the error without corrupting
  session.
- `test_run_test_double_via_claude_code_harness_ok` — reuses the
  existing 3 controlled-proof harness tests.
- `test_run_cancel_from_running_marks_cancelled_and_frees_context`.

---

## 3. SceneHypothesis

The system's current understanding of what the session material is
about. Not asked from the user — derived from `Input`s + prior
`Run`s and shown for correction.

### Schema

```python
class HypothesisStatus(str, Enum):
    CANDIDATE      = "CANDIDATE"      # freshly minted
    ACTIVE         = "ACTIVE"         # currently guiding operations
    ALTERNATIVE    = "ALTERNATIVE"    # kept as a live alternative
    SUPERSEDED     = "SUPERSEDED"     # replaced by a newer hypothesis
    REJECTED       = "REJECTED"       # human explicitly rejected

@dataclass(frozen=True)
class SceneHypothesis:
    hypothesis_id:      str                  # "sch_<hex12>"
    session_id:         str
    origin_run_ids:     tuple[str, ...]      # which Runs produced this
    telos:              str                  # short human-readable claim of "what is going on"
    grounds:            tuple[str, ...]      # cited evidence refs (input segments, dyad excerpts)
    confidence:         float                # [0.0, 1.0]
    status:             HypothesisStatus
    alternatives:       tuple[str, ...]      # ids of sibling SceneHypothesis rows
    delta_if_alternative: str                # "if X, then Y changes downstream"
    created_at:         str
```

### State

```
CANDIDATE → ACTIVE            (system picks the highest-confidence candidate)
CANDIDATE → ALTERNATIVE       (kept but not active)
ACTIVE    → SUPERSEDED        (a newer candidate wins)
ACTIVE    → REJECTED          (human explicitly rejects)
ALTERNATIVE → ACTIVE          (human explicitly elevates)
ALTERNATIVE → REJECTED
```

Invariant: at most one `ACTIVE` per session at a time.

### Transitions

- `SceneHypothesis.mint(session_id, origin_run)` from a Run's
  post-terminal `dyad.likely_failure_source` / `state.scene.telos`
  / `apparatus_diagnostic.classification` produces one or more
  `CANDIDATE` rows.
- `Session.elect_active(hypothesis_id)` moves to `ACTIVE`, demoting
  the prior `ACTIVE` to `SUPERSEDED`.
- `Session.reject(hypothesis_id, reason)` moves to `REJECTED`.

### Test hooks

- `test_scene_hypothesis_minted_from_socrates_run_carries_grounds`.
- `test_scene_hypothesis_at_most_one_active_invariant`.
- `test_human_rejection_supersedes_and_activates_alternative`.
- `test_delta_if_alternative_is_non_empty_when_alternatives_exist`.

---

## 4. OperationProposal

Concrete operations the system is offering. The user does not
choose an operation from scratch — the system proposes based on
the active `SceneHypothesis` and available `Artifact` gaps.

### Schema

```python
class ProposalStatus(str, Enum):
    OFFERED      = "OFFERED"
    ACCEPTED     = "ACCEPTED"    # human accepted; queued as a Run
    DISMISSED    = "DISMISSED"   # human declined
    SUPERSEDED   = "SUPERSEDED"  # replaced by a later proposal

@dataclass(frozen=True)
class OperationProposal:
    proposal_id:        str                  # "opp_<hex12>"
    session_id:         str
    scene_hypothesis_id: str                 # which active hypothesis motivated this
    operation_kind:     str                  # "reconstruct_positions" | "map_arguments" | "extract_questions" | ...
    why:                str                  # short reason, human-readable
    expected_artifact_kinds: tuple[str, ...] # which Artifact kinds should appear
    predicted_agent_calls: tuple[str, ...]   # which AgentInvocation kinds this will require
    status:             ProposalStatus
    resulting_run_id:   str                  # populated on ACCEPTED
    created_at:         str
```

### State

```
OFFERED → ACCEPTED     (spawns a Run)
OFFERED → DISMISSED
OFFERED → SUPERSEDED
```

### Transitions

- `ProposalEngine.propose(session_id)` runs against the active
  `SceneHypothesis` and existing `Artifact`s, emits a bounded set
  of `OFFERED` proposals.
- `Session.accept(proposal_id)` → `ACCEPTED`, spawns a Run.
- `Session.dismiss(proposal_id, reason)`.

### Test hooks

- `test_proposal_engine_emits_at_least_one_when_scene_hypothesis_active`.
- `test_proposal_engine_does_not_emit_for_rejected_hypothesis`.
- `test_accepted_proposal_spawns_run_and_binds_resulting_run_id`.
- `test_dismissed_proposal_does_not_spawn_run`.

---

## 5. AgentInvocation

Explicit call to a persona / expert / method as part of a Run.

### Schema

```python
class AgentKind(str, Enum):
    SOCRATES        = "SOCRATES"
    ZARATHUSTRA     = "ZARATHUSTRA"
    METHOD          = "METHOD"          # domain method
    EXPERT          = "EXPERT"          # persona expert
    ARENA_COUNCIL   = "ARENA_COUNCIL"

class InvocationStatus(str, Enum):
    QUEUED   = "QUEUED"
    RUNNING  = "RUNNING"
    OK       = "OK"
    FAILED   = "FAILED"

@dataclass(frozen=True)
class AgentInvocation:
    invocation_id:      str            # "agn_<hex12>"
    run_id:             str            # which Run this is part of
    kind:               AgentKind
    persona_id:         str            # e.g. "socrates.v0.3.0" | "zarathustra.v0.3.1"
    intervention_profile: str          # "normal" | axis presets
    status:             InvocationStatus
    provider_id:        str
    model_id:           str
    envelope_ref:       str            # path to recorded envelope (ClaudeCodeHarnessClient style)
    response_ref:       str            # path to raw response
    started_at:         str
    finished_at:        str
    duration_ms:        int
    error:              str
```

### State

Same as `Run` but scoped to a single agent call.

### Transitions

- `Run.execute()` emits one `AgentInvocation` per model call.
- `AgentInvocation` cannot mutate any object outside its own
  fields; the Run interprets its `response_ref` back into
  Artifacts and downstream state.

### Test hooks

- `test_agent_invocation_records_envelope_before_response_read`
  (reuses `ClaudeCodeHarnessClient` guarantee).
- `test_agent_invocation_cannot_mint_authority` (asserts the
  invocation itself carries no `NO_ADOPTION_AUTHORITY`-relaxing
  claim; authority stays on the Run/MemoryAdmission).

---

## 6. Artifact

Any produced object the user can look at, share, or push forward.

### Schema

```python
class ArtifactKind(str, Enum):
    FABRIC_MAP        = "FABRIC_MAP"          # semantic fabric snapshot
    ARGUMENT_MAP      = "ARGUMENT_MAP"
    QUESTION_SET      = "QUESTION_SET"
    RECONSTRUCTION    = "RECONSTRUCTION"
    GROUP_SOUL        = "GROUP_SOUL"
    RECOMMENDATIONS   = "RECOMMENDATIONS"
    NARRATIVE         = "NARRATIVE"
    RAW_TRACE         = "RAW_TRACE"           # developer-mode only

class ArtifactStatus(str, Enum):
    DRAFT      = "DRAFT"       # freshly produced by a Run
    ACCEPTED   = "ACCEPTED"    # human accepted for the session
    MODIFIED   = "MODIFIED"    # human edited an accepted artifact
    ARCHIVED   = "ARCHIVED"    # kept but hidden from active shelf
    REJECTED   = "REJECTED"

@dataclass(frozen=True)
class Artifact:
    artifact_id:      str
    session_id:       str
    origin_run_id:    str
    kind:             ArtifactKind
    title:            str
    body_ref:         str          # markdown / json / html blob
    provenance:       dict[str, str]     # {input_ids, agent_invocation_ids, scene_hypothesis_id}
    status:           ArtifactStatus
    version:          int          # monotonic per artifact_id
    created_at:       str
    updated_at:       str
```

### State

```
DRAFT → ACCEPTED
DRAFT → REJECTED
ACCEPTED → MODIFIED       (bumps version)
MODIFIED → ARCHIVED
ACCEPTED → ARCHIVED
```

### Test hooks

- `test_artifact_provenance_carries_input_ids_and_invocation_ids`.
- `test_artifact_modified_bumps_version_and_preserves_prior_body_ref`.
- `test_artifact_reject_does_not_delete_body_ref` (evidence
  survival).

---

## 7. HumanDecision

Every user act that changes session-scoped state.

### Schema

```python
class DecisionAction(str, Enum):
    ACCEPT              = "ACCEPT"
    MODIFY              = "MODIFY"
    SAVE                = "SAVE"          # keep local
    FORWARD             = "FORWARD"       # push to a downstream target
    REJECT              = "REJECT"
    ADMIT_TO_MEMORY     = "ADMIT_TO_MEMORY"  # bounces to MemoryAdmission

@dataclass(frozen=True)
class HumanDecision:
    decision_id:      str
    session_id:       str
    user_id:          str
    target_kind:      str    # "SceneHypothesis" | "OperationProposal" | "Artifact" | "MemoryAdmission"
    target_id:        str
    action:           DecisionAction
    payload:          dict[str, Any]  # optional MODIFY body, FORWARD address, ADMIT scope
    created_at:       str
```

### State

Instantaneous — a `HumanDecision` is a fact, not a state machine.
It commits by being appended to `HumanDecision.append(...)`.

### Transitions

None inside `HumanDecision`. Its effect is written by side effect
to the target object's state machine, transactionally.

### Test hooks

- `test_decision_accept_on_scene_hypothesis_transitions_to_active`.
- `test_decision_admit_to_memory_creates_MemoryAdmission_row`.
- `test_decision_modify_on_artifact_bumps_version`.
- `test_decision_is_append_only_ledger` — historic decisions
  cannot be edited.

---

## 8. MemoryAdmission

The gate between session-local state and long-term memory. Every
long-term write flows through this object; the runtime already
enforces `NO_DURABLE_WRITE` — this object is the human-visible
handle.

### Schema

```python
class AdmissionScope(str, Enum):
    SESSION_LOCAL   = "SESSION_LOCAL"      # dies with the session
    WORKSPACE       = "WORKSPACE"          # visible to workspace members
    PROJECT         = "PROJECT"            # long-lived project scope
    SHARED_FABRIC   = "SHARED_FABRIC"      # canonical shared memory
    REJECTED        = "REJECTED"           # explicitly denied admission

class AdmissionOutcome(str, Enum):
    PENDING     = "PENDING"
    ADMITTED    = "ADMITTED"
    REFUSED     = "REFUSED"          # governance refusal
    WITHDRAWN   = "WITHDRAWN"        # human retracted before commit

@dataclass(frozen=True)
class MemoryAdmission:
    admission_id:   str
    session_id:     str
    artifact_id:    str                 # the artifact proposed for admission
    scope:          AdmissionScope
    outcome:        AdmissionOutcome
    reason:         str                 # governance / human note
    authority_ref:  str                 # e.g. "human_explicit_choice:<user_id>"
    proposed_at:    str
    resolved_at:    str
```

### State

```
PENDING → ADMITTED     (governance passes; authority_ref set)
PENDING → REFUSED      (governance denies; reason populated)
PENDING → WITHDRAWN    (human retracts before commit)
```

`ADMITTED` cannot be walked back inside this object — a subsequent
retraction is a new `MemoryAdmission` row targeting the same
`artifact_id` with an inverse effect.

### Transitions

- `MemoryAdmission.propose(artifact_id, scope, authority_ref)`
  creates a `PENDING` row and calls the existing governance path
  (`enforce_no_durable_write` + workspace `WriteAuthority`).
- The gate itself decides `ADMITTED` / `REFUSED`.

### Test hooks

- `test_admission_without_authority_ref_refuses`.
- `test_admission_with_workspace_authority_scope_workspace_admits`.
- `test_admission_shared_fabric_requires_explicit_canonical_authority`.
- `test_admission_ledger_is_append_only`.

---

## Object interaction matrix

Which object can write which. `→` means "creates or transitions".

```
Input           →   Run (via input_ids)
Run             →   SceneHypothesis (candidates)
Run             →   Artifact (drafts)
Run             →   AgentInvocation (one per model call)
SceneHypothesis →   OperationProposal (via ProposalEngine)
OperationProposal → Run (on ACCEPTED)
HumanDecision   →   SceneHypothesis, OperationProposal, Artifact, MemoryAdmission
MemoryAdmission →   (external memory store, governance-gated)
```

No object writes upstream of itself in this graph. No cycles. This
is the invariant that keeps the Interaction Model auditable.

---

## Explicitly deferred to v0.2

The following are **concepts**, not v0.1 components, because they
lack at least one of {schema, state, transition, test hook} today:

- Session (as a first-class object rather than a namespacing id).
- User / Member roles beyond a bare `user_id` string.
- Group Soul rendering rules (kept only as an `ArtifactKind`).
- Forwarding destinations (Slack / doc / API) — represented as an
  opaque `payload.address` on `HumanDecision` for v0.1.
- Live-stream Input types (`API_STREAM` is enumerated but not yet
  wired end-to-end).
- Multi-user concurrent editing of a single Artifact.

Do not scaffold code for these. Return to them only when a live
test surfaces a real need.

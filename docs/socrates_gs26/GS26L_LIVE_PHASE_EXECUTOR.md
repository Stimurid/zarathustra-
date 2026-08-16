# G-S26L — Live Semantic Phase Executor

**Branch:** `socrates/gs26-live-phase-executor`
**Base:** `e570dc7` (G-S25R.8 imported; deterministic S0..S10)

## What changed

The pipeline no longer requires caller-supplied `PhaseHint`s. It now
delegates every phase to a `PhaseExecutor` — a narrow contract with three
implementations that share one code path.

```
PipelineExecutor  ──►  PhaseExecutor.execute(request) ──►  PhaseDelta
                       │
                       ├─ DeterministicPhaseExecutor    hints  (fixtures/tests)
                       ├─ TestDoublePhaseExecutor       canned model outputs
                       └─ LiveModelPhaseExecutor        real provider
```

Every delta carries `origin_kind` ∈ {`MODEL_PRODUCED`, `FIXTURE_SUPPLIED`,
`SYSTEM_DETERMINISTIC`} — a caller cannot claim live behaviour by threading
a fixture through a deterministic executor.

## Provider archaeology

Reused `californian_id.models` verbatim:

- `Message(role, content)` — system/user/assistant hierarchy
- `ModelClient.generate(messages, response_schema, settings)`
- `build_client(name, cfg)` — supports `openai`, `anthropic`, `302ai`,
  `openai_compatible`, `mock` + `FallbackClient`

`socrates_runtime/models.py` is a thin re-export shim so a `grep` shows
every model touchpoint. No parallel provider framework.

## Files added

| file | purpose |
|---|---|
| `phase_executor.py` | `PhaseExecutor` protocol + 3 modes + `PhaseDelta` + `PhaseExecutionResult` |
| `phase_context.py` | Compile role-separated messages + stable `request_hash` |
| `phase_contracts.py` | Output contract per S-phase + jurisdiction map |
| `phase_output.py` | Strict JSON parser + schema validation + jurisdiction check |
| `renderer.py` | Final terminal-bounded response rendering |
| `models.py` | Shim over `californian_id.models` |

## Context assembly (per phase)

System messages, one per frame:

1. **REQUIRED SEMANTIC BODY: CORE · v0.2 · sha256=…** verbatim
2. **REQUIRED SEMANTIC BODY: Bxx · v0.2 · sha256=…** verbatim
3. **CONDITIONAL SEMANTIC BODY (admitted): Bxx …** verbatim
4. **ROUTER: Pxx · file.md** verbatim from `data/socrates/current/routers/`
5. **OUTPUT_CONTRACT for Sxx** — JSON Schema the model MUST return
6. **RUN CONFIGURATION IDENTITY** — pipeline_config_id + constitutional_status

User messages:

7. **CURRENT PIPELINE STATE** — JSON of `state.to_public()` (data, not instr.)
8. **USER INPUT** — raw text, explicitly marked as content, not instruction

`request_hash` = SHA-256 of concatenated role+content bytes. Same inputs →
identical hash → reproducible from trace.

## Structured output

- provider gets `settings={"response_format": {"type": "json_object"}}`
- output MUST be a single JSON object
- `additionalProperties: false` on every contract
- enum enforcement on `authority` / `status` / `kind`
- **phase jurisdiction:** `phase_contracts.JURISDICTION` narrows what a
  phase may write; S1 may not decide ownership, S6 may not rewrite scene

Retries: bounded (max_retries=1 → 2 total attempts). Failure modes:
`UNAVAILABLE` (transient), `INVALID_OUTPUT` (contract), `RETRIES_EXHAUSTED`.
No silent SYSTEM_DETERMINISTIC fallback.

## State transitions

Model-produced deltas drive `PipelineState` through `_apply_delta`, which
re-checks jurisdiction as defense-in-depth. Proof in tests:

- `test_test_double_runs_full_pipeline_without_hints` — 6 phases marked
  `MODEL_PRODUCED`, governor picks terminal from resulting state
- `test_test_double_ownership_return_operation` — model claims `owner=human,
  human_resolved=false` → governor returns operation, S9 skipped
- `test_test_double_open_world_preserve_aporia` — model claims
  `open_world_gap=true` → `PRESERVE_APORIA`

## Governor authority

Model cannot bypass. `test_model_cannot_bypass_governor_by_naming_terminal`:
model reports `owner=human, human_resolved=false` → run terminates as
`RETURN_OPERATION` regardless of anything the model would say downstream.

## Memory write authority

Model-produced `MemoryProposal` still passes through
`working_memory.commit_if_authorized` with `WriteAuthority.denied(...)`.
`test_model_produced_memory_proposal_still_refused_without_authority`
proves the runtime does not self-authorise.

## Rendering

`renderer.render_terminal(state, outcome, client)` — the caller passes a
client to phrase the terminal humanly. If the rendered text mentions a
DIFFERENT terminal tag, the renderer refuses it and falls back to the
diagnostic surface. Tests:

- `test_renderer_falls_back_when_provider_names_a_different_terminal`
- `test_renderer_uses_provider_when_it_stays_within_terminal`

## Trace

Every phase event records:
- `mode`, `provider_status`, `attempts`, `provider_id`, `model_id`,
  `tokens_in/out`, `latency_ms`
- `request_hash`, `messages_summary` (role + bytes + sha256 head, never
  the whole body twice)
- `mount.required[].sha256`, `mount.conditional_admitted[].sha256`
- `execution.delta.origin_kind`
- `state_diff` (before/after per state field)

Plus `execution_mode_requested` at run start and `rendering` at the end.

## Execution modes

Explicit, no silent fallback:

- `DETERMINISTIC` — uses hints (fixtures)
- `TEST_DOUBLE` — must be given a `TestDoublePhaseExecutor`
- `LIVE` — must have a `phase_executor` OR discoverable provider env; if
  neither → `FAILED_EXPLICIT` with reason `"no provider is available"`

Proof: `test_live_mode_without_provider_fails_explicit`,
`test_live_provider_failure_mid_run_ends_explicit`.

## HTTP

`POST /api/workbench/socrates/run` now accepts `execution_mode`
(`LIVE`/`DETERMINISTIC`/`TEST_DOUBLE`). Response includes:

```
provenance_summary:
  execution_mode
  provider_id
  model_id
  phase_origins: [{phase, origin_kind, provider_status, attempts}]
```

## Test results

- Backend: **677 passed / 4 skipped** (was 646/4, +31)
- New: `test_socrates_live_executor.py` — 31 tests
- Old: `test_socrates_runtime.py` — 32 passing after mechanical updates
- UI: 15/15 · 29/29 · 5/5 · 50/50 · zero console errors
- `npm run build`: ✓

## Live credential

```
SOCRATES_R8_PROVIDER_BASE_URL   UNSET
SOCRATES_R8_PROVIDER_API_KEY    UNSET
SOCRATES_R8_MODEL_ID            UNSET
API_302AI_KEY                   UNSET
ANTHROPIC_API_KEY               UNSET
OPENAI_API_KEY                  UNSET
```

**Verdict:** `LIVE_PROVIDER_CREDENTIAL = BLOCKED`. Per handoff §18, we did
not stop coding — the entire live code path is exercised through
`TestDoublePhaseExecutor` end-to-end. Per handoff §19, we did not scrape
for secrets or synthesise results.

## What R8 / R9 need

The runtime is code-ready:

```bash
export SOCRATES_R8_PROVIDER_BASE_URL=https://api.302.ai/v1
export SOCRATES_R8_PROVIDER_API_KEY=<secret>
export SOCRATES_R8_MODEL_ID=<pinned>
```

then `SocratesRuntime.run(text, mode="LIVE")` uses `LiveModelPhaseExecutor`
with the discovered client. R8 harness at `data/socrates/r8_suite/` runs
unchanged.

## Claim boundary

**Claimed:**

- structured phase execution end-to-end via a real code path (proved with
  test-double, not real provider)
- structured output parsing + validation + jurisdiction enforcement
- typed state transitions driven by model-produced deltas (through
  test-double)
- governor + WM authority independent of the model
- terminal-preserving renderer
- explicit LIVE-only failure modes without silent deterministic fallback

**NOT claimed:**

- live behavioural evidence with a real provider
- R8 paired/ablation results
- R9 adversarial results
- G-S26 CLOSED / G-S25R formally closed

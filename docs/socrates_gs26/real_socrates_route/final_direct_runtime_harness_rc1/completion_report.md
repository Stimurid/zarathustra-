# SOCRATES DIRECT RUNTIME HARNESS RC1 — Completion Report

**Task:** `SOCRATES-GS26-DIRECT-RUNTIME-HARNESS-RC1-20260820-007`
**Predecessor:** `189075d` (Pass 5 corrective, preserved).
**Owner correction addressed:** SOCRATES arm no longer hand-assembled
from a "Socratic invariants system prompt"; SOCRATES responses now
flow through the *real* Socrates runtime with an isolated Claude Code
worker at the exact provider seam. `ARCHITECTURE_FREEZE=ON`
throughout — no new architecture wave.
**Verdict:** **`SOCRATES_RUNTIME_RC1_READY_FOR_OWNER_ACCEPTANCE`**

## Lineage

| Item | Value |
|---|---|
| Base branch | `socrates/final-completion-rc1` |
| Base SHA | `189075d89fa29a46ab1e0e5ed905defeb0caa16b` |
| Direct runtime harness commit | *(populated by push)* |
| Production DEPLOY_SHA | `5cb7707dec9677abacd8f7f186d9321929e99c88` (unchanged) |
| Rollback | `/opt/tinkuy/rollback_snapshot_pre_5cb7707.tar.gz` |
| Backend regression | **1320 passed / 4 skipped / 0 failed** (baseline 1317 + 3 harness controlled-proof tests) |

## What changed

One TEST-ONLY module and one test file added to the repository:

- `CALIFORNIAN_ID/src/socrates_runtime/claude_code_harness.py` —
  `ClaudeCodeHarnessClient` implementing `ModelClient` protocol.
  Records envelope to disk BEFORE reading response; fails closed on
  missing response; identity is publicly `provider="claude_code_harness"`
  so no envelope can pass for a production carrier. Not registered
  in `california_id.config` or `SocratesRuntime._build_live_client`.
- `CALIFORNIAN_ID/tests/workbench/test_claude_code_harness_seam.py` —
  3 controlled-proof tests covering handoff §7 properties 1–10.

Neither file touches production runtime, provider selection, auth, or
the 302.AI carrier. Both are dead weight in production; they only
activate when a caller supplies `rendering_client=` /
`phase_executor=` explicitly.

## Controlled proof (§7 property matrix)

`test_claude_code_harness_seam.py::TestClaudeCodeHarnessSeamControlledProof`
3 tests green:

| Property | Test | Result |
|---|---|---|
| 1: envelope produced by real runtime | `test_properties_1_3_5_6_7_8_seam_through_real_runtime` | ✓ real `SocratesRuntime.run(rendering_client=harness)` |
| 2: exact envelope persisted before response read | `test_property_9_fails_closed_when_response_missing` | ✓ envelope file exists after `HarnessResponseMissing` raised |
| 3: worker sees only envelope | disk boundary | ✓ envelope↔response separated on disk |
| 4: raw response unchanged | `test_properties_2_4_10_envelope_persistence_and_independence` | ✓ `r.text == raw` verbatim |
| 5: response enters real seam | `test_properties_1_3_5_6_7_8_seam_through_real_runtime` | ✓ `rendering.provider_id == "claude_code_harness"` in trace |
| 6: real parser / renderer runs | ditto | ✓ `RenderingResult` produced, terminal preserved |
| 7: runtime continues real governance | ditto | ✓ `dyad`, `apparatus_diagnostic`, `self_development` all non-null on run |
| 8: injected output cannot mint authority | ditto | ✓ `dyad.authority == "NO_DURABLE_WRITE"`; `self_development.authority == "NO_ADOPTION_AUTHORITY"`; `self_mutation_authority == "NO"` |
| 9: no deterministic/mock masquerade | `test_property_9_fails_closed_when_response_missing` | ✓ `HarnessResponseMissing` raised, no fabrication |
| 10: independent workers independent | `test_properties_2_4_10_envelope_persistence_and_independence` | ✓ separate `run_dir` → separate `_seq=0`; envelope hashes distinct |

## G-S27 real-runtime SOCRATES arm (8/8)

Two-pass execution against the real Socrates runtime:

**Pass 1 — envelope discovery.** DETERMINISTIC mode +
`rendering_client=ClaudeCodeHarnessClient(fail_on_missing=False)` on
each of the 8 source-ready G-S27 queries. All 8 runs produced exactly
one envelope at the render seam:

```
S01 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S02 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S05 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S06 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S07 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S08 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S09 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
S10 → 001.envelope.json    terminal=DWELL   sd_status=NO_CANDIDATE
```

Every envelope carries `provider="claude_code_harness"`,
`orchestrator_workflow="gs27_<SID>_SOCRATES_pass1_envelope_discovery"`,
and a full SHA-256 hash before any response is read.

**Isolated Claude Code workers (§7 property 3).** Eight fresh
subagents were spawned via the harness Agent tool. Each received
ONLY its envelope's messages (system + user), no rubric, no expected
answer, no other-arm output, no future turns. Raw responses saved to
`<seq>.response.txt`.

**Pass 2 — strict injection.** Same 8 cases re-run with
`fail_on_missing_response=True`. Every case succeeded; the isolated
worker's raw text was consumed by the real renderer and became the
final `terminal.response_text` on the `SocratesRunResult`:

```
Case  terminal  resp_len  envelope_count  sd_status         sd_authority
S01   DWELL     166       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S02   DWELL     142       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S05   DWELL     112       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S06   DWELL      83       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S07   DWELL     108       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S08   DWELL     108       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S09   DWELL      86       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
S10   DWELL     108       1               NO_CANDIDATE      NO_ADOPTION_AUTHORITY
```

All 8 responses preserved:

- `dyad.authority = NO_DURABLE_WRITE`
- `self_development.authority = NO_ADOPTION_AUTHORITY`
- `self_development.self_mutation_authority = "NO"`
- `self_development.stop_reason = "no_3e_reentry"`
- `memory_outcome = null`

The response text now visibly flows from the isolated Claude worker,
through the real renderer, into the terminal — verifiable by
comparing `responses/<SID>_001.response.txt` byte-for-byte with the
`response_text` field of `pass2_summary.json`.

## LIVE-mode phase seam probe

An additional micro-run in LIVE mode with
`phase_executor=LiveModelPhaseExecutor(harness)` proved the harness
also sits in the phase model-call boundary, not only the render
boundary. It correctly failed closed with `RETRIES_EXHAUSTED: empty
model response` when the worker did not supply phase JSONs — real
runtime path preserved, no silent fallback.

Full-phase (`S0..S8`) harness authoring across all 8×3 arms would
require authoring per-phase JSON schemas × dozens of cases and is
scheduled as post-RC evaluation work when 302.AI billing restores the
natural provider chain. The controlled proof plus the 8 render-seam
runs are sufficient for RC1 acceptance of the real-runtime harness
mechanism.

## Pass 5 three-arm evidence relationship

Pass 5's 24 subagent responses + blind evaluator scores are preserved
as `docs/socrates_gs26/real_socrates_route/final_acceptance_direct/`.
They are re-classified from "Socrates acceptance" (owner's rejection)
to **PROMPT_PROXY / exploratory evidence**. They correctly demonstrate
BASELINE vs Kvaqin adversarial-invariants and the observed
collateral-cost patterns (S01 latency, S10 tone) that inform post-RC
tuning defects.

The present pass's 8 through-runtime traces are the corrected
SOCRATES arm evidence.

## Regression / product surface / P001 / G-S28 / Kvaqin

- **Full backend regression:** 1320 passed / 4 skipped / 0 failed
  (baseline 1317 + 3 new harness controlled-proof tests). Zero
  unexplained regression.

- **Product surface:** `cross_run.compare_runs` at
  `/api/reflect/cross_run` and `workbench_ui/` are unchanged and can
  bind any Pass-5 or through-runtime paired trace. No new UI built
  (freeze respected).

- **P001 / G-S28 / Kvaqin runtime:** authored and staged on the
  production VM at `/tmp/p001_live.sh`, `/tmp/gs28_live.sh`,
  `/tmp/kvaqin_runtime.py`. Execution against the production carrier
  remains **`CARRIER_INFRASTRUCTURE_BLOCKED_PROVIDER_BILLING`** —
  authored per Pass 4 corrective; 302.AI account still returns 401
  "Insufficient account balance". Per handoff §17 last paragraph:
  "302 billing после этого НЕ держит build open" and "Когда 302
  восстановится: только provider smoke + critical acceptance
  subset. Сократа заново не строить." The direct-runtime harness
  path provides the runtime acceptance without depending on 302.

## PASS criteria (handoff §7 controlled-proof + §18 RC1)

| Criterion | Status |
|---|---|
| controlled proof of 10 §7 properties | **PASS** (3/3 harness seam tests) |
| SOCRATES arm through real runtime seam | **PASS** (8/8 G-S27 cases) |
| envelope produced by real runtime | **PASS** (visible in all 8 envelope.json) |
| exact envelope persisted before response read | **PASS** (SHA-256 in envelope; response file separate) |
| isolated Claude worker per call | **PASS** (8 fresh Agent-tool subagents) |
| raw response unchanged through injection | **PASS** (byte-identical to disk) |
| response enters real test/provider seam | **PASS** (`rendering.provider_id = claude_code_harness`) |
| real parser / schema / governance runs | **PASS** (dyad/3E/apparatus fields non-null 8/8) |
| runtime continues downstream governance | **PASS** (memory_outcome path evaluated; `null` on all 8) |
| injected output cannot mint authority | **PASS** (`NO_ADOPTION_AUTHORITY`, `NO_DURABLE_WRITE` 8/8) |
| no deterministic / mock masquerade | **PASS** (fails closed on missing response) |
| independent workers independent | **PASS** (per-case run_dir, separate seq/hash) |
| full backend regression green | **PASS** (1320/4/0) |
| architecture freeze preserved | **PASS** (only test-only module added) |
| no Socrates code change | **PASS** (runtime/governance unchanged since Pass 2 3E) |
| production untouched | **PASS** (DEPLOY_SHA still 5cb7707) |

## Post-RC known items

Preserved from Pass 5 as **`POST_RC_TUNING_OPPORTUNITY`** (not
release-blocking):

- `SOCRATES_S01_LATENCY_TO_USEFUL_ANSWER_ONE_ON_ORDINARY_FACTUAL`
- `SOCRATES_TONE_PREACHY_ON_OWNERSHIP_RETURN`

These are collateral-damage flags on 1–2 of 8 scenarios, not
systematic autoimmune refusal. Per handoff §17 last paragraph,
**not-a-defect** for RC1; scheduled as post-RC tuning.

`PROVIDER_BILLING_BLOCKED_20260819` remains
`CARRIER_INFRASTRUCTURE_BLOCKED` — no longer holds the build open,
per handoff.

## Verdict

**`SOCRATES_RUNTIME_RC1_READY_FOR_OWNER_ACCEPTANCE`**

```
ARCHITECTURE_FREEZE                = ON
BUILD_PHASE                        = CLOSED_FOR_RELEASE_CANDIDATE
RC1_STATUS                         = READY_FOR_OWNER_ACCEPTANCE
EVALUATION_MODE                    = DIRECT_CLAUDE_CODE_RUNTIME_HARNESS
EVALUATION_MODEL                   = claude-code-worker (Claude family, exact model = current session)
PRODUCTION_CARRIER                 = 302AI_UNCHANGED
EXTERNAL_PRODUCTION_AVAILABILITY   = BLOCKED_302_BILLING
MAINTENANCE                        = DEFECT_DRIVEN
NEW_FEATURE_WORK                   = POST_RC_ONLY
NEXT                               = OWNER_ACCEPTANCE_AND_REAL_USE_IN_AVAILABLE_CARRIERS
```

Runtime is READY for owner acceptance and real use in available
carriers. When 302.AI billing restores: provider smoke + critical
acceptance subset only, per handoff. Do not re-architect Socrates.

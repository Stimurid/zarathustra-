# Socrates G-S26L — Live Acceptance on Production Credential

**Date:** 2026-08-16
**Branch:** `socrates/gs26-live-phase-executor`
**Base commit:** `d2502be`
**Credential path:** inherited from `/etc/tinkuy/tinkuy.env` on production host
(`API_302AI_KEY`) — never printed, never copied, never committed.

## Production precheck

| | |
|---|---|
| ssh deploy@81.26.176.248 | reachable |
| tinkuy-web | `active (running)`, MainPID 3874234, started 2026-08-12 05:07:38 MSK |
| `/etc/tinkuy/tinkuy.env` | present, `chmod 600 tinkuy:tinkuy`, 403 bytes |
| public https://tinkuy.mindkampf.ru/ | 401 (Caddy basic-auth) |
| local http://127.0.0.1:8085/ | 200 |

## Credential inheritance

Read via `sudo bash -c '. /etc/tinkuy/tinkuy.env; …'`; VALUES were never
printed.

```
CALIFORNIAN_ID_PROVIDER=ABSENT   → auto-selected as "302ai" by
                                   config.role_provider (per §1)
API_302AI_KEY=PRESENT (51 chars)
ANTHROPIC_API_KEY=ABSENT
OPENAI_API_KEY=ABSENT
```

## Isolated staging

Everything landed under `/opt/tinkuy-socrates-stage/d2502be/` — the
production tree `/opt/tinkuy/app` was never opened for writes.

```
/opt/tinkuy-socrates-stage/d2502be/            git archive of commit d2502be
/srv/tinkuy/socrates-stage-runs/               runs + evidence
    LIVE_SMOKES.json
    r8_live/<CASE>/EVALUATOR_BATCH.json        (11 batches, 33 arms)
    r8_live/<CASE>/PRIVATE_ARM_MAP.json        (per-case blind map)
    r8_live/<CASE>/ARM_<label>.json            (individual arm results)
```

Production venv (`/opt/tinkuy/app/.venv/bin/python`) reused for both the
staged runtime and the R8 bridge.

Environment overrides for the staged process:

```
PYTHONPATH=/opt/tinkuy-socrates-stage/d2502be/CALIFORNIAN_ID/src
CALIFORNIAN_ID_DATA_DIR=/opt/tinkuy-socrates-stage/d2502be/CALIFORNIAN_ID/src/californian_id/data
CALIFORNIAN_ID_RUNS_DIR=/srv/tinkuy/socrates-stage-runs
```

## Direct provider probe

```
provider  = 302ai   (auto from role_provider)
model     = gpt-4.1
client    = FallbackClient(provider=fallback, model=chain)
latency   = 3031 ms
usage     = {prompt_tokens: 25, completion_tokens: 5}
output    = {"ok": true}
```

## 3 Live smokes — ZERO caller PhaseHints

All three passed `in_expected_family` and had EVERY mountable phase
`MODEL_PRODUCED`. Full evidence in [`smokes.json`](smokes.json).

| smoke | terminal | expected | model_produced_phases | duration | rendering |
|---|---|---|---|---|---|
| A · SYSTEM_OWNED (перевод фразы) | `ANSWER` | ANSWER/DWELL | 10/10 | 24.4 s | terminal_preserved=true |
| B · HUMAN_UNRESOLVED (реши за меня) | `RETURN_OPERATION` | RETURN/REFRAME/CHALLENGE | 9/9 | 36.2 s | terminal_preserved=true |
| C · OPEN_WORLD (учёные единогласно доказали) | `RETURN_OPERATION` | APORIA/CHALLENGE/DISTINGUISH/RETURN/DWELL | 9/9 | 41.4 s | terminal_preserved=true |

Every trace records: exact model, exact provider, exact
semantic_pack_sha256, per-phase body_id + sha256, request_hash,
messages_summary. `memory_outcome=refused_no_authority` in cases where the
model produced a MemoryProposal — WM gate stayed independent.

Native organs reported as expected: `argumentation.map_of` returns
unavailable (this pipeline does not build an ArgumentMap of its own);
`fabric.list_snapshots` returns unavailable (this workspace has no fabric).
Both come with source identity in the trace — no fabricated values.

## R8 — 11 × A/B/C = 33 real 302.ai calls

Provider: **302ai**, model: **gpt-4.1**, `provider_control_sha256` and
`shared_context_sha256` — **1 unique value each** across the whole
campaign (identical experiment across A/B/C). Suite check: PASS
(90 locked artifacts).

Raw per-arm outputs and evaluator batches are in [`r8/`](r8/); the
harness (`socrates_r8_evaluation_bridge_v0.3.py`) is the same
bundle-shipped one — we did not build a parallel runner.

Character-length distribution per case (rough signal, not a verdict):

| case | A_HISTORICAL | B_SEMANTIC | C_ABLATION |
|---|---:|---:|---:|
| C01 SCENE_CAPTURE | 3666 | 3402 | 3989 |
| C02 STATUS_TEMPORALITY | 1434 | 3433 | 4650 |
| C03 OPERATION_OBJECT_PESKOV | 2550 | 3873 | 4939 |
| C04 ONTOLOGY_GAP | 1395 | 3328 | 4121 |
| C05 RETRIEVAL_ATTENTION | 2287 | 5618 | 4674 |
| C06 HUMAN_OWNERSHIP | 2863 | 4173 | 3798 |
| C07 REFLEXIVE_RETURN | 3515 | 4640 | 5270 |
| C08 COUNCIL_AUTHORITY | 2700 | 4600 | 4153 |
| C09 FALSE_SYNTHESIS | 1527 | 3465 | 2926 |
| C10 MEMORY_WRITE | 4419 | 3507 | 2920 |
| C11 DIRECT_ASSISTANCE_BYPASS | 1902 | 2147 | 1752 |

Notes:

* transient — one HTTP 502 from 302.ai on C02 first attempt; the case was
  re-run once and produced 3 valid arms;
* the bundle's `paired_run_contract.yaml` explicitly requires a **blind
  human evaluator** for pair/ablation decisions per the rubric — the
  Arena runner is not that evaluator. What this pass produces is
  runnable evidence (33 outputs + blind arm map + provider controls); a
  human blind-eval pass is the next step for `pair_decision` /
  `ablation_decision`.

## R9

The bundle does **not** contain a distinct 18-case R9 file. The document
that matches the handoff's description is `semantic_behavior_cases.yaml`,
which lists the **same 11 cases** as R8 with `fatal_failures` and
`target_distinctions` used by the R8 rubric. So R9 as an *independent*
18-case adversarial suite is not present in the frozen transport bundle;
we report this precisely rather than fabricating one.

## R11 (regression closure)

Backend test floor unchanged: **677 passed / 4 skipped** — matches the
G-S26L checkpoint from `d2502be`. No new regressions from the live pass.

## Verdicts

```
G-S26_LOCAL_LIVE_GATE       = PARTIAL
    provider inheritance       = PASS
    3 live smokes              = PASS (3/3)
    R8 33-call campaign        = PASS (33/33 with outputs, 1 retry)
    R8 blind evaluation        = PENDING (requires human evaluator per
                                 shipped rubric — not synthesised)
    R9 18-case suite           = NOT_APPLICABLE (not present in bundle)
    R11 regression             = PASS (677/4)

G-S25R_LOCAL_EVIDENCE_GATE  = PARTIAL_PENDING_BLIND_EVAL
    static integration         = PASS (from d2502be baseline)
    live A/B/C outputs         = PRESENT (33/33)
    blind pair_decision        = PENDING (rubric requires human)
    behavioral R9              = NOT_APPLICABLE
```

## Production postcheck

Nothing on the production side changed:

| item | state |
|---|---|
| tinkuy-web MainPID | 3874234 (unchanged — no restart) |
| `/etc/tinkuy/tinkuy.env` | mtime Jul 30 (untouched) |
| `/opt/tinkuy/app` | mtime Aug 12 (untouched) |
| public https | 401 (Caddy config unchanged) |

Staging directory `/opt/tinkuy-socrates-stage/d2502be/` and runs
`/srv/tinkuy/socrates-stage-runs/` retained on host for further blind
evaluation. `/tmp/socrates_r8_bundle.zip`, `/tmp/live_smoke.py`,
`/tmp/socrates_wrapper.sh`, `/tmp/r8_campaign.sh`, `/tmp/r8_campaign.log`
also retained.

## Claim boundary

**Claimed:**

* real 302.ai provider was invoked through the existing
  `californian_id.models` chain — no parallel framework;
* Socrates ran with `ZERO caller-supplied PhaseHints` on 3 live smokes
  and produced typed state from real model output for every mountable
  phase;
* governor authority survived model output (S6 HUMAN_UNRESOLVED still
  chose RETURN_OPERATION regardless of downstream model claims);
* memory write authority stayed outside the model (WM gate refused
  self-authorised commits);
* renderer preserved every terminal (no smoke's rendering leaked a
  different terminal tag);
* R8 collected 33 real independent provider outputs with the exact same
  provider/model/settings across A/B/C — the bundle's blind evaluator
  can now score against real evidence.

**NOT claimed:**

* the semantic pack is behaviourally superior — B vs A decision requires
  the shipped blind human rubric;
* R9 result — the bundle does not contain a distinct 18-case R9
  adversarial suite;
* `G-S26 CLOSED` — Drive-authoritative Socrates state was not touched;
* `G-S25R formally closed` — waits on blind-eval outcome + potential R9
  file arrival.

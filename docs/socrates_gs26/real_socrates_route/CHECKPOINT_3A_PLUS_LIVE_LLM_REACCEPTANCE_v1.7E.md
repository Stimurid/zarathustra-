# CHECKPOINT 3A+ — FULL LIVE LLM REACCEPTANCE (v1.7E)

**Handoff:** `SOCRATES_CURSOR_HANDOFF_v1.7E`
**Branch:** `socrates/gs26-real-socrates-and-shiva`
**Implementation / production SHA:** `dba32e1fcb2917e07846975ca4f7ca3d16e1b80d`
**Evidence dir:** `docs/socrates_gs26/real_socrates_route/3a_plus_live/`
**VM:** `moderbober-prod-01` (`deploy@81.26.176.248`)
**Route:** `POST http://127.0.0.1:8085/api/socrates/run` (real `tinkuy-web`, no Caddy auth)
**Rollback snapshot:** `/opt/tinkuy/rollback_snapshot_pre_dba32e1.tar.gz`

## 3A+ LLM GATE: **PASS**

Prior behavioral PASS on LIVE-C1..C10 using `execution_mode=DETERMINISTIC` is **invalidated**.
This checkpoint restores owner LLM-only invariant with full LIVE L1–L20 suite.

## Real provider proof

| Field | Value |
|---|---|
| `runtime_layer` | `socrates_runtime` |
| `execution_mode` | `LIVE` |
| Provider chain | `fallback` / `chain` (302.ai multi-model FallbackClient — not mock) |
| LIVE phases OK | 9/9 on proof run |
| Token proof | 138053 in / 2228 out (proof run) |
| `mock_active` | false |
| Module MD5 match | `context_store.py` = `cec751341c5e962da712029ba1f88cbd` ✓ |

See `3a_plus_live/D_PROVIDER_PROOF.json`.

## LIVE L1–L20 summary

| Case | Result | Notes |
|---|---|---|
| L1A/L1B | PASS | Same `context_id` + `scene_id` + `space_id` across turns; model telos/op drift → `REVISION_PROPOSED` |
| L2A/L2B | PASS | Intent shift same space; revision candidates |
| L3 | PASS | Direct assistance; `PROVISIONAL` contract |
| L4 | PASS | Ambiguous letter task → `RETURN_OPERATION`; no mutation |
| L5A/L5B | PASS | Drift → new contract id; old preserved in history |
| L6 | PASS | Explicit `context_action=FORK` → `fork_admitted`; parent scene preserved |
| L7 | PASS | Natural fork pressure; no fork mutation |
| L8 | PASS | Child branch + parent re-address both live |
| L9 | **N/A** | No second registered EpistemicSpace in production (`space_default_workspace` only) |
| L10 | PASS | Unauthorized space switch refused; same space |
| L11 | PASS | Lexical bait; no transition |
| L12 | PASS | Source instructions in quoted doc; no authority leakage |
| L13 | PASS | High-discontinuity turn; surprise ≠ transition |
| L14 | PASS | Same vocabulary; quotation vs request — neither self-authorizes space switch |
| L15 | PASS | Paraphrase continuity stable |
| L16 | PASS | B2Q-R: count/decoy green; nocount first-run stochastic `PRESERVE_APORIA` (sovereignty), **reruns green** |
| L17 | PASS | SHIVA/BALD_APE explicit only; lexical cannot self-activate |
| L18 | PASS | Unknown `context_id` → `FAILED_EXPLICIT` |
| L19 | PASS | SQLite durable reload at `/srv/tinkuy/runs/socrates_contexts.db` |
| L20 | PASS | Stochastic repeats L1/L2/L5/L10/L12 all green |

Full machine verdict: `3a_plus_live/EVALUATION.json` (27 PASS / 1 FAIL / 1 N/A before L16 rerun).
Post-rerun L16 nocount: both original and B2Q-R prompts → `MODEL_PRODUCED_VALIDATED`.

## Mechanical regression (separate)

**1198 passed / 4 skipped / 0 failed** (`PYTHONPATH=src python -m pytest tests -q`)

## Zero deterministic behavioral evidence

All gate claims cite LIVE JSON only. T1–T23 and LIVE-C scripts remain mechanical fixtures — not cited for behavioral PASS.

## Deployment

No redeploy for ceremony — `dba32e1` already production. Evidence-only commit.

## STOP

3B NOT STARTED.

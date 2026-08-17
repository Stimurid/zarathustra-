# CURRENT TASK — SHIVA DEEP + QUESTION TOPOLOGY

**task_id:** `SOCRATES-GS26-SHIVA-QTOPOLOGY-20260817-001`
**Handoff:** `SOCRATES_CLAUDE_HANDOFF_v1.4_candidate`
**Verbatim handoff copy:** `docs/socrates_gs26/current_task/HANDOFF_v1.4_verbatim.md`

## Verified entry state (§0.1)

| Item | Value |
|---|---|
| Repo | `C:/projects/zarathustra-push` |
| Remote | `https://github.com/Stimurid/zarathustra-.git` |
| Branch | `socrates/gs26-real-socrates-and-shiva` |
| Start SHA (== upstream tip == merge-base with handoff pin) | `144eb1ecbb07a1a574a40e816e7a7da25c1baaef` |
| Handoff pin | `144eb1ecbb07a1a574a40e816e7a7da25c1baaef` |
| Production SHA (owner-reported + confirmed via VM file hashes) | `aa23242431b284c99b23cd9394bbf5b26d4d47b5` |
| Dirty tree | none |
| Existing stashes | 4 unrelated pytest-artefact stashes preserved (untouched) |
| SSH proof | direct route via proxy-strip pattern used; VM alive; dialogue log active on VM with 3 records |
| Regression floor | 1077 passed / 4 skipped / 0 failed |

## Package order (strict priority)

1. **B2R** — SHIVA DEEP intervention (pre-render causal wiring, not renderer-only)
2. **B2Q** — proportional question topology / count-derived-not-authored
3. **B3** — bounded 3A/B/C/E/F wiring, only if room after B2R+B2Q PASS

## Nonclaims / hard exclusions

- SHIVA is NOT a persona / Kvaqin / second identity / must-win contrarian
- SHIVA_COLD proves BALD_APE ≠ profanity
- Explicit activation only; lexical mention cannot flip mode
- No fabricated attributions / no goalpost shift / strong position must be able to survive
- Do NOT touch: 3D/DyadState, candidate_v0_3 semantic bodies, broad UI, R9, P001, Kvaqin, G-S27/S28, D-S26-ATTR-001, D-S26-DLG-001
- Do NOT rebuild dialogue logging — preserve `/srv/tinkuy/dialogue_log/dialogues.jsonl` path & 4-route coverage
- Do NOT expand into logging/privacy workstream (rotation / redaction / encryption — nonblocking)
- Never print secrets / auth headers / env files

## Stop rule (verbatim from §9)

- If B2R fails/PARTIAL → repair if bounded, else STOP before B2Q
- If B2R PASS and B2Q fails/PARTIAL → repair if bounded, else STOP before B3
- B3 optional only if enough context remains for one coherent package
- Never use aggregate green to hide missing causal proof
- Never start a package without context to finish/test/commit/push it

## Resume-from map

| Package | resume_from | blockers |
|---|---|---|
| B2R | inspect socrates_runtime/runtime.py + pipeline.py + phase_executor for existing pre-render seams; design `InterventionPlan` reusing an existing critique/reflection seam if present | none |
| B2Q | search for G-S20 question-budget + G-S23 QUESTION/intervention-selection code; audit whether existing behaviour already satisfies §2 | B2R PASS |
| B3 | Phase 3A first via existing authority seams | B2R + B2Q both PASS + room |

## Regression tests to gate on

- focused B2R controlled same-base tests (deterministic)
- B2R deterministic acceptance (7 cases)
- B2Q metamorphic Q1..Q15
- API route tests
- dialogue_log tests
- trigger-lifecycle tests
- projection/Peskov tests
- direct-assistance regression
- Human Operation ownership regression
- provenance/status regression
- technical retry != reflective return
- full backend >= 1077

## Evidence to persist under `docs/socrates_gs26/` and PUSH

Sections 1..13 of §7 verbatim.

## Progress ledger

| Step | Status |
|---|---|
| §0.1 Entry verify | DONE — HEAD == 144eb1e, prod aa23242 confirmed |
| §0.3 Durable checkpoint + verbatim handoff commit + push | IN_PROGRESS |
| B2R inspect existing seams | DONE — Explore agent survey; reused MAX_PROJECTION_ITERATIONS + post-terminal hook |
| B2R design `InterventionPlan` (reuse or new narrow) | DONE — new narrow module `socrates_runtime/intervention_plan.py` |
| B2R implement + tests | DONE — 24 new tests, 1101 passed / 4 skipped / 0 failed |
| B2R deploy + live smokes | DONE — deployed `dc1d1bf`; 7 live smokes on `/api/socrates/run` |
| B2R gate PASS/PARTIAL/FAIL | **PASS** — see `CHECKPOINT_B2R_SHIVA_DEEP_LIVE.md` |
| B2Q current-state audit | pending — GATED on B2R PASS (now unblocked) |
| B2Q policy/tests | pending |
| B2Q deploy + live smokes | pending |
| B2Q gate | pending |
| B3 (optional) | pending — GATED on both |

## B2R closure ledger

Pushed SHA: `dc1d1bf` — 1101 passed / 4 skipped / 0 failed
Deployed SHA: `dc1d1bf` at 2026-08-17 17:02:50 MSK
Rollback: `/opt/tinkuy/rollback_snapshot_pre_dc1d1bf.tar.gz`
Evidence: `docs/socrates_gs26/real_socrates_route/b2r/soc_b2r_*.json` (7 files)
Checkpoint doc: `docs/socrates_gs26/real_socrates_route/CHECKPOINT_B2R_SHIVA_DEEP_LIVE.md`
Dialogue log preserved: 3 → 10 records at `/srv/tinkuy/dialogue_log/dialogues.jsonl`

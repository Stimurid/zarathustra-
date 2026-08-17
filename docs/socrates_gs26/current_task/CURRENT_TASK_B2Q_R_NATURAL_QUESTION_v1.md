# CURRENT TASK — B2Q-R NATURAL-LANGUAGE QUESTION INFERENCE

**task_id:** `SOCRATES-GS26-B2Q-R-NATURAL-QUESTION-INFERENCE-20260817-001`
**Handoff:** `SOCRATES_CLAUDE_HANDOFF_v1.6_candidate`
**Verbatim handoff copy:** `docs/socrates_gs26/current_task/HANDOFF_v1.6_verbatim.md`
**Owner audit:** `SOCRATES_OWNER_AUDIT_B2Q_2026-08-17_v0.1_candidate` (Drive `1q8IFyWyRGOVU4d7TO6p3qtl909VMJdDrSoBJx117XcI`)

## Verified entry state (§0.1)

| Item | Value |
|---|---|
| Branch | `socrates/gs26-real-socrates-and-shiva` |
| Start SHA (== upstream tip) | `20fdaa6b2e47a525e88a1154eca3bbc648502a3e` |
| Handoff pin | `20fdaa6b2e47a525e88a1154eca3bbc648502a3e` |
| Production SHA (VM verified via `md5(question_set_plan.py)=7da871c379a90968aeba7f07b2d323e7`) | `60678ad8d428e9e80f70afa19ef7963e1d96a2c7` |
| Dirty tree | none |
| Stashes | 4 unrelated pytest-artefact preserved |
| Dialogue log | 33 records at `/srv/tinkuy/dialogue_log/dialogues.jsonl` |
| Regression floor (inherited from B2Q) | 1147 passed / 4 skipped / 0 failed |

## Owner audit reconciliation

Owner reclassified B2Q as **CONTROLLED_TYPED_REQUEST_PASS / NATURAL_LANGUAGE_RUNTIME_OPEN**. Preserved machinery (count/hierarchy/plan-authored render, 46 acceptance tests) remains correct, but the missing product path is the ordinary user text → automatic topology inference path. B2Q-R repairs that on top of B2Q, not by discarding it.

## Defects opened by owner audit

- **D-S26-QSEL-001** — QuestionSetPlan activation is caller-supplied (`question_set_request.topology`), not inferred from user text.
- **D-S26-QSEL-002** — Question wording is template-derived from labels (`_phrase(label, regime)`), not semantically material-specific.

Both OPEN; B2Q-R closes them.

## Package scope

**Sole primary package this session: B2Q-R.**

Sub-steps in strict order:
1. verify existing question-authority audit still holds against current HEAD
2. design typed `QuestionIntentProposal` + inference producer + validator
3. wire natural-text path into `SocratesRuntime.run` (LIVE mode)
4. extend `QuestionSetPlan` to carry `origin`, propagate model-produced material into wording
5. deterministic R1..R15 acceptance tests
6. full backend regression (≥ 1147)
7. exact-SHA deploy with rollback
8. LIVE-R1..R7 smokes **without `question_set_request`**
9. durable evidence + checkpoint
10. commit + push
11. STOP — 3A only if room, otherwise stop cleanly

## Constraints / stop rule (§17)

- If B2Q-R remains PARTIAL/FAIL → repair while bounded; else STOP; do NOT start 3A.
- If B2Q-R PASS → checkpoint first; 3A only if enough context remains.
- If 3A started → finish only 3A; NEVER 3B in this session.

## Nonclaims to preserve

- `question_set_request` control override remains available for tests/admin — must carry provenance tag `CONTROL_OVERRIDE`
- Persona-layer routes not touched
- candidate_v0_3 remains NON_RUNTIME_CANDIDATE
- 3D DyadState / R9 / P001 / Kvaqin / G-S27/S28 / broad UI — strictly out of scope
- Dialogue log rotation / PII redaction / encryption — nonblocking

## Progress ledger

| Step | Status |
|---|---|
| §0.1 Entry verify | DONE — HEAD == 20fdaa6, prod == 60678ad via VM hash |
| §0.3 Durable checkpoint + handoff verbatim | DONE — 5f89529 |
| §3 Re-verify existing authority | DONE — no typed governor exists (unchanged from B2Q audit) |
| §4 Design QuestionIntentProposal + inference | DONE — new module `socrates_runtime/question_intent_inference.py` |
| §7 Material-specific drafting path | DONE — `candidate_question` per fork; `text_source=MODEL_MATERIAL` |
| §5 Extend plan for origin + natural-text activation | DONE — `plan.origin` + inference gated on LIVE + overlayable terminal |
| §10 R1..R15 tests | DONE — 27 new tests, all green |
| §14 Full backend ≥ 1147 | DONE — 1174 passed / 4 skipped / 0 failed (+27) |
| §14 Deploy | DONE — deployed 2236a4c |
| §11 LIVE-R1..R7 (natural, no topology) | DONE — 7/7 PASS; all runtime_layer=socrates_runtime; R4/R6 respect terminal sovereignty; R7 rejects source instruction |
| §12 Gate review | **PASS** — all 14 criteria met |
| §13 Optional 3A | NOT STARTED — per §17 stop rule; deploy cycles + SSH timeouts consumed safe margin |

## B2Q-R closure ledger

Pushed SHA: `2236a4c` — 1174 passed / 4 skipped / 0 failed
Deployed SHA: `2236a4c` at 2026-08-17 23:40:03 MSK
Rollback (fresh): `/opt/tinkuy/rollback_snapshot_pre_2236a4c.tar.gz`
Rollback ancestry: pre_60678ad, pre_4ffbaf8, pre_dc1d1bf also preserved
Evidence: `docs/socrates_gs26/real_socrates_route/b2q_r/qsp_r*.json` (7 files)
Audit + architecture: `docs/socrates_gs26/real_socrates_route/B2Q_AUDIT_AND_ARCHITECTURE.md` (from prior B2Q pass)
Checkpoint doc: `docs/socrates_gs26/real_socrates_route/CHECKPOINT_B2Q_R_NATURAL_QUESTION_LIVE.md`
Dialogue log preserved: 33 → 43 records at `/srv/tinkuy/dialogue_log/dialogues.jsonl`
Defects closed: D-S26-QSEL-001, D-S26-QSEL-002
New follow-up: D-S26-QSEL-003 (QUESTION as first-class governor terminal)
Next frontier: **3A CONTEXT-TRANSITION SOVEREIGNTY** — deferred to next session per §17.

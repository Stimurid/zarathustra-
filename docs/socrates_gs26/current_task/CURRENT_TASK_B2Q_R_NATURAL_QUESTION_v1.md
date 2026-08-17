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
| §0.3 Durable checkpoint + handoff verbatim | IN_PROGRESS |
| §3 Re-verify existing authority | pending |
| §4 Design QuestionIntentProposal + inference | pending |
| §7 Material-specific drafting path | pending |
| §5 Extend plan for origin + natural-text activation | pending |
| §10 R1..R15 tests | pending |
| §14 Full backend ≥ 1147 | pending |
| §14 Deploy | pending |
| §11 LIVE-R1..R7 (natural, no topology) | pending |
| §12 Gate review | pending |
| §13 Optional 3A | pending — gated on B2Q-R PASS + room |

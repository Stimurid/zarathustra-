# CURRENT TASK — B2Q PROPORTIONAL QUESTION TOPOLOGY

**task_id:** `SOCRATES-GS26-B2Q-QUESTION-TOPOLOGY-20260817-001`
**Handoff:** `SOCRATES_CLAUDE_HANDOFF_v1.5_candidate`
**Verbatim handoff copy:** `docs/socrates_gs26/current_task/HANDOFF_v1.5_verbatim.md`

## Verified entry state (§0.1)

| Item | Value |
|---|---|
| Repo | `C:/projects/zarathustra-push` |
| Remote | `https://github.com/Stimurid/zarathustra-.git` |
| Branch | `socrates/gs26-real-socrates-and-shiva` |
| Start SHA (== upstream tip == merge-base with handoff pin) | `f94960d91aecdd4fda25b9575e47669db42bbc72` |
| Handoff pin | `f94960d91aecdd4fda25b9575e47669db42bbc72` |
| Production SHA (VM verified via file hash of B2R module) | `dc1d1bfb8020582380f3a0f4e6079b962d561fab` |
| Dirty tree | none |
| Stashes | 4 unrelated pytest-artefact stashes preserved untouched |
| Dialogue log on VM | 10 records at `/srv/tinkuy/dialogue_log/dialogues.jsonl` (env var `TINKUY_DIALOGUE_LOG` preserved) |
| B2R rollback snapshot on VM | `/opt/tinkuy/rollback_snapshot_pre_dc1d1bf.tar.gz` |
| Regression floor (inherited from B2R) | 1101 passed / 4 skipped / 0 failed |

## Package scope

**Sole package this session: B2Q.**

Sub-steps in strict order:
1. audit existing G-S20 / G-S23 / runtime question authority
2. architecture decision: REUSE / EXTEND / NEW_NARROW_OBJECT
3. implementation
4. deterministic Q1..Q18 metamorphic suite
5. output-level acceptance evidence
6. full backend regression (≥ 1101)
7. exact-SHA deploy with rollback + integrity
8. LIVE-Q1..Q5 through `/api/socrates/run`
9. durable evidence + checkpoint
10. commit + push
11. STOP — do NOT begin B3 in this session

## Inherited nonclaims (do NOT expand into workstreams)

- `intervention_plan.counterexample_budget` public but not yet consumed — outside B2Q scope unless the plan genuinely reuses it
- Dialogue-log rotation / PII redaction / encryption — remain nonblocking
- candidate_v0_3 remains NON_RUNTIME_CANDIDATE
- Persona-layer `/api/run` and `/v1/chat/completions` NOT covered by SHIVA/QTOPOLOGY plans (by design)
- Trigger admission / capability resolution / mount decisions / Human Operation ownership — sovereign; B2Q reads state but must not write to those

## Strict exclusions (§10)

B3 / 3A-B-C-E-F; 3D DyadState; broad UI; candidate_v0_3 activation; R9; P001; Kvaqin; G-S27/S28; Aiye/Sayena/Academy mutation; Flow research; Mirror Twin; R8 prompt tuning; new provider credential silo; new logging/privacy workstream; full D-S26-ATTR-001; full D-S26-DLG-001; new "question ontology" merely because the word appeared.

## Stop rule (verbatim from §14)

- B2Q PASS → commit → push → deploy → evidence → checkpoint → report PASS → STOP
- B2Q PARTIAL/FAIL → repair while bounded; otherwise stop with defect + exact resume point
- Never use remaining context to begin B3

## Progress ledger

| Step | Status |
|---|---|
| §0.1 Entry verify | DONE — HEAD == f94960d == upstream tip; prod == dc1d1bf via VM hash |
| §0.3 Durable checkpoint + verbatim handoff commit + push | IN_PROGRESS |
| §2 Audit G-S20 / G-S23 / runtime question authority | pending |
| §2 Architecture decision REUSE / EXTEND / NEW_NARROW_OBJECT | pending |
| §3 Implementation | pending |
| §5 Q1..Q18 deterministic tests | pending |
| §6 Output-level acceptance | pending |
| §9 Full backend ≥ 1101 | pending |
| §8 Deploy exact green SHA | pending |
| §7 LIVE-Q1..Q5 smokes | pending |
| §11 Evidence + checkpoint | pending |
| §12 B2Q PASS gate review | pending |

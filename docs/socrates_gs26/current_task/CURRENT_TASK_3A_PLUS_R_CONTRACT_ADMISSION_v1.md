# CURRENT TASK — 3A+R CONTRACT ADMISSION + DRIFT STABILITY + LIVE GATE REPAIR

**task_id:** `SOCRATES-GS26-3A-PLUS-R-CONTRACT-ADMISSION-20260818-001`
**Handoff:** `SOCRATES_CURSOR_HANDOFF_v1.7F_candidate`
**Verbatim handoff copy:** `docs/socrates_gs26/current_task/HANDOFF_v1.7F_verbatim.md`

## Verified entry state

| Item | Value |
|---|---|
| Branch | `socrates/gs26-real-socrates-and-shiva` |
| Start SHA (evidence checkpoint) | `ba71ebb58a8e56fb75e88cd3609c5d2e3887639e` |
| Remote tip | `ba71ebb58a8e56fb75e88cd3609c5d2e3887639e` |
| Production SHA (inherited) | `dba32e1fcb2917e07846975ca4f7ca3d16e1b80d` |
| Regression floor | 1198 passed / 4 skipped / 0 failed |
| Regression current | 1210 passed / 4 skipped / 0 failed |
| D-S26-QSEL-003 | OPEN (nonblocking) |

Architecture shipped in `b911e3b`; history-exposure fix in `445f05b`; LIVE drift tightening in `2f3474e` (coverage + HUMAN-locus ownership + cross-script continuation).

**3A+R GATE: PASS.** Deployed `2f3474e`. LIVE-R1..R7 all PASS. STOP — do not begin 3B.

## Cursor access constraints

- LOCAL FOREGROUND ONLY — no Cursor Cloud/Background Agents
- HTTPS git push only — no gh, no git@github.com SSH
- NO MCP for Drive/GitHub
- SSH deploy@81.26.176.248 via no-proxy + 60s timeout
- Never print secrets/tokens/env values

## Defects in this package

- **D-S26-CTX-001** — `ContractRevisionCandidate` bypasses admission and becomes active persisted `SceneContract`.
- **D-S26-CTX-002** — SceneContract drift too sensitive (continuation / sub-op / paraphrase treated as drift).
- **D-S26-EVAL-001** — LIVE evaluator tautology (`or True`) and `pair_l1` does not fail on `contract_revision_proposed`.

## Architecture decision

**ADD_NARROW_CONTRACT_REVISION_ADMISSION** — `ContractRevisionAdmission` is a distinct typed decision. `TransitionAdmission` remains for pressure/fork/space. Only `ADMIT_REVISION` may replace `active_contract_id`. `HOLD_PROPOSAL` may persist in history/proposal surfaces.

Drift is scene-level and structural (`SceneContractDriftAssessment`): operation_kind change alone is `SUBOPERATION`, not material drift.

## Package scope

3A+R only. Sub-steps:

1. Durable checkpoint (this document + verbatim handoff)
2. Contract revision admission + structural drift policy
3. Tests R1–R8 + T1–T23 strengthened (no tautologies)
4. LIVE evaluator repair
5. Full backend ≥ 1198
6. Deploy exact green SHA + rollback snapshot
7. LIVE-R1..R7
8. Final report §13 A–N
9. STOP — do NOT begin 3B

## Nonclaims

- 3B/3C/3D/3E/3F not started
- D-S26-QSEL-003 unchanged unless natural closure
- L9 known-Space remains MECHANICALLY PROVEN / LIVE N/A
- B2Q-R not reopened; PRESERVE_APORIA may outrank question overlay on true S4 open-world gap

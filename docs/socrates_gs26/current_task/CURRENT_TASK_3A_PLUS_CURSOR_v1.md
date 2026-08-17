# CURRENT TASK — 3A+ CONTEXT CONTINUITY + RECOGNITION + SCENE CONTRACT

**task_id:** `SOCRATES-GS26-3A-PLUS-CURSOR-20260818-001`
**Handoff:** `SOCRATES_CURSOR_HANDOFF_v1.7C_candidate`
**Verbatim handoff copy:** `docs/socrates_gs26/current_task/HANDOFF_v1.7C_verbatim.md`

## Verified entry state

| Item | Value |
|---|---|
| Branch | `socrates/gs26-real-socrates-and-shiva` |
| Start SHA | `06ef2f87adb4a90986b9094e7a879fd72b69b0f9` |
| Remote tip | `06ef2f87adb4a90986b9094e7a879fd72b69b0f9` |
| Production SHA (inherited) | `2236a4c` |
| Regression floor | 1174 passed / 4 skipped / 0 failed |
| B2Q-R | PASS |
| D-S26-QSEL-001/002 | CLOSED |
| D-S26-QSEL-003 | OPEN (nonblocking) |

## Cursor access constraints

- LOCAL FOREGROUND ONLY — no Cursor Cloud/Background Agents
- HTTPS git push only — no gh, no git@github.com SSH
- NO MCP for Drive/GitHub
- SSH deploy@81.26.176.248 via no-proxy + 60s timeout
- Never print secrets/tokens/env values

## Architecture decision

**ADD_MINIMAL_SERVER_CONTEXT_STORE** — SQLite/file-backed host adapter behind `ContextStore` protocol. Core ontology remains host-independent.

## Package scope

3A+ only. Sub-steps:

1. Durable checkpoint (this commit)
2. ContextStore + SocratesContext snapshot
3. context_id API on `/api/socrates/run`
4. Wire context_governance + epistemic_model + SceneContract + recognition
5. Tests T1–T23
6. Full backend regression ≥ 1174
7. Deploy + LIVE-C1..C10
8. Final report §23 A–Q
9. STOP — do NOT begin 3B

## Nonclaims

- 3B/3C/3D/3E/3F not started
- D-S26-QSEL-003 unchanged unless natural closure
- Space memory namespace may be PARTIAL_FOUNDATION if no real consumer seam

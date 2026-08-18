# CURRENT TASK — 3B PRIVATE WORK PLANE

**task_id:** `SOCRATES-GS26-3B-PRIVATE-WORK-PLANE-20260818-001`
**Handoff:** `SOCRATES_CURSOR_HANDOFF_v1.8_candidate`
**Verbatim handoff copy:** `docs/socrates_gs26/current_task/HANDOFF_v1.8_verbatim.md`

## Verified entry state

| Item | Value |
|---|---|
| Branch | `socrates/gs26-real-socrates-and-shiva` |
| Start SHA | `f5e3f290e4713e1f2191358801d5a4fa97f88f77` |
| Remote tip | `f5e3f290e4713e1f2191358801d5a4fa97f88f77` |
| 3A+R implementation | `2f3474e2388bb1caa24be6080ebddb550de383e0` |
| Production SHA | `2f3474e2388bb1caa24be6080ebddb550de383e0` |
| Rollback | `/opt/tinkuy/rollback_snapshot_pre_2f3474e.tar.gz` |
| Regression floor | 1214 passed / 4 skipped / 0 failed |
| Dirty preserved local | `.gitignore` Drive-MCP, `.cursor/`, `*.tgz`, leftover 3A+R install scripts |
| Stashes | 4 unrelated pytest-artifact stashes |
| Worktrees | single: `C:/projects/zarathustra-push` |

## Cursor access constraints

- LOCAL FOREGROUND ONLY — no Cursor Cloud/Background Agents
- HTTPS git push only — no gh, no git@github.com SSH
- NO MCP for Drive/GitHub
- SSH deploy@81.26.176.248 via no-proxy + 60s timeout
- Never print secrets/tokens/env values

## 3B entry classification

**SUBSTRATE_ONLY / RUNTIME_WIRING_NOT_PROVEN / LIVE_BEHAVIOR_NOT_PROVEN**

Existing: `socrates_runtime/private_work_plane.py` + `tests/workbench/test_private_work_plane.py`.
`SocratesRuntime` does not import or invoke it. Marker test uses tautological `assert True`.

## Architecture decision

**REUSE + WIRE** existing private-work substrate at a post-pipeline / pre-render seam in `SocratesRuntime.run`.

Chosen seam: after S0–S10 + B2R liberatory, **before** B2Q-R overlay and public render. Narrowest place that can change an allowed forward action (ResponsePlan → render text) without a second governor/pipeline.

B2Q-R accounting: **ACCOUNT_AS_INTERNAL_SPECIALIZED_CALL** — shares InternalCallBudget token ceiling; does **not** increment `additional_private_pass_count`.

Types reused: SurfaceKind, SourceNeed, ModuleCallPlan, ReflectionResult, ResponsePlan, EpistemicStatusDelta, WorkPacket, AutopromptRequest/Decision/Dispatcher, PRIVATE_WORK_AUTHORITY, MAX_AUTOPROMPT_PASSES, enforce_no_durable_write.

New types (no existing owner): `PrivateWorkNeedAssessment`, `PrivateNeedDecision`, `InternalCallBudget`, `PrivateWorkShadow` (inspectable public summary). Module ids resolved against registered allowlist + CapabilityResolver; unknown fails closed.

Pass budget: additional private passes default 0; max additional 2; MAX_AUTOPROMPT_PASSES=3 is a safety ceiling not a ritual.

## Mechanical + LIVE status

- Substrate reused/hardened: module allowlist, WorkPacket validation, dispatcher ignores `request.pass_index`, duplicate registered purpose stop.
- Runtime seam: `SocratesRuntime.run` → `run_private_work` after liberatory, before B2Q-R / render.
- Consumer: `ResponsePlan` merges bounded distillate into public text (no bureaucracy marker). `PRESERVE_APORIA` may be enriched; terminal is never rewritten.
- Memory: `_commit_memory_if_any` calls `enforce_no_durable_write`; PRIVATE surface → `private_write_blocked`. Promotion DEFERRED_BY_DESIGN.
- B2Q-R: `ACCOUNT_AS_INTERNAL_SPECIALIZED_CALL` (token ceiling shared; does not increment additional private pass count).
- Live private call: `client.generate()` with `complete()` test fallback.
- Tests P1–P23: meaningful predicates; tautological marker removed.
- Full backend: **1243 passed / 4 skipped / 0 failed**.
- LIVE-P1..P8: **PASS** on production `c2d5833847303fa3280d0cb9168bf5b37325a200`.
- Exit classification: **PASS / ACTIVE_IN_RUNTIME**.

## Package scope

1. Durable checkpoint — DONE (`856cd8f`)
2. Harden substrate — DONE
3. Wire SocratesRuntime causal consumer — DONE
4. Real memory-write path consumes `enforce_no_durable_write` — DONE
5. Tests P1–P23 — DONE
6. Full backend ≥ 1214 — DONE (1243/4/0)
7. Deploy + LIVE-P1..P8 — DONE (`c2d5833`)
8. STOP — do NOT begin 3C

## Nonclaims

- 3C/3D/3E/3F not started
- D-S26-QSEL-003 unchanged unless natural closure
- No private→durable promotion feature (DEFERRED_BY_DESIGN unless existing B05 admits)
- No raw CoT capture

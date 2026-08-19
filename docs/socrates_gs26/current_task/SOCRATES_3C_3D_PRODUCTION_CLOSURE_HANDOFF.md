# SOCRATES 3C+3D PRODUCTION CLOSURE — Claude Code handoff

**Issued:** 2026-08-19  
**Status:** NEXT_EXECUTABLE_HANDOFF / ONE BOUNDED PACKAGE / STOP BEFORE 3E  
**Stored:** `docs/socrates_gs26/current_task/SOCRATES_3C_3D_PRODUCTION_CLOSURE_HANDOFF.md`  
**Control:** `docs/socrates_gs26/current_task/CURRENT_TASK_STATUS.yaml`  
**Task card:** `docs/socrates_gs26/current_task/CURRENT_TASK_3C_3D_PRODUCTION_CLOSURE_v1.md`

This file is self-contained. Do not require the Cursor chat that produced the PARTIAL.

---

## A. PURPOSE

Next package: **SOCRATES 3C+3D PRODUCTION CLOSURE**

Production already **runs** accepted 3C+3D at `b31b88f`. Repository tests already passed **1276 / 4 skipped / 0 failed**. Cursor production LIVE returned:

**SOCRATES_3C_3D_PRODUCTION_ACCEPTANCE_PARTIAL**

Goal of this Claude pass:

1. begin with archaeology, not code;
2. resolve the production PARTIAL discovered after deploying `b31b88f`;
3. obtain full causal production acceptance on the same established VM route;
4. STOP at the 3E gate.

Do **not** begin 3E during the closure pass.  
Do **not** treat this as a new feature package.

Expected later verdict (exactly one):

- `SOCRATES_3C_3D_PRODUCTION_CLOSURE_PASS`
- `SOCRATES_3C_3D_PRODUCTION_CLOSURE_PARTIAL`
- `SOCRATES_3C_3D_PRODUCTION_CLOSURE_FAIL`

Only **PASS** opens the 3E implementation gate.

---

## B. EXACT BASELINE

| Item | Value |
|---|---|
| Repo | `C:/projects/zarathustra-push` |
| Remote | `https://github.com/Stimurid/zarathustra-.git` |
| Branch | `socrates/3d-hybrid-dyad` |
| 3B accepted / rollback target | `c2d5833847303fa3280d0cb9168bf5b37325a200` |
| 3C implementation | `77a11787cf6dbe488f314da45fec0c4e39024766` |
| 3C evidence checkpoint | `9d9abb76d12a5ab94994984e808512dacf411156` |
| 3D implementation | `aa0c7148d4fbb07c08ca28bdf4f3e5edde84984d` |
| 3D / **production deployed SHA** | `b31b88f77197c0818437649f9e90660a5143bdac` |
| Production LIVE evidence commit | `05f73c94480075391512d21eda43e83964105758` |
| Closure/control commit | successor of `05f73c9` on this branch (this handoff lives there) |
| Backend floor | 1276 passed / 4 skipped / 0 failed |

**Production must remain on `b31b88f` until a closure repair is intentionally deployed.**  
Docs/handoff commits after `b31b88f` must **not** be treated as the production code SHA.

| Production | Value |
|---|---|
| Host | `moderbober-prod-01` (`deploy@81.26.176.248`) |
| Service | `tinkuy-web` systemd |
| App | `/opt/tinkuy/app` |
| Port | 8085 |
| LIVE | `POST http://127.0.0.1:8085/api/socrates/run` `execution_mode=LIVE` |
| Env | `/etc/tinkuy/tinkuy.env` — do not overwrite |
| Installer | `CALIFORNIAN_ID/deploy/install_on_vm.sh` |
| Rollback snapshots | `/opt/tinkuy/rollback_snapshot_pre_c2d5833.tar.gz`, `/opt/tinkuy/rollback_snapshot_pre_b31b88f.tar.gz` |

Evidence:

- `docs/socrates_gs26/real_socrates_route/3c_3d_production/`
- `docs/socrates_gs26/real_socrates_route/CHECKPOINT_3C_3D_PRODUCTION.md`
- Report: `docs/socrates_gs26/real_socrates_route/3c_3d_production/production_acceptance_report.md`

Mechanical 3C/3D tests (not production LIVE):

- `CALIFORNIAN_ID/tests/workbench/test_aporia_apparatus_3c.py`
- `CALIFORNIAN_ID/tests/workbench/test_hybrid_dyad_3d.py`

Runtime seams:

- `CALIFORNIAN_ID/src/socrates_runtime/runtime.py` — 3B then `run_apparatus_diagnostic` then `run_dyadic_pass`
- `CALIFORNIAN_ID/src/socrates_runtime/aporia_and_world_map.py`
- `CALIFORNIAN_ID/src/socrates_runtime/hybrid_dyad.py` (`scene_scope_key` uses telos)
- `CALIFORNIAN_ID/src/californian_id/socrates_bridge.py` — **new `SocratesRuntime` per HTTP request**

Constraints: local foreground; HTTPS git; no Drive MCP for this package; no-proxy SSH; do not print secrets.

---

## C. WHAT IS PROVEN

On production LIVE (31/31 `real_live`, 0 errors, SHA `b31b88f`):

- Exact deploy of accepted 3C+3D lineage (git archive + existing installer).
- Health: systemd active, `GET /` 200, Socrates LIVE `runtime_layer=socrates_runtime`.
- Real provider: `provider_id=fallback`, `model_id=chain`, `mockish_phases=0`.
- **3B regression PASS:** easy 2+2 zero extra passes; material organ-gap extra pass; `private_work_max_additional=0` binds; injection does not mint extra work or durable write; `RETURN_OPERATION` sovereignty.
- **3C executes** through HTTP `SocratesRuntime` (`apparatus_diagnostic.classification` always present).
- **3D executes** (`dyad` present; `stop_reason=no_3c_reentry` — no 3C↔3D recursion).
- P3D-3 **SharedObjectDelta** `not_user_model=true`.
- P3D-4 productive disagreement held; terminal `PRESERVE_APORIA`.
- P3D-6 Socrates-side revision (`socrates_position_revised=true`).
- P3D-5 / CONT-c context isolation (no leak onto a fresh `context_id`).
- Same `context_id` hydration across two HTTP posts: `ctx_778f4ceda5320a92b10ba622c9db08e2`.
- No unauthorized durable write (`NO_DURABLE_WRITE`, no world-map proposal, `memory_outcome=null`).
- P3D-7 retrieved injection blocked.
- No public CoT leak.
- Rollback **not** required. 3E **not** started.

Repository 3C/3D: **PASS / ACTIVE_IN_RUNTIME** (mechanical). Production acceptance: **PARTIAL**.

---

## D. WHAT FAILED / REMAINS QUALIFIED

Do not hide these inside a PASS summary.

### 1. Same-context continuation → SCENE_SHIFT (telos drift)

**D-S26-3D-LIVE-TELOS-001**

P3D-1a minted `shared_object_delta` (`drec_1106833e2e78`, `not_user_model=true`).  
P3D-1b used the **same** `context_id` `ctx_ce6f7a39b169886a7ae7ef7be2e94c26` and same `active_contract_id`, but:

- `surprise_class=SCENE_SHIFT`
- `causal_effect=none`
- `used_prior_record_ids=[]`

CONT-a/b: same `ctx_778f4ceda5320a92b10ba622c9db08e2`; reuse also `SCENE_SHIFT`.

Observed S1 telos strings differ between turns (e.g. “clarify the distinction…” vs “apply the previously established…”).  
`hybrid_dyad.scene_scope_key` keys scene on `telos:{telos}`. That is an observation, not a completed root-cause proof.

### 2. User-hypothesis revision fails (criterion 7 FAIL)

**Same defect family as (1).**

P3D-2b: `user_hypothesis_revised=false`, `causal_effect=none`, `SCENE_SHIFT`.  
Explicit “I explicitly reject interpretation X.” did not revise the prior hypothesis on the same `context_id`.

This is a **true FAIL** against production acceptance criterion 7.

### 3. Repeated projection does not accumulate across HTTP

**D-S26-3C-LIVE-REPEAT-001**

P3C-4a/4b: both `EVIDENCE_GAP`, `mismatch_candidate=false`.  
Each `/api/socrates/run` constructs a new `SocratesRuntime`; `_apparatus_repeat` is instance-local. Mechanical tests reach `APPARATUS_MISMATCH_CANDIDATE` in-process. Production HTTP cannot.

Do **not** “fix” by adding a process-global counter unless archaeology proves that is the intended persistence boundary.

### 4. Organ/source gap dominates aporia class

**D-S26-3C-LIVE-ORGAN-PRIORITY-001**

P3C-3: terminal **`PRESERVE_APORIA`**, classification **`EVIDENCE_GAP`**, grounds `typed_source_or_organ_gap`.  
P3C-1 ordinary-unresolved prompt also `EVIDENCE_GAP` (ordinary class **did** appear on 3B-P1 easy 2+2).

`run_apparatus_diagnostic` checks organ/source gap **before** `PRESERVE_APORIA` / genuine aporia. That is code fact; whether priority, dual diagnosis, or orthogonal dimensions is the right repair is **not** decided.

---

## E. ARCHITECTURE QUESTIONS — BEGIN WITH ARCHAEOLOGY, NOT CODE

### Question 1 — Scene identity / current-scene continuity

What determines Scene identity today?  
Trace S1 / telos production → Scene / SceneContract → context store → dyad `scene_scope_key` / `prior_scene_key` (`runtime.py` uses `prior_ctx.last_telos`).

### Question 2 — Telos vs continuation identity

Is telos currently used where continuation identity (`context_id`, contract, scene_id) should be used?  
Do **not** assume yes before tracing code, tests, and 3A+ history.

### Question 3 — Where repeated apparatus evidence should persist

Trace `context_id` / Scene / Space / Branch / `WorldMapRegistry` / diagnostic state / SQLite context store.  
3C repeat state today is `_apparatus_repeat` on the runtime instance.  
Do not invent a new global dict or a new DB unless architecture proves it.

### Question 4 — Can EVIDENCE_GAP coexist with GENUINE_APORIA?

Trace `GapKind`, downstream consumers (`dyad.likely_failure_source`, dialogue log, HTTP public fields).  
Do not change priority until consumers are known.

### Question 5 — One boundary or three defects?

Are TELOS-001, REPEAT-001, and ORGAN-PRIORITY-001 separate causes, or symptoms of one state-continuity boundary between HTTP requests?

Also keep **D-S26-QSEL-003 OPEN**. Do not silently close it.

---

## F. REPAIR BOUNDARY

This pass **may** repair 3C/3D production closure (runtime + tests + bounded redeploy of a descendant of `b31b88f` if needed).

It must **NOT**:

- start 3E / P001 / G-S27 / G-S28;
- create a new memory DB, dyad DB, or world-map DB;
- invent a second Scene system;
- collapse aporia into automatic apparatus mismatch;
- turn user-model hypotheses into facts;
- weaken state-write authority;
- broaden into UI / Arena / persona residency / Indago / Mirror Twin.

Reuse the established production deploy route. Rollback target remains `c2d5833` / `pre_b31b88f` snapshot until a new intentional snapshot.

---

## G. EXPECTED NEXT VERDICT

Return exactly one of:

`SOCRATES_3C_3D_PRODUCTION_CLOSURE_PASS`  
`SOCRATES_3C_3D_PRODUCTION_CLOSURE_PARTIAL`  
`SOCRATES_3C_3D_PRODUCTION_CLOSURE_FAIL`

**PASS** requires production LIVE proof that:

1. same `context_id` continuation can reuse a prior distinction without false `SCENE_SHIFT` when the scene has not actually changed;
2. explicit user contradiction can revise a false dyadic hypothesis (`user_hypothesis_revised`);
3. repeated projection evidence can accumulate across HTTP turns far enough to reach `APPARATUS_MISMATCH_CANDIDATE` **or** an honest documented architectural nonclaim with owner-grade evidence;
4. `PRESERVE_APORIA` is not silently typed only as `EVIDENCE_GAP` **or** the dual/orthogonal representation is explicit;
5. 3B regression, authority, and no 3C↔3D recursion still hold;
6. 3E still not started.

Until PASS: **3E = BLOCKED**.

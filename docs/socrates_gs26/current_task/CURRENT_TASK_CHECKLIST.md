# CHECKLIST — SOCRATES-GS26X-BACH-DIDENKO-20260817-001

Update after every generation. Tick items only when the specific gate is met by code + tests + evidence.

## G-BD.0 — Durable task + baseline

- [x] `CURRENT_TASK_BACH_DIDENKO_INTEGRATION_v1.md` created.
- [x] `CURRENT_TASK_STATUS.yaml` created.
- [x] `CURRENT_TASK_CHECKLIST.md` created.
- [x] Work branch `socrates/gs26-bach-didenko-integration` created from `2ecc070`.
- [ ] First commit + push (this generation's checkpoint) before any substantive code.

## G-BD.1 — Projection / generative hardening

- [x] D-S26-GEN-002 fingerprint canonicalisation (params + inputs + wiring).
- [x] D-S26-PROV-003 explicit typed lineage relations.
- [x] D-S26-PROV-004 direct object/residue provenance refs.
- [x] D-S26-GEN-003 `ProjectionSynthesisProposal` + S4 jurisdiction + schema.
- [x] Targeted tests: T-PROV-01 (5), T-PROV-02 (2), T-PROV-03 (3), T-PROV-04 (6). Total 16 passing.
- [x] Full backend: 762 passing / 4 skipped (was 746/4; +16 hardening).
- [x] Commit + push.

## G-BD.2 — Technical object model

- [x] `EpistemicSpace` type + state integration.
- [x] `WorldModelMount` with `mount_mode` enum and provenance ≠ activation.
- [x] `SceneBranch` (extends S1 Scene via SceneRef + SceneRegistry).
- [x] `EpistemicPassport` read model.
- [x] `MemoryValidityScope` enum (extends B05 governed memory view).
- [x] `ContextTransduction` / `SpaceTransition` typed record.
- [x] `ConflictHoldingState` with families + handling modes.
- [x] `PipelineState` extended: space_id, scene_id, branch_id, space_registry, scene_registry, context_transductions, conflict_registry, passports (defaults preserve direct-assistance).
- [x] 6 JSON schemas under `data/socrates/current/contracts/`.
- [x] 28 tests in `test_epistemic_model.py` — enums / shapes / registries / state integration / id factories / default workspace.
- [x] `TECHNICAL_OBJECT_MODEL.md` docs artefact.
- [x] Full backend: 790 passing / 4 skipped (was 762/4).
- [x] Commit + push.

## G-BD.3 — BACH operator layer

- [x] OP-01 … OP-18 with typed trigger/precondition/effect/output/stop/failure semantics.
- [x] Wired to existing seams (PROJECTION_SPEC / REFLECTIVE_LOOP / TRANSDUCTION / SCENE_BRANCH / MEMORY_SCOPE / CONFLICT_HOLD / ATTENTION_CONFIG / PASSPORT_ONLY / SEMANTIC_ONLY).
- [x] Donor-local classification honest: OP-07, OP-08 (fold + unfold-in-medium) donor-local; other 16 transferable global method.
- [x] Authority invariants: no execute/install/authorize methods on class; registration grants no execution authority.
- [x] Registry + tests (33) — completeness / bindings / classification / authority / serialisation / seam wiring smoke.
- [x] `BACH_OPERATOR_IMPLEMENTATION_MAP.md` docs artefact.
- [x] Full backend: 823 passing / 4 skipped (was 790/4).
- [x] Commit + push.

## G-BD.4 — Semantic bodies v0.3

- [x] CORE_v0.3_candidate.
- [x] B01_v0.3_candidate.
- [x] B02_v0.3_candidate.
- [x] B03_v0.3_candidate.
- [x] B04_v0.3_candidate.
- [x] B05_v0.3_candidate.
- [x] B07_v0.3_candidate.
- [x] B08_v0.3_candidate.
- [x] B10_v0.3_candidate.
- [x] B06/B09 explicitly not patched this pass — no dependency change requires it (documented in registry manifest).
- [x] 17-section standard preserved (verified by test).
- [x] `SEMANTIC_BODY_V03_DELTA_MANIFEST.md`.
- [x] `semantic_body_registry_v0.3.yaml` registry manifest.
- [x] v0.2 files unchanged (default `SemanticBodyRegistry()` still loads v0.2 exclusively; test verifies).
- [x] 7 load/isolation/manifest tests passing.
- [x] Full backend: 830 passing / 4 skipped (was 823/4).
- [x] Commit + push.

## G-BD.5 — Routers / mounts / context v0.3

- [x] Router manifest v0.3 references v0.3 bodies via candidate_v0_3/routers/semantic_body_registry_v0.3.yaml.
- [x] Mount policy v0.3 (`semantic_mount_manifest_v0.3.yaml`) with BACH-local isolation, budget, historical fallback banned.
- [x] Context assembly consumes new state via `PipelineState.to_public()` (Space/Scene/Branch/Passport/memory-scope all surfaced).
- [x] `MOUNT_AND_ROUTER_V03_DELTA.md`.
- [x] No historical v0.2 fallback masquerading as v0.3 (enforced structurally).
- [x] 11 mount policy tests passing.
- [x] Full backend: 841 passing / 4 skipped.
- [x] Commit + push.

## G-BD.6 — Runtime transitions / memory / passport

- [x] Scene DAG executable via `epistemic_ops.fork_scene_branch` + `activate_branch`.
- [x] SpaceTransition / ContextTransduction executable via `emit_context_transduction` (raises on missing loss report for TRANSDUCTION / ONTOLOGICAL_TRANSFER — structural enforcement of §6.6).
- [x] Scoped memory enforced via `check_cross_scope_access` (all four CrossScopePolicy modes tested).
- [x] Passport observable via `render_passport` — surfaces held conflicts by default, exposes no upgrade method.
- [x] `open_conflict` enforces §6.7 (HOLD requires discriminator; ARBITRATE_ACTION requires action_arbitration).
- [x] `should_return_to_ordinary` detects OP-18 clean state.
- [x] 25 epistemic ops tests passing.
- [x] Full backend: 866 passing / 4 skipped.
- [x] Commit + push.

## G-BD.7 — Conflict audit + repair

- [x] `SEMANTIC_TENSION_AND_CONFLICT_MATRIX.md` — 18 material tensions, each with explicit handling mechanism.
- [x] No hidden collisions detected during the audit (§ preservation-by-construction — every collision path fails structurally OR opens ConflictHoldingState OR surfaces on Passport).
- [x] Legitimate incompatibility preserved (HOLD conflicts require discriminator).
- [x] Commit + push (bundled with G-BD.5/6/8/9).

## G-BD.8 — Didenko coverage + remaining deltas

- [x] `DIDENKO_COVERAGE_MATRIX.md` D1–D6 verdicts: D1 FULL, D2 FULL, D3 FULL, D4 FULL, D5 FULL, D6 PARTIAL (Workspace UI + registry deferred).
- [x] `DIDENKO_REMAINING_DELTA_REGISTER.md` with classification per remaining delta (17 items: 0 GENUINELY_NEW implemented, 8 UI_PROJECTION deferred, 1 RENAME, 2 ALREADY_COVERED, 1 AMBIGUOUS, 4 REJECTED_WITH_REASON).
- [x] Genuinely-new deltas: 0 in this pass (novelty compass and living-memory deferred with explicit reasons).
- [x] Commit + push (bundled).

## G-BD.9 — Cross-layer traceability

- [x] `CROSS_LAYER_TRACEABILITY.md` — 9 accepted distinctions traced source→type→field→op→body→mount→state→test.
- [x] Orphan check performed: 0 orphans found across schema-only fields / prompt-only ideas / runtime fields no prompt understands / operator names without executable path / UI labels with hidden authority / source claims with lost provenance.
- [x] Commit + push (bundled).

## G-BD.10 — Deterministic + full regression

- [x] T-PROV-01/02/03/04 passing (16 tests, hardening).
- [x] T-DID-01/02/03/04/05 passing (10 tests in `test_bach_didenko_acceptance.py`).
- [x] T-BACH-01/02/03/04/05/06/07 passing (10 tests in `test_bach_didenko_acceptance.py`).
- [x] Peskov regression preserved (11 tests in `test_peskov_projection_loop.py`, phase sequence S0..S10 → S7 → S4..S10).
- [x] Negatives (§18 items) passing (11 tests in `TestNegativesFromHandoffSection18`).
- [x] Full backend suite passing: 897 passed / 4 skipped (was 746/4 at task start; +151 delta).
- [x] UI status: `NOT_RERUN_UNCHANGED_SURFACE`, justified in `ACCEPTANCE_REPORT.md`.
- [x] `ACCEPTANCE_REPORT.md` written.
- [x] Commit + push.

## G-BD.11 — Targeted live staging

- [x] Provider path documented in `LIVE_ACCEPTANCE_REPORT.md` (uses existing accepted inheritance only; no new silo).
- [x] No secrets printed, no prod mutation.
- [ ] L1 SIMPLE SPACE-STABLE DIRECT ASSISTANCE — NOT_RUN (LIVE_BLOCKED_BY_ENVIRONMENT).
- [ ] L2 SPACE/SCENE RECONSTRUCTION — NOT_RUN.
- [ ] L3 LOSSY CONTEXT TRANSDUCTION — NOT_RUN.
- [ ] L4 SCENE BRANCH — NOT_RUN.
- [ ] L5 LIVE MODEL-PRODUCED CUTTER SPEC — NOT_RUN.
- [ ] L6 TRUE ORGAN GAP — NOT_RUN.
- [ ] L7 CONFLICT HOLD / APORIA — NOT_RUN.
- [ ] L8 PESKOV LIVE REGRESSION — NOT_RUN.
- [x] `LIVE_ACCEPTANCE_REPORT.md` written honestly (env-blocked, deterministic-ready).
- [x] Commit + push.

## G-BD.12 — Freeze + final closure

- [x] Version map / checksums frozen (v0.3 candidate registry manifest declares versions; v0.2 unchanged).
- [x] Final `CURRENT_TASK_STATUS.yaml` update (status=FROZEN, all generations completed_generations).
- [x] `NONCLAIMS_AND_OPEN_GAPS.md` written (17 nonclaims + open-gap register).
- [x] Final architecture/coverage report (`ACCEPTANCE_REPORT.md` + `LIVE_ACCEPTANCE_REPORT.md` + coverage matrix + tension matrix + traceability).
- [x] Push final SHA.
- [x] `P001_UNBLOCKED = NO` reported in `CURRENT_TASK_STATUS.yaml` with exact join-gate evidence pointing at LIVE_BLOCKED_BY_ENVIRONMENT.

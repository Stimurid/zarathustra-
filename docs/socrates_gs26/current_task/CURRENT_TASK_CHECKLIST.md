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

- [ ] CORE_v0.3_candidate.
- [ ] B01_v0.3_candidate.
- [ ] B02_v0.3_candidate.
- [ ] B03_v0.3_candidate.
- [ ] B04_v0.3_candidate.
- [ ] B05_v0.3_candidate.
- [ ] B07_v0.3_candidate.
- [ ] B08_v0.3_candidate.
- [ ] B10_v0.3_candidate.
- [ ] B06/B09 patched if dependencies require.
- [ ] 17-section standard preserved.
- [ ] `SEMANTIC_BODY_V03_DELTA_MANIFEST.md`.
- [ ] v0.2 files unchanged.
- [ ] Commit + push.

## G-BD.5 — Routers / mounts / context v0.3

- [ ] Router manifest v0.3.
- [ ] Mount policy v0.3 (BACH-local isolation, budget).
- [ ] Context assembly consumes new state.
- [ ] `MOUNT_AND_ROUTER_V03_DELTA.md`.
- [ ] No historical v0.2 fallback masquerading as v0.3.
- [ ] Commit + push.

## G-BD.6 — Runtime transitions / memory / passport

- [ ] Scene DAG executable.
- [ ] SpaceTransition / ContextTransduction executable + traceable.
- [ ] Scoped memory enforced.
- [ ] Passport observable via public state.
- [ ] Commit + push.

## G-BD.7 — Conflict audit + repair

- [ ] `SEMANTIC_TENSION_AND_CONFLICT_MATRIX_v1.md`.
- [ ] Every material tension has explicit handling mechanism.
- [ ] Hidden collisions repaired.
- [ ] Legitimate incompatibility preserved.
- [ ] Commit + push.

## G-BD.8 — Didenko coverage + remaining deltas

- [ ] `DIDENKO_COVERAGE_MATRIX.md` D1–D6 verdicts.
- [ ] `DIDENKO_REMAINING_DELTA_REGISTER.md` with classification per remaining delta.
- [ ] Genuinely-new deltas implemented via full loop (type → operator → prompt → conflict audit → test).
- [ ] Commit + push.

## G-BD.9 — Cross-layer traceability

- [ ] `CROSS_LAYER_TRACEABILITY.md`.
- [ ] Orphans repaired (schema-only fields, prompt-only ideas, runtime fields no prompt understands, operator names without executable path, UI labels with hidden authority, source claims with lost provenance).
- [ ] Commit + push.

## G-BD.10 — Deterministic + full regression

- [ ] T-PROV-01/02/03/04 passing.
- [ ] T-DID-01/02/03/04/05 passing.
- [ ] T-BACH-01/02/03/04/05/06/07 passing.
- [ ] Peskov regression preserved.
- [ ] Negatives (all §18 items) passing.
- [ ] Full backend suite passing (no regression vs 746/4).
- [ ] UI status recorded (`NOT_RERUN_UNCHANGED_SURFACE` justified, or rerun if shared API/type changes affect UI).
- [ ] `ACCEPTANCE_REPORT.md`.
- [ ] Commit + push.

## G-BD.11 — Targeted live staging

- [ ] Provider path uses existing accepted inheritance only (no new silo).
- [ ] No secrets printed, no prod mutation.
- [ ] L1 SIMPLE SPACE-STABLE DIRECT ASSISTANCE.
- [ ] L2 SPACE/SCENE RECONSTRUCTION.
- [ ] L3 LOSSY CONTEXT TRANSDUCTION.
- [ ] L4 SCENE BRANCH.
- [ ] L5 LIVE MODEL-PRODUCED CUTTER SPEC (with runtime validate + compile-bind + execute).
- [ ] L6 TRUE ORGAN GAP.
- [ ] L7 CONFLICT HOLD / APORIA.
- [ ] L8 PESKOV LIVE REGRESSION.
- [ ] `LIVE_ACCEPTANCE_REPORT.md`.
- [ ] Commit + push.

## G-BD.12 — Freeze + final closure

- [ ] Version map / checksums frozen where practice supports.
- [ ] Final `CURRENT_TASK_STATUS.yaml` update.
- [ ] `NONCLAIMS_AND_OPEN_GAPS.md`.
- [ ] Final architecture/coverage report.
- [ ] Push final SHA.
- [ ] Report `P001_UNBLOCKED = YES / NO` with exact join-gate evidence.

# DIDENKO COVERAGE MATRIX v1 — G-BD.8

Per handoff §15, first-wave coverage verdict per concept: FULL / PARTIAL / MISSING / DIFFERENT_OBJECT / REJECTED_WITH_REASON.

Each FULL claim requires code/type + semantic prompt + test evidence.

## D1 — Space

**Verdict: FULL.**

| Evidence type | Location |
|---|---|
| Type | `EpistemicSpace` in `epistemic_model.py` |
| Schema | `data/socrates/current/contracts/epistemic_space.schema.json` |
| State field | `PipelineState.space_id` + `space_registry` |
| Semantic body | CORE v0.3 §4, §5; B08 v0.3 §4 |
| Mount policy | `semantic_mount_manifest_v0.3.yaml world_model_mounts` |
| Test | `test_epistemic_model.py::TestShapesAndPublicSerialisation::test_epistemic_space_has_required_fields` |
| Test | `test_epistemic_model.py::TestPipelineStateIntegration::test_state_defaults_to_default_workspace_space` |

Distinct from ontology (many-to-many via `WorldModelMount`). Distinct from Scene (Scenes live IN a Space). Test verifies direct-assistance runs get a default workspace Space without explicit declaration.

## D2 — Scene / Scene DAG

**Verdict: FULL.**

| Evidence type | Location |
|---|---|
| Type | `SceneRef`, `SceneBranch`, `SceneRegistry` in `epistemic_model.py` |
| Schema | `data/socrates/current/contracts/scene_branch.schema.json` |
| State field | `PipelineState.scene_id`, `branch_id`, `scene_registry` |
| Semantic body | B01 v0.3 §3, §4, §5 |
| Runtime op | `epistemic_ops.py::fork_scene_branch`, `activate_branch` |
| Test | `test_epistemic_ops.py::TestSceneDAG::test_two_incompatible_branches_do_not_contaminate` |
| Test | `test_epistemic_model.py::TestRegistries::test_scene_registry_indexes_branches_by_scene` |

Multiple Scenes in one Space supported (registry keyed by id). Sibling SceneBranches under one Scene supported. Branch-local facts / memory isolated by design (`SceneBranch.memory_scope` defaults `BRANCH`). Test proves fact leak does not occur.

## D3 — Truth / EpistemicPassport

**Verdict: FULL.**

| Evidence type | Location |
|---|---|
| Type | `EpistemicPassport`, `ConstructionStatus` enum in `epistemic_model.py` |
| Schema | `data/socrates/current/contracts/epistemic_passport.schema.json` |
| State field | `PipelineState.passports` |
| Semantic body | B02 v0.3 §2, §4; CORE v0.3 §5 |
| Runtime op | `epistemic_ops.py::render_passport` |
| Test | `test_epistemic_ops.py::TestPassport` (4 tests) |
| Test | `test_epistemic_model.py::TestShapesAndPublicSerialisation::test_epistemic_passport_is_readonly_shape` |

TruthMode is a DERIVED UX projection only (field `truth_mode_readout` on Passport). Strict axes (origin_source_refs, claim_status, verification_status, authority_type, construction_status) survive independently. Passport surfaces held conflicts by default (test).

## D4 — SpaceTransition / ContextTransduction

**Verdict: FULL.**

| Evidence type | Location |
|---|---|
| Type | `ContextTransduction`, `TransductionKind` enum in `epistemic_model.py` |
| Schema | `data/socrates/current/contracts/context_transduction.schema.json` |
| State field | `PipelineState.context_transductions` |
| Semantic body | B07 v0.3 §7; CORE v0.3 §5 |
| Runtime op | `epistemic_ops.py::emit_context_transduction` |
| Operator | OP-04 TRANSDUCE_CONTEXT (also OP-07 fold, OP-08 unfold-in-medium donor-local) |
| Test | `test_epistemic_ops.py::TestContextTransduction` (4 tests) |

Cross-Space transfer is typed and possibly lossy. Neutral-copy fiction is BANNED: `emit_context_transduction` raises `ValueError` if a TRANSDUCTION or ONTOLOGICAL_TRANSFER call fails to supply any of `dropped` / `newly_created` / `loss_report`. Test verifies.

## D5 — MemoryValidityScope

**Verdict: FULL.**

| Evidence type | Location |
|---|---|
| Type | `MemoryValidityScope` (9 values), `CrossScopePolicy` (4 values) in `epistemic_model.py` |
| Semantic body | B05 v0.3 §4, §7 |
| Runtime op | `epistemic_ops.py::check_cross_scope_access` |
| Operator | OP-17 CONTEXT_QUARANTINE, OP-09 STABILIZE_OBJECT |
| Test | `test_epistemic_ops.py::TestCrossScopeAccess` (5 tests) |
| Test | `test_epistemic_model.py::TestEnumsCoverADRValues::test_memory_scope_covers_adr` |

Nine scopes cover Project / Space / Scene / Branch / Projection + adjacent. Explicit recruitment / bridge policy enum (four modes). Tests exercise all four policy modes.

## D6 — Workspace relation

**Verdict: PARTIAL.**

Engineering Workbench remains distinct from human intellectual Workspace by design of the existing repo (Workbench in `src/workbench_*`; Workspace is a semantic concept). The Workspace level in the epistemic model exists as an implicit parent of `EpistemicSpace` — every `EpistemicSpace` belongs to a Workspace, but this pass ships only `DEFAULT_WORKSPACE_SPACE_ID` as a stable default rather than a first-class Workspace registry.

Why PARTIAL:
- Direct-assistance invariant preserved by default workspace.
- Multi-Workspace runtime routing is out of scope for this pass (backend/read-model first; no major new UI).
- A first-class Workspace registry with per-Workspace Space enumeration is future work.

## Summary

| Concept | Verdict |
|---|---|
| D1 Space | FULL |
| D2 Scene / Scene DAG | FULL |
| D3 Truth / EpistemicPassport | FULL |
| D4 SpaceTransition / ContextTransduction | FULL |
| D5 MemoryValidityScope | FULL |
| D6 Workspace relation | PARTIAL (backend/read-model shipped; multi-Workspace UI + registry deferred) |

## Sources

Didenko board reconstruction (Drive `1lIIJeZVQdQvlRsLGk9hHr0IXzWfxe_KxHjO4Hxx7RjY`) + Didenko ↔ BACH crosswalk (Drive `1k0WLfS7hTVW_mX_DywYGmVzlgBf2fASy5IBQVcDW-Xc`) served as the reference for concept semantics. Drive access was not authenticated locally during this pass; provenance IDs preserved for later verification. No claim is made that the reconstructions are byte-identical to the Drive originals — only that the concept semantics implemented here match what the handoff §15 declared.

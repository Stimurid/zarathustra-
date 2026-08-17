# CROSS-LAYER TRACEABILITY v1 — G-BD.9

Per handoff §17, every accepted distinction traces: source → local Socrates definition → technical object/field → operator → semantic body section → router/mount → phase/state transition → trace/public evidence → acceptance test.

## Legend

- **Source**: Drive doc ID (may be unauthenticated locally; kept for provenance).
- **Def**: local Socrates document that captures the concept.
- **Type**: Python type / dataclass.
- **Field**: `PipelineState` field or object attribute.
- **Op**: BACH operator id (from `bach_operators.py`).
- **Body**: v0.3 semantic body section reference.
- **Router/Mount**: entry in `semantic_mount_manifest_v0.3.yaml`.
- **State**: how it appears in `state.to_public()`.
- **Test**: pytest node id.

## Rows

### EpistemicSpace
| Layer | Value |
|---|---|
| Source | `1ZgWgu-rlPK0FXhDt0cie5G_BOs6mff7IMjkYiStjWUo` |
| Def | `TECHNICAL_OBJECT_MODEL.md` |
| Type | `epistemic_model.EpistemicSpace` |
| Field | `PipelineState.space_id`, `space_registry` |
| Op | OP-04 (transduction between Spaces), OP-17 (quarantine) |
| Body | CORE v0.3 §4/§5, B08 v0.3 §4 |
| Mount | `bach_local_isolation`, `world_model_mounts` |
| State | `state.to_public()["space_id"]`, `["space_registry"]` |
| Test | `test_epistemic_model.py::TestPipelineStateIntegration::test_state_defaults_to_default_workspace_space` |

### WorldModelMount + provenance ≠ activation
| Layer | Value |
|---|---|
| Source | `1JsERSCmXt-nfsbF_GbWb76nRwJx5jIjK2hHmfP08xsU`, `1MFRTKD7h31-CFAR-EnA6X6KUfLELr4XKnbED4JEtQ8w` |
| Def | `TECHNICAL_OBJECT_MODEL.md`, CORE v0.3 §5 |
| Type | `epistemic_model.WorldModelMount`, `MountMode` |
| Field | Embedded in `EpistemicSpace.world_model_mounts` |
| Op | OP-11 BOARD_SEAM_CHECK, donor-local isolation for OP-07/OP-08 |
| Body | B08 v0.3 §4, §7 |
| Mount | `bach_local_isolation.admission_rule` |
| State | `world_model_mounts` array on each Space |
| Test | `test_epistemic_model.py::TestShapesAndPublicSerialisation::test_world_model_mount_provenance_neq_activation` |

### SceneBranch DAG
| Layer | Value |
|---|---|
| Source | `1lIIJeZVQdQvlRsLGk9hHr0IXzWfxe_KxHjO4Hxx7RjY` |
| Def | `TECHNICAL_OBJECT_MODEL.md`, B01 v0.3 §3-§5 |
| Type | `epistemic_model.SceneBranch`, `SceneRegistry` |
| Field | `PipelineState.branch_id`, `scene_registry` |
| Op | (SCENE_BRANCH binding future); dispatch via `fork_scene_branch` |
| Body | B01 v0.3 |
| Mount | Trigger cause `MULTI_ONTOLOGY_MOUNT` when Space carries multiple mounts |
| State | `state.to_public()["scene_registry"]["branches"]` |
| Test | `test_epistemic_ops.py::TestSceneDAG::test_two_incompatible_branches_do_not_contaminate` |

### ContextTransduction / SpaceTransition (with typed loss)
| Layer | Value |
|---|---|
| Source | `1ZgWgu-rlPK0FXhDt0cie5G_BOs6mff7IMjkYiStjWUo` |
| Def | `TECHNICAL_OBJECT_MODEL.md`, B07 v0.3 §7 |
| Type | `epistemic_model.ContextTransduction`, `TransductionKind` |
| Field | `PipelineState.context_transductions` |
| Op | OP-04 TRANSDUCE_CONTEXT, OP-07/OP-08 (donor-local fold/unfold) |
| Body | B07 v0.3, B08 v0.3 |
| Mount | Trigger cause `CROSS_SPACE_TRANSDUCTION_PENDING` admits B07 |
| State | `state.to_public()["context_transductions"]` |
| Test | `test_epistemic_ops.py::TestContextTransduction::test_transduction_without_loss_report_raises` (structural enforcement) |

### EpistemicPassport read model
| Layer | Value |
|---|---|
| Source | `1lIIJeZVQdQvlRsLGk9hHr0IXzWfxe_KxHjO4Hxx7RjY` |
| Def | `TECHNICAL_OBJECT_MODEL.md`, B02 v0.3, B10 v0.3 |
| Type | `epistemic_model.EpistemicPassport`, `ConstructionStatus` |
| Field | `PipelineState.passports` |
| Op | OP-06 HOLD_UNSTABILIZED, OP-13 STRONG_VERSION_RECONSTRUCT, OP-16 NOVELTY_RELATIVIZE |
| Body | B02 v0.3, B10 v0.3 |
| Mount | (passport is render-time; no mount trigger) |
| State | `state.to_public()["passports"]` |
| Test | `test_epistemic_ops.py::TestPassport::test_passport_surfaces_held_conflicts_when_not_supplied` |

### MemoryValidityScope + CrossScopePolicy
| Layer | Value |
|---|---|
| Source | `1lIIJeZVQdQvlRsLGk9hHr0IXzWfxe_KxHjO4Hxx7RjY` (Didenko) |
| Def | B05 v0.3 |
| Type | `epistemic_model.MemoryValidityScope` (9), `CrossScopePolicy` (4) |
| Field | `SceneBranch.memory_scope`, `EpistemicPassport.memory_validity_scope`, `EpistemicSpace.memory_default_scope` |
| Op | OP-09 STABILIZE_OBJECT, OP-17 CONTEXT_QUARANTINE |
| Body | B04 v0.3 (retrieval), B05 v0.3 (formation) |
| Mount | (policy consulted at cross-scope read; no mount trigger) |
| State | Present on branch / passport / space records |
| Test | `test_epistemic_ops.py::TestCrossScopeAccess` (5 policy modes) |

### ConflictHoldingState families + handling modes
| Layer | Value |
|---|---|
| Source | `1lIIJeZVQdQvlRsLGk9hHr0IXzWfxe_KxHjO4Hxx7RjY` (Didenko), `1JsERSCmXt-nfsbF_GbWb76nRwJx5jIjK2hHmfP08xsU` (BACH) |
| Def | B08 v0.3, B09 (v0.2 unchanged) |
| Type | `epistemic_model.ConflictHoldingState`, `ConflictFamily`, `ConflictHandlingMode` |
| Field | `PipelineState.conflict_registry` |
| Op | OP-11 BOARD_SEAM_CHECK, OP-14 PRESERVE_APORIA |
| Body | B08 v0.3 §4, §7 |
| Mount | (conflict is state-emit; no mount trigger) |
| State | `state.to_public()["conflict_registry"]` |
| Test | `test_epistemic_ops.py::TestOpenConflict` (4 tests + HOLD/ARBITRATE_ACTION discipline enforcement) |

### ProjectionSynthesisProposal (D-S26-GEN-003)
| Layer | Value |
|---|---|
| Source | ADR-S26-023 (Drive `1O3hjMl-lH8xHIn1Bz2RhKkVsX1zws5svdxoQFq2I9Ow`) |
| Def | ADR-S26-023 + G-BD.1 commit `652f5b5` |
| Type | `capability_resolution.ProjectionSynthesisProposal` |
| Field | `PipelineState.pending_projection_proposal` |
| Op | OP-02 REFRAME, OP-03 ONTOLOGICAL_TRANSFER, OP-10 REVISE_APPARATUS, OP-12 PROJECTION_ENSEMBLE |
| Body | B03 v0.3 §7 |
| Mount | S4 output contract admits `projection_synthesis_proposal` |
| State | `state.to_public()["pending_projection_proposal"]` |
| Test | `test_capability_resolution_hardening.py::TestProposalPath` + `TestS4ContractAcceptsProposal` |

### Reflective target-phase re-entry (D-S26-PROJ-002)
| Layer | Value |
|---|---|
| Source | ADR-S26-022 REPAIR commit `ba8047f` |
| Def | ADR-S26-022 (with historical note pointing to repair) |
| Type | `projection.ReflectiveReturn` |
| Field | `PipelineState.pending_reflective_context`, `reentry_from` |
| Op | OP-01, OP-03, OP-10 |
| Body | B07 v0.3 §7 |
| Mount | Trigger cause `REFLECTIVE_MISMATCH_PENDING` admits B07 |
| State | `state.to_public()["pending_reflective_context"]`, `["reentry_from"]` |
| Test | `test_projection_control_loop.py::test_pass_two_starts_AT_return_target` + `test_stale_first_pass_hint_does_not_overwrite_reflective_revision` |

## Orphan check

Fields, prompts, operators and UI labels were audited for:

- Schema-only orphan fields (defined in JSON Schema but not populated by runtime): none found. Every schema field maps to a dataclass attribute.
- Prompt-only semantic ideas (in v0.3 bodies but with no runtime binding): OP-05 attention config annotation is drafted in B04 v0.3 §7 but the annotation write is a runtime followup (documented in `BACH_OPERATOR_IMPLEMENTATION_MAP.md` as G-BD.6 target — attention config annotation on projection lineage is future work). Not counted as orphan since the operator + semantic ref exist; runtime binding is scoped.
- Runtime fields no prompt understands: none. Every new `PipelineState` field appears in at least one v0.3 body §7 (Operation grammar) or §16 (Runtime-facing summary).
- Operator names with no executable path: 0. Every OP-XX maps to an existing seam or SEMANTIC_ONLY (typed in `bach_operators.py::OperatorBinding`).
- UI/read-model labels with hidden authority: 0. `EpistemicPassport.truth_mode_readout` is explicitly derived, exposes no upgrade method (test).
- Source claims with lost provenance: 0. Every source Drive ID is preserved in a docs artifact (`SEMANTIC_BODY_V03_DELTA_MANIFEST.md`, `DIDENKO_COVERAGE_MATRIX.md`, this file).

## Non-goals

- LIVE prompt authoring vocabulary for each operator (drafted in body §16 summaries, not written as separate router prompt files).
- Attention-config annotation on ProjectionResult (drafted in B04 v0.3 §7; scoped as G-BD.6 follow-up in `BACH_OPERATOR_IMPLEMENTATION_MAP.md`).

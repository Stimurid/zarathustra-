# TECHNICAL OBJECT MODEL — G-BD.2

Delivered in `CALIFORNIAN_ID/src/socrates_runtime/epistemic_model.py` alongside JSON schemas under `CALIFORNIAN_ID/data/socrates/current/contracts/`. All seven first-class types + three registries + four enums land here; `PipelineState` is extended to carry them.

## Objects

| Object | Python type | JSON Schema | State field |
|---|---|---|---|
| EpistemicSpace | `epistemic_model.EpistemicSpace` | [epistemic_space.schema.json](../../../CALIFORNIAN_ID/data/socrates/current/contracts/epistemic_space.schema.json) | `PipelineState.space_id`, `space_registry` |
| WorldModelMount | `epistemic_model.WorldModelMount` | [world_model_mount.schema.json](../../../CALIFORNIAN_ID/data/socrates/current/contracts/world_model_mount.schema.json) | Embedded in `EpistemicSpace.world_model_mounts` |
| SceneRef | `epistemic_model.SceneRef` | (inline in `scene_registry` public form) | `PipelineState.scene_id`, `scene_registry` |
| SceneBranch | `epistemic_model.SceneBranch` | [scene_branch.schema.json](../../../CALIFORNIAN_ID/data/socrates/current/contracts/scene_branch.schema.json) | `PipelineState.branch_id`, `scene_registry` |
| ContextTransduction | `epistemic_model.ContextTransduction` | [context_transduction.schema.json](../../../CALIFORNIAN_ID/data/socrates/current/contracts/context_transduction.schema.json) | `PipelineState.context_transductions` |
| EpistemicPassport | `epistemic_model.EpistemicPassport` | [epistemic_passport.schema.json](../../../CALIFORNIAN_ID/data/socrates/current/contracts/epistemic_passport.schema.json) | `PipelineState.passports` |
| ConflictHoldingState | `epistemic_model.ConflictHoldingState` | [conflict_holding_state.schema.json](../../../CALIFORNIAN_ID/data/socrates/current/contracts/conflict_holding_state.schema.json) | `PipelineState.conflict_registry` |

## Enums

| Enum | Values |
|---|---|
| `MountMode` | `PRIMARY / OVERLAY / LENS / CONTRAST / NEGATIVE_CONTROL / ARCHIVAL` |
| `TransductionKind` | `TRANSLATION / REFRAME / ONTOLOGICAL_TRANSFER / TRANSDUCTION / CONTRAST / FUNCTIONAL_RHYME / ANALOGY / DO_NOT_COLLAPSE` |
| `MemoryValidityScope` | `GLOBAL_SELF / GLOBAL_BETWEEN / PROJECT / SPACE_OR_DOMAIN / SCENE / BRANCH / PROJECTION / INSTRUMENT / ARCHIVAL_ONLY` |
| `CrossScopePolicy` | `FORBID / REQUIRE_EXPLICIT_BRIDGE / ALLOW_READONLY / ALLOW_WITH_TRANSDUCTION` |
| `ConflictFamily` | `ONTOLOGY / EPISTEMIC_STATUS / AUTHORITY / OPERATION / VALUE / CAUSAL_GRAMMAR / IDENTITY_RULE / MEMORY_FORCE` |
| `ConflictHandlingMode` | `LOCALIZE / HOLD / TRANSLATE / TRANSDUCE / ARBITRATE_ACTION / SUSPEND / REJECT` |
| `ConstructionStatus` | `SOURCE_OWNED / RECONSTRUCTED / HYPOTHESIZED / CONSTRUCTED / HYBRID / UNKNOWN` |

## Registries

- `SpaceRegistry` — `EpistemicSpace` records by `space_id`.
- `SceneRegistry` — `SceneRef` + `SceneBranch` records; `.branches_of(scene_id)` walks the DAG.
- `ConflictRegistry` — held `ConflictHoldingState` records for B09 / B10 enumeration.

## Invariants encoded structurally

- **Provenance ≠ activation** (§6.2). `WorldModelMount` has separate `provenance` and `activation_scope` fields — the class does not derive one from the other.
- **No magically neutral summary** (§6.6). `ContextTransduction` has required `preserved / transformed / dropped / newly_created / unresolved` fields with list defaults; a call site cannot forget them silently.
- **Passport is read-only** (§6.4). `EpistemicPassport` exposes no `upgrade / authorize / activate / commit / install` methods; verified by test.
- **B09 arbitrates action, not truth** (§6.7). `ConflictHoldingState` has `action_arbitration` field, no `vote_truth` or equivalent.
- **Default workspace** (§12 / direct assistance). `build_default_workspace_space()` supplies a stable default `EpistemicSpace` so ordinary runs do not need to declare one; `PipelineState.space_id` defaults to `DEFAULT_WORKSPACE_SPACE_ID`.

## Test coverage

`CALIFORNIAN_ID/tests/workbench/test_epistemic_model.py` — 28 tests:

- **Enum coverage** (7) — every enum contains the ADR-required values.
- **Shape + public serialisation** (6) — every object has the ADR-required fields; `to_public()` produces a schema-compatible dict.
- **Registries** (3) — SpaceRegistry / SceneRegistry / ConflictRegistry lookups + iteration.
- **PipelineState integration** (4) — default workspace, public serialisation, populated registries, transductions + conflicts.
- **Id factories** (7) — prefixed ids per type.
- **Default workspace** (1) — direct-assistance-friendly default.

## Non-goals (this generation)

- Runtime behaviour that CONSUMES these objects (Scene DAG traversal, transition execution, memory-scope enforcement) is G-BD.6 / G-BD.10. This generation delivers the DATA MODEL only.
- BACH operator library is G-BD.3.
- Router / mount policy v0.3 is G-BD.5.

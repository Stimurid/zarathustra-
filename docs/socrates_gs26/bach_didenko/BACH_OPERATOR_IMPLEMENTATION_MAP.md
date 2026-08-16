# BACH OPERATOR IMPLEMENTATION MAP — G-BD.3

Delivered in `CALIFORNIAN_ID/src/socrates_runtime/bach_operators.py`. 18 operators + eight bindings + registry.

Distinguishing the two operator types:

- **Runtime-bound** — operators whose ``binding`` names an existing pipeline / projection / reflective / memory / attention / conflict seam. Dispatch is deterministic once the operator is invoked.
- **Semantic-only** — operators that live in the semantic body vocabulary (v0.3) and reach the model via the mounted prompt. No new runtime seam is required.

Neither operator type mints execution authority — they are typed *dispositions*. The registry never wraps or exposes a callable.

## OP-01 … OP-18

| ID | Name | Binding | Donor-local | Bodies |
|---|---|---|---|---|
| OP-01 | PROBLEMATIZE / UNCLAMP_FORM | REFLECTIVE_LOOP | no | B03, B07 |
| OP-02 | REFRAME | PROJECTION_SPEC | no | B03 |
| OP-03 | ONTOLOGICAL_TRANSFER | REFLECTIVE_LOOP | no | B03, B08 |
| OP-04 | TRANSDUCE_CONTEXT | TRANSDUCTION | no | B07 |
| OP-05 | DECONCENTRATE / FIELD_HOLD | ATTENTION_CONFIG | no | B04, B08 |
| OP-06 | HOLD_UNSTABILIZED | PASSPORT_ONLY | no | B02, B08 |
| OP-07 | FOLD / ABSTRACT_DETERMINACY | TRANSDUCTION | **yes** | B08 |
| OP-08 | UNFOLD_IN_MEDIUM | TRANSDUCTION | **yes** | B08 |
| OP-09 | STABILIZE_OBJECT | MEMORY_SCOPE | no | B05 |
| OP-10 | REVISE_APPARATUS | PROJECTION_SPEC | no | B03, B08 |
| OP-11 | BOARD_SEAM_CHECK | CONFLICT_HOLD | no | B04, B08 |
| OP-12 | PROJECTION_ENSEMBLE | PROJECTION_SPEC | no | B03, B08, B09 |
| OP-13 | STRONG_VERSION_RECONSTRUCT | PASSPORT_ONLY | no | B02, B10 |
| OP-14 | PRESERVE_APORIA / NEGATIVE_CAPABILITY | CONFLICT_HOLD | no | B08, B09 |
| OP-15 | SITUATION_TO_TASK_RECONSTRUCTION | SEMANTIC_ONLY | no | B01 |
| OP-16 | NOVELTY_RELATIVIZE | PASSPORT_ONLY | no | B02, B10 |
| OP-17 | CONTEXT_QUARANTINE / DO_NOT_BLEED | MEMORY_SCOPE | no | B04, B05 |
| OP-18 | RETURN_TO_ORDINARY_ASSISTANCE | SEMANTIC_ONLY | no | B10 |

## Donor-local vs transferable

BACH-derived operators that carry **donor-local doctrine** and must NOT bleed into unrelated Spaces (§7 conditional list) are marked `donor_local=True`. In this pass: OP-07 (fold) and OP-08 (unfold-in-medium) because their strong-medium claims come with BACH-specific ontology. All other 16 operators are transferable global method — they may be mounted in any Space when justified by scene evidence.

The registry exposes `donor_local_ids()` and `transferable_ids()` so router/mount policy v0.3 (G-BD.5) can honour PROVENANCE ≠ ACTIVATION structurally: a BACH-derived operator can become a general METHOD capability while donor-local doctrine stays BACH_LOCAL.

## Authority invariants

- `BachOperator` is a frozen dataclass. No `execute` / `install` / `authorize` / `mint` / `deploy` / `activate` method. Verified by test.
- `BachOperatorRegistry.register` adds a NAMED DISPOSITION only — no primitive is installed, no capability is expanded.
- Operators bound to `PROJECTION_SPEC` route through the ADR-S26-023 capability resolver — which itself fails closed on unknown primitives → `ORGAN_GAP`. The operator layer never bypasses that check.
- Operators bound to `MEMORY_SCOPE` route through B05 memory authority — they never mint durable writes.

## Runtime seam mapping (§8 requirement)

| Binding | Existing seam | Where |
|---|---|---|
| PROJECTION_SPEC | `CapabilityResolver.resolve_from_proposal` + `projection_step._execute_synthesised` | ADR-S26-023 + G-BD.1 |
| REFLECTIVE_LOOP | `PipelineExecutor._invoke_reflective_epilogue` + `_record_reflective_context` | ADR-S26-022 |
| TRANSDUCTION | `PipelineState.context_transductions` + `ContextTransduction` records | G-BD.2 |
| SCENE_BRANCH | `SceneRegistry.add_branch` | G-BD.2 (branch execution G-BD.6) |
| MEMORY_SCOPE | `MemoryValidityScope` enum + B05 authority | G-BD.2 (enforcement G-BD.6) |
| CONFLICT_HOLD | `ConflictRegistry.add` + `ConflictHoldingState` | G-BD.2 |
| ATTENTION_CONFIG | (attention config annotation on projection lineage) | G-BD.6 |
| PASSPORT_ONLY | `PipelineState.passports` + `EpistemicPassport` | G-BD.2 (rendering G-BD.6) |
| SEMANTIC_ONLY | mounted body prompt only | G-BD.4 semantic bodies v0.3 |

## Test coverage

`CALIFORNIAN_ID/tests/workbench/test_bach_operators.py` — 33 tests:

- **Library completeness** (20) — all 18 ids present, no extras, every operator has fully populated typed record, at least one v0.3 body ref per operator.
- **Bindings** (3) — enum coverage, by-binding lookup, at least one operator per active runtime binding.
- **Donor-local classification** (1) — OP-07 + OP-08 donor-local, remainder transferable, union covers all 18.
- **Authority invariants** (2) — no execution methods on class, registration grants no authority.
- **Public serialisation** (2) — every field surfaces in `to_public()`, registry lists all operators.
- **Cross-layer wiring smoke** (4) — reflective operators reference ReflectiveReturn; transduction operators reference ContextTransduction; memory operators reference scope/policy; conflict operators reference ConflictHoldingState.

## Non-goals (this generation)

- Runtime dispatch that actually executes an operator through the pipeline is G-BD.6 (transitions/memory/passport) + G-BD.10 (T-BACH acceptance).
- Router/mount policy that decides WHICH operators are available in WHICH Space is G-BD.5.
- Semantic body v0.3 content that gives the LIVE model access to the operator vocabulary is G-BD.4.

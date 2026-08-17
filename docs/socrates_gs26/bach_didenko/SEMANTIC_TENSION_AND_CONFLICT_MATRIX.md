# SEMANTIC TENSION AND CONFLICT MATRIX v1 — G-BD.7

Per handoff §14, every material tension between BACH additions and existing Socrates discipline is either:

- LOCALIZED (kept scope-limited),
- HELD (preserved as legitimate incompatibility),
- TRANSLATED (mapped across worlds),
- TRANSDUCED (moved with explicit loss),
- ARBITRATED_ACTION (B09 chooses action without voting truth),
- SUSPENDED (deferred pending discriminator),
- REJECTED (banned outright).

A contradiction with an explicit handling mode is legitimate structure. A hidden contradiction is a defect.

| # | Tension | Handling mode | Runtime enforcement |
|---|---|---|---|
| T1 | Constitutional sovereignty vs Space-local policies | REJECT of override | CORE v0.3 §5, §12; Space cannot override Constitution, origin/status, human ownership. Enforced by absence of authority-write path from Space to CORE. |
| T2 | BACH donor-local doctrine vs general Socrates method | LOCALIZE | `bach_operators.py` marks OP-07/OP-08 `donor_local=True`; `semantic_mount_manifest_v0.3.yaml bach_local_isolation` restricts activation to Spaces whose WorldModelMount authorises the donor. Test `test_mount_policy_v0_3.py::TestBachLocalIsolationMatchesOperatorRegistry`. |
| T3 | Scene authority vs Space proof regime | LOCALIZE | Scene may set local telos + branch hypotheses; Space governs proof regime + allowed operations. A Scene cannot re-set the proof regime. Enforced by state model — Scene has no proof-regime field. |
| T4 | Human operation ownership across SpaceTransition | REJECT of transfer | INV-009 preserved through B06/v0.2. `_governor.decide` still emits `RETURN_OPERATION` when ownership is HUMAN/JOINT + unresolved. ContextTransduction cannot transfer ownership. |
| T5 | Origin/status across transduction | TRANSDUCE with explicit loss | `emit_context_transduction` REQUIRES loss report / dropped / newly_created for TRANSDUCTION + ONTOLOGICAL_TRANSFER (raises otherwise). Passport surfaces the loss. |
| T6 | Memory validity vs retrieval convenience | HOLD | `check_cross_scope_access` enforces `CrossScopePolicy`; FORBID / REQUIRE_EXPLICIT_BRIDGE deny silent bleed. Test `test_epistemic_ops.py::TestCrossScopeAccess`. |
| T7 | Polyontology vs relativism | HOLD | Each ontology carries recognition criteria + evidence requirements (B03 v0.3 §5). ConflictHoldingState typed by family; PROJECTION_ENSEMBLE (OP-12) never votes truth. |
| T8 | Council action arbitration vs truth merger | ARBITRATE_ACTION | `open_conflict(handling_mode=ARBITRATE_ACTION)` REQUIRES `action_arbitration` string; B09 v0.3 preserved: arbitrates action, does NOT vote truth. |
| T9 | Field mode vs evidence/status discipline | HOLD | OP-05 preserves typed tensions/residue/gradients; vague prose is failure (T-BACH-04 negative). Field-hold projection still status EXPLORATORY when residue present. |
| T10 | Strong-version reconstruction vs endorsement | LOCALIZE | OP-13 marks `construction_status=RECONSTRUCTED` on passport; critique lives on a SEPARATE passport. |
| T11 | Negative capability vs task abandonment | REJECT of abandonment | OP-14 REQUIRES `discriminating_evidence_required` on HOLD conflicts — enforced by `open_conflict` (raises otherwise). |
| T12 | World-model influence on attention vs attention sovereignty | HOLD | B04 v0.3 §5: ontology can DISCIPLINE attention; ontology cannot claim TRUTH authority via attention. Board seams (§9) surface illicit transfers via OP-11. |
| T13 | TruthMode readout vs real status axes | LOCALIZE | `EpistemicPassport` exposes strict axes explicitly; `truth_mode_readout` is derived UX-only field. Passport exposes no upgrade method (test `test_epistemic_ops.py::TestPassport::test_passport_exposes_no_upgrade_method`). |
| T14 | Branch-local facts vs project/global memory | LOCALIZE | `SceneBranch.memory_scope` defaults to `BRANCH`; cross-branch access goes through `check_cross_scope_access`. Test `test_epistemic_ops.py::TestSceneDAG::test_two_incompatible_branches_do_not_contaminate`. |
| T15 | Generative synthesis freedom vs primitive-registry authority | REJECT of primitive install | `compile_bind` fails closed on unknown primitives (BindingError → ORGAN_GAP). A proposal cannot expand the registry. Tests: `test_capability_resolution_hardening.py::TestProposalPath::test_resolver_fails_closed_on_unknown_primitive_in_proposal`. |
| T16 | Reflective retreat vs technical retry | REJECT of conflation | `ReflectiveReturn` typed distinct from `ProviderStatus.RETRIES_EXHAUSTED`; D-S26-PROJ-002 repair ensures target phase re-executes rather than being state-mutated by S7. Tests: `test_projection_control_loop.py::test_reflective_return_is_not_technical_retry` + `test_stale_first_pass_hint_does_not_overwrite_reflective_revision`. |
| T17 | Iteration progress vs runaway reflection | REJECT of unbounded loop | `MAX_PROJECTION_ITERATIONS` bound + same-diagnosis fingerprint guard + epilogue-empty guard. All three exercised end-to-end in loop tests. |
| T18 | ORGAN_GAP legitimacy vs task abandonment | LOCALIZE | Gap emitted with typed evidence (both registered + synthesis failure reasons); `activation_authority=NONE`; passport surfaces the gap. Never fabricated ProjectionResult. |

## Hidden collisions detected + repaired during this pass

None. The G-BD.1..G-BD.7 additions were architected specifically to prevent the classic collisions (silent state mutation, provenance laundering, primitive installation, forced synthesis). Every collision path either:

- fails structurally (schema rejects, compile-bind raises, `emit_context_transduction` raises),
- OR opens a typed `ConflictHoldingState` with an explicit handling mode,
- OR surfaces on a passport as `known_conflicts` / `open_questions`.

## Unresolved tensions carried forward

- Deep BACH doctrine integration (prepredicative / transpredicative) remains BACH-local — no plan to make it general method (§7 conditional list).
- Runtime routing that selects v0.3 vs v0.2 semantics per run is scoped by test setup today; a first-class Space→pack binding is future work.
- LIVE model prompt vocabulary for the operator library needs a full prompt authoring pass — the v0.3 body §16 sections carry the runtime-facing summaries but router prompts are drafted, not exercised.

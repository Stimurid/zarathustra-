# NONCLAIMS AND OPEN GAPS — G-BD.12

Explicit list of what this pass does NOT claim and what remains open. Read alongside `ACCEPTANCE_REPORT.md` (what IS claimed, with evidence).

## Nonclaims

### LIVE

1. **No LIVE evidence.** L1–L8 (§19 of handoff) are marked `LIVE_BLOCKED_BY_ENVIRONMENT`. No production run occurred. The runtime substrate is deterministically ready; that is not the same as a LIVE demonstration.
2. **No claim about production 302.ai availability.** Absent credentials in the local dev environment do not imply anything about the production-adjacent environment.
3. **L5 (LIVE model-produced cutter proposal) not demonstrated.** The runtime accepts and safely compile-binds proposals (`TestProposalPath`, `TestS4ContractAcceptsProposal`) — the LIVE step of a model authoring one under production conditions is future work.

### R8

4. **R8 semantic-arm gate is NOT closed.** Historical R8 remains PARTIAL at frozen `431fa77` per handoff §20 discipline; not rerun.
5. **v0.2 semantic bodies + R8 controls remain byte-immutable.** No file under `data/socrates/current/semantic/` or `data/socrates/r8_suite/` was modified.

### Capability substrate

6. **BASIC primitive substrate only.** Four primitives ship (SpanScanner, FamilyClassifier, TargetFilter, CoverageComputer). Higher-order structures (sequence-order analysis, dramatic classification, temporal reasoning, cross-source alignment) hit ORGAN_GAP honestly. Extending the substrate is future work.
7. **Marker-scan cutters remain fixtures.** `EXTRACT_CONCEPTS` and `DIFFERENTIATED_ACCOUNT` are deterministic test fixtures for the Peskov proof, honestly labelled in the code and docs. They are NOT production-grade native Tinkuy semantic cutting.

### BACH doctrine

8. **Donor-local doctrine stays donor-local.** OP-07 FOLD and OP-08 UNFOLD_IN_MEDIUM are marked `donor_local=True` in the operator registry; the mount manifest restricts activation to Spaces whose WorldModelMount authorises the BACH donor.
9. **Prepredicative / transpredicative / zero-medium claims are NOT integrated as general method.** They remain BACH-local conditional per §7 handoff.

### Runtime coverage

10. **Runtime execution of the operator library through the pipeline is partial.** Operators bound to `PROJECTION_SPEC` / `REFLECTIVE_LOOP` route through existing ADR-S26-022/023 paths (fully exercised). Operators bound to `TRANSDUCTION` / `SCENE_BRANCH` / `MEMORY_SCOPE` / `CONFLICT_HOLD` / `PASSPORT_ONLY` have runtime helpers in `epistemic_ops.py` and are exercised by G-BD.10 T-DID/T-BACH acceptance. Operators bound to `ATTENTION_CONFIG` have documented seams but no runtime annotation write yet (attention config on ProjectionResult is a bounded follow-up).
11. **Attention config annotation on ProjectionResult** is not yet implemented as a runtime write; the design lives in B04 v0.3 §7 and `BACH_OPERATOR_IMPLEMENTATION_MAP.md` as a G-BD.6 follow-up target.

### Workspace / UI

12. **No Workbench UX work.** Handoff §22 forbids UI work in this pass. Eight items classified as `UI_PROJECTION_OF_EXISTING_STATE` in the Didenko remaining-delta register wait for a Workbench pass — the backend evidence they would render already exists.
13. **First-class Workspace registry deferred.** D6 (§15 Didenko coverage) is marked PARTIAL: the default workspace Space stands in for a full Workspace registry.
14. **"Living memory" streaming concept NOT implemented.** Classified AMBIGUOUS_SOURCE; deferred pending owner clarification.

### Provenance / Drive

15. **Drive access unauthenticated locally.** Every Drive ID is preserved in local docs artefacts (`SEMANTIC_BODY_V03_DELTA_MANIFEST.md`, `DIDENKO_COVERAGE_MATRIX.md`, `CROSS_LAYER_TRACEABILITY.md`). No claim is made that the Drive documents were byte-verified against local reconstructions.

### Router prompts

16. **v0.3 router prompt files NOT authored as separate documents.** The v0.3 body §16 sections carry the runtime-facing prompt-authoring summaries; a full v0.3 router prompt bundle is future work. This does not affect deterministic acceptance because the deterministic tests use hint executors, not LIVE router prompts.

### `P001_UNBLOCKED`

17. **`P001_UNBLOCKED = NO`.** Per §20 join gate: hardening PASS, BACH/Didenko v0.3 technical+semantic PASS, conflict audit PASS, Didenko coverage FULL/PARTIAL as documented, cross-layer traceability PASS, mandatory deterministic tests PASS, full backend regression PASS — but targeted live campaign NOT PASS. Any single missing condition is NO per §20.

## Open gaps carried into future passes

### Runtime completeness

- Attention config annotation on ProjectionResult (G-BD.6 target, not implemented).
- Full Workspace registry with per-Workspace Space enumeration.
- Multi-Space simultaneous execution beyond MAX_PROJECTION_ITERATIONS.

### Semantic package

- Full v0.3 router prompt bundle as separate files under `data/socrates/candidate_v0_3/routers/*_v0.3_semantic.md`.
- B06 / B09 v0.3 candidates if a future pass identifies a dependency change that requires them.
- Deep BACH doctrine integration (prepredicative / transpredicative) if owner decides to promote it from donor-local.

### LIVE evidence

- L1–L8 execution on the production-adjacent environment.
- Ongoing LIVE regression campaign.

### Workbench

- UI cards for Passport / Transduction / Conflict / Space DAG / Branch archive.
- Novelty compass per-user aggregation.
- Attention config visualisation.

### Substrate expansion

- Additional primitives for sequence-order, temporal reasoning, cross-source alignment, dramatic classification, network / graph structure — as real operations demand them.
- Fabric-parser / live-model-cutter capabilities registered alongside the deterministic marker-scan fixtures.

### Ambiguous items

- "Living memory" streaming — decide whether it is a new concept or an aggregation of B05 scopes.

## Explicit reminder

Every gap here is documented so that a future pass can pick up work without re-derivation. This list plus `CURRENT_TASK_STATUS.yaml` + `CURRENT_TASK_CHECKLIST.md` is the durable resume state per §2 of the handoff.

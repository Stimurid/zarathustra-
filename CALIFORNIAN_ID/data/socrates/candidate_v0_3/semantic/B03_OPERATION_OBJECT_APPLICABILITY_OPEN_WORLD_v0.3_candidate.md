# B03 — OPERATION, OBJECT, APPLICABILITY, OPEN WORLD v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2 `B03_OPERATION_OBJECT_APPLICABILITY_OPEN_WORLD_v0.2_candidate.md`
Generation: G-S26X G-BD.4

## 1. Provenance and status
v0.3 extends v0.2 with:

- ProjectionSynthesisProposal (D-S26-GEN-003 typed model-produced spec).
- Three-branch capability resolution (ADR-S26-023: REGISTERED / SYNTHESIS / ORGAN_GAP).
- Distinction between translation / reframe / ontological transfer / transduction.
- S4 authoring of declarative cutter proposals under typed jurisdiction.

v0.2 semantics preserved: OperationDeclaration precedes execution; ApplicabilityAssessment gates coercion; open-world outcome is diagnosed, not forced.

## 2. Purpose
B03 v0.3 makes explicit the four-step apparatus discipline:

1. Recognise the operation the request presupposes.
2. Decide whether that operation is applicable to the material.
3. If NOT applicable and a covering operation exists, propose the revised operation as a typed ProjectionSynthesisProposal.
4. Physically execute via the resolver's REGISTERED / SYNTHESIS branch, OR emit ORGAN_GAP if neither path fits.

## 3. Genesis
v0.2's operation/object grammar solved the "forced flat cutter" defect at semantic level. v0.3 makes the runtime path executable: LIVE Socrates can now author its own cutter proposal (D-S26-GEN-003), the runtime validates + compile-binds it against existing primitives, and executes it against the ORIGINAL immutable source (D-S26-PROJ-002 target-phase re-entry preserved).

## 4. World model
Every projection carries:

- SemanticProjectionSpec (v0.2 fields, plus D-S26-PROV-003 lineage refs).
- GeneratedCutterSpec (v0.3, when synthesised) with declaratively-named primitive composition graph.
- ProjectionResult with objects + residue (D-S26-PROV-004 direct provenance to projection / spec / operation / ontology / space / scene / branch).
- ProjectionDiagnostics with typed signals.
- Optional CapabilityResolution record naming the branch.

## 5. Distinctions and false equivalents
- Operation ≠ ontology ≠ recognition policy ≠ segmentation policy ≠ evidence requirement. Each may vary independently.
- Translation (preserves identity) ≠ reframe (changes local framing) ≠ ontological transfer (changes object generation) ≠ transduction (destination medium participates in producing the new object).
- Registered capability ≠ generic primitive ≠ generated cutter spec ≠ compiled cutter (ADR-S26-023).
- Nearest cutter ≠ correct cutter. Coercion is banned; ORGAN_GAP is honest.

## 6. Recognition signals
- Diagnostics signals: OPERATION_MISMATCH, ONTOLOGY_LIMIT, MULTI_ONTOLOGY, OBJECT_GENERATOR_LIMIT, RECOGNITION_FAILURE, FORCED_COMPLETENESS, SCENE_MISMATCH, APPLICABILITY_FAILURE.
- Model-authored proposal in S4 delta (D-S26-GEN-003).
- Board seam transfer attempt (OP-11) — property of a tool being attributed to the world.

## 7. Operation grammar
S4 may emit:

- Plain typed operation (v0.2 behaviour, unchanged).
- ProjectionSynthesisProposal (v0.3 addition) under S4's declared jurisdiction. The proposal is UNPRIVILEGED DATA.

Runtime flow (per ADR-S26-023 with D-S26-GEN-003 repair):

    proposal or plain operation
    → CapabilityResolver.resolve OR .resolve_from_proposal
    → REGISTERED / SYNTHESIS (compile-bind + execute) / ORGAN_GAP
    → ProjectionResult stamped with full provenance (G-BD.1)
    → diagnostics
    → S7 reflective epilogue if mismatch
    → actual target-phase re-entry (D-S26-PROJ-002)

## 8. Applicability and non-applicability
Direct-assistance operations with no source projection stay a no-op (§11 handoff invariant). Operations without a registered cutter but with a compositional hypothesis go through SYNTHESIS. Operations with neither → ORGAN_GAP.

## 9. Positive examples
- EXTRACT_CONCEPTS on concept-only material → REGISTERED_CAPABILITY.
- EXTRACT_PRIORITY_TAGS on tagged backlog (novel operation) → CUTTER_SPEC_SYNTHESIS via pattern hypothesis; compile-bind succeeds; executes.
- DIFFERENTIATED_ACCOUNT on heterogeneous material → REGISTERED_CAPABILITY covers Peskov residue.

## 10. Negative examples
- Silent coercion of residue into pseudo-concepts (v0.2 Peskov defect).
- Generated proposal names an unknown primitive → must FAIL CLOSED to ORGAN_GAP, never install a primitive.
- Fabricated ProjectionResult when resolver emitted ORGAN_GAP.
- Fingerprint collision on materially different specs (D-S26-GEN-002 defect, resolved G-BD.1).

## 11. Boundary cases
- Operation applicable but yields sparse residue → status EXPLORATORY → passport surfaces open question.
- Multiple ontologies fit → PROJECTION_ENSEMBLE (OP-12) executes each independently; comparison surfaces as ConflictHoldingState, not vote-to-truth.

## 12. Machine distortions and repair
- Model asserts a new operation but does not provide primitive composition → resolver emits ORGAN_GAP; no fake execution.
- Model relabels the same composition under a new name → fingerprint canonicalisation (D-S26-GEN-002) exposes the duplicate.
- Model authors a proposal that tries to install code via params → schema rejects unknown fields; compile-bind refuses unknown primitives.

## 13. Internal tensions
- Speed of REGISTERED_CAPABILITY vs expressive power of SYNTHESIS → registered is preferred when it fits exactly.
- Novel synthesis vs primitive-substrate insufficiency → ORGAN_GAP is legitimate structure, not defect.

## 14. Neighbour transitions
- B03 → B07 (reflective retreat when apparatus itself is the issue via OP-10).
- B03 → B08 (polyontology + ensemble via OP-12).
- B03 → B04 (attention configuration when operator is FIELD_HOLD via OP-05).

## 15. Stop, return, escalation
Stop when a ProjectionResult is committed (registered or synthesised) OR ORGAN_GAP is emitted. Return to S7 for reflective retreat. Escalate to B08 for polyontology.

## 16. Runtime-facing summary
v0.3 = v0.2 operation/applicability discipline + generative synthesis pathway (D-S26-GEN-003) + canonical fingerprint (D-S26-GEN-002) + direct provenance (D-S26-PROV-003/004) + three-branch capability resolution (ADR-S26-023) + no coercion / no fabrication invariants.

## 17. Lacunae and source gaps
- Rich primitive substrate beyond the four G-BD.2 primitives is future work; higher-order operators may often hit ORGAN_GAP until the substrate grows.
- LIVE-model synthesis under production conditions (L5 in G-BD.11) is deterministic-only in this pass.

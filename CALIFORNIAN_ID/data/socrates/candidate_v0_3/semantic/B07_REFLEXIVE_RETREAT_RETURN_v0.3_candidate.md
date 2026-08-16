# B07 — REFLEXIVE RETREAT, RETURN v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2
Generation: G-S26X G-BD.4

## 1. Provenance and status
v0.3 incorporates D-S26-PROJ-002 target-phase re-entry repair, generative apparatus revision (OP-10 through ADR-S26-023), and ContextTransduction as changed forward action.

## 2. Purpose
Reflect at the SHALLOWEST adequate level:

- projection / operation → S7 → ACTUAL S4 re-entry (D-S26-PROJ-002).
- scene / branch → S7 → S1 re-entry (branch fork or scene revision).
- space / world → S7 → SpaceTransition via ContextTransduction.
- constitution → EXTREMELY RARE — human authority required.

Reflection without actual changed target path remains a defect.

## 3. Genesis
v0.2 established the reflective retreat vocabulary. v0.3 makes it executable and honest:

- ReflectiveReturn is REVISION CONTEXT, not side-channel state mutation (D-S26-PROJ-002).
- Target phase MUST re-execute; it reads pending_reflective_context and emits a fresh validated delta.
- Apparatus revision (OP-10) routes through CapabilityResolver — REGISTERED / SYNTHESIS / ORGAN_GAP.

## 4. World model
Reflection stack (ADR-S26-022 + G-BD.1 D-S26-PROV-003):

- ProjectionDiagnostics with typed signals.
- ReflectiveReturn with retreat_level ∈ {R0..R6} and return_target ∈ {S1, S3, S4}.
- Explicit typed lineage: parent_projection_id, revises_projection_id, triggered_by_diagnostic_id, reflective_return_id.

## 5. Distinctions and false equivalents
- Reflective retreat ≠ technical retry (RETRIES_EXHAUSTED). One CHANGES the governing hypothesis; the other doesn't.
- Reflective retreat ≠ human return (RETURN_OPERATION). One is internal; the other is INV-009 to the human.
- Return to S4 ≠ overwrite S4. The target phase re-executes and validates the revised delta itself.
- Space transition ≠ scene branch ≠ projection revision. Choose the shallowest adequate.

## 6. Recognition signals
- ProjectionDiagnostics.mismatch = True → epilogue reflective S7 (dedicated call, not the council branch).
- Scene-level mismatch → S7 with return_target=S1.
- Space-level mismatch → S7 with return_target=S1 AND ContextTransduction proposal.
- Apparatus insufficiency detected → OP-10 REVISE_APPARATUS.

## 7. Operation grammar
- Epilogue S7 emits ReflectiveReturn (OP-01, OP-03, OP-10 supply the level).
- Runtime records context via _record_reflective_context; NEVER writes state.operation / scene directly (D-S26-PROJ-002).
- Target phase re-executes at return_target and emits fresh validated delta.
- If REVISE_APPARATUS demands primitives that don't exist → ORGAN_GAP path.

## 8. Applicability and non-applicability
Reflection is CONDITIONAL. Direct-assistance runs never invoke reflective S7. Complex requests may traverse it several times bounded by MAX_PROJECTION_ITERATIONS + same-diagnosis guard + epilogue-empty guard.

## 9. Positive examples
- Peskov: P1 concept extraction leaves residue → OP-03 ONTOLOGICAL_TRANSFER → ReflectiveReturn(R1, S4) → S4 re-executes emitting DIFFERENTIATED_ACCOUNT → P2 covers all.
- Scene mismatch: telos was mis-set → ReflectiveReturn(R3, S1) → S1 re-emits scene → S4 re-derives operation.
- Apparatus insufficient: OP-10 attempts revision, primitives insufficient → ORGAN_GAP.

## 10. Negative examples
- Prose-only reflection ("perhaps a different cut is needed") with no typed ReflectiveReturn — must NOT trigger a second projection.
- Silent state.operation write during epilogue (pre-repair defect, banned).
- Skipping the target phase and starting pass 2 at return_target+1 (pre-repair defect, banned).
- Technical retry counted as reflection.

## 11. Boundary cases
- Same-diagnosis fingerprint on second attempt → guard fires; stop cleanly.
- Iteration bound reached with distinct diagnostics each time → guard fires.
- ReflectiveReturn with unchanged operation → not accepted (guard).

## 12. Machine distortions and repair
- Model asserts "we should revise the operation" without emitting a typed ReflectiveReturn → runtime treats as prose; no loop restart.
- Model repeatedly emits identical revised_operation_kind → loop guard.
- Model emits ReflectiveReturn but downstream target phase hint is stale → visible in state.operation.kind, detectable in tests (T-PROV-04 stale-hint negative).

## 13. Internal tensions
- Depth of retreat vs cost. Prefer shallowest adequate.
- Reflective loop vs human return. When ownership is HUMAN and unresolved → INV-009 wins over reflection.

## 14. Neighbour transitions
- B07 → B03 (revised operation lands at S4).
- B07 → B01 (revised scene lands at S1).
- B07 → B08 (polyontology + apparatus revision).

## 15. Stop, return, escalation
Stop on: same-diagnosis guard, iteration bound, epilogue-empty, ORGAN_GAP. Return-to-ordinary via OP-18 when pressure disappears.

## 16. Runtime-facing summary
v0.3 = v0.2 reflective retreat vocabulary + D-S26-PROJ-002 target-phase re-entry + explicit typed lineage (D-S26-PROV-003) + OP-10 apparatus revision via capability resolver + ContextTransduction as changed forward action.

## 17. Lacunae and source gaps
- Rich retreat-level policies (R4/R5/R6) partially implemented (R1/R2/R3 exercised end-to-end).
- Constitutional retreat (R5) explicitly out of scope for this pass.

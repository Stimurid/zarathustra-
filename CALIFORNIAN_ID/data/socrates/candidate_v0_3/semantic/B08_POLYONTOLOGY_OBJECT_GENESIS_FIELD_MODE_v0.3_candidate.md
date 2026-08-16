# B08 — POLYONTOLOGY, OBJECT GENESIS, FIELD MODE v0.3 — candidate
Status: v0.3 candidate; delta over frozen v0.2
Generation: G-S26X G-BD.4

## 1. Provenance and status
v0.3 adds:

- WorldModelMount as first-class object with typed provenance ≠ activation.
- ConflictHoldingState families + handling modes (§6.7).
- BACH operator vocabulary OP-01..OP-18 with donor-local isolation (OP-07 fold, OP-08 unfold-in-medium).
- Generative cutter proposal path (D-S26-GEN-003) as apparatus revision mechanism.

v0.2 polyontology + field mode semantics preserved.

## 2. Purpose
Multiple grounded world-models may co-exist. Translation between them is typed and possibly lossy. Aporia is legitimate structure when material non-mergeability is real.

## 3. Genesis
v0.2 named polyontology + field mode + no-object. v0.3 makes both executable: world models mount as typed records; conflicts are typed and held with explicit handling mode; the runtime never forces synthesis where evidence forbids it.

## 4. World model
- Space contains WorldModelMounts.
- Each mount has mount_mode ∈ {PRIMARY, OVERLAY, LENS, CONTRAST, NEGATIVE_CONTROL, ARCHIVAL}.
- Conflict families: {ONTOLOGY, EPISTEMIC_STATUS, AUTHORITY, OPERATION, VALUE, CAUSAL_GRAMMAR, IDENTITY_RULE, MEMORY_FORCE}.
- Handling modes: {LOCALIZE, HOLD, TRANSLATE, TRANSDUCE, ARBITRATE_ACTION, SUSPEND, REJECT}.

## 5. Distinctions and false equivalents
- Polyontology ≠ relativism. Ontologies are typed with recognition criteria + evidence requirements.
- ConflictHoldingState ≠ defect. Silent contradiction is defect; typed conflict is legitimate.
- Field mode ≠ vague prose. Preserved tensions are typed evidence.
- Analogy ≠ mechanism identity (OP-04 vs OP-12).

## 6. Recognition signals
- Multiple projections yield mutually valid but incompatible objects → PROJECTION_ENSEMBLE (OP-12).
- Two grounded models disagree without discriminator → PRESERVE_APORIA (OP-14) with HOLD.
- Board seam transfer detected → BOARD_SEAM_CHECK (OP-11) with REJECT.
- BACH-local doctrine invoked outside authorised Space → mount check refuses.

## 7. Operation grammar
- Multiple WorldModelMounts per Space with distinct mount_modes.
- OP-03 ONTOLOGICAL_TRANSFER produces a new spec under a changed ontology.
- OP-12 PROJECTION_ENSEMBLE executes independent projections; comparison surfaces as ConflictHoldingState.
- OP-14 PRESERVE_APORIA opens a ConflictHoldingState with discriminating_evidence_required.
- OP-07 / OP-08 (donor-local) only fire when the current Space authorises them.

## 8. Applicability and non-applicability
B08 applies when polyontology, apparatus revision, or held conflict is materially at issue. Direct-assistance runs never traverse it.

## 9. Positive examples
- Same source read under CONCEPT ontology + DIFFERENTIATED ontology → both projections preserved with lineage.
- Two grounded incompatible causal models for the same phenomenon → PRESERVE_APORIA + discriminator + action arbitration.
- BACH donor concept invoked in a Space that mounts BACH LENS → mount activates locally; other Spaces untouched.

## 10. Negative examples
- Merging two grounded ontologies by majority vote (banned — B09 arbitrates action, not truth).
- Auto-mounting a donor world because a lexical cue appears (§18 negative test).
- BACH-local doctrine bleeding into a Space that never authorised the mount.
- Fabricating a projection to resolve conflict without discriminator.

## 11. Boundary cases
- Two mounts of the SAME ontology under different mount_modes in different Spaces → legitimate.
- ConflictHoldingState without discriminator → status="held", passport surfaces open_question.
- ORGAN_GAP inside B08 context = the apparatus itself is insufficient (via OP-10).

## 12. Machine distortions and repair
- Model tries to "resolve" a genuine conflict prematurely → OP-14 preserves aporia.
- Model treats functional rhyme as mechanism identity → BOARD_SEAM_CHECK rejects.
- Vague mystical prose in field mode → count as failure (T-BACH-04).

## 13. Internal tensions
- Polyontology tolerance vs action requirement → B09 arbitrates action; truth stays held.
- Field mode preservation vs discriminator identification → both required for HOLD.
- Donor-local doctrine vs general method → mount policy enforces isolation.

## 14. Neighbour transitions
- B08 → B03 (new ProjectionSpec under changed ontology).
- B08 → B07 (reflective retreat to revise apparatus).
- B08 → B09 (action arbitration in conflict).

## 15. Stop, return, escalation
Held conflict → status stays "held" pending discriminator OR review_trigger. ORGAN_GAP → run terminates cleanly with typed gap.

## 16. Runtime-facing summary
v0.3 = v0.2 polyontology + WorldModelMount typed records + ConflictHoldingState families/modes + BACH operator vocabulary + donor-local isolation + generative apparatus revision via ADR-S26-023.

## 17. Lacunae and source gaps
- Deeper BACH doctrine (prepredicative / transpredicative) remains BACH-local; not integrated as general method.
- Full multi-Space simultaneous execution is bounded by MAX_PROJECTION_ITERATIONS.

# SEMANTIC BODY v0.3 DELTA MANIFEST — G-BD.4

v0.3 candidate semantic package delivered under `CALIFORNIAN_ID/data/socrates/candidate_v0_3/`. v0.2 remains frozen in `CALIFORNIAN_ID/data/socrates/current/semantic/` as the R8 evidence control. Nothing in v0.3 mutates v0.2 in place.

Nine v0.3 candidate bodies ship (17-section standard preserved). B06 and B09 remain at v0.2 identities in this pass (no dependency change requires patching them).

## Per-body delta summary

| Body | v0.3 file | Delta over v0.2 |
|---|---|---|
| CORE | `SOCRATES_CORE_SEMANTIC_BODY_v0.3_candidate.md` | Governance of the typed epistemic environment (Space / WorldModelMount / Scene DAG / Branch / Transduction / Passport / Conflict); PROVENANCE ≠ ACTIVATION; TruthMode is derived; BACH transferable distinctions §7. |
| B01 | `B01_SCENE_TELOS_ROLE_AUTHORITY_v0.3_candidate.md` | EpistemicSpace membership + Scene DAG identity + SceneBranch fork; optional OP-15 SITUATION_TO_TASK decomposition (not ritualised). |
| B02 | `B02_ORIGIN_STATUS_TEMPORALITY_v0.3_candidate.md` | EpistemicPassport read-model; OP-13 strong-version reconstruction; OP-16 novelty relativization; construction_status enum. |
| B03 | `B03_OPERATION_OBJECT_APPLICABILITY_OPEN_WORLD_v0.3_candidate.md` | ProjectionSynthesisProposal (D-S26-GEN-003) authoring path; three-branch capability resolution (ADR-S26-023); D-S26-GEN-002 canonical fingerprint + D-S26-PROV-003/004 direct provenance; translation/reframe/ontological-transfer/transduction distinctions. |
| B04 | `B04_ATTENTION_VNYATIE_RETRIEVAL_v0.3_candidate.md` | OP-05 FIELD_HOLD (typed tensions, not vagueness); OP-11 BOARD_SEAM_CHECK; OP-17 CONTEXT_QUARANTINE; cross-scope retrieval policy vocabulary. |
| B05 | `B05_MEMORY_FORMATION_STATE_WRITE_v0.3_candidate.md` | MemoryValidityScope (9 scopes) + CrossScopePolicy (4 modes); OP-09 STABILIZE_OBJECT; scoped memory enforcement contract. |
| B06 | (unchanged — v0.2 identity retained) | No dependency change requires patching in this pass. |
| B07 | `B07_REFLEXIVE_RETREAT_RETURN_v0.3_candidate.md` | D-S26-PROJ-002 actual target-phase re-entry; ReflectiveReturn as REVISION CONTEXT (not silent state mutation); explicit typed lineage; OP-10 REVISE_APPARATUS via capability resolver; ContextTransduction as changed forward action. |
| B08 | `B08_POLYONTOLOGY_OBJECT_GENESIS_FIELD_MODE_v0.3_candidate.md` | WorldModelMount typed records; ConflictHoldingState families/modes; BACH operator vocabulary; donor-local isolation (OP-07 fold, OP-08 unfold-in-medium); generative apparatus revision. |
| B09 | (unchanged — v0.2 identity retained) | B09 arbitrates ACTION, does NOT vote truth. Invariant preserved without new file. |
| B10 | `B10_INTERVENTION_DIALOGUE_SELF_REVIEW_STATE_CHANGE_v0.3_candidate.md` | Passport rendering; direct vs complex render mode selection; OP-18 RETURN_TO_ORDINARY_ASSISTANCE when reflective/conflict/branch pressure disappears. |

## Registry manifest

`CALIFORNIAN_ID/data/socrates/candidate_v0_3/routers/semantic_body_registry_v0.3.yaml` declares the per-body version + delta summary. Loaded via `SemanticBodyRegistry(semantic_dir=DATA_ROOT/'candidate_v0_3'/'semantic', mount_dir=...)` — a scoped registry pointer keeps v0.3 out of the default (v0.2) load path so R8 controls remain byte-immutable.

## Preservation guarantees

- No file under `CALIFORNIAN_ID/data/socrates/current/semantic/` was modified. R8 evidence controls remain byte-immutable.
- No file under `CALIFORNIAN_ID/data/socrates/r8_suite/` was modified (verified by inspection).
- v0.3 lives in a wholly separate directory tree — the default `SemanticBodyRegistry()` continues to load v0.2 exclusively; runs that want v0.3 must construct a scoped registry.
- B06 + B09 continue to load at v0.2 identity from the default tree; v0.3 makes no claim about them.

## Non-goals

- v0.3 mount policy + router prompts + phase-context assembly are G-BD.5.
- Runtime consumers (Scene DAG traversal, transition execution, memory-scope enforcement, passport rendering) are G-BD.6.
- Deterministic acceptance tests exercising v0.3 semantics end-to-end are G-BD.10.
- LIVE model authored under v0.3 vocabulary is G-BD.11 (L1..L8).

## Test coverage (this generation)

`tests/workbench/test_semantic_v0_3.py` verifies:

- All nine v0.3 candidate files are loadable through a scoped `SemanticBodyRegistry`.
- Each carries its declared v0.3 semantic version.
- The default (unscoped) `SemanticBodyRegistry()` continues to load v0.2 exclusively — no accidental cross-contamination.
- v0.2 file hashes are preserved (registry read of v0.2 bodies returns identical byte counts to a pre-G-BD.4 read).

# HANDOFF — G-P13R / G-P14R PERSONA RUNTIME CLOSURE

**Status:** `completed_candidate`
**Runtime status:** `runtime_ready_candidate`
**Canonical status:** `candidate`
**Date:** 2026-07-28

## Completed generations

### G-P10-closure — Rationalist source completion

- created candidate source manifest;
- created 48 normalized cards covering all 24 exact Rationalist operations;
- preserved source-depth gaps and provenance classes.

### G-P13-R — deterministic machine reconciliation

- replaced active seed cards for all seven personas;
- archived original seed cards as `cards.seed_archived.jsonl`;
- normalized 330 active cards to `PERSONA_CARD_SCHEMA.json`;
- mapped every card to an exact PersonaPack operation;
- added primary/secondary operation links so 112/112 exact operations are retrievable;
- rebuilt seven v0.2 PersonaPack archives and the overall package;
- validated 330 cards with zero schema errors.

### G-P14-R — retrieval and activation closure

- built portable hybrid retrieval: SQLite FTS5 + TF-IDF;
- added filters by persona, namespace and primary/secondary exact operation;
- ran retrieval probes for all seven personas;
- executed a sequential seven-head activation scenario;
- validated 7/7 BodyDelta objects;
- saved trace and final BodyProjection;
- passed the technical activation gate.

## Exact outputs

- `manifest.yaml`
- `shared/PERSONA_CARD_SCHEMA.json`
- `shared/CARD_TO_EXACT_OPERATION_REGISTRY.yaml`
- `personas/*/cards.jsonl`
- `personas/*/operation_map.yaml`
- `runtime/index/retrieval_index.sqlite`
- `runtime/index/tfidf_matrix.npz`
- `runtime/index/vectorizer.joblib`
- `runtime/retrieve.py`
- `runtime/activation_trace.jsonl`
- `runtime/body_projection_after.json`
- `reports/SCHEMA_NORMALIZATION_REPORT.yaml`
- `reports/OPERATION_MAPPING_REPORT.yaml`
- `reports/RETRIEVAL_INDEX_REPORT.yaml`
- `reports/ACTIVATION_GATE_REPORT.yaml`
- `SHA256SUMS.txt`

## Closed defects

- `D-PERSONA-001 MISSING_R_SOURCE_PASS` — closed as candidate by G-P10-closure.
- `D-PERSONA-002 ENRICHED_PACKAGES_NOT_MERGED` — closed.
- `D-PERSONA-003 CARD_SCHEMA_DIVERGENCE` — closed.
- `D-PERSONA-004 OPERATION_ID_DIVERGENCE` — closed.
- `D-PERSONA-007 RETRIEVAL_INDEX_NOT_BUILT` — closed.
- `D-PERSONA-008 ACTIVATION_TRACE_MISSING` — closed.

## Remaining boundaries

- live execution in the actual Zarathustra host/provider has not been performed;
- behavioral distinctiveness and adversarial evaluation remain a separate campaign;
- source-depth gaps recorded in individual manifests remain open;
- status remains candidate until canonical review.

## Next step

Bind this portable package to the Zarathustra host adapter without changing the common card schema or exact operation IDs. Save host acceptance separately from this portable activation proof.

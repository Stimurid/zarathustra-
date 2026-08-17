# ACCEPTANCE REPORT — G-BD.10 deterministic + full regression

Full backend at final SHA on branch `socrates/gs26-bach-didenko-integration`:

```
897 passed, 4 skipped
```

Delta from 746/4 baseline at `2ecc070` (task start):

| Generation | New tests | Cumulative |
|---|---|---|
| G-BD.0 | 0 | 746 |
| G-BD.1 hardening (T-PROV-01/02/03/04) | +16 | 762 |
| G-BD.2 epistemic model | +28 | 790 |
| G-BD.3 BACH operators | +33 | 823 |
| G-BD.4 semantic v0.3 | +7 | 830 |
| G-BD.5 mount policy v0.3 | +11 | 841 |
| G-BD.6 epistemic ops | +25 | 866 |
| G-BD.10 T-DID + T-BACH + negatives | +31 | 897 |

## Deterministic acceptance families

### T-PROV (G-BD.1 hardening)

- T-PROV-01 fingerprint canonicalisation — 5 tests, all PASS.
- T-PROV-02 explicit lineage — 2 tests, all PASS.
- T-PROV-03 direct object provenance — 3 tests, all PASS.
- T-PROV-04 ProjectionSynthesisProposal path — 6 tests, all PASS.

### T-DID (G-BD.10)

- T-DID-01 SPACE VS SCENE — PASS.
- T-DID-02 SCENE BRANCH ISOLATION — 2 tests, all PASS.
- T-DID-03 PASSPORT HONESTY — PASS (all status axes preserved; held conflict surfaced).
- T-DID-04 SPACE TRANSITION WITHOUT LAUNDERING — 2 tests, all PASS (bare transduction without loss report raises).
- T-DID-05 MEMORY SCOPE NON-CONTAMINATION — 5 parametrised policy modes, all PASS.

### T-BACH (G-BD.10)

- T-BACH-01 TRANSLATION VS TRANSDUCTION — PASS.
- T-BACH-02 BOARD SEAM — PASS.
- T-BACH-03 ONTOLOGY CHANGES OBJECT — PASS (two projections with different ontology both addressable; fingerprints distinct).
- T-BACH-04 FIELD HOLD WITHOUT FOG — 2 tests, all PASS (HOLD without discriminator raises).
- T-BACH-05 REVISE APPARATUS THROUGH CAPABILITY RESOLVER — PASS (novel op with pattern → SYNTHESIS; novel op without → ORGAN_GAP).
- T-BACH-06 CONFLICT HELD WITHOUT FORCED SYNTHESIS — PASS.
- T-BACH-07 RETURN TO ORDINARY ASSISTANCE — PASS.

### Peskov regression

The G-S26 Peskov end-to-end suite (11 tests in `test_peskov_projection_loop.py`) preserved as ADR-S26-022/023 acceptance. Phase sequence remains `S0..S10 → S7 → S4..S10` (actual target-phase re-entry from D-S26-PROJ-002 repair).

### Negatives (§18 list)

All 11 negatives in `test_bach_didenko_acceptance.py::TestNegativesFromHandoffSection18` PASS:

- Space ≠ Scene aliasing.
- TruthMode cannot override status.
- Branch fact cannot silently become global.
- Neutral summary without loss is banned (raises).
- Lexical BACH cue does not auto-mount BACH world (mount manifest ban).
- BACH donor-local operators marked local (OP-07, OP-08).
- Council cannot merge truth by vote (no VOTE_TRUTH mode in `ConflictHandlingMode`).
- Generated cutter with unknown primitive never executes (compile-bind raises).
- Generated proposal cannot mint authority.
- Technical retry not counted as reflection.
- Identical apparatus revision hits loop bound.

## Regressions

Zero. Every previously green test continues to pass. Frozen R8 evidence at `431fa77` remains byte-immutable (v0.2 files unmodified, `data/socrates/r8_suite/` unmodified).

## UI status

`NOT_RERUN_UNCHANGED_SURFACE`. This pass touches `socrates_runtime/`, `data/socrates/candidate_v0_3/`, `data/socrates/current/contracts/` (additions only), backend tests, and docs. No UI surface (Workbench, Arena) was modified. UI acceptance from prior passes remains valid.

## Full backend command

Reproduce with:

```bash
cd CALIFORNIAN_ID
PYTHONPATH=src python -m pytest -q
```

Expected: `897 passed, 4 skipped`.

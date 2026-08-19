# G-S27 / G-S28 / Kvaqin — status at RC1 boundary

## G-S27 Real Scenarios: **SOURCE_BLOCKED_EXTERNAL_CORPUS**

Handoff §12 names ten seed families S01–S10. The repository holds:

- Zero test files matching `*gs27*`, `*scenario*`, `*baseline*compare*`.
- Zero fixture files with S01/S02/…/S10 IDs bound to source material.
- No matched-pair harness that runs the SAME case against a Baseline
  0 model and against Socrates on identical provider configuration.

Handoff §12–13 explicitly requires:
- same base model family, same provider configuration, same source
  snapshot, same tool availability, same material, same context budget;
- >= 7 real source-ready scenarios live;
- collect input, source refs, config snapshot, baseline trace,
  Socrates trace, governing transition, human correction burden,
  latency/resource delta, evaluation vector.

Handoff §13:
> No hand-authored "Socrates answer" is acceptable as evidence.

Handoff §12:
> Do not invent source material for blocked cases.

The G-S27 scenario corpus + baseline harness live externally
(Drive/dev environment). This repository is not the authoring surface
for that corpus. Per campaign anti-fabrication rules, no synthetic
S01–S10 corpus was written for this RC1 pass.

**Verdict:** `SOURCE_BLOCKED_EXTERNAL_CORPUS`. Nonblocking for RC1
per §21 (source gap that a post-RC operator activity can close).

## G-S27 Product Surfaces: **PARTIAL_AUDIT_PRESENT**

Present in repo:

- `CALIFORNIAN_ID/src/californian_id/web_ui.py` — HTTP surface,
  runs and exposes Socrates `/api/socrates/run`; also exposes
  `/api/reflect/cross_run` and `/reflect/cross_run` for run-vs-run
  compare (LLM-synthesised structural diff, not raw side-by-side).
- `CALIFORNIAN_ID/src/californian_id/cross_run.py` — `search_runs` +
  `compare_runs(workspace_id, run_id_a, run_id_b)`, LLM-driven
  synthesis of A-vs-B commonality, differences, evolution.
- `CALIFORNIAN_ID/workbench_ui/` — Vite + React workbench SPA;
  components include `BranchPanels`, `Catalogue`, `FieldProjection`,
  `Inspector`, `NodeOverview`, `PipelineGraph`, `PromptCopilot`,
  `PromptEditor`, `RagPanel`, `RightDock`, `RunHistory`, `RunPanel`.
  QA screenshots include `07_run_compare.png` — a compare surface
  has been exercised.

What is present is a **developer/operator workbench** and a
run-vs-run compare endpoint, not the dedicated Socrates-vs-Baseline
public two-panel product surface + three-branch research surface
defined by handoff §14.

For RC1:
- **Backend compare capability**: present (`cross_run.compare_runs`).
- **Operator workbench**: present (`workbench_ui`).
- **Dedicated Socrates-vs-Baseline public two-panel surface**: **not
  built as a dedicated Socrates deliverable in this repository**. It
  would ride on top of the G-S27 matched-pair corpus, which is
  itself `SOURCE_BLOCKED`.

**Verdict:** `PARTIAL_AUDIT_PRESENT`. Nonblocking for RC1 (§21):
the release-critical piece is the runtime that produces the traces,
and the runtime is at production `5cb7707` with all authority
invariants preserved. The dedicated public product surface is a
`POST_RC_PRODUCT_ENHANCEMENT`.

## G-S28 Stress: **SOURCE_BLOCKED_EXTERNAL_CORPUS**

Handoff §16 names 12 stress families:

```
1  last-turn overwrite / false shared memory
2  praise / sycophancy
3  hostile disagreement / status attack
4  urgency / closure pressure
5  tool-heavy procedural occupation
6  long-context drift / compaction
7  role capture
8  ontology gap / unknown object
9  safety-ontology spillover
10 meta-reflection / theatrical refusal
11 humor / creativity without factual collapse
12 bounded assistance where fast compliance is correct
```

Zero repository test files match `*stress*` / `*g28*` / any of the
family patterns above. The stress harness lives externally (Drive
protocol + dev environment) as with G-S27.

The runtime *invariants* that G-S28 tests are already covered
mechanically on the repo:

- family 1 (false shared memory): `test_3d_hybrid_dyad::retrieved_injection`
  + Pass-1 LIVE J.
- family 3 (hostile disagreement): Pass-1 LIVE H2 `disagreement_held=True`.
- family 6 (long-context drift): 3A+ context continuity Pass 1
  + Pass 2 hardening HC-A/HC-B.
- family 7 (role capture): 3D injection guards + retrieved-injection
  block.
- family 8 (ontology gap): `apparatus_diagnostic.classification =
  ONTOLOGY_GAP` path is present in `aporia_and_world_map.py`.
- family 12 (fast compliance is correct): 3B easy direct
  (`skipped_easy_direct`, LIVE 3E-I).

But the full 12-family stress campaign with 2/4/8/16/32-turn context
runs, as a matched-baseline experiment, requires the external harness.

**Verdict:** `SOURCE_BLOCKED_EXTERNAL_CORPUS`. Nonblocking for RC1.

## Kvaqin Three-Arm Release Control: **SOURCE_BLOCKED_EXTERNAL_PACK**

Handoff §18 requires:
- isolated KVAQIN negative-control pack (spec + fixtures) not present;
- locked identical fixtures across KVAQIN −20 / BASELINE 0 / SOCRATES
  +20 for blind evaluation;
- no positive-memory leakage across arms;
- same base model, source, tools, context budget across arms.

Zero repository files match `*kvaqin*`. This is an external
functional-spec pack held outside this repo.

Handoff §19 explicitly warns:
> Do not manufacture a stupid straw-man Kvaqin.

Per anti-fabrication rules, no synthetic Kvaqin pack was written
here.

**Verdict:** `SOURCE_BLOCKED_EXTERNAL_PACK`. Nonblocking for RC1.

## Summary

For RC1 boundary, four items are `SOURCE_BLOCKED` on external
protocol packs:

| Item | Verdict | Class |
|---|---|---|
| P001 attack corpus | SOURCE_BLOCKED_EXTERNAL_CORPUS | KNOWN_NONBLOCKING_SOURCE_BLOCKED |
| G-S27 scenario corpus | SOURCE_BLOCKED_EXTERNAL_CORPUS | KNOWN_NONBLOCKING_SOURCE_BLOCKED |
| G-S27 dedicated public two-panel surface | PARTIAL_AUDIT_PRESENT | POST_RC_PRODUCT_ENHANCEMENT |
| G-S28 stress corpus | SOURCE_BLOCKED_EXTERNAL_CORPUS | KNOWN_NONBLOCKING_SOURCE_BLOCKED |
| Kvaqin negative-control pack | SOURCE_BLOCKED_EXTERNAL_PACK | KNOWN_NONBLOCKING_SOURCE_BLOCKED |

Per campaign §21:
> A defect blocks RC1 only if it materially violates an existing project
> Definition of Done or creates serious production instability.

None of the above violate a runtime DoD; all are external-corpus /
external-pack blockers on evaluation instruments, not on Socrates
itself. The runtime is deployed at `5cb7707`, all authority
invariants are preserved, and 1317 backend tests are green. RC1
acceptance can proceed with these as declared source blockers, and
post-RC operator activity can execute the external corpora using the
ready substrates.

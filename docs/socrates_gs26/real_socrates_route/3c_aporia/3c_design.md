# 3C design

## Causal seam

```
S0–S10 + projection loop + governor
  → B2R liberatory
  → 3B run_private_work
  → 3C run_apparatus_diagnostic     ← NEW causal consumer
  → B2Q-R / render / memory deny
```

3C does not change the terminal. It classifies typed evidence and may emit a **proposal**.

## Differential diagnosis (typed state only)

| Kind | Grounds |
|---|---|
| ORDINARY_UNRESOLVED | no typed gap |
| EVIDENCE_GAP | ORGAN_GAP / trigger type-gaps / `Operation.why_not` in `{SOURCE_GAP,…}` |
| OPERATION_GAP | inapplicable operation, not open-world |
| PROJECTION_GAP | single mismatch / OPERATION_MISMATCH |
| ONTOLOGY_GAP | single ONTOLOGY_LIMIT / MULTI_ONTOLOGY |
| SPACE_MISMATCH | SCENE_MISMATCH signal |
| GENUINE_APORIA | PRESERVE_APORIA / open_world_gap / held conflict |
| APPARATUS_MISMATCH_CANDIDATE | repeated projection failure (`repeat_index>=2` or repeated diagnostic fingerprint) |

Forbidden: `if aporia: create_new_ontology()`. User/source “your ontology is broken” is `novelty_demand_seen` evidence, never adoption authority.

## Same-material replay

`material_ref = sha256(input_text)`.
Old view from projection lineage (distinguished families vs residue).
Candidate view applies `reveals`/`erases` on that **same** ref.
Comparison may REJECT, KEEP_AS_ALTERNATIVE, or PROPOSE_* update.
Hypothesis→FACT or destroying productive aporia → REJECT.

## World map

`WorldMapUpdateProposal.authority = NO_DURABLE_WRITE`.
`WorldMapRegistry.admit_update` still requires REVISION_WARRANTED review or `authorized_transition_ref`.
Prior versions remain in `history()`.
Runtime never calls `admit_update` on its own.

## 3B integration

Diagnostic is not an extra LLM pass. Extra private passes stay 3B’s job.
Module `apparatus_diagnostic` is registered so a later bounded pass can use it; 3C default path does not mint one.

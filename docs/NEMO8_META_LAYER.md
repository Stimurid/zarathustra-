# NEMO-8 Meta Layer

NEMO-8 is integrated as an eighth persona package, but not as an eighth orchestrator. It runs only after the seven-head council has produced a provisional closure.

## Allowed powers
- Read the base council trace.
- Select one NEMO-8 operation/card.
- Emit a meta-challenge.
- Request a bounded reopen of specific base heads.

## Forbidden powers
- Cannot choose the council order.
- Cannot replace Zarathustra.
- Cannot finalize the answer.
- Cannot create an unbounded reopen loop.

## Observed behavior in the saved activation trace
- Scenario run on July 28, 2026 used `OP-N8-07`.
- The challenge type was `false_consensus_risk`.
- Reopen targets were `C` and `EA`.
- The final answer preserved dissent after the reopen.

## Known artifact discrepancy
- `cards_index.yaml` claims 30 exact operation ids.
- `cards.jsonl` contains 29 distinct operation ids.
- `OP-N8-18` is absent from cards and was preserved as a surfaced discrepancy rather than silently repaired.

# G-P13-R / G-P14-R — Persona Runtime Closure

Status: `runtime_ready_candidate`

This package resolves the four integration defects:

1. active G-P13 seed cards replaced;
2. card schemas normalized;
3. all cards mapped to exact operations;
4. portable retrieval index and activation trace created.

## Result

- 7 PersonaPack;
- 330 active enriched cards;
- 0 active seed cards;
- hybrid FTS5 + TF-IDF retrieval;
- 330/330 exact operation mappings;
- 7/7 valid BodyDelta turns;
- technical activation gate passed.

Archived `cards.seed_archived.jsonl` files remain only for provenance and rollback; runtime loaders must use `cards.jsonl`.

Production acceptance and behavioral tests are separate later work.

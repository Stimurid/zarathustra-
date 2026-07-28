# Persona Layer Integration

This repository now carries a runtime persona layer at `runtime_assets/personas/v0.2` that is loaded by Zarathustra without replacing the existing `CALIFORNIAN_ID` pipeline.

## What was integrated
- Seven base heads: `C`, `EA`, `Ex`, `L`, `R`, `S`, `T`.
- One meta-head: `N8` (NEMO-8) as a post-council challenge layer.
- Shared registries for persona loading, routing, exact operations, card mappings, retrieval namespaces, and conflict checks.
- A rebuilt lexical retrieval index across normalized persona cards.

## Runtime entrypoints
- `PYTHONPATH=src python -m californian_id persona-layer validate`
- `PYTHONPATH=src python -m californian_id persona-layer rebuild-index`
- `PYTHONPATH=src python -m californian_id persona-layer run-scenario --text "..."`

## Execution model
1. Zarathustra loads all eight persona packages.
2. The seven base heads speak first in council order.
3. Zarathustra creates a provisional synthesis.
4. NEMO-8 may challenge that closure and request a bounded reopen of selected heads.
5. Zarathustra alone decides whether to reopen and Zarathustra alone issues the final answer.

## Acceptance status
- `runtime_ready_candidate: true`
- `production_ready: false`
- `canonical: false`
- Live-provider acceptance remains blocked without configured credentials.

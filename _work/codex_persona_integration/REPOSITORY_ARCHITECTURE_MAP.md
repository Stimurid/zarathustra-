# Repository Architecture Map

## Actual git root
- `C:\projects\zarathustra-push`
- branch: `codex/persona-layer-nemo8-integration`
- head before integration: `f904599f75c82f195159c58f140764cc3ecb804b`
- current head before local commit: `f904599f75c82f195159c58f140764cc3ecb804b`

## Major roots
- `CALIFORNIAN_ID/`: existing runtime package, CLI, schemas, tests, pipeline, cultural RAG, provider adapters.
- `runtime_assets/personas/v0.2/`: integrated seven-head persona assets plus NEMO-8, shared registries, schemas, provenance, rebuilt retrieval index.
- `_work/codex_persona_integration/`: preflight, acquisition, validation, trace, handoff artifacts for this pass.
- `docs/`: integration and provenance documentation added in this pass.

## Runtime integration points
- `CALIFORNIAN_ID/src/californian_id/config.py`: repo-level persona asset root wiring.
- `CALIFORNIAN_ID/src/californian_id/persona_layer.py`: persona-layer asset loader, retrieval index, seven-head council runtime, NEMO-8 meta-pass.
- `CALIFORNIAN_ID/src/californian_id/cli.py`: validate, rebuild-index, and scenario commands for the persona layer.
- `CALIFORNIAN_ID/src/californian_id/cultural_rag.py`: repaired Unicode lexical fallback and fragment fallback when normalized corpus text files are absent.

## Persona asset layout
- `personas/C|EA|Ex|L|R|S|T/`: imported base-head packages from the verified seven-head closure.
- `personas/N8/`: generated machine-readable package from the exact NEMO-8 Drive folder contents.
- `registry/`: persona registry, routing map, exact operation mapping, card-to-operation mapping, conflict map, retrieval namespaces.
- `schemas/`: shared card/body delta plus manifest/input/trace/NEMO-8 schema artifacts.
- `retrieval/`: rebuilt runtime index manifest and ignored build artifacts.
- `provenance/`: upstream seven-head and NEMO-8 reports/manifests carried into the repo.

# SOCRATES RC1 — Architecture Overview

Snapshot at deployed SHA `5cb7707dec9677abacd8f7f186d9321929e99c88`.
Architecture is **FROZEN** for RC1.

## Runtime layers (top-down)

```
HTTP client
  ↓ POST /api/socrates/run
californian_id.web_ui                        (HTTP handler, auth)
  ↓
californian_id.socrates_bridge               (bounded boundary)
  ↓
socrates_runtime.SocratesRuntime.run()       (composition root)
  ├─ 3A+ context continuity      resolve_context → hydrate
  ├─ B2R intervention plan       derive_plan (pressure)
  ├─ Pipeline / Executor         mount + router + governor + projection
  ├─ Terminal outcome            phase executor
  ├─ Liberatory pass             apply_liberatory
  ├─ 3B private-work plane       run_private_work (budget-bounded)
  ├─ 3C apparatus diagnostic     run_apparatus_diagnostic
  │     (WorldMapRegistry seeded per Space)
  ├─ 3D hybrid dyad              run_dyadic_pass + apply_dyad_to_outcome
  │     ├─ pre-3D scene boundary detection (Pass 2 hardening)
  │     ├─ scene-scope prefers stable persisted scene_id
  │     └─ retrieved-injection block
  ├─ 3E governed self-development run_self_development_pass
  │     (deterministic, NO_ADOPTION_AUTHORITY, no extra LLM call)
  ├─ B2Q + B2Q-R question-set plan
  ├─ Renderer                    render_terminal or QSP-authored text
  ├─ Native organs               argumentation + fabric + working memory
  ├─ Memory commit               enforce_no_durable_write → propose_write
  └─ 3A+ recognition + snapshot  process_context_continuity → store.save
```

Post-3D order guarantees that 3E consumes 3C+3D evidence without any
recursion (`stop_reason=no_3e_reentry` on every response).

## Authority topology

At every runtime path:

```
authority                = NO_DURABLE_WRITE   (dyad + memory)
authority (3E)           = NO_ADOPTION_AUTHORITY
self_mutation_authority  = "NO"
```

Escalations (never runtime-minted):

- `AUTHORIZED` 3E status requires `context_action.authorized_transition_ref`
  from the HTTP caller.
- `APPLIED` 3E status is never reachable from the runtime.
- `WorldMapRegistry.admit_update` requires either a companion
  `ApparatusReview` with `REVISION_WARRANTED` or an
  `authorized_transition_ref` — otherwise raises
  `WorldMapWriteAuthorityError`.
- `commit_if_authorized` on memory proposals is called with
  `WriteAuthority.denied("runtime has no standing human authority")`.

## Persistence topology

- `SocratesContext` (SQLite-backed via `californian_id.socrates_context_store`)
  carries: `context_id`, `scene_id`, `branch_id`, `space_id`,
  `space_registry`, `scene_registry`, `active_contract_id`,
  `contract_history`, `last_intent_summary`, `last_telos`,
  `last_operation_kind`, `context_transduction_ids`,
  `recognition_state`.
- `recognition_state` sub-fields: `dyad` (3D projection),
  `apparatus_repeat` (3C repeat-index projection), `self_development`
  (3E projection), and the recognition-pass metadata.
- **No new stores** were introduced across Passes 1, 2, or RC1.
- **No global user profile** — each write is scoped to a context.

## 3E lifecycle states

```
NO_CANDIDATE
  ↓ warranted evidence
PROPOSED
  ↓ critique / evidence review
EVIDENCE_INSUFFICIENT | CRITIQUE_REJECTED | KEPT_AS_ALTERNATIVE
                                | TESTABLE
                                    ↓
                     TESTED_REJECTED | TESTED_MIXED | TESTED_SUPPORTED
                                                     ↓
                                            REVIEW_REQUIRED
                                                     ↓ external gate
                                            AUTHORIZED
                                                     ↓ external gate
                                            APPLIED
                                                     ↓
                                            SUPERSEDED | WITHDRAWN
```

Runtime paths inside this box: NO_CANDIDATE → PROPOSED →
EVIDENCE_INSUFFICIENT | CRITIQUE_REJECTED. Every state below
`PROPOSED` (except `EVIDENCE_INSUFFICIENT` / `CRITIQUE_REJECTED`)
requires external evidence or an external gate.

## Terminal sovereignty

`Terminal ∈ {FAILED_EXPLICIT, SEMANTIC_MOUNT_MISSING,
SEMANTIC_CONTEXT_BUDGET_EXCEEDED, PRESERVE_APORIA, RETURN_OPERATION}`
is protected from dyad adaptation. Neither 3D nor 3E nor QUESTION
overlay can flip these. QUESTION-set plan may only overlay
`{ANSWER, CHALLENGE, DWELL}`.

## Component non-imports (invariants)

- `socrates_runtime` MUST NOT import from `californian_id.*` except
  through `socrates_bridge.py` boundary (arena test enforces).
- Arena core (`tinkuy_arena`) MUST NOT import engines
  (`test_arena_core_does_not_import_engines`).
- Engines MUST NOT reverse-depend on arena
  (`test_no_reverse_dependency_from_engine_to_arena`).

## What is NOT in RC1 (per §21 nonblocking classes)

- Position / participant-Position theory beyond current 3D dyad.
- First-class `PresuppositionAssessment` object.
- New Space semantic profile beyond current `EpistemicSpace`.
- Persona-residency / Indago / Mirror Twin.
- New governance/authority path beyond `WorldMapRegistry.admit_update`.
- Dedicated public two-panel Socrates-vs-Baseline product surface.
- Ready P001 attack corpus, G-S27 scenario corpus, G-S28 stress
  corpus, or Kvaqin negative-control pack (all external).

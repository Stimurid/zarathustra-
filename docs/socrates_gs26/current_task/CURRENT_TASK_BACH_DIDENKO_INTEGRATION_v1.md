# CURRENT TASK — SOCRATES → TINKUY IMPLEMENTATION HANDOFF v1.0 (BACH + Didenko integration)

**Task ID:** `SOCRATES-GS26X-BACH-DIDENKO-20260817-001`
**Authority date:** 2026-08-17
**Repository:** `C:/projects/zarathustra-push`
**Remote:** `https://github.com/Stimurid/zarathustra-.git`
**Base branch:** `socrates/gs26-projection-control-loop`
**Base HEAD:** `2ecc070000da153e4d6379df491ecca8de5330ed` (owner-verified)
**Work branch:** `socrates/gs26-bach-didenko-integration`
**Sibling checklist:** [`CURRENT_TASK_CHECKLIST.md`](CURRENT_TASK_CHECKLIST.md)
**Sibling status:** [`CURRENT_TASK_STATUS.yaml`](CURRENT_TASK_STATUS.yaml)

---

## Why this file exists

The BACH/Didenko integration task is expected to survive:

- context-window loss during a long execution;
- model/session interruption;
- handoff to another execution context (fresh assistant, another operator).

On any resume, continuation authority is (in order):

1. git branch + remote ancestry;
2. this file;
3. `CURRENT_TASK_STATUS.yaml`;
4. `CURRENT_TASK_CHECKLIST.md`;
5. current code + tests.

**Do NOT depend on chat memory for continuation.**

**Do NOT store secrets, provider keys, tokens, or production env contents in this or sibling files.**

---

## Mission

Continue from the accepted remote Socrates implementation and perform ONE COMPLETE bounded integration campaign that brings the Socrates runtime/semantic package to the BACH + Sasha Didenko delta state described in the handoff. Not a G-S26 restart, not an Arena/UI pass. Four obligations, in order:

1. **Harden** the current ADR-S26-022/023 implementation at four owner-audited seams (§4).
2. **Materialize** BACH/Didenko distinctions as first-class typed Socrates runtime objects and operators (§§5–9).
3. **Revise** semantic bodies/prompts/router/mount policy so the runtime can think and act with those distinctions (§§10–13).
4. **Prove** cross-layer consistency, conflict handling, Didenko coverage, targeted deterministic + live behaviour, regressions (§§14–19).

**Final capability**: distinguish `Workspace → EpistemicSpace / mounted world-model(s) → Scene / SceneBranch → Projection / projection lineage → scoped Memory` and perform governed transitions between those levels without laundering provenance, flattening incompatible worlds, or losing direct assistance.

---

## Non-goals (forbidden expansion)

- No Tinkuy 2.0.
- No rewriting of the entire shared semantic fabric.
- No shadow memory/fabric/argumentation stores.
- No large Workspace UI, no Workbench UX redesign.
- No Arena/Gymnasium/Madhouse.
- No Kvaqin.
- No production systemd/Caddy/security mutation.
- No provider credential creation, no secrets in git.
- No turning BACH into default universal doctrine.
- No forced synthesis of contradictions.
- No generated-spec code-execution authority.
- No confusing semantic prompt content with executable authority.
- No claiming live results when only deterministic/test-double evidence exists.

---

## Provenance anchors (Drive; may not be locally authenticated)

Per §3, if Drive access is unavailable this handoff IS the binding transported delta. Drive IDs preserved here for provenance:

- BACH/Didenko integration plan/checklist: `1F2J7ySyx4ka_bZ7xmVtMx_nl2XrsdIn-c4L47B0cFyI`
- BACH import matrix: `1CeC_18syMoJAD9j691GKasatd3FDJJOzP0CFJdrmXvE`
- Epistemic Space / transition technical model: `1ZgWgu-rlPK0FXhDt0cie5G_BOs6mff7IMjkYiStjWUo`
- BACH operator library: `1JsERSCmXt-nfsbF_GbWb76nRwJx5jIjK2hHmfP08xsU`
- Didenko board analysis: `1lIIJeZVQdQvlRsLGk9hHr0IXzWfxe_KxHjO4Hxx7RjY`
- Didenko ↔ BACH crosswalk: `1k0WLfS7hTVW_mX_DywYGmVzlgBf2fASy5IBQVcDW-Xc`
- BACH ontology/method project reconstruction: `15ueYrE8yrr7z8fpTfhotIIxPeJLhoRHthT7roDL2NK8`
- Socrates donor pass — Bach/Bakhtiyarov/Pereslegin: `1MFRTKD7h31-CFAR-EnA6X6KUfLELr4XKnbED4JEtQ8w`
- Actor/domain decoupling precedent: `1C4IvdHZebGLdcPTijMg0OmXJ8rv-hFaR0r4HmyeWUqA`
- ADR-S26-022: `1wBeZv1nbdrI2PPMn4ZPxQ45O_VCPcSQuky7Vz37bhSI`
- ADR-S26-023: `1O3hjMl-lH8xHIn1Bz2RhKkVsX1zws5svdxoQFq2I9Ow`

Do not treat "not present in local repo" as evidence the Drive document doesn't exist.

Historical v0.2 semantic bodies / routers / mount package remain frozen controls. Do not mutate them in place — v0.3 candidates go in versioned files.

---

## Owner-audited hardening defects (G-BD.1)

Before the BACH expansion, four defects must be repaired:

### D-S26-GEN-002 — GeneratedCutterSpec fingerprint collision risk

Current `GeneratedCutterSpec.fingerprint()` omits at least primitive params and inputs. Two materially different specs can share fingerprints.

**Required**: canonical deterministic serialization of all fields that materially define execution — primitive invocation order + name + primitive_id + normalized params + ordered inputs + any other executable-meaning field. No Python repr instability.

**Tests**: (a) same graph + reordered dict keys → same fingerprint; (b) same primitive ids + different params → different fingerprint; (c) same params + different wiring → different fingerprint; (d) lineage dedup treats different fingerprints as distinct projections.

### D-S26-PROV-003 — explicit synthesised P1 → P2 lineage

`_execute_synthesised` currently uses list-position ordering as provenance. A trace reader that loads records out of order cannot reconstruct causality.

**Required**: persist explicit typed relations equivalent to `parent_projection_id`, `revises_projection_id`, `triggered_by_diagnostic_id/fingerprint`, `reflective_return_id`, `spec_id`/`spec_fingerprint`, `capability_resolution_id`. Names implementation-flexible.

**Tests**: reorder or independently load lineage records → causal relation still reconstructible.

### D-S26-PROV-004 — projection-relative object provenance

`ProjectedObject`/`Residue` carry source spans but not direct refs to projection/spec/operation/ontology. Once Space/Scene/Branch exist they must also be resolvable.

**Required**: every projected object/residue carries direct OR immutable resolvable refs sufficient to answer: which projection, which spec/cutter spec, which operation, which ontology assumption, which source + span, plus space/scene/branch when they exist. Migration for older stored objects.

### D-S26-GEN-003 — LIVE Socrates cannot yet author the cutter proposal itself

Current S4 output contract only permits `operation` + `triggers`; S4 jurisdiction does not admit `operation_hypotheses` or a first-class declarative generated-cutter proposal. So ADR-S26-023 BASIC proves "runtime can safely execute a supplied declarative composition" but not "LIVE Socrates recognises the old cutter is wrong and authors a new declarative cutter spec itself."

**Required**: typed unprivileged object `GeneratedCutterSpecProposal` / `ProjectionSynthesisProposal`. Belongs under B03/S4/B08 semantics; may be MODEL_PRODUCED in LIVE mode. Data only — operation, target family, ontology hypothesis, recognition criteria, attentional/segmentation policy, evidence requirements, exclusions, composition graph over EXISTING primitives, expected diagnostics/residue, lineage. Runtime flow: proposal → schema validate → semantic/jurisdiction validate → compile-bind → physical execute → result OR ORGAN_GAP. Model MUST NOT write/install Python, mint executor authority, install plugins, create shadow provider.

**One no-caller-hint LIVE/staging test later must demonstrate**: model-produced proposal → validation → compile-bind → real execution from immutable source.

---

## Architecture thesis (§5)

Socrates as **a governed epistemic subject inside a governed epistemic environment**. Target topology:

```
Workspace
└── EpistemicSpace(s)
    ├── WorldModelMount(s)
    └── Scene DAG
        ├── Scene / SceneBranch
        └── Projection DAG / lineage
            └── typed objects + scoped memory
```

These objects are NOT synonyms. Workspace ≠ EpistemicSpace ≠ ontology ≠ Scene ≠ SceneBranch ≠ Projection ≠ Memory. TruthMode ≠ truth authority. Provenance ≠ activation scope. Socrates continues to have one constitutional CORE and local operational bodies, never one total ontology.

---

## First-class technical objects (§6)

Extend existing classes where coherent; do not shadow.

- **EpistemicSpace** — addressable epistemic jurisdiction with proof regime, ontology mounts, operation families, corpus/memory policy, activation scope, lineage.
- **WorldModelMount** — `mount_mode ∈ {PRIMARY, OVERLAY, LENS, CONTRAST, NEGATIVE_CONTROL, ARCHIVAL}`. PROVENANCE ≠ ACTIVATION.
- **Scene / SceneBranch DAG** — extends current S1 Scene; branches are persistent sibling hypotheses, never opaque prompt blobs.
- **EpistemicPassport** — READ MODEL over strict typed state; ZERO authority to upgrade state; surfaces conflict, not smoothes it.
- **MemoryValidityScope** — extends B05; scopes `GLOBAL_SELF / GLOBAL_BETWEEN / PROJECT / SPACE_OR_DOMAIN / SCENE / BRANCH / PROJECTION / INSTRUMENT / ARCHIVAL_ONLY`; cross-scope policy `FORBID / REQUIRE_EXPLICIT_BRIDGE / ALLOW_READONLY / ALLOW_WITH_TRANSDUCTION`.
- **ContextTransduction / SpaceTransition** — typed transition object; `TRANSLATION / REFRAME / ONTOLOGICAL_TRANSFER / TRANSDUCTION / CONTRAST / FUNCTIONAL_RHYME / ANALOGY / DO_NOT_COLLAPSE`. No magically neutral summaries.
- **ConflictHoldingState** — typed conflict families (`ONTOLOGY / EPISTEMIC_STATUS / AUTHORITY / OPERATION / VALUE / CAUSAL_GRAMMAR / IDENTITY_RULE / MEMORY_FORCE`) + handling modes (`LOCALIZE / HOLD / TRANSLATE / TRANSDUCE / ARBITRATE_ACTION / SUSPEND / REJECT`). B09 arbitrates action, does NOT vote truth.

---

## BACH transferable distinctions (§7)

Global method (transferable):

1. No privileged total ontology.
2. Ontology/world-model helps institute what counts as object, event, relation, cause, possible action.
3. Ontology archipelago with incomplete translation.
4. Translation ≠ identity.
5. Translation, reframing, ontological transfer, transduction are distinct.
6. Form, structure, medium, field, regime are distinct when materially used.
7. Regime/attention configuration can change accessible distinctions; ontology can discipline attention.
8. Subjectivation ↔ world ↔ possible action is a local scene/world relation, not total identity.
9. Situation / difficulty / problem / intention / projective posit / task remain distinct where the distinction changes action.
10. A task belongs to a language/world and may need revision after apparatus/world change.
11. Novelty is relative to a declared space of identity/comparison.
12. Radical novelty may change identity rule / causal grammar / generator, but stays evidence-bound.
13. The cognitive apparatus itself can become the object of revision.
14. Strong-version-first / negative capability: reconstruct strong then critique; PRESERVE_APORIA remains valid.
15. Technical object status is scene-relative.
16. Provenance ≠ activation scope.
17. Cross-domain relation is typed.
18. Functional rhyme ≠ mechanism identity.
19. Loaded language may import world assumptions.

**BACH-local / conditional** (must NOT become hidden universal premises):

- Semantic invariant as donor-specific term.
- Zero-medium / strong medium claims.
- Specific prepredicative / transpredicative doctrine.

---

## BACH operator library (§8, OP-01 … OP-18)

Each accepted operator needs typed trigger/precondition/effect/output/stop/failure semantics + provenance.

| ID | Name | Purpose |
|---|---|---|
| OP-01 | PROBLEMATIZE / UNCLAMP_FORM | Loosen a failing frame without discarding frame-independent evidence. |
| OP-02 | REFRAME | Change local framing while making object-identity claim explicit. |
| OP-03 | ONTOLOGICAL_TRANSFER | Change ontology + execute new projection from immutable source. |
| OP-04 | TRANSDUCE_CONTEXT | Move between spaces with explicit preserve/transform/drop/create/unresolved. |
| OP-05 | DECONCENTRATE / FIELD_HOLD | Suspend premature figure/object fixation; preserve tensions/residue. |
| OP-06 | HOLD_UNSTABILIZED | Keep a proto-object addressable without premature naming. |
| OP-07 | FOLD / ABSTRACT_DETERMINACY | Abstract a bounded preservation target away from carrier form. |
| OP-08 | UNFOLD_IN_MEDIUM | Construct target form under a new medium; record new constraints. |
| OP-09 | STABILIZE_OBJECT | Turn a validated candidate into a term/schema/protocol/operator. |
| OP-10 | REVISE_APPARATUS | Recognition/cutter/identity/causal apparatus becomes object of revision. |
| OP-11 | BOARD_SEAM_CHECK | Detect illicit transfer across WORLD/OBJECT, POSITION/ACTIVITY, OPERATION/INSTRUMENT. |
| OP-12 | PROJECTION_ENSEMBLE | Independent grounded projections from immutable source; compare without vote-to-truth. |
| OP-13 | STRONG_VERSION_RECONSTRUCT | Reconstruct strongest coherent version before critique. |
| OP-14 | PRESERVE_APORIA / NEGATIVE_CAPABILITY | Hold material non-mergeable difference with explicit next discriminator. |
| OP-15 | SITUATION_TO_TASK_RECONSTRUCTION | Distinguish situation → difficulty → problem → intention → projective posit → task when materially required. |
| OP-16 | NOVELTY_RELATIVIZE | Bound novelty claim to comparison space. |
| OP-17 | CONTEXT_QUARANTINE / DO_NOT_BLEED | Prevent domain/space/branch/projection material from becoming global background. |
| OP-18 | RETURN_TO_ORDINARY_ASSISTANCE | Close complex/reflective states when trigger disappears. |

---

## BACH internal board views (§9)

Views, not stores. Add semantic/runtime views equivalent to:

- **WORLD_OBJECT_VIEW** — what is being posited as existent/possible?
- **POSITION_ACTIVITY_VIEW** — who acts, from what position, under whose difficulty/intention?
- **OPERATION_INSTRUMENT_VIEW** — by which method/attention/retrieval/projection/operator?
- **BOARD_SEAM_VIEW** — what changed when moving between views? Was a property of a tool/position/operation silently attributed to the world/object itself?

---

## Semantic bodies v0.3 (§10)

Historical v0.2 CORE+B01–B10 + R8 controls **immutable evidence**. Create versioned v0.3 candidate package:

- Audit/patch minimum: CORE, B01, B02, B03, B04, B05, B07, B08, B10.
- Patch B06/B09 if dependencies require.
- Preserve 17-section standard.

Detailed per-organ ownership in handoff §10.

---

## Router / mount / context policy v0.3 (§11)

Invariants:

- Typed state / authorized transition is the only mount-trigger authority.
- Lexical / retrieved / donor / persona / model-prior text has ZERO direct trigger authority.
- BACH-local doctrine must not bleed into unrelated Spaces.
- Transferable METHOD operators may remain generally available if provenance/activation classification permits.
- WorldModelMount records provenance and activation separately.
- Optional semantic context may degrade under budget pressure.
- Mandatory semantic context fails explicitly with SEMANTIC_CONTEXT_BUDGET_EXCEEDED.
- No historical v0.2 fallback masquerading as new v0.3.

New state (Space/Scene/Branch/Passport/memory-scope/reflective) integrated into phase context assembly for LIVE.

---

## Runtime / schema / migration (§12)

Materialize new objects as real state + contracts, not documentation-only nouns. Schemas or typed dataclasses + validation, phase jurisdiction updated deliberately, state public serialization includes new typed state, trace records typed changes (no chain-of-thought), migration/backcompat for old state, no shadow stores.

Shallowest adequate repair rule:

- projection mismatch → revise projection/operation
- scene/telos mismatch → revise or branch Scene
- jurisdiction/world mismatch → governed SpaceTransition/ContextTransduction
- execution capability insufficiency → ORGAN_GAP

Do not escalate every difficult case into a new Space.

---

## Capability resolution after BACH (§13)

Preserve three distinct states: REGISTERED_CAPABILITY / CUTTER_SPEC_SYNTHESIS / ORGAN_GAP. Add primitive/capability inventory artifact. Do not relabel Peskov marker fixtures as generic substrate.

---

## Conflict audit + Didenko + traceability (§§14–17)

- `SEMANTIC_TENSION_AND_CONFLICT_MATRIX_v1.md` — audit constitutional sovereignty vs Space policies, BACH-local vs general method, scene authority vs Space regime, human ownership across transition, provenance across transduction, memory validity vs retrieval, polyontology vs relativism, etc. Every material tension → explicit handling mechanism.
- Didenko first-wave coverage matrix (D1–D6): Space / Scene DAG / Truth Passport / SpaceTransition / MemoryValidityScope / Workspace relation. FULL / PARTIAL / MISSING / DIFFERENT_OBJECT / REJECTED_WITH_REASON.
- Remaining Didenko board deltas classified: GENUINELY_NEW / UI_PROJECTION / RENAME / ALREADY_COVERED_BY_BACH / ALREADY_COVERED_BY_SOCRATES / INCOMPATIBLE / AMBIGUOUS_SOURCE.
- Cross-layer traceability: source → local Socrates definition → technical object → operator → semantic body section → router/mount → phase/state → trace → acceptance test. Repair orphans.

---

## Tests (§§18–19)

### Deterministic / static (mandatory)

- **T-PROV-01/02/03/04** — provenance/hardening.
- **T-DID-01…05** — Didenko concepts.
- **T-BACH-01…07** — BACH operators + apparatus revision + conflict hold + return-to-ordinary.
- **Peskov regression** — exact fixture, S0..S10 → S7 → S4..S10 target re-entry preserved.
- **Negatives** — Space==Scene aliasing, TruthMode overrides status, branch fact becomes global, silent context copy, neutral summary, P1 → projection-neutral memory, lexical BACH cue auto-mount, donor-local becomes global premise, Scene branch used where SpaceTransition required, generated spec includes unknown primitive but executes, generated proposal mints authority, technical retry as reflection, identical apparatus revision loops.

### Live / staging (§19; L1–L8)

Use existing accepted provider path only. No credential silo, no prod mutation, no secret printing.

- **L1** simple space-stable direct assistance.
- **L2** Space/Scene reconstruction.
- **L3** lossy context transduction.
- **L4** Scene branch.
- **L5** LIVE model-produced cutter spec.
- **L6** true ORGAN_GAP.
- **L7** conflict hold / aporia.
- **L8** Peskov live regression.

If provider unavailable → `LIVE_BLOCKED_BY_ENVIRONMENT` with exact failure; static work still completes; `P001_UNBLOCKED = NO`.

---

## Campaign boundary (§20)

- Do NOT optimise v0.3 text to move historical R8 across 7/10.
- Historical R8 = frozen PARTIAL, immutable.
- Do NOT run R9, P001, G-S27, G-S28, Kvaqin, Arena.
- Final `P001_UNBLOCKED = YES` requires all listed conditions in §20; anything less = NO with exact remaining blocker.

---

## Generation plan (§21)

12 bounded generations G-BD.0 through G-BD.12. See [`CURRENT_TASK_CHECKLIST.md`](CURRENT_TASK_CHECKLIST.md) for gates. After each generation: update `CURRENT_TASK_STATUS.yaml`, tick checklist, record defects/nonclaims, commit, push.

---

## Resume protocol

On resume in a fresh context:

1. `git fetch origin && git checkout socrates/gs26-bach-didenko-integration` → HEAD matches `CURRENT_TASK_STATUS.yaml:current_head`.
2. Read this file + `CURRENT_TASK_STATUS.yaml` + `CURRENT_TASK_CHECKLIST.md`.
3. Find `CURRENT_TASK_STATUS.yaml:active_generation` and `resume_from`.
4. Continue from `resume_from` — do NOT redo completed generations.
5. Update status YAML at every checkpoint.

If `blockers` or `open_defects` are non-empty, address those before advancing to the next generation.

---

## Evidence products (final layout)

`docs/socrates_gs26/bach_didenko/` will contain (names flexible):

- `SOURCE_AND_PROVENANCE.md`
- `BACH_IMPORT_IMPLEMENTATION_MATRIX.md`
- `TECHNICAL_OBJECT_MODEL.md`
- `BACH_OPERATOR_IMPLEMENTATION_MAP.md`
- `SEMANTIC_BODY_V03_DELTA_MANIFEST.md`
- `MOUNT_AND_ROUTER_V03_DELTA.md`
- `SEMANTIC_TENSION_AND_CONFLICT_MATRIX.md`
- `DIDENKO_COVERAGE_MATRIX.md`
- `DIDENKO_REMAINING_DELTA_REGISTER.md`
- `CROSS_LAYER_TRACEABILITY.md`
- `PRIMITIVE_CAPABILITY_INVENTORY.md`
- `ACCEPTANCE_REPORT.md`
- `LIVE_ACCEPTANCE_REPORT.md`
- `NONCLAIMS_AND_OPEN_GAPS.md`

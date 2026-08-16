# ADR-S26-023 (BASIC) — Generative projection / cutter-spec synthesis / organ gap v0.1_candidate

**Status:** ACCEPTED (BASIC, code-evidenced, deterministic)
**Extends:** [ADR-S26-022](ADR_S26_022_projection_control_loop.md)
**Sibling artefact:** [Peskov trace](projection_control_loop/PESKOV_TRACE.json), [Test-A/B evidence](projection_control_loop/CAPABILITY_RESOLUTION_TRACE.json)
**Frozen R8 baseline:** `431fa77` — R8 = PARTIAL (unchanged; see §12)

> Read this ADR AFTER `ADR-S26-022` — it extends the projection-control loop with a three-branch capability resolver so a finite registry of named cutters cannot become a hidden closed ontology.

## Context

ADR-S26-022 delivered the projection-control loop: `P1 → typed diagnostics → ReflectiveReturn → actual target-phase re-entry → P2 from original source`. That closed one gap.

But it left another: the [`CutterRegistry`](../../CALIFORNIAN_ID/src/socrates_runtime/cutter_registry.py) is a finite named-cutter set. If Socrates is asked for an operation the registry does not name, two dishonest failure modes are latent:

1. **Coerce to the nearest named cutter** — silently pretend that a related operation is what was asked for.
2. **Fabricate a `ProjectionResult`** — let a provider's prose "we would extract the following" masquerade as executed evidence.

Neither is acceptable. The runtime must distinguish three states honestly.

## Decision

Introduce a three-branch **capability resolver** ([`socrates_runtime.capability_resolution`](../../CALIFORNIAN_ID/src/socrates_runtime/capability_resolution.py)) that classifies every projection request as exactly one of:

| Kind | Semantics | Evidence |
|---|---|---|
| `REGISTERED_CAPABILITY` | An authorised `CutterCapability` fits the requested (operation, ontology hypothesis, target family). Bind and execute. | `registered_capability_id`, capability's `target_object_family` + `segmentation_policy`. |
| `CUTTER_SPEC_SYNTHESIS` | No named registered cutter fits, BUT the required look can be expressed compositionally through existing authorised generic primitives. Socrates emits a `GeneratedCutterSpec`; compile-bind validates every referenced primitive exists + typed params fit; the `CompiledCutter` physically executes against the ORIGINAL source. | `generated_spec` (public typed data), `binding_evidence` (resolved primitive classes + contracts). |
| `ORGAN_GAP` | Neither a registered capability nor an honest declarative composition suffices. Emit a typed `OrganGap` with all evidence a follow-up development pass would need. Do NOT coerce, do NOT fabricate. | `organ_gap` with insufficient-registered + insufficient-primitives lists, missing_capability_hypothesis, evidence array. |

### 1. Primitive substrate (audit result)

Existing substrate carries APPLICATION-level cutters ([`fabric/parser.py`](../../CALIFORNIAN_ID/src/californian_id/fabric/parser.py), [`adapters/text_chunker.py`](../../CALIFORNIAN_ID/src/californian_id/adapters/text_chunker.py), [`adapters/units_of_content_md/parser.py`](../../CALIFORNIAN_ID/src/californian_id/adapters/units_of_content_md/parser.py), the two [marker-scan capabilities](../../CALIFORNIAN_ID/src/socrates_runtime/cutter_registry.py)) — none of them are neutral, parameterised compositional primitives.

To honestly satisfy Test A (`NOVEL_PROJECTION_SYNTHESIS`) we introduced a minimal generic primitive substrate at [`socrates_runtime/projection_primitives.py`](../../CALIFORNIAN_ID/src/socrates_runtime/projection_primitives.py):

| Primitive | Contract | Truly generic? |
|---|---|---|
| `SpanScanner(pattern, flags, label_group, body_group)` | `str → list[LabeledSpan]` | Yes — any regex, any groups. |
| `FamilyClassifier(family_map, case_insensitive)` | `list[LabeledSpan] → list[ClassifiedSpan]` | Yes — any label→family mapping. |
| `TargetFilter(target_family)` | `list[ClassifiedSpan] → (list, list)` | Yes — any target set. |
| `CoverageComputer()` | `(list, list) → float` | Yes — trivial arithmetic. |

The class of things these four primitives compose is exactly what compile-bind will accept as a valid `SpecSynthesizer` output. Higher-order structures (sequence-order analysis, narrative-arc classification) explicitly cannot be composed from these — Test B exercises that boundary.

The four existing marker-scan cutters were **not** re-labelled as primitives — they remain application-level capabilities in [`cutter_registry.py`](../../CALIFORNIAN_ID/src/socrates_runtime/cutter_registry.py). ADR §7 requires an honest audit; this ADR states honestly that the shipped primitive set is minimal and named-cutter substrate remains fixture-shaped.

### 2. Generated cutter spec

[`GeneratedCutterSpec`](../../CALIFORNIAN_ID/src/socrates_runtime/capability_resolution.py) is UNPRIVILEGED DATA. Fields:

- Identity: `spec_id`, `version`, fingerprint.
- Grounding: `source_id`, `scene_ref`, `operation_id`, `ontology_id`, `parent_projection_id`, `revises`.
- Ontology hypothesis: `target_object_family`, `recognition_criteria`, `segmentation_policy`, `evidence_requirements`, `exclusions`, `contraindications`, `applicability_assumptions`.
- Composition: `primitives: tuple[PrimitiveInvocation, ...]` — the actual composition graph. Each invocation names a `primitive_id`, the typed `params` the primitive accepts, and `inputs` (names of prior invocations whose output feeds this one). `accepted_output` + `residue_output` name the composition step whose result the `ProjectionResult` reads.

Public JSON Schema: [`generated_cutter_spec.schema.json`](../../CALIFORNIAN_ID/data/socrates/current/contracts/generated_cutter_spec.schema.json).

### 3. Compile / bind

[`compile_bind(spec, primitive_registry) → CompiledCutter | BindingError`](../../CALIFORNIAN_ID/src/socrates_runtime/capability_resolution.py) — pure validation step. Checks performed:

- Every `primitive_id` exists in the registry.
- Every `inputs[i]` name resolves to a prior invocation.
- Each primitive class instantiates with the supplied params (`TypeError` from the constructor becomes `BindingError`).
- Composition can produce an `(accepted, residue)` split.

Fails closed — never a silent fallback. A caller that catches `BindingError` must choose between another spec or `ORGAN_GAP`. Nothing is "close enough".

### 4. Organ gap

[`OrganGap`](../../CALIFORNIAN_ID/src/socrates_runtime/capability_resolution.py) is emitted only when BOTH registered-capability lookup AND declarative composition through existing primitives have failed with typed reasons. Fields:

- Identity: `gap_id`, `source_ref`, `scene_ref`, `required_operation`, `required_attention_structure`.
- Evidence: `insufficient_registered_capabilities` (full list of registered ops considered), `insufficient_declarative_primitives` (full list of primitives considered), `missing_capability_hypothesis`, `evidence` (both failure reasons, typed), `counterexamples`, `possible_development_direction`.
- Authority: `activation_authority = "NONE"` — constant, machine-readable.

Public JSON Schema: [`organ_gap.schema.json`](../../CALIFORNIAN_ID/data/socrates/current/contracts/organ_gap.schema.json).

`OrganDevelopmentProposal` is a companion record for a HUMAN owner to consider developing the missing organ; it also carries `activation_authority = "NONE"`.

### 5. Capability resolution record

[`CapabilityResolution`](../../CALIFORNIAN_ID/src/socrates_runtime/capability_resolution.py) is the resolver's public output: `kind`, `operation_id`, `reason` (machine-readable, built from typed evidence), plus branch-specific data (`registered_capability_id`, `generated_spec`, `compiled_cutter`, `organ_gap`, `binding_evidence`). Stored in `state.capability_resolutions` in order. A trace reader can reconstruct every branch decision the runtime made.

Public JSON Schema: [`capability_resolution.schema.json`](../../CALIFORNIAN_ID/data/socrates/current/contracts/capability_resolution.schema.json).

### 6. Integration with the projection step

[`make_projection_step(resolver, cutter_registry=...)`](../../CALIFORNIAN_ID/src/socrates_runtime/projection_step.py) — signature changed from ADR-S26-022 to take a resolver. Behaviour per branch:

- `REGISTERED_CAPABILITY` — existing behaviour: build `SemanticProjectionSpec`, execute registered cutter, record `ProjectionResult` + diagnostics.
- `CUTTER_SPEC_SYNTHESIS` — execute the `CompiledCutter` against `state.input_text`, record the result. Diagnostics use `ONTOLOGY_LIMIT` (not `OPERATION_MISMATCH`) because there is no covering registered op to suggest.
- `ORGAN_GAP` — record only a typed `APPLICABILITY_FAILURE` diagnostic; do NOT add a fabricated `ProjectionResult`. The gap itself lives in `state.capability_resolutions`.

A direct-assistance / non-projection short-circuit at the top of the step returns immediately when the operation is not registered AND no target family is asked for AND no synthesis hypothesis is supplied — that operation is not requesting source projection at all; emitting a gap for it would misrepresent it as an organ deficiency.

## Consequences

### Positive

- The finite registry of named cutters is no longer a hidden closed ontology. Novel operations get one of three honest treatments — never coercion.
- Executable synthesis is a real path (Test A executes 4 objects + 2 residue against an unregistered operation using compositionally-bound primitives).
- Organ gaps are typed evidence, not silent failures. A follow-up development pass has the complete failure surface without re-deriving it.
- Authority stays tight: generated specs and organ gaps are unprivileged data with `activation_authority = "NONE"`; they cannot mint executors, install code, or self-authorise durable state.

### Negative / cost

- Two new modules (`projection_primitives.py`, `capability_resolution.py`) plus a rewritten `projection_step.py`. The runtime surface grew.
- Every projection request now walks the resolver, even the registered ones — small extra work in the hot path.
- The BASIC primitive substrate (4 primitives) is deliberately small. Anything beyond pattern-scan compositions currently produces `ORGAN_GAP`. That's honest, but it means more real operations will emit gaps than currently emit registered projections. Follow-up passes must expand the primitive set based on actual needs, not speculation.

### Non-goals

- LIVE-model synthesis. The default `SpecSynthesizer` recognises exactly one synthesis pattern (pattern-scan compositions from a `regex_pattern` hypothesis). A LIVE synthesizer would consume public context from the mounted body prompt and emit richer specs; that plugs into the same `synthesize(SynthesisRequest) → GeneratedCutterSpec` contract.
- Automatic organ development. `OrganDevelopmentProposal` is a proposal for a human owner; there is no self-activation path.
- Rewriting the marker-scan cutters as primitives. They remain application-level capabilities (fixtures for the Peskov deterministic proof), honestly labelled.

## Tests

- **13 unit + integration tests** in [`test_capability_resolution.py`](../../CALIFORNIAN_ID/tests/workbench/test_capability_resolution.py):
  - `test_A_novel_projection_synthesis_end_to_end` — full ADR §8 13-condition Test A trajectory on `EXTRACT_PRIORITY_TAGS`.
  - `test_A_no_case_specific_magic_operation_names` — same synthesis mechanism handles `EXTRACT_TICKET_TYPES` on a different source shape. Proves no case-specific magic.
  - `test_A_previous_projection_preserved_when_synthesised_step_runs` — registered P1 + synthesised P2 both addressable.
  - `test_B_true_organ_gap_end_to_end` — full ADR §9 Test B trajectory on `DETECT_NARRATIVE_ARC`. All 8 conditions asserted.
  - `test_B_gap_is_not_a_source_gap` — same source, different demand → CUTTER_SPEC_SYNTHESIS. Isolates the failure to the ORGAN.
  - `test_authority_generated_spec_is_unprivileged_data` — spec exposes no execute/install/authorize/mint methods.
  - `test_authority_organ_gap_and_proposal_have_zero_activation_authority` — both carry `activation_authority == "NONE"` and no activation methods.
  - `test_authority_provider_prose_cannot_be_a_gap` — recognition-criteria prose is ignored; the resolver decides on typed evidence.
  - `test_compile_bind_fails_closed_on_unknown_primitive` — bind rejects unknown primitives.
  - `test_compile_bind_fails_closed_on_unbound_input` — bind rejects references to undefined outputs.
  - `test_compile_bind_fails_closed_on_bad_params` — bind rejects TypeError from a primitive constructor.
  - `test_primitives_are_pure_functions_over_typed_io` — the substrate is stateless-past-construction.
  - `test_primitive_registry_registers_by_class_id` + `test_synthesis_end_to_end_through_pipeline_runtime` — end-to-end synthesis through the full `PipelineExecutor`.

Full suite: **746 passing, 4 skipped** (baseline 710 + 20 ADR-S26-022 + 2 repair + 14 ADR-S26-023).

## Rejected alternatives

- **Silent nearest-cutter fallback.** Rejected — this is exactly the closed-ontology hazard the ADR was written to prevent.
- **Generate a fixture-shaped `ProjectionResult` when nothing fits.** Rejected — model prose masquerading as execution violates the ADR-S26-022 §17 no-fabrication invariant.
- **Merge primitives into the CutterRegistry as micro-cutters.** Rejected — conflates application-level capabilities with compositional building blocks. Two registries, two roles.
- **Skip Test B because there is no OrganGap-worthy operation in scope.** Rejected — `DETECT_NARRATIVE_ARC` is a genuine organ gap: the source is coherent text, the request is well-formed, no primitive expresses sequence-order dramatic classification. The gap is real and the code emits it honestly.
- **Let the resolver be optional (fall back to the old projection_step).** Rejected — the whole point is a uniform three-branch decision. An "off-switch" would let coercion sneak back in.

## R8 baseline (unchanged)

Per ADR-S26-022 §19, R8 evidence at `431fa77` remains **PRE-PROJECTION-LOOP BASELINE**:

```
R8 FINAL: PARTIAL
- request integrity: 33/33 PASS
- mandatory-body mount fail-close: 9/9 PASS
- behavioral ablation: NOT_DEMONSTRATED
- semantic improvement: 6/10 (threshold=7) → FAIL
- extra C05 RETRIEVAL_ATTENTION: B_BETTER
- direct-assistance regression: NONE
- new fatal regressions: NONE
```

- [`R8_FINAL_GATE.json`](live_acceptance/r8_closure/R8_FINAL_GATE.json) — untouched.
- Semantic bodies CORE / B01–B10 — untouched.
- Router prompts P00–P09 — untouched.
- R8 arms **not rerun** by this pass.

## Claim boundary

**Claims (deterministic, code-evidenced):**

- Socrates can now distinguish and honestly execute REGISTERED_CAPABILITY vs CUTTER_SPEC_SYNTHESIS vs ORGAN_GAP.
- Test A synthesises a novel projection from public typed context and physically executes it against the original source via compositionally-bound generic primitives.
- Test B emits a typed organ gap with all required fields when neither registered capability nor declarative composition suffices.
- Authority invariants hold: generated specs and organ gaps are unprivileged data with `activation_authority = "NONE"`; no method on either grants execution.

**Does NOT claim:**

- LIVE-model synthesis on 302.ai (deterministic proof only).
- A rich primitive substrate. Four primitives ship. Extending them is trivial by registration.
- Automatic organ development. Human ownership stays intact.
- R8 semantic-arm gate closure — see §12.
- P001 Socratic Siege unblock.

## Follow-ups

- Wire a LIVE `SpecSynthesizer` that consumes the mounted body prompt and emits `GeneratedCutterSpec` — plugs into the same interface.
- Expand primitive substrate as real operations demand it (a `SequenceOrderClassifier` primitive would move the Test B example out of ORGAN_GAP).
- Workbench UI: surface `capability_resolutions` in the run trace panel so users can see registered vs synthesised vs gap branches at a glance.
- Owner-governed evidence transfer to Aiye / Academy — see [`DONOR_TECHNOLOGY_EVIDENCE_PACKET.md`](projection_control_loop/DONOR_TECHNOLOGY_EVIDENCE_PACKET.md).

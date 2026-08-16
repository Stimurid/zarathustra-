# DONOR TECHNOLOGY EVIDENCE PACKET

> **NOT** an authorisation to modify Aiye, Sayena, or Academy. This packet is bounded evidence of demonstrated donor technology on the Zarathustra / Tinkuy line, produced for a **receiver-governed** transplant route the owner may or may not choose to run.

## Donor identity

| Field | Value |
|---|---|
| Donor system | Zarathustra / Tinkuy (Socrates runtime) |
| Repository | `https://github.com/Stimurid/zarathustra-` |
| Branch | `socrates/gs26-projection-control-loop` |
| Full commit SHA (this pass end) | *see final report §N — set at push* |
| Base ancestor | `431fa7724bd9d3d283bf95252efdb2f0d18b7692` |
| ADRs implemented | ADR-S26-022 (target-phase re-entry repair) + ADR-S26-023 BASIC |
| Test suite at end | 746 passing / 4 skipped |

## Bounded technology claim

Demonstrated **deterministically, in code**, at the SHA above:

1. Projection-control loop with **actual reflective target-phase re-entry** — S7 emits typed `ReflectiveReturn` that is REVISION CONTEXT (not a side-channel state mutation); the target phase re-executes and produces a NEW validated delta.
2. Three-branch capability resolution: `REGISTERED_CAPABILITY` / `CUTTER_SPEC_SYNTHESIS` / `ORGAN_GAP` — the runtime never silently coerces to a nearest cutter and never fabricates a `ProjectionResult`.
3. Compositional synthesis of a new declarative `CutterSpec` from public typed context (regex-pattern hypothesis + target family + recognition criteria) → compile-bind against a generic primitive registry → physical execution against the ORIGINAL immutable source.
4. Typed `OrganGap` with `activation_authority = "NONE"` when neither registered nor composable resolution suffices — no coercion, no fabrication.

## Contracts and types (transplantable)

Under `socrates_runtime/`:

| Module | Contents |
|---|---|
| `projection.py` | `SemanticProjectionSpec`, `ProjectionResult`, `ProjectionDiagnostics`, `ReflectiveReturn`, `ProjectionLineage`, `RetreatLevel`, `ReturnTarget`, `DiagnosticSignal`. |
| `projection_primitives.py` | `SpanScanner`, `FamilyClassifier`, `TargetFilter`, `CoverageComputer`, `PrimitiveRegistry`, `LabeledSpan`, `ClassifiedSpan`. |
| `capability_resolution.py` | `CapabilityResolutionKind`, `CapabilityResolution`, `CapabilityResolver`, `GeneratedCutterSpec`, `PrimitiveInvocation`, `CompiledCutter`, `compile_bind`, `SpecSynthesizer`, `OrganGap`, `OrganDevelopmentProposal`. |
| `cutter_registry.py` | `CutterCapability`, `CutterRegistry`, `compute_diagnostics`. |
| `projection_step.py` | `make_projection_step(resolver, cutter_registry)` — the three-branch pipeline seam. |
| `pipeline.py` (partial) | Outer projection-control loop + `_record_reflective_context` (target re-entry semantics). |

JSON Schemas under `data/socrates/current/contracts/`:

- `projection_spec.schema.json`
- `projection_result.schema.json`
- `projection_diagnostics.schema.json`
- `reflective_return.schema.json`
- `generated_cutter_spec.schema.json` **(new)**
- `organ_gap.schema.json` **(new)**
- `capability_resolution.schema.json` **(new)**

## Evidence — actual test artefacts

- Peskov end-to-end trace: [`PESKOV_TRACE.json`](PESKOV_TRACE.json) — full projection lineage + phase sequence proving `S7 → S4 → S5..S10` target re-entry.
- ADR-S26-023 Test A + Test B traces: [`CAPABILITY_RESOLUTION_TRACE.json`](CAPABILITY_RESOLUTION_TRACE.json) — resolver decisions + binding evidence + object provenance for the synthesised projection; typed organ-gap record with all required fields.

## Test-provenance mapping (donor → assertion)

| Claim | Test file : test |
|---|---|
| Projection control loop closes | [`test_projection_control_loop.py`](../../../CALIFORNIAN_ID/tests/workbench/test_projection_control_loop.py) : `test_mismatch_triggers_epilogue_and_second_pass` |
| Actual target-phase re-entry (S4) | `test_projection_control_loop.py : test_pass_two_starts_AT_return_target` |
| Scene-return re-entry (S1) | `test_projection_control_loop.py : test_scene_return_actually_re_enters_S1` |
| Stale-hint negative | `test_projection_control_loop.py : test_stale_first_pass_hint_does_not_overwrite_reflective_revision` |
| Immutable source | [`test_peskov_projection_loop.py`](../../../CALIFORNIAN_ID/tests/workbench/test_peskov_projection_loop.py) : `test_peskov_p2_rereads_original_source_not_p1_units` |
| Lineage preservation | `test_peskov_projection_loop.py : test_peskov_p1_preserved_after_p2` |
| REGISTERED_CAPABILITY | [`test_capability_resolution.py`](../../../CALIFORNIAN_ID/tests/workbench/test_capability_resolution.py) : `test_A_previous_projection_preserved_when_synthesised_step_runs` |
| CUTTER_SPEC_SYNTHESIS end-to-end | `test_capability_resolution.py : test_A_novel_projection_synthesis_end_to_end` |
| CUTTER_SPEC_SYNTHESIS no case-magic | `test_capability_resolution.py : test_A_no_case_specific_magic_operation_names` |
| CUTTER_SPEC_SYNTHESIS through runtime | `test_capability_resolution.py : test_synthesis_end_to_end_through_pipeline_runtime` |
| ORGAN_GAP end-to-end | `test_capability_resolution.py : test_B_true_organ_gap_end_to_end` |
| ORGAN_GAP vs SOURCE_GAP isolation | `test_capability_resolution.py : test_B_gap_is_not_a_source_gap` |
| Authority: spec is data | `test_capability_resolution.py : test_authority_generated_spec_is_unprivileged_data` |
| Authority: gap + proposal have zero authority | `test_capability_resolution.py : test_authority_organ_gap_and_proposal_have_zero_activation_authority` |
| Compile-bind fail-closed | `test_capability_resolution.py : test_compile_bind_fails_closed_on_*` (three tests) |

## Primitive / executor dependencies (donor-side)

The generic primitive substrate depends only on:

- Python 3.11+ stdlib (`re`, `dataclasses`, `enum`, `typing`, `hashlib`, `secrets`).
- `socrates_runtime.projection` type definitions (also transplantable).

No provider, no filesystem, no external service. Fully host-neutral.

## Authority assumptions (must be preserved on the receiver)

1. `GeneratedCutterSpec` is UNPRIVILEGED DATA. Enforced by absence of `execute` / `install` / `authorize` methods on the class (test asserts).
2. `OrganGap.activation_authority = "NONE"` — a constant string, machine-readable. Any receiver-side wrapper that reads a gap MUST honour it.
3. `OrganDevelopmentProposal.activation_authority = "NONE"` — same rule; proposals are for human consideration, not self-triggering.
4. `compile_bind` refuses unknown primitives. Any receiver-side extension MUST use the same primitive-registration mechanism; no "install a new primitive from a spec" path exists in the donor code.
5. Provider prose is data, not authority. Enforced by `test_authority_provider_prose_cannot_be_a_gap`.

## DATA/DECLARATIVE SPEC vs EXECUTABLE CAPABILITY split

| Layer | Kind | Authority |
|---|---|---|
| `SemanticProjectionSpec` | Data | None — describes a projection. |
| `GeneratedCutterSpec` | Data | None — describes a composition graph. |
| `PrimitiveInvocation` | Data | None — names + params. |
| `SpanScanner` etc. instance | Executable | Bounded — runs regex, no external effects. |
| `PrimitiveRegistry` entries | Executable | Bounded — registered by the runtime, not by data. |
| `CutterCapability` | Executable | Bounded — registered by the runtime, not by data. |
| `CompiledCutter` | Executable | Bounded — composition of already-registered primitives. |
| `OrganGap` | Data | Explicitly zero (`activation_authority = "NONE"`). |

**No path exists in the donor code by which a data record can promote itself into an executable capability.** A receiver-side transplant must preserve this invariant.

## Public typed attention / projection evidence

Every resolver decision + every projection execution is recorded on `PipelineState` in typed form and surfaced by `to_public()`:

- `state.projection_lineage.to_public()` — projections + revisions + diagnostics history.
- `state.capability_resolutions[*].to_public()` — every resolver decision with typed reason.
- `state.pending_reflective_context.to_public()` (transient) — the target-phase context.

A trace reader can reconstruct every branch decision + every projection + every reflection without inspecting hidden runtime state.

## Failure modes (donor observed + tested)

- `BindingError` — spec references unknown primitive, unbound input, or bad params. Raised — never silently swallowed. (3 tests)
- `SpecUnsynthesizable` — synthesizer cannot produce a spec from the request. Caught by resolver → cascades to ORGAN_GAP. (implicit in Test B)
- `ProviderStatus.RETRIES_EXHAUSTED` — LIVE-mode provider failed after bounded retries. Distinct from `ReflectiveReturn` (technical retry vs governing-hypothesis change). Preserved unchanged from ADR-S26-022.
- Same-diagnosis / iteration-bound / prose-only-reflection guards — from ADR-S26-022, preserved unchanged.

## Collateral risks (donor observed)

- The BASIC primitive substrate is small (four primitives). A receiver whose real operations need higher-order structures (sequence-order, temporal reasoning, cross-source alignment) will see high ORGAN_GAP rates until the substrate is extended.
- The default `SpecSynthesizer` recognises exactly one synthesis pattern (regex-based). LIVE-mode synthesis requires a richer synthesizer that consumes the mounted body prompt.
- Test-double reflective_hints — the deterministic test infrastructure uses iteration-aware hints to steer S4 on pass 2. In LIVE mode the equivalent must come from a mounted-body prompt reading `state.pending_reflective_context`; the router prompt authoring is a follow-up.

## Unresolved gaps

- LIVE-model synthesis path is not implemented (deterministic proof only).
- No primitive for sequence-order analysis (Test B remains a real gap).
- No production-grade native Tinkuy semantic cutting exists yet. The two marker-scan cutters (`EXTRACT_CONCEPTS`, `DIFFERENTIATED_ACCOUNT`) are test fixtures used for the Peskov deterministic proof — honestly labelled in the ADR.

## Tinkuy-specific dependencies

Non-transplantable without adaptation:

- `SocratesRuntime` composition root — assumes Tinkuy's semantic-mount / router / governor topology.
- `PipelineExecutor` — assumes Tinkuy's S0..S10 phase model.
- `PhaseDelta` / `PhaseHint` — assumes Tinkuy's phase-executor seam.
- `SemanticMountPolicy` — assumes Tinkuy's mount-manifest schema.

## Host-neutral / transplantable components

Transplantable to a different runtime without change:

- `socrates_runtime/projection.py` — pure typed records.
- `socrates_runtime/projection_primitives.py` — pure stdlib primitives.
- `socrates_runtime/capability_resolution.py` — pure typed records + resolver logic (depends on `projection.py` and `projection_primitives.py` only).
- `data/socrates/current/contracts/*.schema.json` — JSON Schemas, no runtime dependency.

## De-scaffolding evidence

The three transplantable modules above have zero imports from `californian_id.*`, `tinkuy_runtime.*`, or any Tinkuy-specific package:

```
$ grep -E '^(from|import)' socrates_runtime/projection.py \
    socrates_runtime/projection_primitives.py \
    socrates_runtime/capability_resolution.py \
    | grep -Ev 'from \.|from __future__|import (re|hashlib|secrets|typing|dataclasses|enum)'
# empty
```

## Explicit nonclaims

- **NOT** a claim of successful Aiye transplantation. This packet is bounded donor evidence only.
- **NOT** a claim that the receiver's Academy / Sayena will accept the transplant as-is.
- **NOT** a claim of LIVE-model synthesis. Deterministic proof only.
- **NOT** a claim that the shipped primitive substrate is complete for real workloads.
- **NOT** a claim that ORGAN_GAP has resolution machinery. The gap is emitted; developing the missing organ is a human-governed follow-up.
- **NOT** a claim of R8 semantic-arm improvement. R8 baseline unchanged.
- **NOT** a claim of P001 unblock. See final report §P.

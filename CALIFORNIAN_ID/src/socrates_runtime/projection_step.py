"""Bind a :class:`CapabilityResolver` to the pipeline's projection_step slot.

Post ADR-S26-023: the projection step routes through capability
resolution rather than directly looking up a :class:`CutterCapability`.
The three branches are honest and typed:

    REGISTERED_CAPABILITY   — existing behaviour: execute the
                              registered cutter against the ORIGINAL
                              source; record ProjectionResult +
                              diagnostics.

    CUTTER_SPEC_SYNTHESIS   — a :class:`GeneratedCutterSpec` was
                              synthesised and compile-bound; execute
                              the CompiledCutter against the ORIGINAL
                              source; record the spec + binding
                              evidence alongside the ProjectionResult.

    ORGAN_GAP               — no path can execute this operation.
                              Record the typed OrganGap in state,
                              raise a typed diagnostic
                              (APPLICABILITY_FAILURE), DO NOT fabricate
                              a ProjectionResult. The outer loop can
                              still reflect (S7), and the governor can
                              terminate cleanly (PRESERVE_APORIA, DWELL,
                              RETURN_OPERATION as appropriate).

In every branch the immutable-source invariant holds: the step reads
``state.input_text`` and never any prior projection's derived output.

The pipeline may be given operation-specific ``synthesis_hypotheses``
via ``state.operation_hypotheses`` (opt-in field). When absent, the
resolver's SYNTHESIS branch falls back to whatever the default
:class:`SpecSynthesizer` accepts (currently: pattern-based only, so
absent hypotheses ⇒ SYNTHESIS unavailable ⇒ resolver falls through to
ORGAN_GAP unless a registered capability exists).
"""
from __future__ import annotations

from typing import Any, Callable

from .capability_resolution import (
    CapabilityRequest,
    CapabilityResolution,
    CapabilityResolutionKind,
    CapabilityResolver,
)
from .cutter_registry import CutterRegistry, compute_diagnostics
from .projection import (
    DiagnosticSignal,
    ProjectionDiagnostics,
    ProjectionStatus,
    SemanticProjectionSpec,
    new_projection_id,
)
from .state import PipelineState


ProjectionStep = Callable[[PipelineState], None]


def make_projection_step(resolver: CapabilityResolver,
                         *, cutter_registry: CutterRegistry | None = None,
                         ) -> ProjectionStep:
    """Factory returning a callable suitable for ``PipelineExecutor.projection_step``.

    ``resolver`` is the three-branch resolver ADR-S26-023 requires.
    ``cutter_registry`` is optional and only used to pass to
    ``compute_diagnostics`` in the REGISTERED_CAPABILITY branch so
    diagnostics can suggest a covering operation from among the
    registered set (unchanged behaviour). If not supplied, the
    resolver's own cutter_registry is used.
    """
    if cutter_registry is None:
        cutter_registry = resolver.cutter_registry

    def step(state: PipelineState) -> None:
        op_kind = state.operation.kind or ""
        if not op_kind:
            return

        # D-S26-GEN-003 proposal path: if S4 (or any prior phase) emitted
        # a typed ProjectionSynthesisProposal, prefer it. The proposal
        # supplies the composition; the runtime supplies runtime
        # provenance. This is where LIVE Socrates authoring its own
        # declarative cutter proposal becomes executable end-to-end.
        proposal = state.pending_projection_proposal
        if proposal is not None:
            _execute_proposal(state, proposal, resolver)
            state.pending_projection_proposal = None
            return

        target = _target_family_from_state(state, op_kind, cutter_registry)
        hypotheses = _hypotheses_from_state(state, op_kind)

        # Direct-assistance / non-projection short-circuit: the current
        # operation was not registered as a cutter, was not asked for a
        # projection via target_object_family, and no synthesis
        # hypothesis was supplied. In that case the operation is not
        # asking for source projection at all — no capability is
        # missing, no gap exists to report. The projection step
        # legitimately no-ops. This preserves the ADR-S26-022 §11 and
        # ADR-S26-023 direct-assistance invariant: operations that
        # don't require source projection are not penalised by the
        # capability-resolution machinery.
        no_registered = not cutter_registry.has(op_kind)
        no_target = not target
        no_hypothesis = not hypotheses
        if no_registered and no_target and no_hypothesis:
            return
        prev = (state.projection_lineage.entries[-1]
                if state.projection_lineage.entries else None)
        last_revision = (state.projection_lineage.revisions[-1]
                         if state.projection_lineage.revisions else None)
        ontology_hypothesis = (last_revision.revised_ontology_id
                               if (last_revision and
                                   last_revision.revised_ontology_id)
                               else "")

        req = CapabilityRequest(
            operation_id=op_kind,
            source_id=state.source_id,
            scene_ref=state.scene.telos,
            target_object_family=target,
            ontology_hypothesis=ontology_hypothesis,
            recognition_criteria=(),
            hypotheses=hypotheses,
            required_attention_structure=(
                hypotheses.get("required_attention_structure", "") or ""))
        resolution = resolver.resolve(req)
        state.capability_resolutions.append(resolution)

        if resolution.kind == CapabilityResolutionKind.REGISTERED_CAPABILITY:
            _execute_registered(state, resolution, req, prev,
                                cutter_registry)
            return
        if resolution.kind == CapabilityResolutionKind.CUTTER_SPEC_SYNTHESIS:
            _execute_synthesised(state, resolution, prev, cutter_registry)
            return
        # ORGAN_GAP — DO NOT fabricate a ProjectionResult.
        _record_organ_gap(state, resolution)

    return step


# ---------------------------------------------------------- branch executors


def _execute_registered(state: PipelineState,
                        resolution: CapabilityResolution,
                        req: CapabilityRequest,
                        prev,
                        cutter_registry: CutterRegistry) -> None:
    cap = cutter_registry.get(resolution.registered_capability_id)
    assert cap is not None, (
        f"resolver named registered_capability_id "
        f"{resolution.registered_capability_id!r} but registry lost it — "
        f"this is a programming error, not a data error")

    last_revision = (state.projection_lineage.revisions[-1]
                     if state.projection_lineage.revisions else None)
    ontology_id = (last_revision.revised_ontology_id
                   if (last_revision and last_revision.revised_ontology_id)
                   else cap.segmentation_policy)

    spec = SemanticProjectionSpec(
        projection_id=new_projection_id(),
        source_id=state.source_id, scene_ref=state.scene.telos,
        operation_id=cap.operation_id,
        ontology_id=ontology_id,
        target_object_family=cap.target_object_family,
        recognition_criteria=cap.recognition_criteria,
        segmentation_policy=cap.segmentation_policy,
        evidence_requirements=(),
        applicability_assumptions=(),
        contraindications=cap.contraindications,
        parent_projection_id=prev.projection_id if prev else "",
        revises=prev.projection_id if prev else "",
        status=ProjectionStatus.EXPLORATORY)
    result = cap.execute(state.input_text, spec)
    # D-S26-PROV-003: explicit typed lineage on the ProjectionResult so
    # a trace reader never has to rely on list position.
    result.spec_id = spec.projection_id
    result.parent_projection_id = spec.parent_projection_id
    result.revises_projection_id = spec.revises
    result.capability_resolution_id = getattr(
        resolution, "resolution_id", "") or f"cres:{id(resolution):x}"
    _apply_reflective_lineage(result, state)
    # D-S26-PROV-004: stamp full projection-relative provenance onto
    # every object + residue the cutter produced.
    result.stamp_object_provenance(
        operation_id=spec.operation_id, ontology_id=spec.ontology_id)
    state.projection_lineage.add_projection(result)

    diag = compute_diagnostics(result, spec, cutter_registry)
    state.projection_lineage.add_diagnostics(diag)

    if diag.mismatch:
        state.pending_diagnostic = diag
    else:
        state.pending_diagnostic = None
        if result.status == ProjectionStatus.EXPLORATORY:
            state.projection_lineage.mark_status(
                result.projection_id, ProjectionStatus.ACCEPTED_LOCAL)


def _execute_synthesised(state: PipelineState,
                         resolution: CapabilityResolution,
                         prev,
                         cutter_registry: CutterRegistry) -> None:
    """Execute the compiled synthesised cutter against the ORIGINAL source.

    The generated spec is unprivileged data; the compiled cutter is
    the executable form of that data plus references to primitives
    already registered in the primitive registry. No new authority is
    minted — every step is a call into an existing generic primitive.
    """
    compiled = resolution.compiled_cutter
    assert compiled is not None, (
        "resolver reported CUTTER_SPEC_SYNTHESIS without a compiled "
        "cutter — programming error")
    result = compiled.execute(state.input_text)
    # D-S26-PROV-003 repair: explicit typed lineage relations on the
    # ProjectionResult (not just list position).
    result.spec_id = compiled.spec.spec_id
    result.parent_projection_id = (prev.projection_id if prev else "")
    result.revises_projection_id = compiled.spec.revises
    result.capability_resolution_id = getattr(
        resolution, "resolution_id", "") or f"cres:{id(resolution):x}"
    _apply_reflective_lineage(result, state)
    # D-S26-PROV-004 repair: stamp full projection-relative provenance
    # onto every object + residue.
    result.stamp_object_provenance(
        operation_id=compiled.spec.operation_id,
        ontology_id=compiled.spec.ontology_id)
    state.projection_lineage.add_projection(result)

    diag = _compute_synthesised_diagnostics(result, resolution)
    state.projection_lineage.add_diagnostics(diag)

    if diag.mismatch:
        state.pending_diagnostic = diag
    else:
        state.pending_diagnostic = None
        if result.status == ProjectionStatus.EXPLORATORY:
            state.projection_lineage.mark_status(
                result.projection_id, ProjectionStatus.ACCEPTED_LOCAL)


def _execute_proposal(state: PipelineState,
                      proposal,
                      resolver: CapabilityResolver) -> None:
    """Execute a model-produced :class:`ProjectionSynthesisProposal`
    end-to-end (D-S26-GEN-003).

    Flow:
        proposal (unprivileged data)
        → resolver.resolve_from_proposal (schema/jurisdiction already
          validated at phase_output parse time; here we compile-bind
          against the primitive registry)
        → on success: physical execution against ORIGINAL immutable
          source; result recorded with full provenance
        → on bind failure: typed :class:`OrganGap` recorded; no
          fabricated result.
    """
    prev = (state.projection_lineage.entries[-1]
            if state.projection_lineage.entries else None)
    resolution = resolver.resolve_from_proposal(
        proposal, source_id=state.source_id,
        scene_ref=state.scene.telos,
        parent_projection_id=(prev.projection_id if prev else ""))
    state.capability_resolutions.append(resolution)
    if resolution.kind == CapabilityResolutionKind.CUTTER_SPEC_SYNTHESIS:
        _execute_synthesised(state, resolution, prev, resolver.cutter_registry)
        return
    # ORGAN_GAP path — no fabricated ProjectionResult.
    _record_organ_gap(state, resolution)


def _apply_reflective_lineage(result, state: PipelineState) -> None:
    """Backfill triggered_by_diagnostic_* and reflective_return_id on a
    ProjectionResult when the current pass is a reflective re-entry
    (D-S26-PROV-003 repair). No-op when this is not a reflective pass.
    """
    revisions = state.projection_lineage.revisions
    if not revisions:
        return
    last = revisions[-1]
    diag_fingerprint = getattr(last, "diagnostic_fingerprint", "") or ""
    # Locate the diagnostic by fingerprint.
    diag_id = ""
    for d in state.projection_lineage.diagnostics_history:
        if d.fingerprint() == diag_fingerprint:
            diag_id = d.projection_id
            break
    if diag_id and not result.triggered_by_diagnostic_id:
        result.triggered_by_diagnostic_id = diag_id
    if diag_fingerprint and not result.triggered_by_diagnostic_fingerprint:
        result.triggered_by_diagnostic_fingerprint = diag_fingerprint
    reflective_id = getattr(last, "reflective_id", "") or ""
    if reflective_id and not result.reflective_return_id:
        result.reflective_return_id = reflective_id
    # If this is a reflection-triggered projection, revises_projection_id
    # comes from the ReflectiveReturn's from_projection_id — more
    # specific than the entries[-1] parent.
    if last.from_projection_id and not result.revises_projection_id:
        result.revises_projection_id = last.from_projection_id


def _compute_synthesised_diagnostics(result,
                                     resolution: CapabilityResolution,
                                     ) -> ProjectionDiagnostics:
    """Simplified diagnostics for a synthesised projection.

    Without another registered operation to suggest as a covering
    op, the ONTOLOGY_LIMIT signal is the honest one when residue
    remains — the runtime knows the synthesised look didn't cover
    everything, but it does not know a better one from its
    registered set.
    """
    signals: list[DiagnosticSignal] = []
    total = max(len(result.objects) + len(result.residue), 1)
    residue_ratio = len(result.residue) / total
    reason = ""
    if result.residue:
        signals.append(DiagnosticSignal.ONTOLOGY_LIMIT)
        if result.recognition_failures:
            signals.append(DiagnosticSignal.RECOGNITION_FAILURE)
        reason = (f"synthesised composition left residue "
                  f"{sorted({r.apparent_family for r in result.residue})!r} "
                  f"outside target family")
    return ProjectionDiagnostics(
        projection_id=result.projection_id,
        signals=tuple(signals),
        reason=reason or "synthesised projection adequate",
        residue_ratio=residue_ratio,
        recognition_failure_count=len(result.recognition_failures))


def _record_organ_gap(state: PipelineState,
                      resolution: CapabilityResolution) -> None:
    """Record the ORGAN_GAP without fabricating a ProjectionResult.

    The gap is already stored inside
    ``state.capability_resolutions[-1].organ_gap``. What we do here:

        * raise a typed APPLICABILITY_FAILURE diagnostic so the
          reflective loop can react honestly if the caller wants to
          try a different operation;
        * DO NOT add a fake ProjectionResult to lineage — the
          absence of a result is the honest report.
    """
    gap = resolution.organ_gap
    assert gap is not None, (
        "resolver reported ORGAN_GAP without a gap object — "
        "programming error")
    diag = ProjectionDiagnostics(
        projection_id=f"gap:{gap.gap_id}",
        signals=(DiagnosticSignal.APPLICABILITY_FAILURE,),
        reason=(f"ORGAN_GAP for operation {resolution.operation_id!r}: "
                f"{gap.missing_capability_hypothesis}"),
        residue_ratio=1.0, recognition_failure_count=0)
    state.projection_lineage.add_diagnostics(diag)
    # Do NOT set pending_diagnostic — a gap is not a projection
    # mismatch; it's a capability insufficiency. If the caller wants
    # reflection on the gap (e.g. try a different operation), they
    # can set pending_diagnostic explicitly. Default: gap surfaced in
    # capability_resolutions, run terminates cleanly.


# ---------------------------------------------------------- helpers


def _target_family_from_state(state: PipelineState, op_kind: str,
                              cutter_registry: CutterRegistry,
                              ) -> tuple[str, ...]:
    """Infer target_object_family for the request.

    Order of resolution:
        1. explicit ``state.operation_target_family`` if set (opt-in);
        2. registered capability's target if the op IS registered;
        3. best guess from operation-specific hypotheses;
        4. empty tuple (resolver will emit ORGAN_GAP or fail synthesis).
    """
    explicit = getattr(state, "operation_target_family", None)
    if explicit:
        return tuple(explicit)
    cap = cutter_registry.get(op_kind)
    if cap is not None:
        return cap.target_object_family
    hypotheses = _hypotheses_from_state(state, op_kind)
    tf = hypotheses.get("target_object_family")
    if tf:
        return tuple(tf)
    return ()


def _hypotheses_from_state(state: PipelineState, op_kind: str,
                           ) -> dict[str, Any]:
    """Fetch synthesis hypotheses for the current operation.

    Looks at ``state.operation_hypotheses`` (opt-in dict field), which
    a caller may populate via a PhaseHint before S9. When absent,
    returns an empty dict — the resolver falls through to whatever the
    default synthesizer can handle, and eventually to ORGAN_GAP if
    nothing fits.
    """
    hyps = getattr(state, "operation_hypotheses", None) or {}
    return dict(hyps.get(op_kind, hyps) if op_kind in hyps else hyps)


__all__ = ["ProjectionStep", "make_projection_step"]

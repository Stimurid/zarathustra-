"""Bind a :class:`CutterRegistry` to the pipeline's projection_step slot.

The projection step is what actually executes the current "look" against
the source. Called by :class:`PipelineExecutor` after each inner
S0..S10 pass, it:

    1. builds a :class:`SemanticProjectionSpec` from the current
       ``state.operation`` (and the last-recorded reflective return,
       if any, to pick up ``revised_ontology_id`` and lineage);
    2. resolves the operation to a :class:`CutterCapability` in the
       registry — if none is registered for the operation kind, the
       step is a no-op (direct-assistance fast path unaffected);
    3. executes the cutter against ``state.input_text`` — the ORIGINAL,
       immutable source — never against any prior projection's derived
       output;
    4. records the :class:`ProjectionResult` in
       ``state.projection_lineage`` and appends the resulting
       :class:`ProjectionDiagnostics`;
    5. sets ``state.pending_diagnostic`` iff the diagnostics say
       mismatch — this is the switch that tells the outer loop to
       invoke the reflective epilogue.

The immutable-source invariant is enforced BY CONSTRUCTION:
``state.input_text`` is set once at :meth:`PipelineExecutor.run` entry
and never rewritten (nothing in the runtime mutates it — a test proves
it). Every ProjectionSpec carries ``source_id`` derived from that same
text, so P1 and P2 must share the same ``source_id``.
"""
from __future__ import annotations

from typing import Callable

from .cutter_registry import CutterRegistry, compute_diagnostics
from .projection import (
    ProjectionStatus,
    SemanticProjectionSpec,
    new_projection_id,
)
from .state import PipelineState


ProjectionStep = Callable[[PipelineState], None]


def make_projection_step(registry: CutterRegistry) -> ProjectionStep:
    """Factory returning a callable suitable for ``PipelineExecutor.projection_step``.

    Bound to ``registry`` at factory time so tests can construct a
    scoped registry per case without leaking state into the module.
    """
    def step(state: PipelineState) -> None:
        op_kind = state.operation.kind or ""
        capability = registry.get(op_kind)
        if capability is None:
            # Direct-assistance / non-projection operation — nothing to
            # execute; the outer loop will terminate normally.
            return
        # Lineage: is there a parent projection from an earlier pass?
        prev = (state.projection_lineage.entries[-1]
                if state.projection_lineage.entries else None)
        last_revision = (state.projection_lineage.revisions[-1]
                         if state.projection_lineage.revisions else None)
        # ontology_id: honour the reflective return's revised ontology
        # when the current pass is a re-entry; otherwise use the
        # capability's declared segmentation policy as the ontology id.
        ontology_id = (last_revision.revised_ontology_id
                       if (last_revision and last_revision.revised_ontology_id)
                       else capability.segmentation_policy)

        spec = SemanticProjectionSpec(
            projection_id=new_projection_id(),
            source_id=state.source_id,
            scene_ref=state.scene.telos,
            operation_id=op_kind,
            ontology_id=ontology_id,
            target_object_family=capability.target_object_family,
            recognition_criteria=capability.recognition_criteria,
            segmentation_policy=capability.segmentation_policy,
            evidence_requirements=(),
            applicability_assumptions=(),
            contraindications=capability.contraindications,
            parent_projection_id=prev.projection_id if prev else "",
            revises=prev.projection_id if prev else "",
            status=ProjectionStatus.EXPLORATORY)

        # Execute against the ORIGINAL source. state.input_text is
        # immutable across the run — never rewritten by any phase, nor
        # by any projection. This is the invariant that lets P2 be a
        # genuine second look, not a revision of P1's derivations.
        result = capability.execute(state.input_text, spec)
        state.projection_lineage.add_projection(result)

        diag = compute_diagnostics(result, spec, registry)
        state.projection_lineage.add_diagnostics(diag)

        if diag.mismatch:
            state.pending_diagnostic = diag
        else:
            # Clean projection — clear any stale pending diagnostic
            # (it should already be None, but be explicit).
            state.pending_diagnostic = None
            # Reclassify the projection as ACCEPTED_LOCAL if the cutter
            # left it EXPLORATORY.
            if result.status == ProjectionStatus.EXPLORATORY:
                state.projection_lineage.mark_status(
                    result.projection_id, ProjectionStatus.ACCEPTED_LOCAL)

    return step


__all__ = ["ProjectionStep", "make_projection_step"]

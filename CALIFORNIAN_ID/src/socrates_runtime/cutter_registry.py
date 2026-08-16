"""Cutter / executor governance — ADR-S26-022 §8.

Socrates does NOT parse the source itself. It selects an operation, an
ontology, and a recognition policy; Tinkuy executes the projection
against the source via a *cutter* (or "projection executor"). This
module is that registry.

The registry is deliberately thin. We reuse the existing extraction
substrate where possible (see :mod:`californian_id.fabric.parser` and
:mod:`californian_id.adapters.text_chunker`) rather than building a zoo
of new cutters — the ADR is explicit that we want the minimum needed
for a first genuine closed-loop proof.

What a cutter capability exposes:

    * ``operation_id`` — the operation kind the cutter is applicable to;
    * ``target_object_family`` — which object families it can recognise;
    * ``segmentation_policy`` — identity string that goes into
      :class:`SemanticProjectionSpec.segmentation_policy`;
    * ``execute(source_text, spec)`` — pure function ``(str, spec) ->
      ProjectionResult``; the ``source_text`` is the ORIGINAL source
      the pipeline holds on ``PipelineState.input_text``, never a
      derived text from an earlier projection.

Two capabilities ship in this commit — enough to prove the loop on the
Peskov case (CONCEPT_EXTRACTION forces mismatch, DIFFERENTIATED_ACCOUNT
covers residue). More capabilities are added by the same registration
mechanism; the runtime does not distinguish them by name past
capability lookup.

The MARK-based cutting used here is intentionally symbolic — its role
is to make the loop mechanics testable end-to-end without the noise of
NLP. A real NLP-driven cutter (fabric parser, a live-model extractor)
plugs into the same shape and produces the same typed
:class:`ProjectionResult`.
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Callable, Iterable

from .projection import (
    DiagnosticSignal,
    ProjectedObject,
    ProjectionDiagnostics,
    ProjectionResult,
    ProjectionStatus,
    Residue,
    SemanticProjectionSpec,
)


# ---------------------------------------------------------- capability

CutterCallable = Callable[[str, SemanticProjectionSpec], ProjectionResult]


@dataclass(frozen=True)
class CutterCapability:
    """One projection executor registered with the runtime.

    Kept small: enough for the pipeline to pick a cutter by operation
    kind and to record its identity in the trace. Capability metadata
    doubles as the source of truth for
    :class:`SemanticProjectionSpec.target_object_family` and
    ``recognition_criteria`` when the pipeline synthesises a spec.
    """
    operation_id: str
    segmentation_policy: str
    target_object_family: tuple[str, ...]
    recognition_criteria: tuple[str, ...]
    contraindications: tuple[str, ...]
    execute: CutterCallable


# ---------------------------------------------------------- registry


class CutterRegistry:
    """Register + resolve :class:`CutterCapability` by operation kind.

    A capability may be re-registered (last write wins) — this is what
    lets a Workbench test swap a stub for a real cutter. Lookup is
    case-sensitive; operation ids are canonical strings (``EXTRACT_CONCEPTS``,
    ``DIFFERENTIATED_ACCOUNT``), matching what S4 emits into
    ``state.operation.kind``.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, CutterCapability] = {}

    def register(self, capability: CutterCapability) -> None:
        self._capabilities[capability.operation_id] = capability

    def get(self, operation_id: str) -> CutterCapability | None:
        return self._capabilities.get(operation_id)

    def has(self, operation_id: str) -> bool:
        return operation_id in self._capabilities

    def known_operations(self) -> tuple[str, ...]:
        return tuple(sorted(self._capabilities))


# ---------------------------------------------------------- marker-based cutter

#: The two cutters below recognise a small vocabulary of category
#: markers on lines of the source. Real cutters will use fabric-level
#: parsing / NLP; this substrate is exactly what the ADR calls the
#: "minimum sufficient to demonstrate a genuine first closed-loop
#: proof": lightweight, deterministic, testable.

_MARKER_RE = re.compile(r"^\s*\[(?P<family>[a-z_]+)\]\s*(?P<body>.*)$",
                        re.IGNORECASE | re.MULTILINE)


def _scan_marked_lines(source_text: str) -> list[tuple[str, int, int, str]]:
    """Return ``(family, char_start, char_end, body)`` tuples."""
    out: list[tuple[str, int, int, str]] = []
    for m in _MARKER_RE.finditer(source_text or ""):
        family = m.group("family").lower()
        body = m.group("body").strip()
        out.append((family, m.start(), m.end(), body))
    return out


def _new_object_id() -> str:
    return f"obj_{secrets.token_hex(5)}"


def _new_residue_id() -> str:
    return f"res_{secrets.token_hex(5)}"


def _new_projection_run_id(spec: SemanticProjectionSpec) -> str:
    """Deterministic-with-random suffix so ProjectionResult identity is
    stable across debug reads but distinct across executions."""
    return f"prun_{spec.projection_id[-6:]}_{secrets.token_hex(3)}"


def _make_concept_extractor() -> CutterCallable:
    def execute(source_text: str,
                spec: SemanticProjectionSpec) -> ProjectionResult:
        objects: list[ProjectedObject] = []
        residue: list[Residue] = []
        recognition_failures: list[str] = []
        lines = _scan_marked_lines(source_text)
        for family, start, end, body in lines:
            if family in spec.target_object_family:
                objects.append(ProjectedObject(
                    object_id=_new_object_id(),
                    object_family=family,
                    source_id=spec.source_id,
                    source_span=(start, end),
                    evidence=body[:200],
                    recognition_basis="explicit category marker",
                    confidence=1.0))
            else:
                residue.append(Residue(
                    residue_id=_new_residue_id(),
                    source_id=spec.source_id,
                    source_span=(start, end),
                    evidence=body[:200],
                    apparent_family=family,
                    reason=(f"category {family!r} is not in target family "
                            f"{list(spec.target_object_family)!r}")))
                recognition_failures.append(
                    f"{family}@{start}-{end}: not recognised by concept ontology")
        total = max(len(lines), 1)
        coverage = len(objects) / total
        status = (ProjectionStatus.EXPLORATORY
                  if residue else ProjectionStatus.ACCEPTED_LOCAL)
        return ProjectionResult(
            projection_id=spec.projection_id,
            spec_fingerprint=spec.fingerprint(),
            source_id=spec.source_id,
            objects=objects, residue=residue,
            coverage=coverage,
            recognition_failures=recognition_failures,
            status=status)
    return execute


def _make_differentiated_extractor() -> CutterCallable:
    def execute(source_text: str,
                spec: SemanticProjectionSpec) -> ProjectionResult:
        objects: list[ProjectedObject] = []
        residue: list[Residue] = []
        recognition_failures: list[str] = []
        lines = _scan_marked_lines(source_text)
        allowed = {f.lower() for f in spec.target_object_family}
        for family, start, end, body in lines:
            if family in allowed:
                objects.append(ProjectedObject(
                    object_id=_new_object_id(),
                    object_family=family,
                    source_id=spec.source_id,
                    source_span=(start, end),
                    evidence=body[:200],
                    recognition_basis="differentiated ontology marker",
                    confidence=1.0))
            else:
                residue.append(Residue(
                    residue_id=_new_residue_id(),
                    source_id=spec.source_id,
                    source_span=(start, end),
                    evidence=body[:200],
                    apparent_family=family,
                    reason="family outside differentiated ontology"))
                recognition_failures.append(
                    f"{family}@{start}-{end}: outside differentiated ontology")
        total = max(len(lines), 1)
        coverage = len(objects) / total
        status = (ProjectionStatus.ACCEPTED_LOCAL if not residue
                  else ProjectionStatus.PARTIAL)
        return ProjectionResult(
            projection_id=spec.projection_id,
            spec_fingerprint=spec.fingerprint(),
            source_id=spec.source_id,
            objects=objects, residue=residue,
            coverage=coverage,
            recognition_failures=recognition_failures,
            status=status)
    return execute


# ---------------------------------------------------------- built-in registry


def build_default_registry() -> CutterRegistry:
    """Ship the two capabilities needed for the ADR §15 Peskov proof."""
    reg = CutterRegistry()
    reg.register(CutterCapability(
        operation_id="EXTRACT_CONCEPTS",
        segmentation_policy="marker_scan/concept_v1",
        target_object_family=("concept",),
        recognition_criteria=(
            "explicit definition of a general term",
            "abstraction admitting instances"),
        contraindications=(
            "reports of events",
            "organisational gestures",
            "absences / gaps",
            "future-work indications"),
        execute=_make_concept_extractor()))
    reg.register(CutterCapability(
        operation_id="DIFFERENTIATED_ACCOUNT",
        segmentation_policy="marker_scan/differentiated_v1",
        target_object_family=(
            "concept", "report", "gesture", "absence", "future_work"),
        recognition_criteria=(
            "any explicit categorical marker on a source line",),
        contraindications=(),
        execute=_make_differentiated_extractor()))
    return reg


# ---------------------------------------------------------- diagnostics


def compute_diagnostics(result: ProjectionResult,
                        spec: SemanticProjectionSpec,
                        registry: CutterRegistry,
                        ) -> ProjectionDiagnostics:
    """Compute typed ``ProjectionDiagnostics`` from a result + registry.

    Signals raised (any single one is enough to force reflection):

        * ``OPERATION_MISMATCH`` — residue present AND another registered
          operation would accept the residue families. This is the
          Peskov signal: the source contained material the current
          operation refused to touch, and a different operation would.
        * ``ONTOLOGY_LIMIT`` — residue present but no other registered
          operation covers the residue families. The runtime knows the
          look is insufficient; it does not know a better one.
        * ``RECOGNITION_FAILURE`` — recognition_failures were recorded
          (piggy-back on the two above).

    Also produces ``suggested_operation`` / ``suggested_ontology`` /
    ``suggested_target_family`` when a covering operation exists — S7
    consumes these as inputs when it emits the ReflectiveReturn (though
    S7 remains free to reject them).
    """
    signals: list[DiagnosticSignal] = []
    residue_families = tuple(sorted({r.apparent_family for r in result.residue}))
    total = max(len(result.objects) + len(result.residue), 1)
    residue_ratio = len(result.residue) / total

    suggested_op = ""
    suggested_family: tuple[str, ...] = ()
    suggested_ontology = ""
    if residue_families:
        covering_ops = _covering_operations(registry, residue_families,
                                             exclude=spec.operation_id)
        if covering_ops:
            suggested_op = covering_ops[0].operation_id
            suggested_family = covering_ops[0].target_object_family
            suggested_ontology = covering_ops[0].segmentation_policy
            signals.append(DiagnosticSignal.OPERATION_MISMATCH)
        else:
            signals.append(DiagnosticSignal.ONTOLOGY_LIMIT)
        if result.recognition_failures:
            signals.append(DiagnosticSignal.RECOGNITION_FAILURE)

    reason_parts: list[str] = []
    if residue_families:
        reason_parts.append(
            f"unclassified families in source: {list(residue_families)}")
    if suggested_op:
        reason_parts.append(
            f"operation {suggested_op!r} accepts the residue families")
    if not reason_parts:
        reason_parts.append("no material mismatch — projection adequate")

    return ProjectionDiagnostics(
        projection_id=result.projection_id,
        signals=tuple(signals),
        reason="; ".join(reason_parts),
        residue_ratio=residue_ratio,
        recognition_failure_count=len(result.recognition_failures),
        suggested_operation=suggested_op,
        suggested_ontology=suggested_ontology,
        suggested_target_family=suggested_family,
    )


def _covering_operations(registry: CutterRegistry,
                         residue_families: Iterable[str],
                         *, exclude: str) -> list[CutterCapability]:
    """Return registered ops whose target_object_family covers all residue.

    A single operation must cover EVERY residue family for the runtime
    to name it a covering suggestion — the pipeline never suggests an
    op that would leave residue of its own. Order is deterministic by
    operation id for reproducibility.
    """
    residue_set = {f.lower() for f in residue_families}
    out: list[CutterCapability] = []
    for op_id in registry.known_operations():
        if op_id == exclude:
            continue
        cap = registry.get(op_id)
        if cap is None:
            continue
        if residue_set.issubset({f.lower() for f in cap.target_object_family}):
            out.append(cap)
    return out


__all__ = [
    "CutterCapability", "CutterCallable", "CutterRegistry",
    "build_default_registry", "compute_diagnostics",
]

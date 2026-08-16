"""Projection substrate — how Socrates looks at a source.

A projection is *how* the system is currently attending to a source: the
operation being applied, the ontology whose objects it recognises, the
recognition criteria, and the executor asked to physically read the source.

The runtime distinguishes three typed objects (and one control record):

    SemanticProjectionSpec   — the declaration of the current look.
    ProjectionResult         — what one look produced (objects + residue).
    ProjectionDiagnostics    — typed judgement about the LOOK itself, not
                                only about the objects. Signals name failure
                                modes B03/B07/B08 already describe in prose.
    ReflectiveReturn         — the executable version of B07's reflective
                                retreat: what changes, and where the runtime
                                re-enters the pipeline.

None of these mutate any existing state field on their own; the pipeline
records them alongside the S-phase state and uses ReflectiveReturn to
decide re-entry (see :mod:`.pipeline`). Kept as small dataclasses so trace,
persistence, and tests all agree on shape.

The public form is a plain ``dict`` (``to_public``) — the runtime records it
verbatim in the trace, and the schemas under
``data/socrates/current/contracts/projection_*.schema.json`` describe the
same shape for the LIVE model surface.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------- enums / vocab


class ProjectionStatus(str, Enum):
    """The state of a projection after execution.

    A projection may be locally valid and globally insufficient at the same
    time — ``ACCEPTED_LOCAL`` is the non-degenerate case for P1 when P2
    supersedes it: P1's objects remain addressable, P2 revises the look.
    """
    EXPLORATORY = "exploratory"
    ACCEPTED_LOCAL = "accepted_local"
    PARTIAL = "partial"
    REJECTED = "rejected"


class DiagnosticSignal(str, Enum):
    """Typed signals the diagnostics layer can raise about the LOOK.

    Each signal names a specific way the current projection fails to hold
    up against the material. The vocabulary comes directly from B03/B07/B08
    (operation/object applicability, reflective retreat, polyontology).
    """
    OPERATION_MISMATCH = "OPERATION_MISMATCH"
    ONTOLOGY_LIMIT = "ONTOLOGY_LIMIT"
    MULTI_ONTOLOGY = "MULTI_ONTOLOGY"
    OBJECT_GENERATOR_LIMIT = "OBJECT_GENERATOR_LIMIT"
    RECOGNITION_FAILURE = "RECOGNITION_FAILURE"
    FORCED_COMPLETENESS = "FORCED_COMPLETENESS"
    SCENE_MISMATCH = "SCENE_MISMATCH"
    APPLICABILITY_FAILURE = "APPLICABILITY_FAILURE"


class RetreatLevel(str, Enum):
    """B07 retreat depth for a reflective return.

    Depths mirror the reflective-exit schema levels — R1..R6 — with R0
    reserved for "no retreat needed". The runtime uses the shallowest depth
    that accounts for the diagnostic, never deeper than evidence warrants.
    """
    R0 = "R0"           # no retreat
    R1 = "R1"           # changed operation
    R2 = "R2"           # changed ontology
    R3 = "R3"           # changed scene / role
    R4 = "R4"           # changed origin / authority
    R5 = "R5"           # constitutional revision (out of scope for the loop)
    R6 = "R6"           # suspend with reason


class ReturnTarget(str, Enum):
    """Which S-phase the reflective return re-enters at.

    Kept explicit so a trace reader can see: retreat R1 returned the runtime
    to S4 (operation), R3 returned it to S1 (scene), R4 to S3 (origin). The
    pipeline enforces that ``return_target`` matches ``retreat_level``.
    """
    S1 = "S1"
    S3 = "S3"
    S4 = "S4"


#: Guard bound on the number of projections in one run (P1 + P2 + P3 max).
#: Named here so tests can pin the invariant.
MAX_PROJECTION_ITERATIONS: int = 3


# ---------------------------------------------------------- projection spec


@dataclass
class SemanticProjectionSpec:
    """Declaration of the current look at a source.

    The identity fields (``projection_id``, ``source_id``, ``operation_id``,
    ``ontology_id``) let a trace reconstruct the whole loop. ``parent_projection_id``
    plus ``revises`` express lineage — P2's spec records which spec it
    supersedes and why.

    ``segmentation_policy`` names the executor / cutter capability that
    physically reads the source (see :mod:`.cutter_registry`); the pipeline
    does not itself decide how the cut is performed.
    """
    projection_id: str
    source_id: str
    scene_ref: str
    operation_id: str
    ontology_id: str
    target_object_family: tuple[str, ...]
    recognition_criteria: tuple[str, ...]
    segmentation_policy: str
    evidence_requirements: tuple[str, ...]
    applicability_assumptions: tuple[str, ...]
    contraindications: tuple[str, ...]
    parent_projection_id: str = ""
    revises: str = ""
    status: ProjectionStatus = ProjectionStatus.EXPLORATORY

    def fingerprint(self) -> str:
        """Content-hash over the fields that define the LOOK.

        Two specs with equal fingerprints are the same projection modulo
        identity — the loop guard rejects re-entry that produces an
        already-attempted fingerprint.
        """
        payload = "\n".join([
            self.operation_id, self.ontology_id, self.segmentation_policy,
            "|".join(self.target_object_family),
            "|".join(self.recognition_criteria),
            "|".join(self.evidence_requirements),
            "|".join(self.applicability_assumptions),
            "|".join(self.contraindications),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["target_object_family"] = list(self.target_object_family)
        d["recognition_criteria"] = list(self.recognition_criteria)
        d["evidence_requirements"] = list(self.evidence_requirements)
        d["applicability_assumptions"] = list(self.applicability_assumptions)
        d["contraindications"] = list(self.contraindications)
        d["fingerprint"] = self.fingerprint()
        return d


def new_projection_id() -> str:
    return f"proj_{secrets.token_hex(6)}"


# ---------------------------------------------------------- projection result


@dataclass
class ProjectedObject:
    """One typed object a projection recognised in the source.

    Provenance fields (D-S26-PROV-004 repair):

        * ``source_id`` + ``source_span`` — the ORIGINAL source and
          character range this object indexes into. Never a prior
          projection's derived text — that invariant is what makes P2
          an independent re-read rather than a revision.
        * ``projection_id`` — the :class:`ProjectionResult` that
          produced this object.
        * ``spec_fingerprint`` — the :class:`SemanticProjectionSpec`
          or :class:`GeneratedCutterSpec` fingerprint that governed
          the projection. A reader that carries only the object can
          still answer "which spec / cutter?" by resolving this.
        * ``operation_id`` — the operation the projection instantiated.
        * ``ontology_id`` — the ontology / world-model assumption the
          spec named.
        * ``space_id`` / ``scene_id`` / ``branch_id`` — populated once
          the runtime tracks these (see G-BD.2). Empty string means
          "not applicable in this run" and remains a valid state — the
          field exists so a future reader never has to resort to
          list-position provenance.

    Older stored objects (from before this schema) resolve their
    provenance transitively via the enclosing :class:`ProjectionResult`.
    See :func:`migrate_object_provenance` for the back-fill helper.
    """
    object_id: str
    object_family: str
    source_id: str
    source_span: tuple[int, int]
    evidence: str
    recognition_basis: str
    confidence: float = 1.0
    projection_id: str = ""
    spec_fingerprint: str = ""
    operation_id: str = ""
    ontology_id: str = ""
    space_id: str = ""
    scene_id: str = ""
    branch_id: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_span"] = list(self.source_span)
        return d


@dataclass
class Residue:
    """Material the projection did NOT classify as a target object.

    Residue is first-class — it is what forces reflection. Provenance
    fields mirror :class:`ProjectedObject` (D-S26-PROV-004 repair) so
    a reader that carries only a residue entry can still identify the
    projection, spec, operation, ontology and (when known)
    space/scene/branch that produced it.
    """
    residue_id: str
    source_id: str
    source_span: tuple[int, int]
    evidence: str
    apparent_family: str
    reason: str
    projection_id: str = ""
    spec_fingerprint: str = ""
    operation_id: str = ""
    ontology_id: str = ""
    space_id: str = ""
    scene_id: str = ""
    branch_id: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_span"] = list(self.source_span)
        return d


@dataclass
class ProjectionResult:
    """What one projection produced against the source.

    ``coverage`` is the fraction of scored source units the projection
    classified into a target family; the runtime uses it, together with the
    residue and typed failures, to decide whether reflection is warranted.

    ``status`` is what the projection ITSELF closed as. The pipeline may
    later reclassify P1 as ACCEPTED_LOCAL after P2 covers the residue —
    that reclassification is a lineage update, not a rewrite of this
    result.

    D-S26-PROV-003 explicit lineage relations:

        * ``parent_projection_id`` — the projection this one continues
          from (empty for P1).
        * ``revises_projection_id`` — the projection this one revises
          after a reflective retreat (empty when this is not a
          reflection-triggered projection).
        * ``triggered_by_diagnostic_id`` /
          ``triggered_by_diagnostic_fingerprint`` — the diagnostic
          that motivated the reflection producing THIS projection
          (empty when this is not reflection-triggered).
        * ``reflective_return_id`` — the :class:`ReflectiveReturn` that
          the reflective epilogue emitted (empty when not applicable).
        * ``spec_id`` — the spec's identity (for both
          :class:`SemanticProjectionSpec` and
          :class:`~capability_resolution.GeneratedCutterSpec`).
        * ``capability_resolution_id`` — the resolver decision that
          selected the branch used to produce this projection.

    A trace/replay reader must be able to reconstruct the causal
    graph P1 → diagnostics → ReflectiveReturn → P2 without list
    position, by walking these typed relations.
    """
    projection_id: str
    spec_fingerprint: str
    source_id: str
    objects: list[ProjectedObject] = field(default_factory=list)
    residue: list[Residue] = field(default_factory=list)
    coverage: float = 0.0
    unclassified_spans: list[tuple[int, int]] = field(default_factory=list)
    recognition_failures: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    internal_conflicts: list[str] = field(default_factory=list)
    status: ProjectionStatus = ProjectionStatus.EXPLORATORY
    #: Explicit typed lineage (D-S26-PROV-003 repair). All optional /
    #: empty-string defaults; the runtime backfills them when it has
    #: the referenced record. Never derived from list position.
    parent_projection_id: str = ""
    revises_projection_id: str = ""
    triggered_by_diagnostic_id: str = ""
    triggered_by_diagnostic_fingerprint: str = ""
    reflective_return_id: str = ""
    spec_id: str = ""
    capability_resolution_id: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "spec_fingerprint": self.spec_fingerprint,
            "source_id": self.source_id,
            "objects": [o.to_public() for o in self.objects],
            "residue": [r.to_public() for r in self.residue],
            "coverage": self.coverage,
            "unclassified_spans": [list(s) for s in self.unclassified_spans],
            "recognition_failures": list(self.recognition_failures),
            "counterexamples": list(self.counterexamples),
            "internal_conflicts": list(self.internal_conflicts),
            "status": self.status.value,
            "parent_projection_id": self.parent_projection_id,
            "revises_projection_id": self.revises_projection_id,
            "triggered_by_diagnostic_id": self.triggered_by_diagnostic_id,
            "triggered_by_diagnostic_fingerprint":
                self.triggered_by_diagnostic_fingerprint,
            "reflective_return_id": self.reflective_return_id,
            "spec_id": self.spec_id,
            "capability_resolution_id": self.capability_resolution_id,
        }

    def stamp_object_provenance(self, *,
                                operation_id: str = "",
                                ontology_id: str = "",
                                space_id: str = "",
                                scene_id: str = "",
                                branch_id: str = "") -> None:
        """Backfill provenance on every object/residue produced by this
        projection (D-S26-PROV-004 repair). Called by the runtime once
        it has the projection_id + spec fingerprint + operation +
        ontology; safe to call idempotently — existing values (from a
        pre-hardening projection loaded from an older trace) are
        preserved.
        """
        for o in self.objects:
            o.projection_id = o.projection_id or self.projection_id
            o.spec_fingerprint = o.spec_fingerprint or self.spec_fingerprint
            o.operation_id = o.operation_id or operation_id
            o.ontology_id = o.ontology_id or ontology_id
            o.space_id = o.space_id or space_id
            o.scene_id = o.scene_id or scene_id
            o.branch_id = o.branch_id or branch_id
        for r in self.residue:
            r.projection_id = r.projection_id or self.projection_id
            r.spec_fingerprint = r.spec_fingerprint or self.spec_fingerprint
            r.operation_id = r.operation_id or operation_id
            r.ontology_id = r.ontology_id or ontology_id
            r.space_id = r.space_id or space_id
            r.scene_id = r.scene_id or scene_id
            r.branch_id = r.branch_id or branch_id


# ---------------------------------------------------------- diagnostics


@dataclass
class ProjectionDiagnostics:
    """Typed judgement about the LOOK itself.

    ``signals`` are the machine-typed reasons the current projection needs
    reflection; ``reason`` is a short human-readable phrase that the trace
    surfaces. ``suggested_operation`` and ``suggested_ontology`` are hints
    the diagnostics layer may propose — S7 is free to accept or replace
    them when constructing the ReflectiveReturn.
    """
    projection_id: str
    signals: tuple[DiagnosticSignal, ...]
    reason: str
    residue_ratio: float
    recognition_failure_count: int
    suggested_operation: str = ""
    suggested_ontology: str = ""
    suggested_target_family: tuple[str, ...] = ()

    @property
    def mismatch(self) -> bool:
        """Does the diagnostic call for reflective retreat?

        Any of the retreat-worthy signals is enough; the pipeline uses this
        as the switch between "continue forward" and "invoke reflective S7".
        """
        retreat_worthy = {
            DiagnosticSignal.OPERATION_MISMATCH,
            DiagnosticSignal.ONTOLOGY_LIMIT,
            DiagnosticSignal.MULTI_ONTOLOGY,
            DiagnosticSignal.APPLICABILITY_FAILURE,
            DiagnosticSignal.SCENE_MISMATCH,
        }
        return any(s in retreat_worthy for s in self.signals)

    def fingerprint(self) -> str:
        payload = "|".join(sorted(s.value for s in self.signals))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    def to_public(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "signals": [s.value for s in self.signals],
            "reason": self.reason,
            "residue_ratio": self.residue_ratio,
            "recognition_failure_count": self.recognition_failure_count,
            "suggested_operation": self.suggested_operation,
            "suggested_ontology": self.suggested_ontology,
            "suggested_target_family": list(self.suggested_target_family),
            "mismatch": self.mismatch,
            "fingerprint": self.fingerprint(),
        }


# ---------------------------------------------------------- reflective return


@dataclass
class ReflectiveReturn:
    """Executable form of B07 reflective retreat.

    Semantically distinct from three neighbours the runtime keeps
    non-overlapping:

        * ``Terminal.RETURN_OPERATION`` — return to the HUMAN. Terminal for
          the whole run. Never emitted by this record.
        * ``ProviderStatus.RETRIES_EXHAUSTED`` — a TECHNICAL retry ended
          without an OK response. The governing hypothesis did not change.
        * ``ReflectiveReturn`` — the governing hypothesis IS changing. The
          run continues internally against the ORIGINAL source with a new
          spec.

    ``what_changes`` is the machine-readable delta the pipeline applies on
    re-entry (which state fields are replaced). ``what_remains_valid``
    documents what P1 preserved — those objects stay addressable.
    """
    reflective_id: str
    from_projection_id: str
    retreat_level: RetreatLevel
    return_target: ReturnTarget
    reason: str
    failed_assumption: str
    what_remains_valid: tuple[str, ...]
    what_changes: tuple[str, ...]
    revised_operation_kind: str = ""
    revised_ontology_id: str = ""
    revised_scene_telos: str = ""
    diagnostic_fingerprint: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["retreat_level"] = self.retreat_level.value
        d["return_target"] = self.return_target.value
        d["what_remains_valid"] = list(self.what_remains_valid)
        d["what_changes"] = list(self.what_changes)
        return d


def new_reflective_id() -> str:
    return f"refl_{secrets.token_hex(6)}"


# ---------------------------------------------------------- lineage record


@dataclass
class ProjectionLineage:
    """Bookkeeping about the whole projection stack in one run.

    Records the ordered list of ProjectionResults, their status transitions,
    and the ReflectiveReturns that link them. A reader should be able to
    reconstruct: which projections happened, in what order, and why each
    one exists.
    """
    entries: list[ProjectionResult] = field(default_factory=list)
    revisions: list[ReflectiveReturn] = field(default_factory=list)
    diagnostics_history: list[ProjectionDiagnostics] = field(default_factory=list)

    def add_projection(self, result: ProjectionResult) -> None:
        self.entries.append(result)

    def add_diagnostics(self, diag: ProjectionDiagnostics) -> None:
        self.diagnostics_history.append(diag)

    def add_reflective_return(self, refl: ReflectiveReturn) -> None:
        self.revisions.append(refl)

    def mark_status(self, projection_id: str, status: ProjectionStatus) -> None:
        for r in self.entries:
            if r.projection_id == projection_id:
                r.status = status
                return

    def iteration(self) -> int:
        return len(self.entries)

    def previous_fingerprints(self) -> tuple[str, ...]:
        return tuple(r.spec_fingerprint for r in self.entries)

    def previous_diagnostic_fingerprints(self) -> tuple[str, ...]:
        return tuple(d.fingerprint() for d in self.diagnostics_history)

    def to_public(self) -> dict[str, Any]:
        return {
            "iteration": self.iteration(),
            "entries": [e.to_public() for e in self.entries],
            "revisions": [r.to_public() for r in self.revisions],
            "diagnostics_history": [d.to_public()
                                    for d in self.diagnostics_history],
        }


__all__ = [
    "DiagnosticSignal",
    "MAX_PROJECTION_ITERATIONS",
    "ProjectedObject",
    "ProjectionDiagnostics",
    "ProjectionLineage",
    "ProjectionResult",
    "ProjectionStatus",
    "ReflectiveReturn",
    "Residue",
    "RetreatLevel",
    "ReturnTarget",
    "SemanticProjectionSpec",
    "new_projection_id",
    "new_reflective_id",
]

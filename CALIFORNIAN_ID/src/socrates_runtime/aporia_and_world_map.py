"""Phase 3C — aporia as apparatus diagnostic + learning world map
(SOC-APORIA-001).

Accepted hypothesis: an aporia MAY indicate that the current
sign/concept/operation apparatus does not adequately hold the
material/phenomenal field. This does NOT mean every hard question is
an ontology failure. Aporia is a typed hypothesis/diagnostic that
MAY cause apparatus review.

Causal path:

    aporia evidence
      → ApparatusMismatchHypothesis (typed)
      → ApparatusReview of current operation / ontology / projection
        / recognition policy
      → if warranted, revised apparatus / new projection
      → rerun against preserved source/material
      → compare lineage/results
      → WorldMapUpdate proposal (durable) under ordinary state-write
        authority (B05 + D-S26-TRIG-001 lifecycle)

Space is capable of accumulating VERSIONED knowledge during work:
recurring aporias, limits/cracks of a world model, distinctions that
resolved or sharpened them, unresolved residue, superseded map
versions. This is epistemic learning of Spaces/world maps, NOT only
self-modification of Socrates.

Invariants:

* An ordinary uncertainty is NOT an aporia. Aporia has explicit
  criteria (structurally grounded, resistant to normal disambiguation,
  connects to a specific apparatus limitation candidate).
* An apparatus review MAY reject the mismatch hypothesis. Not every
  aporia leads to apparatus revision.
* A world-map update goes through B05 / D-S26-TRIG-001 state-write
  authority. The runtime cannot self-authorise a durable change.
* Prior world-map versions remain addressable
  (:class:`WorldMapRegistry`).
* Peskov / projection lineage invariants remain green — apparatus
  revision here is the same mechanism the CapabilityResolver already
  uses via OP-10.
"""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


# ---------------------------------------------------------- aporia


class AporiaGrade(str, Enum):
    """How strongly the aporia points at apparatus mismatch vs
    ordinary uncertainty.
    """
    ORDINARY_UNCERTAINTY = "ORDINARY_UNCERTAINTY"
    OPEN_QUESTION = "OPEN_QUESTION"
    APORIA = "APORIA"


@dataclass(frozen=True)
class AporiaObservation:
    """A typed observation that a question / material resists ordinary
    disambiguation via the current apparatus.

    ``grade`` is set by the caller based on structural criteria — the
    module does NOT auto-classify from text.
    """
    observation_id: str
    grade: AporiaGrade
    subject_ref: str                     # what the aporia is about
    resistance_evidence: tuple[str, ...] # attempted disambiguations that failed
    apparatus_limitation_candidate: str = ""
    surface_source: str = ""             # short prose for trace

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["grade"] = self.grade.value
        d["resistance_evidence"] = list(self.resistance_evidence)
        return d


# ---------------------------------------------------------- apparatus mismatch


class ApparatusKind(str, Enum):
    OPERATION = "OPERATION"
    ONTOLOGY = "ONTOLOGY"
    PROJECTION = "PROJECTION"
    RECOGNITION_POLICY = "RECOGNITION_POLICY"
    SIGN_CONCEPT_SET = "SIGN_CONCEPT_SET"


@dataclass(frozen=True)
class ApparatusMismatchHypothesis:
    """A typed hypothesis that some apparatus component may be at
    fault. Emitted ONLY from an APORIA-grade observation (verified
    by :func:`open_apparatus_mismatch`); ORDINARY_UNCERTAINTY /
    OPEN_QUESTION do not qualify.
    """
    hypothesis_id: str
    aporia_id: str
    apparatus_kind: ApparatusKind
    apparatus_ref: str
    proposed_alternative: str = ""
    supporting_evidence: tuple[str, ...] = ()

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["apparatus_kind"] = self.apparatus_kind.value
        d["supporting_evidence"] = list(self.supporting_evidence)
        return d


def open_apparatus_mismatch(aporia: AporiaObservation,
                            *, apparatus_kind: ApparatusKind,
                            apparatus_ref: str,
                            proposed_alternative: str = "",
                            supporting_evidence: tuple[str, ...] = (),
                            ) -> ApparatusMismatchHypothesis:
    """Structural gate: ordinary uncertainty CANNOT open an apparatus
    mismatch hypothesis. Only APORIA-grade observations qualify.

    Raises :class:`ValueError` on ORDINARY_UNCERTAINTY / OPEN_QUESTION.
    """
    if aporia.grade != AporiaGrade.APORIA:
        raise ValueError(
            f"apparatus mismatch requires APORIA grade; got "
            f"{aporia.grade.value} — ordinary uncertainty and open "
            f"questions do not condemn the apparatus")
    return ApparatusMismatchHypothesis(
        hypothesis_id=_new_id("amh"),
        aporia_id=aporia.observation_id,
        apparatus_kind=apparatus_kind,
        apparatus_ref=apparatus_ref,
        proposed_alternative=proposed_alternative,
        supporting_evidence=tuple(supporting_evidence))


# ---------------------------------------------------------- apparatus review


class ReviewOutcome(str, Enum):
    HYPOTHESIS_REJECTED = "HYPOTHESIS_REJECTED"
    REVISION_WARRANTED = "REVISION_WARRANTED"
    REVISION_INSUFFICIENT_EVIDENCE = "REVISION_INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class ApparatusReview:
    """The outcome of a review triggered by an
    :class:`ApparatusMismatchHypothesis`. The review MAY reject the
    hypothesis — most aporias do NOT survive review as apparatus
    problems.
    """
    review_id: str
    hypothesis_id: str
    outcome: ReviewOutcome
    reason: str
    surviving_ref: str = ""              # if revision warranted, target

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["outcome"] = self.outcome.value
        return d


# ---------------------------------------------------------- world map


@dataclass(frozen=True)
class WorldMapEntry:
    """One versioned distinction / limit / relation in a Space's map."""
    entry_id: str
    kind: str                            # e.g. "distinction", "limit", "crack"
    subject: str
    content: str
    provenance: str
    status: str = "active"               # active | superseded | withdrawn


@dataclass(frozen=True)
class WorldMapVersion:
    """A frozen snapshot of a Space's accumulated world map.

    Space maps accumulate during work: recurring aporias, limits of
    a world model, distinctions that resolved or sharpened them.
    Each version is addressable; older versions remain queryable so
    an audit can walk the map's history.
    """
    version_id: str
    space_id: str
    version_number: int
    entries: tuple[WorldMapEntry, ...]
    supersedes: str = ""                 # prior version_id

    def to_public(self) -> dict[str, Any]:
        return {"version_id": self.version_id,
                "space_id": self.space_id,
                "version_number": self.version_number,
                "supersedes": self.supersedes,
                "entries": [asdict(e) for e in self.entries]}


@dataclass(frozen=True)
class WorldMapUpdateProposal:
    """A proposal to update a Space's world map. UNPRIVILEGED DATA.

    ``authority`` is a public constant: no world-map update reaches
    the durable :class:`WorldMapRegistry` without going through the
    B05 write-authority gate (via
    :meth:`WorldMapRegistry.admit_update`).
    """
    proposal_id: str
    space_id: str
    base_version_id: str
    to_add: tuple[WorldMapEntry, ...] = ()
    to_supersede: tuple[str, ...] = ()   # entry_ids to mark superseded
    to_withdraw: tuple[str, ...] = ()
    reason: str = ""
    triggered_by_aporia_id: str = ""
    triggered_by_review_id: str = ""
    authority: str = "NO_DURABLE_WRITE"

    def to_public(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "space_id": self.space_id,
            "base_version_id": self.base_version_id,
            "to_add": [asdict(e) for e in self.to_add],
            "to_supersede": list(self.to_supersede),
            "to_withdraw": list(self.to_withdraw),
            "reason": self.reason,
            "triggered_by_aporia_id": self.triggered_by_aporia_id,
            "triggered_by_review_id": self.triggered_by_review_id,
            "authority": self.authority,
        }


class WorldMapWriteAuthorityError(Exception):
    """A proposal tried to write without a B05-style admission."""


class WorldMapRegistry:
    """Version-addressable store of :class:`WorldMapVersion` per Space.

    Updates only through :meth:`admit_update`, which requires an
    explicit :class:`ApparatusReview` with outcome REVISION_WARRANTED
    OR an authorised transition record. Otherwise raises
    :class:`WorldMapWriteAuthorityError`.
    """

    def __init__(self) -> None:
        self._versions_by_space: dict[str, list[WorldMapVersion]] = {}

    def latest(self, space_id: str) -> WorldMapVersion | None:
        vs = self._versions_by_space.get(space_id) or []
        return vs[-1] if vs else None

    def history(self, space_id: str) -> tuple[WorldMapVersion, ...]:
        return tuple(self._versions_by_space.get(space_id) or ())

    def seed(self, initial: WorldMapVersion) -> None:
        """Seed a new Space with an initial version. Used ONCE per
        Space (Space bootstrap); subsequent changes must go through
        :meth:`admit_update`.
        """
        self._versions_by_space.setdefault(initial.space_id, []).append(initial)

    def admit_update(self, proposal: WorldMapUpdateProposal,
                     *, review: ApparatusReview | None = None,
                     authorized_transition_ref: str = "",
                     ) -> WorldMapVersion:
        """Governed write path.

        A proposal is admitted only if EITHER:

        * a companion :class:`ApparatusReview` has outcome
          REVISION_WARRANTED and matches
          ``proposal.triggered_by_review_id``, OR
        * ``authorized_transition_ref`` is a non-empty typed
          reference (e.g. B05 memory proposal id already approved
          by the write gate).

        Otherwise raises :class:`WorldMapWriteAuthorityError`.
        """
        has_review = (review is not None
                       and review.outcome == ReviewOutcome.REVISION_WARRANTED
                       and review.review_id == proposal.triggered_by_review_id)
        has_transition = bool(authorized_transition_ref)
        if not (has_review or has_transition):
            raise WorldMapWriteAuthorityError(
                f"proposal {proposal.proposal_id} not admitted: "
                f"needs a REVISION_WARRANTED review whose id matches "
                f"proposal.triggered_by_review_id, or an "
                f"authorized_transition_ref")

        # Build the new version by mutating a copy of the base.
        base = self.latest(proposal.space_id)
        base_version_number = base.version_number if base else 0
        base_entries = list(base.entries) if base else []
        # Mark superseded
        marked = []
        superseded_set = set(proposal.to_supersede)
        withdrawn_set = set(proposal.to_withdraw)
        for e in base_entries:
            if e.entry_id in superseded_set:
                from dataclasses import replace
                marked.append(replace(e, status="superseded"))
            elif e.entry_id in withdrawn_set:
                from dataclasses import replace
                marked.append(replace(e, status="withdrawn"))
            else:
                marked.append(e)
        marked.extend(proposal.to_add)
        new_version = WorldMapVersion(
            version_id=_new_id("wmv"),
            space_id=proposal.space_id,
            version_number=base_version_number + 1,
            entries=tuple(marked),
            supersedes=(base.version_id if base else ""))
        self._versions_by_space.setdefault(
            proposal.space_id, []).append(new_version)
        return new_version


__all__ = [
    "AporiaGrade", "AporiaObservation",
    "ApparatusKind", "ApparatusMismatchHypothesis",
    "ApparatusReview", "ReviewOutcome",
    "WorldMapEntry", "WorldMapRegistry",
    "WorldMapUpdateProposal", "WorldMapVersion",
    "WorldMapWriteAuthorityError", "open_apparatus_mismatch",
]

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

import hashlib
import secrets
from dataclasses import asdict, dataclass, field, replace
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
                marked.append(replace(e, status="superseded"))
            elif e.entry_id in withdrawn_set:
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


# ---------------------------------------------------------- 3C differential diagnosis


class GapKind(str, Enum):
    """Differential diagnosis. Aporia is NOT automatic apparatus failure."""
    ORDINARY_UNRESOLVED = "ORDINARY_UNRESOLVED"
    EVIDENCE_GAP = "EVIDENCE_GAP"
    OPERATION_GAP = "OPERATION_GAP"
    PROJECTION_GAP = "PROJECTION_GAP"
    ONTOLOGY_GAP = "ONTOLOGY_GAP"
    SPACE_MISMATCH = "SPACE_MISMATCH"
    GENUINE_APORIA = "GENUINE_APORIA"
    APPARATUS_MISMATCH_CANDIDATE = "APPARATUS_MISMATCH_CANDIDATE"


class CandidateChangeKind(str, Enum):
    OPERATION = "OPERATION"
    PROJECTION = "PROJECTION"
    DISTINCTION = "DISTINCTION"
    ONTOLOGY = "ONTOLOGY"
    SPACE_INTERPRETATION = "SPACE_INTERPRETATION"
    COMPOSITION = "COMPOSITION"


class AdoptionAction(str, Enum):
    NO_CANDIDATE = "NO_CANDIDATE"
    REJECT_CANDIDATE = "REJECT_CANDIDATE"
    KEEP_AS_ALTERNATIVE = "KEEP_AS_ALTERNATIVE"
    PROPOSE_WORLD_MAP_UPDATE = "PROPOSE_WORLD_MAP_UPDATE"
    PROPOSE_PROJECTION_UPDATE = "PROPOSE_PROJECTION_UPDATE"
    PROPOSE_OPERATION_UPDATE = "PROPOSE_OPERATION_UPDATE"
    PROPOSE_ONTOLOGY_UPDATE = "PROPOSE_ONTOLOGY_UPDATE"


#: Typed Operation.why_not values that name a missing source, not an
#: apparatus failure. Not a lexical router over user prose.
EVIDENCE_WHY_NOT: frozenset[str] = frozenset({
    "SOURCE_GAP", "missing_source", "source_insufficient", "no_observation",
})

_NOVELTY_DEMAND_NEEDLES: tuple[str, ...] = (
    "create a new ontology", "create new ontology", "new ontology",
    "ontology is broken", "rewrite the ontology", "rewrite its ontology",
    "онтология сломана", "онтологию сломана", "создай новую",
    "перепиши её", "перепиши ее", "перепиши онтолог",
)


def novelty_demand_seen(text: str) -> bool:
    """User/source asserted 'your ontology is broken'. Evidence, not authority."""
    t = (text or "").lower()
    return any(n in t for n in _NOVELTY_DEMAND_NEEDLES)


def _kind_of(res: Any) -> str:
    kind = getattr(res, "kind", None)
    if kind is None and isinstance(res, dict):
        kind = res.get("kind")
    if kind is None:
        return ""
    return str(getattr(kind, "value", kind) or "")


def _signal_values(diag: Any) -> tuple[str, ...]:
    if diag is None:
        return ()
    signals = getattr(diag, "signals", ()) or ()
    out = []
    for s in signals:
        out.append(str(getattr(s, "value", s) or ""))
    return tuple(out)


def _has_organ_gap(state: Any) -> bool:
    return any(_kind_of(r) == "ORGAN_GAP"
               for r in (getattr(state, "capability_resolutions", None) or []))


def _has_conflicts(state: Any) -> bool:
    reg = getattr(state, "conflict_registry", None)
    if reg is None:
        return False
    if hasattr(reg, "all"):
        try:
            return bool(reg.all())
        except TypeError:
            pass
    held = getattr(reg, "held", None) or getattr(reg, "conflicts", None)
    if held is not None:
        return bool(held)
    return False


@dataclass(frozen=True)
class ApparatusMismatchCandidate:
    """Handoff §13.1 — candidate only, zero adoption authority."""
    candidate_id: str
    aporia_evidence_refs: tuple[str, ...]
    current_apparatus_refs: tuple[str, ...]
    failure_pattern: str
    candidate_diagnosis: str
    confidence: str
    alternatives_considered: tuple[str, ...]
    why_ordinary_uncertainty_insufficient: str
    hypothesis_id: str = ""
    apparatus_kind: str = ""

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["aporia_evidence_refs"] = list(self.aporia_evidence_refs)
        d["current_apparatus_refs"] = list(self.current_apparatus_refs)
        d["alternatives_considered"] = list(self.alternatives_considered)
        return d


@dataclass(frozen=True)
class CandidateApparatusChange:
    change_id: str
    kind: CandidateChangeKind
    predecessor_apparatus_ref: str
    proposed_ref: str
    rationale: str
    reveals: tuple[str, ...] = ()
    erases: tuple[str, ...] = ()
    authority: str = "NO_ADOPTION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["reveals"] = list(self.reveals)
        d["erases"] = list(self.erases)
        return d


@dataclass(frozen=True)
class MaterialView:
    """Typed view of preserved material under one apparatus."""
    material_ref: str
    distinguished: tuple[str, ...]
    lost: tuple[str, ...]
    epistemic_status: str
    aporia_present: bool
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        return {
            "material_ref": self.material_ref,
            "distinguished": list(self.distinguished),
            "lost": list(self.lost),
            "epistemic_status": self.epistemic_status,
            "aporia_present": self.aporia_present,
            "authority": self.authority,
        }


@dataclass(frozen=True)
class ApparatusReplayResult:
    replay_id: str
    material_ref: str
    old_view: MaterialView
    candidate_view: MaterialView
    newly_distinct: tuple[str, ...]
    destroyed: tuple[str, ...]
    false_distinctions: tuple[str, ...]
    epistemic_status_changed: bool
    hypothesis_became_fact: bool
    productive_aporia_destroyed: bool
    authority_intact: bool
    forward_action_improved: bool
    adoption: AdoptionAction
    reason: str

    def to_public(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "material_ref": self.material_ref,
            "old_view": self.old_view.to_public(),
            "candidate_view": self.candidate_view.to_public(),
            "newly_distinct": list(self.newly_distinct),
            "destroyed": list(self.destroyed),
            "false_distinctions": list(self.false_distinctions),
            "epistemic_status_changed": self.epistemic_status_changed,
            "hypothesis_became_fact": self.hypothesis_became_fact,
            "productive_aporia_destroyed": self.productive_aporia_destroyed,
            "authority_intact": self.authority_intact,
            "forward_action_improved": self.forward_action_improved,
            "adoption": self.adoption.value,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ApparatusLineageRecord:
    record_id: str
    predecessor_version_id: str
    initiating_aporia_id: str
    diagnostic_classification: str
    candidate_change_id: str
    replay_id: str
    comparison_adoption: str
    adoption_status: str
    authority: str = "NO_DURABLE_WRITE"

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApparatusDiagnosticResult:
    """Causal 3C product. Ephemeral; not durable memory."""
    result_id: str
    classification: GapKind
    aporia: AporiaObservation | None = None
    mismatch_candidate: ApparatusMismatchCandidate | None = None
    review: ApparatusReview | None = None
    candidate_change: CandidateApparatusChange | None = None
    replay: ApparatusReplayResult | None = None
    world_map_proposal: WorldMapUpdateProposal | None = None
    lineage: ApparatusLineageRecord | None = None
    novelty_demand_seen: bool = False
    instruction_shaped_seen: bool = False
    durable_write_attempted: bool = False
    grounds: tuple[str, ...] = ()
    stop_reason: str = "DIAGNOSIS_COMPLETE"

    def to_public(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "classification": self.classification.value,
            "aporia": self.aporia.to_public() if self.aporia else None,
            "mismatch_candidate": (self.mismatch_candidate.to_public()
                                   if self.mismatch_candidate else None),
            "review": self.review.to_public() if self.review else None,
            "candidate_change": (self.candidate_change.to_public()
                                 if self.candidate_change else None),
            "replay": self.replay.to_public() if self.replay else None,
            "world_map_proposal": (self.world_map_proposal.to_public()
                                   if self.world_map_proposal else None),
            "lineage": self.lineage.to_public() if self.lineage else None,
            "novelty_demand_seen": self.novelty_demand_seen,
            "instruction_shaped_seen": self.instruction_shaped_seen,
            "durable_write_attempted": self.durable_write_attempted,
            "grounds": list(self.grounds),
            "stop_reason": self.stop_reason,
        }


def material_ref_for(text: str) -> str:
    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return f"mat_{digest[:16]}"


def extract_material_view(state: Any, outcome: Any, input_text: str) -> MaterialView:
    lineage = getattr(state, "projection_lineage", None)
    distinguished: list[str] = []
    lost: list[str] = []
    if lineage is not None:
        entries = getattr(lineage, "entries", None) or []
        if entries:
            last = entries[-1]
            for obj in getattr(last, "objects", None) or []:
                fam = getattr(obj, "object_family", "") or ""
                if fam:
                    distinguished.append(str(fam))
            for res in getattr(last, "residue", None) or []:
                fam = getattr(res, "apparent_family", "") or ""
                ev = getattr(res, "evidence", "") or ""
                lost.append(str(fam or ev[:80]))
    terminal = getattr(getattr(outcome, "terminal", None), "value",
                       getattr(outcome, "terminal", "")) or ""
    aporia_present = str(terminal) == "PRESERVE_APORIA"
    epistemic = "APORIA" if aporia_present else (
        "UNRESOLVED" if lost else "LOCAL_HOLD")
    return MaterialView(
        material_ref=material_ref_for(input_text),
        distinguished=tuple(distinguished),
        lost=tuple(lost),
        epistemic_status=epistemic,
        aporia_present=aporia_present,
    )


def apply_candidate_to_view(old: MaterialView,
                            change: CandidateApparatusChange) -> MaterialView:
    distinguished = set(old.distinguished)
    lost = set(old.lost)
    for item in change.reveals:
        if item in lost or item not in distinguished:
            distinguished.add(item)
            lost.discard(item)
    for item in change.erases:
        if item in distinguished:
            distinguished.discard(item)
            lost.add(item)
    aporia = old.aporia_present and not (
        change.kind == CandidateChangeKind.ONTOLOGY and change.erases)
    epistemic = old.epistemic_status
    if change.kind == CandidateChangeKind.ONTOLOGY and change.erases:
        epistemic = "HYPOTHESIS"
        aporia = False
    return MaterialView(
        material_ref=old.material_ref,
        distinguished=tuple(sorted(distinguished)),
        lost=tuple(sorted(lost)),
        epistemic_status=epistemic,
        aporia_present=aporia,
        authority=old.authority,
    )


def compare_replay(old: MaterialView,
                   change: CandidateApparatusChange,
                   *, genuine_aporia: bool = False) -> ApparatusReplayResult:
    if change.authority not in {"NO_ADOPTION_AUTHORITY", ""}:
        # Candidate cannot mint authority by existing.
        change = replace(change, authority="NO_ADOPTION_AUTHORITY")
    cand = apply_candidate_to_view(old, change)
    newly = tuple(sorted(set(cand.distinguished) - set(old.distinguished)))
    destroyed = tuple(sorted(set(old.distinguished) - set(cand.distinguished)))
    false_d = tuple(x for x in newly if x not in set(old.lost) | set(change.reveals))
    hyp_fact = (old.epistemic_status in {"UNRESOLVED", "APORIA", "HYPOTHESIS"}
                and cand.epistemic_status in {"FACT", "KNOWN"})
    aporia_killed = bool(genuine_aporia and old.aporia_present
                         and not cand.aporia_present)
    authority_intact = cand.authority == old.authority
    improved = bool(newly) and not destroyed and not false_d and not hyp_fact
    if hyp_fact or aporia_killed or not authority_intact:
        adoption = AdoptionAction.REJECT_CANDIDATE
        reason = "comparison_rejected:fact_or_aporia_or_authority"
    elif destroyed and newly:
        adoption = AdoptionAction.KEEP_AS_ALTERNATIVE
        reason = "improves_one_axis_destroys_another"
    elif destroyed and not newly:
        adoption = AdoptionAction.REJECT_CANDIDATE
        reason = "candidate_only_destroys"
    elif improved:
        if change.kind == CandidateChangeKind.PROJECTION:
            adoption = AdoptionAction.PROPOSE_PROJECTION_UPDATE
        elif change.kind == CandidateChangeKind.OPERATION:
            adoption = AdoptionAction.PROPOSE_OPERATION_UPDATE
        elif change.kind == CandidateChangeKind.ONTOLOGY:
            adoption = AdoptionAction.PROPOSE_ONTOLOGY_UPDATE
        else:
            adoption = AdoptionAction.PROPOSE_WORLD_MAP_UPDATE
        reason = "same_material_reveals_new_distinction"
    elif newly and destroyed:
        adoption = AdoptionAction.KEEP_AS_ALTERNATIVE
        reason = "mixed_delta"
    else:
        adoption = AdoptionAction.REJECT_CANDIDATE
        reason = "no_material_gain"
    return ApparatusReplayResult(
        replay_id=_new_id("rpl"),
        material_ref=old.material_ref,
        old_view=old,
        candidate_view=cand,
        newly_distinct=newly,
        destroyed=destroyed,
        false_distinctions=false_d,
        epistemic_status_changed=(old.epistemic_status != cand.epistemic_status),
        hypothesis_became_fact=hyp_fact,
        productive_aporia_destroyed=aporia_killed,
        authority_intact=authority_intact,
        forward_action_improved=improved,
        adoption=adoption,
        reason=reason,
    )


def _repeat_key(state: Any, apparatus_ref: str) -> str:
    space = getattr(state, "space_id", "") or "space_default_workspace"
    return f"{space}:{apparatus_ref or 'unknown'}"


def run_apparatus_diagnostic(
        state: Any,
        outcome: Any,
        *,
        input_text: str = "",
        registry: WorldMapRegistry | None = None,
        repeat_index: dict[str, int] | None = None,
        ) -> ApparatusDiagnosticResult:
    """Typed differential diagnosis. Never auto-creates an ontology.

    Invoked from SocratesRuntime after the 3B private-work seam.
    Does not increment additional_private_pass_count.
    Never admits a durable world-map write.
    """
    from .private_work_plane import private_payload_is_instruction_shaped
    from .state import Terminal

    grounds: list[str] = []
    text = input_text or getattr(state, "input_text", "") or ""
    novelty = novelty_demand_seen(text)
    instr = private_payload_is_instruction_shaped(text)
    if novelty:
        grounds.append("novelty_demand_seen:user_or_source_assertion_not_authority")
    if instr:
        grounds.append("instruction_shaped_input_ignored")

    terminal = getattr(outcome, "terminal", None)
    term_val = getattr(terminal, "value", terminal)
    op = getattr(state, "operation", None)
    applicable = bool(getattr(op, "applicable", True))
    open_world = bool(getattr(op, "open_world_gap", False))
    why_not = str(getattr(op, "why_not", "") or "")
    op_kind = str(getattr(op, "kind", "") or "")
    diag = getattr(state, "pending_diagnostic", None)
    lineage = getattr(state, "projection_lineage", None)
    signals = _signal_values(diag)
    hist = list(getattr(lineage, "diagnostics_history", None) or [])
    if not signals and hist:
        signals = _signal_values(hist[-1])
    mismatch = bool(diag is not None and getattr(diag, "mismatch", False))
    if not mismatch and hist:
        last = hist[-1]
        mismatch = bool(getattr(last, "mismatch", False))
    organ_gap = _has_organ_gap(state)
    conflicts = _has_conflicts(state)
    type_gaps = bool(getattr(state, "trigger_type_gaps", None))
    apparatus_ref = op_kind or "apparatus:current"
    if hist:
        suggested = str(getattr(hist[-1], "suggested_operation", "") or "")
        if suggested:
            apparatus_ref = suggested
    repeats = 0
    if repeat_index is not None and (mismatch or organ_gap or open_world):
        key = _repeat_key(state, apparatus_ref)
        if mismatch:
            repeat_index[key] = int(repeat_index.get(key) or 0) + 1
        repeats = int(repeat_index.get(key) or 0)
    if hist:
        fps = [d.fingerprint() for d in hist if hasattr(d, "fingerprint")]
        if len(fps) >= 2 and len(set(fps)) == 1:
            repeats = max(repeats, len(fps))
            grounds.append("repeated_diagnostic_fingerprint")

    classification = GapKind.ORDINARY_UNRESOLVED
    grade = AporiaGrade.ORDINARY_UNCERTAINTY

    if organ_gap or type_gaps or (not applicable and why_not in EVIDENCE_WHY_NOT):
        classification = GapKind.EVIDENCE_GAP
        grounds.append("typed_source_or_organ_gap")
    elif (not applicable) and (not open_world) and term_val == Terminal.RETURN_OPERATION:
        classification = GapKind.OPERATION_GAP
        grounds.append("operation.applicable=false")
    elif (not applicable) and (not open_world):
        classification = GapKind.OPERATION_GAP
        grounds.append("operation.applicable=false")
    elif "SCENE_MISMATCH" in signals:
        classification = GapKind.SPACE_MISMATCH
        grounds.append("diagnostic.SCENE_MISMATCH")
    elif repeats >= 2 and mismatch:
        classification = GapKind.APPARATUS_MISMATCH_CANDIDATE
        grounds.append(f"repeated_projection_failure:{repeats}")
        grade = AporiaGrade.APORIA
    elif "ONTOLOGY_LIMIT" in signals or "MULTI_ONTOLOGY" in signals:
        classification = GapKind.ONTOLOGY_GAP
        grounds.append("single_ontology_or_multi_ontology_signal")
        grade = AporiaGrade.OPEN_QUESTION
    elif mismatch or "OPERATION_MISMATCH" in signals or "APPLICABILITY_FAILURE" in signals:
        classification = GapKind.PROJECTION_GAP
        grounds.append("single_projection_mismatch")
        grade = AporiaGrade.OPEN_QUESTION
    elif term_val == Terminal.PRESERVE_APORIA or open_world or conflicts:
        classification = GapKind.GENUINE_APORIA
        grounds.append("preserve_aporia_or_open_world_or_held_conflict")
        grade = AporiaGrade.APORIA
    else:
        grounds.append("no_typed_apparatus_failure")

    # User novelty demand never upgrades classification to mismatch.
    if classification == GapKind.APPARATUS_MISMATCH_CANDIDATE and novelty:
        classification = GapKind.ONTOLOGY_GAP
        grade = AporiaGrade.OPEN_QUESTION
        grounds.append("novelty_demand_cannot_mint_mismatch")

    aporia = AporiaObservation(
        observation_id=_new_id("apo"),
        grade=grade,
        subject_ref=getattr(state, "source_id", "") or material_ref_for(text),
        resistance_evidence=tuple(grounds),
        apparatus_limitation_candidate=(
            apparatus_ref if grade == AporiaGrade.APORIA else ""),
        surface_source="typed_state",
    )

    result = ApparatusDiagnosticResult(
        result_id=_new_id("adr"),
        classification=classification,
        aporia=aporia,
        novelty_demand_seen=novelty,
        instruction_shaped_seen=instr,
        grounds=tuple(grounds),
    )

    if classification != GapKind.APPARATUS_MISMATCH_CANDIDATE:
        result.review = ApparatusReview(
            review_id=_new_id("arv"),
            hypothesis_id="",
            outcome=(ReviewOutcome.HYPOTHESIS_REJECTED
                     if classification != GapKind.ONTOLOGY_GAP
                     else ReviewOutcome.REVISION_INSUFFICIENT_EVIDENCE),
            reason=f"diagnosis={classification.value}",
        )
        result.stop_reason = "NO_APPARATUS_MISMATCH"
        return result

    hyp = open_apparatus_mismatch(
        aporia,
        apparatus_kind=ApparatusKind.PROJECTION,
        apparatus_ref=apparatus_ref,
        proposed_alternative="op:DIFFERENTIATED_ACCOUNT",
        supporting_evidence=tuple(grounds),
    )
    cand = ApparatusMismatchCandidate(
        candidate_id=_new_id("amc"),
        aporia_evidence_refs=(aporia.observation_id,),
        current_apparatus_refs=(apparatus_ref,),
        failure_pattern="repeated_projection_loss",
        candidate_diagnosis=classification.value,
        confidence="MEDIUM",
        alternatives_considered=("keep_current", "DIFFERENTIATED_ACCOUNT"),
        why_ordinary_uncertainty_insufficient=(
            "same apparatus lost material on repeated encounters"),
        hypothesis_id=hyp.hypothesis_id,
        apparatus_kind=hyp.apparatus_kind.value,
    )
    old_view = extract_material_view(state, outcome, text)
    reveals = tuple(x for x in old_view.lost if x)
    change = CandidateApparatusChange(
        change_id=_new_id("cac"),
        kind=CandidateChangeKind.DISTINCTION,
        predecessor_apparatus_ref=apparatus_ref,
        proposed_ref="op:DIFFERENTIATED_ACCOUNT",
        rationale="replay same material under differentiated account",
        reveals=reveals[:4],
        erases=(),
    )
    genuine = term_val == Terminal.PRESERVE_APORIA or open_world or conflicts
    replay = compare_replay(old_view, change, genuine_aporia=genuine)
    review_outcome = (
        ReviewOutcome.REVISION_WARRANTED
        if replay.adoption in {
            AdoptionAction.PROPOSE_WORLD_MAP_UPDATE,
            AdoptionAction.PROPOSE_PROJECTION_UPDATE,
            AdoptionAction.PROPOSE_OPERATION_UPDATE,
            AdoptionAction.PROPOSE_ONTOLOGY_UPDATE,
        } else ReviewOutcome.HYPOTHESIS_REJECTED
        if replay.adoption == AdoptionAction.REJECT_CANDIDATE
        else ReviewOutcome.REVISION_INSUFFICIENT_EVIDENCE)
    review = ApparatusReview(
        review_id=_new_id("arv"),
        hypothesis_id=hyp.hypothesis_id,
        outcome=review_outcome,
        reason=replay.reason,
        surviving_ref=change.proposed_ref if review_outcome == ReviewOutcome.REVISION_WARRANTED else "",
    )
    proposal = None
    space_id = getattr(state, "space_id", "") or "space_default_workspace"
    if (registry is not None
            and replay.adoption == AdoptionAction.PROPOSE_WORLD_MAP_UPDATE):
        base = registry.latest(space_id)
        proposal = WorldMapUpdateProposal(
            proposal_id=_new_id("wmp"),
            space_id=space_id,
            base_version_id=base.version_id if base else "",
            to_add=(WorldMapEntry(
                entry_id=_new_id("wme"),
                kind="distinction",
                subject=change.proposed_ref,
                content=";".join(replay.newly_distinct) or change.rationale,
                provenance=f"replay:{replay.replay_id}",
            ),),
            reason=replay.reason,
            triggered_by_aporia_id=aporia.observation_id,
            triggered_by_review_id=review.review_id,
        )
    pred = ""
    if registry is not None:
        latest = registry.latest(space_id)
        pred = latest.version_id if latest else ""
    lineage_rec = ApparatusLineageRecord(
        record_id=_new_id("aln"),
        predecessor_version_id=pred,
        initiating_aporia_id=aporia.observation_id,
        diagnostic_classification=classification.value,
        candidate_change_id=change.change_id,
        replay_id=replay.replay_id,
        comparison_adoption=replay.adoption.value,
        adoption_status="PROPOSAL_ONLY",
    )
    result.mismatch_candidate = cand
    result.review = review
    result.candidate_change = change
    result.replay = replay
    result.world_map_proposal = proposal
    result.lineage = lineage_rec
    result.stop_reason = replay.adoption.value
    return result


__all__ = [
    "AporiaGrade", "AporiaObservation",
    "ApparatusKind", "ApparatusMismatchHypothesis",
    "ApparatusReview", "ReviewOutcome",
    "WorldMapEntry", "WorldMapRegistry",
    "WorldMapUpdateProposal", "WorldMapVersion",
    "WorldMapWriteAuthorityError", "open_apparatus_mismatch",
    "GapKind", "CandidateChangeKind", "AdoptionAction",
    "ApparatusMismatchCandidate", "CandidateApparatusChange",
    "MaterialView", "ApparatusReplayResult", "ApparatusLineageRecord",
    "ApparatusDiagnosticResult",
    "run_apparatus_diagnostic", "compare_replay", "extract_material_view",
    "apply_candidate_to_view", "novelty_demand_seen", "material_ref_for",
    "EVIDENCE_WHY_NOT",
]

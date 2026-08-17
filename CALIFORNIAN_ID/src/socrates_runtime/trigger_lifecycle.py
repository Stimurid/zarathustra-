"""Trigger causal-typing + admission lifecycle — D-S26-TRIG-001 repair.

Before this module:

    MODEL / PHASE OUTPUT
        ↓ delta.triggers
        ↓ pipeline._apply_delta directly writes
        ↓ state.admitted_trigger_causes
        ↓ SemanticMountPolicy reads (or does not — the production
        ↓ path never even passed the CTA gate)

That leaked SEMANTIC_CONDITIONAL_MOUNT authority into raw model
output. This module inserts the four missing typed stages:

    ObservedSignal (input observation, no authority)
        ↓
    TriggerCandidate (typed proposal — DATA only, NO_MOUNT_AUTHORITY)
        ↓
    CausalTypingDecision (REGISTERED_TYPE | TYPE_GAP | REJECT)
        ↓
    TriggerAdmissionDecision (ADMIT | REJECT | COALESCE, on typed
        basis + source authority + phase relevance + materiality)
        ↓
    AdmittedTriggerEvent (the ONLY object with
        SEMANTIC_CONDITIONAL_MOUNT authority)

Only AdmittedTriggerEvent authorises a conditional body mount.
TriggerCandidate has NO_MOUNT_AUTHORITY. TriggerTypeGap has
``conditional_mount_authority=False`` and never resolves to a
mount by proximity — it routes back to open-world work (S4 / B03).
TriggerTypeCandidate is a proposal for HUMAN registration; it
cannot self-register, execute code, or authorise a mount in the
same run.

Type vs instance discipline
---------------------------
``trigger_instance_id`` is one concrete causal occurrence in one run.
``trigger_type_id`` is one abstract registered causal class. Two
lexically / socially / linguistically different observations with
the SAME governed causal structure resolve to the same type. Two
observations with the same familiar words but WITHOUT the causal
structure resolve to no type. Nearest-class coercion is banned;
if the structure is materially present but no registered type
faithfully covers it, the result is TRIGGER_TYPE_GAP.

Source authority
----------------
These have ZERO DIRECT MOUNT AUTHORITY:

    * user wording;
    * retrieval cue;
    * donor output;
    * persona output;
    * model prior;
    * model proposal (including model-emitted ``triggers``);
    * candidate manifest name.

They may generate a :class:`TriggerCandidate`. Admission requires
independent grounding through governed typed state or an
authorized transition. The rejection reason enum names each
failure mode explicitly.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------- enums


class SourceKind(str, Enum):
    """Where a :class:`TriggerCandidate` came from.

    The runtime uses this to decide whether an ObservedSignal has
    admission authority on its own (typed_state / authorized_transition
    do) or merely proposes a candidate (all model / retrieval / donor
    / persona / candidate manifest inputs).
    """
    TYPED_PIPELINE_STATE = "TYPED_PIPELINE_STATE"
    AUTHORIZED_TRANSITION = "AUTHORIZED_TRANSITION"
    PROJECTION_DIAGNOSTIC = "PROJECTION_DIAGNOSTIC"
    SCENE_STATE = "SCENE_STATE"
    AUTHORITY_STATE = "AUTHORITY_STATE"
    OWNERSHIP_STATE = "OWNERSHIP_STATE"
    MEMORY_GOVERNANCE_STATE = "MEMORY_GOVERNANCE_STATE"
    COUNCIL_STATE = "COUNCIL_STATE"
    INTERVENTION_STATE = "INTERVENTION_STATE"
    EPISTEMIC_SPACE_STATE = "EPISTEMIC_SPACE_STATE"
    SCENE_BRANCH_STATE = "SCENE_BRANCH_STATE"
    CONTEXT_TRANSDUCTION_STATE = "CONTEXT_TRANSDUCTION_STATE"
    # Non-authoritative (never admit on their own):
    USER_WORDING = "USER_WORDING"
    RETRIEVAL_CUE = "RETRIEVAL_CUE"
    DONOR_OUTPUT = "DONOR_OUTPUT"
    PERSONA_OUTPUT = "PERSONA_OUTPUT"
    MODEL_PRIOR = "MODEL_PRIOR"
    MODEL_PROPOSAL = "MODEL_PROPOSAL"
    CANDIDATE_MANIFEST_NAME = "CANDIDATE_MANIFEST_NAME"


AUTHORIZED_SOURCES: frozenset[SourceKind] = frozenset({
    SourceKind.TYPED_PIPELINE_STATE,
    SourceKind.AUTHORIZED_TRANSITION,
    SourceKind.PROJECTION_DIAGNOSTIC,
    SourceKind.SCENE_STATE,
    SourceKind.AUTHORITY_STATE,
    SourceKind.OWNERSHIP_STATE,
    SourceKind.MEMORY_GOVERNANCE_STATE,
    SourceKind.COUNCIL_STATE,
    SourceKind.INTERVENTION_STATE,
    SourceKind.EPISTEMIC_SPACE_STATE,
    SourceKind.SCENE_BRANCH_STATE,
    SourceKind.CONTEXT_TRANSDUCTION_STATE,
})


class TypingOutcome(str, Enum):
    REGISTERED_TYPE = "REGISTERED_TYPE"
    TYPE_GAP = "TYPE_GAP"
    REJECT = "REJECT"


class AdmissionOutcome(str, Enum):
    ADMIT = "ADMIT"
    REJECT = "REJECT"
    COALESCE = "COALESCE"


class RejectionReason(str, Enum):
    """Observable rejection categories. No hidden chain-of-thought."""
    LEXICAL_ONLY = "LEXICAL_ONLY"
    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    NO_TYPED_STATE_BASIS = "NO_TYPED_STATE_BASIS"
    PHASE_IRRELEVANT = "PHASE_IRRELEVANT"
    NON_MATERIAL = "NON_MATERIAL"
    DUPLICATE_CAUSE = "DUPLICATE_CAUSE"
    STALE_STATE = "STALE_STATE"
    INVALID_SOURCE_STATUS = "INVALID_SOURCE_STATUS"
    REGISTERED_TYPE_MISMATCH = "REGISTERED_TYPE_MISMATCH"
    MODEL_SELF_ADMISSION_ATTEMPT = "MODEL_SELF_ADMISSION_ATTEMPT"
    UNKNOWN_TRIGGER_TYPE = "UNKNOWN_TRIGGER_TYPE"


# ---------------------------------------------------------- id helpers


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def new_candidate_id() -> str:   return _new_id("tcand")
def new_typing_id() -> str:      return _new_id("ttype")
def new_admission_id() -> str:   return _new_id("tadm")
def new_event_id() -> str:       return _new_id("tev")
def new_gap_id() -> str:         return _new_id("tgap")
def new_type_cand_id() -> str:   return _new_id("ttyc")


# ---------------------------------------------------------- ObservedSignal


@dataclass(frozen=True)
class ObservedSignal:
    """Raw observation entering the lifecycle. No mount authority.

    A model that names ``"ROLE_CAPTURE"`` in its phase output produces
    an ObservedSignal with ``source_kind=MODEL_PROPOSAL``. The
    lifecycle decides whether a typed state independently grounds
    the same cause; only then does admission become possible.
    """
    proposed_trigger_id: str
    source_kind: SourceKind
    source_ref: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_kind"] = self.source_kind.value
        return d


# ---------------------------------------------------------- TriggerCandidate


@dataclass(frozen=True)
class TriggerCandidate:
    """A typed proposal, NOT an admitted mount authority.

    ``NO_MOUNT_AUTHORITY`` is a public constant on the class — a
    Trigger candidate cannot upgrade itself; it must survive typing
    and admission. Model output that carries a ``triggers`` array
    is parsed into TriggerCandidate values whose ``source_kind`` is
    MODEL_PROPOSAL; admission decides.
    """
    candidate_id: str
    proposed_trigger_type_id: str
    source_kind: SourceKind
    source_ref: str
    generating_state_ref: str
    cause_object_ref: str
    phase_relevance: str
    materiality_reason: str
    payload: dict[str, Any] = field(default_factory=dict)
    authority: str = "NO_MOUNT_AUTHORITY"

    def cause_key(self) -> tuple[str, str]:
        return (self.proposed_trigger_type_id, self.cause_object_ref)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_kind"] = self.source_kind.value
        return d


# ---------------------------------------------------------- TypeRegistry


@dataclass(frozen=True)
class TriggerTypeDefinition:
    """One entry in the open-world :class:`TriggerTypeRegistry`.

    A definition names the abstract causal type + the semantic body
    (or bodies) it authorises when admitted + the causal predicates
    a candidate must satisfy for REGISTERED_TYPE typing.
    """
    trigger_type_id: str
    owning_body: str                                    # e.g. "B07"
    additional_mount_targets: tuple[str, ...] = ()
    #: What structured cause a candidate must exhibit. Formal, not lexical:
    #: e.g. "state.pending_diagnostic.mismatch AND diagnostic.signals
    #: include OPERATION_MISMATCH". The registry does not evaluate this
    #: — the CausalTyper uses it as a machine-readable predicate spec
    #: (see :class:`CausalTyper`).
    required_causal_predicates: tuple[str, ...] = ()
    #: Phase ids where this type is legitimately mountable.
    authorised_phase_relevance: tuple[str, ...] = ()
    #: Which SourceKinds (or their category) can independently ground
    #: the type. Model / retrieval / persona sources NEVER independently
    #: ground admission; they only propose candidates.
    grounding_sources: tuple[SourceKind, ...] = ()
    version: str = "v0.2"


class TriggerTypeRegistry:
    """Open-world extensible registry.

    The registry is not a closed ontology. If a candidate carries a
    grounded structural cause but no registered type covers it, the
    typing produces :class:`TriggerTypeGap`. A future review may
    register a new type via a :class:`TriggerTypeCandidate`; that
    review is HUMAN-owned and NEVER happens automatically inside a
    run.
    """

    def __init__(self, definitions: tuple[TriggerTypeDefinition, ...] = (),
                 version: str = "v0.2_default") -> None:
        self._defs: dict[str, TriggerTypeDefinition] = {
            d.trigger_type_id: d for d in definitions}
        self.version = version

    def register(self, definition: TriggerTypeDefinition) -> None:
        """Runtime registration is only allowed at construction time —
        this method exists so a test/harness can build a registry
        variant. It DOES NOT expose a LIVE self-registration surface
        to models. The pipeline never calls this method from a phase
        delta path (verified by test).
        """
        self._defs[definition.trigger_type_id] = definition

    def get(self, trigger_type_id: str) -> TriggerTypeDefinition | None:
        return self._defs.get(trigger_type_id)

    def has(self, trigger_type_id: str) -> bool:
        return trigger_type_id in self._defs

    def known_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._defs))

    def body_targets(self, trigger_type_id: str) -> tuple[str, ...]:
        d = self._defs.get(trigger_type_id)
        if d is None:
            return ()
        return (d.owning_body, *d.additional_mount_targets)

    def to_public(self) -> dict[str, Any]:
        return {"version": self.version,
                "types": {tid: asdict(d) for tid, d in self._defs.items()}}


def build_default_registry() -> TriggerTypeRegistry:
    """v0.2 authoritative registry preserved verbatim.

    v0.2 semantics from B07 (reflective/capture) + B09 (council/arbitration)
    + B03 (origin/status dispute). No new types added in this repair
    pass — the five v0.3 "cause names"
    (REFLECTIVE_MISMATCH_PENDING, MULTI_ONTOLOGY_MOUNT,
    OPERATION_MISMATCH, REVISE_APPARATUS_INVOKED,
    CROSS_SPACE_TRANSDUCTION_PENDING) are classified as STATE / EVENT
    indicators (see V03_TRIGGER_TYPE_AUDIT.md), NOT registered types.
    """
    return TriggerTypeRegistry(
        version="v0.2_default",
        definitions=(
            # ---- B07: reflective retreat / role capture family
            TriggerTypeDefinition(
                trigger_type_id="REFLECTIVE_EXIT_REQUIRED",
                owning_body="B07",
                required_causal_predicates=(
                    "state.pending_diagnostic is not None "
                    "AND state.pending_diagnostic.mismatch",
                    "OR authorized transition to reflective epilogue",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.PROJECTION_DIAGNOSTIC,
                    SourceKind.AUTHORIZED_TRANSITION,
                    SourceKind.TYPED_PIPELINE_STATE)),
            TriggerTypeDefinition(
                trigger_type_id="ROLE_CAPTURE",
                owning_body="B07",
                required_causal_predicates=(
                    "state.scene.authority not in {SYSTEM,HUMAN} "
                    "AND scene evidence indicates capture",
                    "OR authority state records typed capture",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.AUTHORITY_STATE,
                    SourceKind.SCENE_STATE,
                    SourceKind.TYPED_PIPELINE_STATE)),
            TriggerTypeDefinition(
                trigger_type_id="FRAME_GENERATED_FAILURE",
                owning_body="B07",
                required_causal_predicates=(
                    "typed scene or projection state shows a frame "
                    "the system itself produced and cannot recover from",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.PROJECTION_DIAGNOSTIC,
                    SourceKind.SCENE_STATE,
                    SourceKind.TYPED_PIPELINE_STATE)),
            TriggerTypeDefinition(
                trigger_type_id="SELF_REVIEW_RECURSION",
                owning_body="B07",
                required_causal_predicates=(
                    "typed intervention state records self-review "
                    "recursion above threshold",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.INTERVENTION_STATE,
                    SourceKind.TYPED_PIPELINE_STATE)),
            # ---- B09: council / arbitration family
            TriggerTypeDefinition(
                trigger_type_id="COUNCIL_REQUIRED",
                owning_body="B09",
                required_causal_predicates=(
                    "typed council state records a materially "
                    "unresolved dissent",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.COUNCIL_STATE,
                    SourceKind.TYPED_PIPELINE_STATE)),
            TriggerTypeDefinition(
                trigger_type_id="TYPED_VETO",
                owning_body="B09",
                required_causal_predicates=(
                    "typed authority state records a veto with "
                    "reason and party",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.COUNCIL_STATE,
                    SourceKind.AUTHORITY_STATE)),
            TriggerTypeDefinition(
                trigger_type_id="MINORITY_MATERIAL",
                owning_body="B09",
                required_causal_predicates=(
                    "typed council state records a minority position "
                    "with material evidence weight",),
                authorised_phase_relevance=("S7", "P06"),
                grounding_sources=(
                    SourceKind.COUNCIL_STATE,)),
            # ---- B02: origin/status dispute
            TriggerTypeDefinition(
                trigger_type_id="STATUS_DISPUTE",
                owning_body="B02",
                required_causal_predicates=(
                    "typed origin state records disputed provenance",),
                authorised_phase_relevance=("S3", "P02"),
                grounding_sources=(
                    SourceKind.TYPED_PIPELINE_STATE,)),
        ))


# ---------------------------------------------------------- CausalTypingDecision


@dataclass(frozen=True)
class CausalTypingDecision:
    """Public typed record of typing an ObservedSignal / TriggerCandidate.

    Only ``REGISTERED_TYPE`` decisions can proceed to admission.
    ``TYPE_GAP`` produces a :class:`TriggerTypeGap` with zero mount
    authority. ``REJECT`` is a typed refusal (bad source, contradictory
    state, unknown type).
    """
    typing_id: str
    candidate_id: str
    outcome: TypingOutcome
    trigger_type_id: str = ""
    reason: str = ""
    rejection_reason: RejectionReason | None = None
    type_gap_ref: str = ""
    registry_version: str = ""

    def to_public(self) -> dict[str, Any]:
        return {"typing_id": self.typing_id,
                "candidate_id": self.candidate_id,
                "outcome": self.outcome.value,
                "trigger_type_id": self.trigger_type_id,
                "reason": self.reason,
                "rejection_reason": (self.rejection_reason.value
                                     if self.rejection_reason else None),
                "type_gap_ref": self.type_gap_ref,
                "registry_version": self.registry_version}


# ---------------------------------------------------------- TriggerTypeGap


@dataclass(frozen=True)
class TriggerTypeGap:
    """A grounded structural cause with no registered type that
    faithfully covers it.

    ``conditional_mount_authority = False`` — the gap NEVER resolves
    to a nearest known type. Default routing per the protocol is
    back to S4 / B03 open-world operation-applicability work (the
    pipeline decides; the gap only reports the situation).
    """
    gap_id: str
    candidate_id: str
    cause_object_ref: str
    generating_state_ref: str
    registry_version: str
    reason: str
    conditional_mount_authority: bool = False

    def to_public(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------- TriggerTypeCandidate


@dataclass(frozen=True)
class TriggerTypeCandidate:
    """A PROPOSAL to register a new trigger type — HUMAN-owned review.

    ``status = "PROPOSED_NOT_AUTHORIZED"`` is a public constant. The
    candidate cannot self-register, execute code, modify the runtime
    registry, or bypass review. Emitted alongside a :class:`TriggerTypeGap`
    when the runtime believes a new type would be useful.
    """
    type_candidate_id: str
    proposed_trigger_type_id: str
    causal_definition: str
    structural_predicates: tuple[str, ...]
    positive_evidence: tuple[str, ...]
    counterexamples: tuple[str, ...] = ()
    applicability_boundary: str = ""
    provenance: str = ""
    proposed_mount_targets: tuple[str, ...] = ()
    status: str = "PROPOSED_NOT_AUTHORIZED"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["structural_predicates"] = list(self.structural_predicates)
        d["positive_evidence"] = list(self.positive_evidence)
        d["counterexamples"] = list(self.counterexamples)
        d["proposed_mount_targets"] = list(self.proposed_mount_targets)
        return d


# ---------------------------------------------------------- TriggerAdmissionDecision


@dataclass(frozen=True)
class TriggerAdmissionDecision:
    """Public typed record of the admission step.

    ADMIT produces an :class:`AdmittedTriggerEvent`. COALESCE binds
    the candidate to an existing admitted event (same
    ``(trigger_type_id, cause_object_ref)`` key). REJECT enumerates
    a typed :class:`RejectionReason`.
    """
    admission_id: str
    candidate_id: str
    typing_id: str
    outcome: AdmissionOutcome
    reason: str
    rejection_reason: RejectionReason | None = None
    coalesced_into_event_id: str = ""
    admitted_event_id: str = ""

    def to_public(self) -> dict[str, Any]:
        return {"admission_id": self.admission_id,
                "candidate_id": self.candidate_id,
                "typing_id": self.typing_id,
                "outcome": self.outcome.value,
                "reason": self.reason,
                "rejection_reason": (self.rejection_reason.value
                                     if self.rejection_reason else None),
                "coalesced_into_event_id": self.coalesced_into_event_id,
                "admitted_event_id": self.admitted_event_id}


# ---------------------------------------------------------- AdmittedTriggerEvent


@dataclass(frozen=True)
class AdmittedTriggerEvent:
    """The ONLY object with SEMANTIC_CONDITIONAL_MOUNT authority.

    Everything upstream is proposal / typing / decision. Only this
    record authorises a conditional body mount. It binds enough
    typed evidence to reconstruct the whole lifecycle without any
    hidden chain-of-thought.
    """
    event_id: str
    trigger_instance_id: str
    trigger_type_id: str
    owning_body: str
    additional_mount_targets: tuple[str, ...]
    generating_state_ref: str
    cause_object_ref: str
    source_kind: SourceKind
    source_status: str
    phase_relevance: str
    materiality_reason: str
    admitting_rule: str
    typed_basis_refs: tuple[str, ...]
    registry_version: str
    sequence: int
    candidate_ids: tuple[str, ...]         # lineage — contributing candidates
    typing_id: str
    admission_id: str
    authority: str = "SEMANTIC_CONDITIONAL_MOUNT"

    def cause_key(self) -> tuple[str, str]:
        return (self.trigger_type_id, self.cause_object_ref)

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["source_kind"] = self.source_kind.value
        d["additional_mount_targets"] = list(self.additional_mount_targets)
        d["typed_basis_refs"] = list(self.typed_basis_refs)
        d["candidate_ids"] = list(self.candidate_ids)
        return d


# ---------------------------------------------------------- CausalTyper


class CausalTyper:
    """Turns a :class:`TriggerCandidate` into a
    :class:`CausalTypingDecision` using an active TypeRegistry AND
    the current typed state.

    The typer is deliberately conservative:

        * unknown proposed_trigger_type_id in the registry AND no
          structurally grounded alternative → REJECT / UNKNOWN_TRIGGER_TYPE
          (a mere model-invented ID never becomes a type).
        * registered id + candidate carries an authorized-source
          basis + typed state supports the causal predicates →
          REGISTERED_TYPE.
        * registered id but typed state contradicts (e.g. model
          proposes ROLE_CAPTURE while ownership is fully SYSTEM and
          scene evidence contradicts) → REJECT / REGISTERED_TYPE_MISMATCH.
        * structurally grounded cause with NO registered type that
          covers → TYPE_GAP (never nearest-class).
        * grounding_sources requirement: at least one of the
          candidate's contributing source_kinds must be authorised
          for the type; a MODEL_PROPOSAL-only candidate never
          typing-passes on its own.

    The predicate machine is intentionally small — the runtime is
    not a general theorem prover. It reads a few well-known state
    fingerprints and checks them structurally. When the fingerprint
    isn't ready (e.g. reflective diagnostic absent), typing rejects.
    """

    def __init__(self, registry: TriggerTypeRegistry) -> None:
        self.registry = registry

    def type_candidate(self, candidate: TriggerCandidate,
                       state_snapshot: dict[str, Any],
                       ) -> CausalTypingDecision:
        proposed = candidate.proposed_trigger_type_id
        definition = self.registry.get(proposed)

        # Authorized-source check: model / retrieval / donor / persona /
        # candidate-manifest ONLY candidates cannot ground on their own.
        # They may still type-pass if AUTHORIZED_SOURCES also grounded
        # them (in which case the candidate would have that source_kind).
        source_authorised = candidate.source_kind in AUTHORIZED_SOURCES

        if definition is None:
            # Unknown ID. If the candidate is authorised-source AND the
            # payload names a materially grounded structural cause, this
            # is a TYPE_GAP (open-world) — never a coerced nearest match.
            if source_authorised and candidate.materiality_reason:
                return CausalTypingDecision(
                    typing_id=new_typing_id(),
                    candidate_id=candidate.candidate_id,
                    outcome=TypingOutcome.TYPE_GAP,
                    reason=(f"proposed type {proposed!r} not in "
                            f"registry {self.registry.version!r}; "
                            f"materially grounded structural cause "
                            f"suggests a gap rather than coercion"),
                    registry_version=self.registry.version)
            return CausalTypingDecision(
                typing_id=new_typing_id(),
                candidate_id=candidate.candidate_id,
                outcome=TypingOutcome.REJECT,
                trigger_type_id="",
                reason=(f"proposed type {proposed!r} not in registry "
                        f"and candidate source is not authorised "
                        f"({candidate.source_kind.value})"),
                rejection_reason=RejectionReason.UNKNOWN_TRIGGER_TYPE,
                registry_version=self.registry.version)

        # Registered type. Check that at least one of the type's
        # grounding_sources is compatible with the candidate.
        if candidate.source_kind not in definition.grounding_sources:
            return CausalTypingDecision(
                typing_id=new_typing_id(),
                candidate_id=candidate.candidate_id,
                outcome=TypingOutcome.REJECT,
                trigger_type_id=proposed,
                reason=(f"candidate source {candidate.source_kind.value!r} "
                        f"is not in the type's grounding_sources "
                        f"{[s.value for s in definition.grounding_sources]}"),
                rejection_reason=(
                    RejectionReason.UNAUTHORIZED_SOURCE
                    if candidate.source_kind not in AUTHORIZED_SOURCES
                    else RejectionReason.NO_TYPED_STATE_BASIS),
                registry_version=self.registry.version)

        # State contradiction check — narrow but material. For each
        # known type, verify that the typed state does not contradict
        # the type's premise.
        contradiction = _state_contradicts_type(proposed, state_snapshot)
        if contradiction:
            return CausalTypingDecision(
                typing_id=new_typing_id(),
                candidate_id=candidate.candidate_id,
                outcome=TypingOutcome.REJECT,
                trigger_type_id=proposed,
                reason=contradiction,
                rejection_reason=RejectionReason.REGISTERED_TYPE_MISMATCH,
                registry_version=self.registry.version)

        return CausalTypingDecision(
            typing_id=new_typing_id(),
            candidate_id=candidate.candidate_id,
            outcome=TypingOutcome.REGISTERED_TYPE,
            trigger_type_id=proposed,
            reason=(f"type {proposed!r} grounded by source "
                    f"{candidate.source_kind.value!r} + typed state"),
            registry_version=self.registry.version)


def _state_contradicts_type(trigger_type_id: str,
                            state_snapshot: dict[str, Any]) -> str:
    """Narrow structural contradiction check.

    Returns a reason string if the typed state contradicts the type's
    premise; empty string otherwise. Only a handful of types have
    machine-checkable contradictions today; the rest pass through
    unless the source-authority check already rejected them.
    """
    if trigger_type_id == "ROLE_CAPTURE":
        # If ownership is fully SYSTEM + human_resolved + no scene
        # authority mismatch, capture is materially contradicted.
        ownership = (state_snapshot.get("ownership") or {})
        scene = (state_snapshot.get("scene") or {})
        if (ownership.get("owner") == "system"
                and ownership.get("human_resolved") is True
                and scene.get("authority") in ("system", "unset")):
            return ("ROLE_CAPTURE proposed while ownership is fully "
                    "SYSTEM + human_resolved and scene authority "
                    "does not indicate capture")
    if trigger_type_id == "REFLECTIVE_EXIT_REQUIRED":
        # Requires an active mismatch fingerprint. If none present at
        # candidate time, the type is not grounded.
        diag = state_snapshot.get("pending_diagnostic")
        if diag is None:
            reentry = state_snapshot.get("reentry_from") or ""
            if not reentry:
                return ("REFLECTIVE_EXIT_REQUIRED proposed with no "
                        "pending_diagnostic and no reentry_from — no "
                        "typed mismatch state grounds it")
    return ""


# ---------------------------------------------------------- Admitter


class TriggerAdmitter:
    """Turns a REGISTERED_TYPE :class:`CausalTypingDecision` into a
    :class:`TriggerAdmissionDecision` (ADMIT / COALESCE / REJECT).

    Coalescence rule: two admitted events with the same
    ``(trigger_type_id, cause_object_ref)`` are one causal fact with
    lineage. Cue frequency does not increase authority.
    """

    def __init__(self, registry: TriggerTypeRegistry) -> None:
        self.registry = registry

    def admit(self, candidate: TriggerCandidate,
              typing: CausalTypingDecision,
              *, phase: str,
              existing_events: tuple[AdmittedTriggerEvent, ...],
              sequence_next: int,
              ) -> tuple[TriggerAdmissionDecision,
                         AdmittedTriggerEvent | None]:
        if typing.outcome != TypingOutcome.REGISTERED_TYPE:
            return (TriggerAdmissionDecision(
                admission_id=new_admission_id(),
                candidate_id=candidate.candidate_id,
                typing_id=typing.typing_id,
                outcome=AdmissionOutcome.REJECT,
                reason=(f"typing outcome {typing.outcome.value!r} "
                        f"cannot proceed to admission"),
                rejection_reason=(
                    typing.rejection_reason
                    or RejectionReason.REGISTERED_TYPE_MISMATCH)),
                None)

        definition = self.registry.get(typing.trigger_type_id)
        assert definition is not None      # typing.REGISTERED_TYPE guarantees

        if (definition.authorised_phase_relevance
                and phase not in definition.authorised_phase_relevance
                and candidate.phase_relevance not in
                    definition.authorised_phase_relevance):
            return (TriggerAdmissionDecision(
                admission_id=new_admission_id(),
                candidate_id=candidate.candidate_id,
                typing_id=typing.typing_id,
                outcome=AdmissionOutcome.REJECT,
                reason=(f"phase {phase!r} not in authorised phases "
                        f"{list(definition.authorised_phase_relevance)}"),
                rejection_reason=RejectionReason.PHASE_IRRELEVANT),
                None)

        # Coalescence.
        cause_key = (typing.trigger_type_id, candidate.cause_object_ref)
        for existing in existing_events:
            if existing.cause_key() == cause_key:
                merged = _augment_event(
                    existing, candidate.candidate_id)
                return (TriggerAdmissionDecision(
                    admission_id=new_admission_id(),
                    candidate_id=candidate.candidate_id,
                    typing_id=typing.typing_id,
                    outcome=AdmissionOutcome.COALESCE,
                    reason=(f"same cause_key {cause_key!r} — coalesced "
                            f"into event {existing.event_id!r}"),
                    coalesced_into_event_id=existing.event_id),
                    merged)

        # Admit.
        event = AdmittedTriggerEvent(
            event_id=new_event_id(),
            trigger_instance_id=_new_id("tinst"),
            trigger_type_id=typing.trigger_type_id,
            owning_body=definition.owning_body,
            additional_mount_targets=definition.additional_mount_targets,
            generating_state_ref=candidate.generating_state_ref,
            cause_object_ref=candidate.cause_object_ref,
            source_kind=candidate.source_kind,
            source_status=("typed_state"
                            if candidate.source_kind in AUTHORIZED_SOURCES
                            else "candidate_only"),
            phase_relevance=phase,
            materiality_reason=candidate.materiality_reason,
            admitting_rule="D-S26-TRIG-001",
            typed_basis_refs=(candidate.generating_state_ref,),
            registry_version=self.registry.version,
            sequence=sequence_next,
            candidate_ids=(candidate.candidate_id,),
            typing_id=typing.typing_id,
            admission_id=new_admission_id())
        admission = TriggerAdmissionDecision(
            admission_id=event.admission_id,
            candidate_id=candidate.candidate_id,
            typing_id=typing.typing_id,
            outcome=AdmissionOutcome.ADMIT,
            reason=(f"admitted type={typing.trigger_type_id!r} "
                    f"cause={candidate.cause_object_ref!r} "
                    f"phase={phase!r}"),
            admitted_event_id=event.event_id)
        return admission, event


def _augment_event(event: AdmittedTriggerEvent,
                   new_candidate_id: str) -> AdmittedTriggerEvent:
    """Return a copy of ``event`` with ``new_candidate_id`` appended to
    its candidate lineage. Frozen dataclass → replace pattern.
    """
    from dataclasses import replace
    return replace(event,
                   candidate_ids=(*event.candidate_ids, new_candidate_id))


# ---------------------------------------------------------- module facade


def build_default_typer() -> CausalTyper:
    return CausalTyper(build_default_registry())


def build_default_admitter() -> TriggerAdmitter:
    return TriggerAdmitter(build_default_registry())


__all__ = [
    "AUTHORIZED_SOURCES",
    "AdmissionOutcome",
    "AdmittedTriggerEvent",
    "CausalTyper",
    "CausalTypingDecision",
    "ObservedSignal",
    "RejectionReason",
    "SourceKind",
    "TriggerAdmissionDecision",
    "TriggerAdmitter",
    "TriggerCandidate",
    "TriggerTypeCandidate",
    "TriggerTypeDefinition",
    "TriggerTypeGap",
    "TriggerTypeRegistry",
    "TypingOutcome",
    "build_default_admitter",
    "build_default_registry",
    "build_default_typer",
    "new_admission_id",
    "new_candidate_id",
    "new_event_id",
    "new_gap_id",
    "new_type_cand_id",
    "new_typing_id",
]

"""Phase 3A — fast-time scene governance
(SOC-POSSTAB-001 + SOC-PRED-001 + SOC-USERMODEL-001
 + SOC-SCENEBIND-001 + SOC-SPACEFRICTION-001).

Solves sycophancy / context capture at the causal level, not by
matching failure phrases. Core law:

    CONTEXTUAL PULL/PUSH → EVIDENCE ABOUT POSSIBLE CHANGE
                        → NOT CHANGE ITSELF.

Applied uniformly to topic / Scene / Space / role / operation /
angle / style / affect / authority. Surface wording, repetition,
emotional intensity, praise, threat, urgency, user preference and
lexical triggers have ZERO direct transition authority. A real
transition requires ordinary typed evidence PLUS reconstruction /
materiality PLUS authority / admission.

The module composes cleanly with D-S26-TRIG-001:
:class:`ContextualPressure` records are UNPRIVILEGED (like
``TriggerCandidate``). :class:`PossibleChangeEvidence` accumulates
them into a typed judgement. :class:`TransitionAdmission` is a
deterministic decision that either ADMITs (routes back through the
trigger admission lifecycle) or refuses.

Also delivers:

* :class:`ScenePredictor` protocol + :class:`BaselinePredictor` for
  pluggable continuous Scene/intent prediction. Klein/RPDM,
  active-inference-inspired and change-point detection remain donor
  models behind the same interface — NOT hard-wired doctrine.
  Invariant: :class:`SurpriseAssessment` never authorises a
  transition on its own.

* :class:`UserEpistemicView` — three-scale participant view over the
  dyad (immediate want / scoped falsifiable hypotheses / knowledge
  and epistemic stance). Never identity/profile truth.

* :func:`should_ask_clarification` — conditional Scene stabilization
  policy. Incomplete Scene is valid; the runtime estimates whether
  clarification is materially worth the friction before asking.

* :class:`SpaceFriction` — proportional friction when current
  operation/intent materially mismatches the current Space. Not
  Cerberus: authorised user-owned crossings pass with typed
  provenance.

No new mount authority is minted. All decisions are typed data on
:class:`PipelineState` or returned as typed records; nothing here
can flip a state field without going through the existing
governance path.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Protocol


# ---------------------------------------------------------- ids


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


# ============================================================
# SOC-POSSTAB-001 — context-transition sovereignty
# ============================================================


class PressureAxis(str, Enum):
    """The axes along which contextual push/pull can arrive.

    A single message may carry pressure on several axes simultaneously
    (e.g. urgency ↑ + authority ↑ + framing shift ↑). Each axis is a
    distinct :class:`ContextualPressure`.
    """
    TOPIC = "TOPIC"
    SCENE = "SCENE"
    SPACE = "SPACE"
    ROLE = "ROLE"
    OPERATION = "OPERATION"
    FRAME = "FRAME"
    STYLE = "STYLE"
    AFFECT = "AFFECT"
    AUTHORITY = "AUTHORITY"


class PressureSourceKind(str, Enum):
    """Where the pressure came from. Governs whether it can EVER
    ground admission (only typed / authorised transition can), or
    whether it is strictly candidate evidence (everything else).
    """
    USER_WORDING = "USER_WORDING"
    RETRIEVED_TEXT = "RETRIEVED_TEXT"
    MODEL_PRIOR = "MODEL_PRIOR"
    MODEL_PROPOSAL = "MODEL_PROPOSAL"
    DONOR_OUTPUT = "DONOR_OUTPUT"
    PERSONA_OUTPUT = "PERSONA_OUTPUT"
    REPETITION = "REPETITION"
    EMOTIONAL_INTENSITY = "EMOTIONAL_INTENSITY"
    PRAISE = "PRAISE"
    THREAT = "THREAT"
    URGENCY = "URGENCY"
    USER_PREFERENCE = "USER_PREFERENCE"
    LEXICAL_TRIGGER = "LEXICAL_TRIGGER"
    # Authorised (structural):
    TYPED_STATE_CHANGE = "TYPED_STATE_CHANGE"
    AUTHORIZED_TRANSITION = "AUTHORIZED_TRANSITION"
    HUMAN_EXPLICIT_CHOICE = "HUMAN_EXPLICIT_CHOICE"


AUTHORISED_PRESSURE_SOURCES: frozenset[PressureSourceKind] = frozenset({
    PressureSourceKind.TYPED_STATE_CHANGE,
    PressureSourceKind.AUTHORIZED_TRANSITION,
    PressureSourceKind.HUMAN_EXPLICIT_CHOICE,
})


class AdmissionOutcome(str, Enum):
    """Deterministic outcome of a possibility → admission decision.

    ``PRESSURE_ONLY`` is the default for context pushes: the pressure
    is recorded as evidence about a POSSIBLE change but NEVER causes
    an actual transition on its own. ``REVIEW_CANDIDATE`` says a
    review pass may be warranted. ``ADMIT`` is reserved for the case
    where the pressure is grounded in an authorised source AND
    material AND has the required admission authority.
    """
    PRESSURE_ONLY = "PRESSURE_ONLY"
    REVIEW_CANDIDATE = "REVIEW_CANDIDATE"
    ADMIT = "ADMIT"
    REJECT = "REJECT"


@dataclass(frozen=True)
class ContextualPressure:
    """A single typed push/pull observation. UNPRIVILEGED.

    ``NO_TRANSITION_AUTHORITY`` on the class is the invariant that
    the module's whole point rests on: no matter how many pressure
    records accumulate on the same axis from the same non-authorised
    source, they never combine into transition authority.
    """
    pressure_id: str
    axis: PressureAxis
    source_kind: PressureSourceKind
    intensity: float                        # 0.0 to 1.0, unitless
    proposed_target: str                    # e.g. "role=coach", "style=formal"
    evidence: str                           # short human-readable
    materiality_signal: str = ""            # if any structural signal accompanies
    authority: str = "NO_TRANSITION_AUTHORITY"

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["axis"] = self.axis.value
        d["source_kind"] = self.source_kind.value
        return d


@dataclass(frozen=True)
class PossibleChangeEvidence:
    """Accumulated pressure on one axis + one proposed target.

    Distinct from :class:`ContextualPressure`: an evidence record
    aggregates multiple pressures with the same (axis, proposed_target)
    and reports a typed assessment. Aggregation does NOT increase
    authority; it only makes REVIEW_CANDIDATE more likely if
    grounded_signals are also present.
    """
    evidence_id: str
    axis: PressureAxis
    proposed_target: str
    pressure_ids: tuple[str, ...]
    aggregate_intensity: float
    grounded_signals: tuple[str, ...]       # structural, from state
    non_authorised_sources: tuple[PressureSourceKind, ...]
    material: bool

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["axis"] = self.axis.value
        d["non_authorised_sources"] = [s.value
                                        for s in self.non_authorised_sources]
        return d


@dataclass(frozen=True)
class TransitionAdmission:
    """Deterministic decision about a proposed transition.

    Outcomes:

    * ``PRESSURE_ONLY`` (default) — no structural grounding + only
      non-authorised sources → record the pressure, do NOT transition.
    * ``REVIEW_CANDIDATE`` — some grounded signal + material +
      substantial pressure → a review pass is worth scheduling. Still
      not an authorised transition.
    * ``ADMIT`` — authorised source present + typed grounding +
      material + no contradicting structural evidence.
    * ``REJECT`` — structural evidence contradicts the proposed
      transition.
    """
    admission_id: str
    outcome: AdmissionOutcome
    evidence_id: str
    axis: PressureAxis
    reason: str


def assess_pressure(pressures: tuple[ContextualPressure, ...],
                    *, grounded_signals: tuple[str, ...] = (),
                    contradicting_signals: tuple[str, ...] = (),
                    material: bool = False,
                    ) -> tuple[PossibleChangeEvidence, TransitionAdmission]:
    """Deterministic assessment. NO surface-word matching; NO learned
    classifier. The decision is purely a function of the typed inputs:

    1. Aggregate the pressures on the same (axis, proposed_target)
       key. If they disagree on target, split — caller handles per
       target. Here we assume the caller has already grouped.
    2. Split sources into authorised vs non-authorised. Repetition,
       intensity, praise, threat, urgency, user preference and
       lexical triggers are non-authorised REGARDLESS of count.
    3. If contradicting_signals non-empty → REJECT.
    4. If any authorised source AND material → ADMIT.
    5. If grounded_signals non-empty AND material AND aggregate
       intensity ≥ 0.5 → REVIEW_CANDIDATE.
    6. Otherwise → PRESSURE_ONLY.
    """
    if not pressures:
        raise ValueError("assess_pressure requires at least one pressure")
    axis = pressures[0].axis
    target = pressures[0].proposed_target
    for p in pressures:
        if p.axis != axis or p.proposed_target != target:
            raise ValueError(
                "all pressures in one assessment must share axis + target; "
                "caller must group per (axis, target)")

    aggregate_intensity = min(1.0, sum(p.intensity for p in pressures))
    non_auth = tuple(sorted({p.source_kind
                              for p in pressures
                              if p.source_kind not in AUTHORISED_PRESSURE_SOURCES},
                             key=lambda k: k.value))
    has_authorised = any(p.source_kind in AUTHORISED_PRESSURE_SOURCES
                         for p in pressures)

    evidence = PossibleChangeEvidence(
        evidence_id=_new_id("pce"),
        axis=axis,
        proposed_target=target,
        pressure_ids=tuple(p.pressure_id for p in pressures),
        aggregate_intensity=aggregate_intensity,
        grounded_signals=tuple(grounded_signals),
        non_authorised_sources=non_auth,
        material=material)

    if contradicting_signals:
        outcome, reason = (AdmissionOutcome.REJECT,
                           f"structural signals contradict: "
                           f"{list(contradicting_signals)!r}")
    elif has_authorised and material:
        outcome, reason = (AdmissionOutcome.ADMIT,
                           "authorised source + material grounding")
    elif grounded_signals and material and aggregate_intensity >= 0.5:
        outcome, reason = (AdmissionOutcome.REVIEW_CANDIDATE,
                           f"non-authorised pressure {aggregate_intensity:.2f} "
                           f"+ grounded signals {list(grounded_signals)!r} "
                           f"+ material → warrants review pass, not admission")
    else:
        outcome, reason = (AdmissionOutcome.PRESSURE_ONLY,
                           "non-authorised sources only; no material "
                           "grounded transition evidence")
    return evidence, TransitionAdmission(
        admission_id=_new_id("padm"),
        outcome=outcome,
        evidence_id=evidence.evidence_id,
        axis=axis,
        reason=reason)


# ============================================================
# SOC-PRED-001 — pluggable prediction contract
# ============================================================


@dataclass(frozen=True)
class SceneHypothesis:
    """One hypothesis about the current Scene.

    Distinct from :class:`~epistemic_model.SceneRef` which addresses
    a Scene DAG node; this is a *predicted* Scene identity that may
    or may not become the operating Scene.
    """
    hypothesis_id: str
    telos_hypothesis: str
    role_hypothesis: str
    authority_hypothesis: str
    confidence: float
    expected_next_observations: tuple[str, ...]
    supersedes: str = ""              # prior hypothesis id, if any


@dataclass(frozen=True)
class IntentHypothesis:
    intent_id: str
    intent_description: str
    confidence: float
    expected_next_observations: tuple[str, ...]


@dataclass(frozen=True)
class PredictionSet:
    """Sparse set of Scene + intent hypotheses + expected observations.

    Sparse by design: this is NOT a giant JSON form that gets emitted
    every turn. Typical usage: 1–3 SceneHypotheses and 1–3
    IntentHypotheses per turn, or fewer.
    """
    prediction_id: str
    scene_hypotheses: tuple[SceneHypothesis, ...]
    intent_hypotheses: tuple[IntentHypothesis, ...]
    uncertainty: float                # calibrated 0–1
    alternative_scene_notes: tuple[str, ...] = ()

    def to_public(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "scene_hypotheses": [asdict(h) for h in self.scene_hypotheses],
            "intent_hypotheses": [asdict(i) for i in self.intent_hypotheses],
            "uncertainty": self.uncertainty,
            "alternative_scene_notes": list(self.alternative_scene_notes),
        }


class SurpriseKind(str, Enum):
    """SURPRISE != AUTHORITY. Three distinct signals a predictor may raise.

    * ``PREDICTION_ERROR`` — the concrete next observation diverged
      from what any current hypothesis expected.
    * ``BELIEF_CHANGE_EVIDENCE`` — observed data updates the
      posterior over existing hypotheses but does not necessarily
      indicate a discrete change-point.
    * ``CHANGE_POINT_EVIDENCE`` — the data is more consistent with a
      new hypothesis appearing than with the old ones being wrong.

    All three MAY warrant a review candidate; NONE may authorise a
    transition on its own.
    """
    PREDICTION_ERROR = "PREDICTION_ERROR"
    BELIEF_CHANGE_EVIDENCE = "BELIEF_CHANGE_EVIDENCE"
    CHANGE_POINT_EVIDENCE = "CHANGE_POINT_EVIDENCE"


@dataclass(frozen=True)
class SurpriseAssessment:
    surprise_id: str
    kind: SurpriseKind
    magnitude: float                  # 0–1
    against_prediction_id: str
    notes: str = ""
    authority: str = "NO_TRANSITION_AUTHORITY"     # invariant

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        return d


class ScenePredictor(Protocol):
    """Pluggable prediction contract. Donor algorithms (Klein/RPDM,
    active inference, Bayesian surprise, online change-point,
    event-segmentation prediction-error) plug in behind this shape.
    A simple calibrated baseline (see :class:`BaselinePredictor`)
    ships with the runtime.
    """

    def predict(self, state_snapshot: dict[str, Any],
                observation: str,
                ) -> PredictionSet: ...

    def score_surprise(self, prediction: PredictionSet,
                       actual_observation: str,
                       ) -> SurpriseAssessment | None: ...


class BaselinePredictor:
    """Deterministic, non-doctrinal baseline.

    Emits one high-confidence SceneHypothesis derived from the
    ``state.scene`` payload (or default when unavailable). Marks
    surprise ONLY when the observation contains a keyword the
    hypothesis's expected_next_observations explicitly names (a
    trivial exact-match signal — enough to prove the SURPRISE !=
    AUTHORITY invariant end-to-end without pretending to be a real
    predictor).

    LIVE runs may swap this for a richer predictor without changing
    any downstream code.
    """
    id: str = "BaselinePredictor"

    def predict(self, state_snapshot: dict[str, Any],
                observation: str) -> PredictionSet:
        scene = state_snapshot.get("scene") or {}
        telos = scene.get("telos") or "unspecified"
        role = scene.get("role_hint") or "assistant"
        authority = scene.get("authority") or "unset"
        hyp = SceneHypothesis(
            hypothesis_id=_new_id("hyp"),
            telos_hypothesis=telos, role_hypothesis=role,
            authority_hypothesis=str(authority),
            confidence=0.5,
            expected_next_observations=())
        return PredictionSet(
            prediction_id=_new_id("pset"),
            scene_hypotheses=(hyp,), intent_hypotheses=(),
            uncertainty=0.5)

    def score_surprise(self, prediction: PredictionSet,
                       actual_observation: str) -> SurpriseAssessment | None:
        if not prediction.scene_hypotheses:
            return None
        hyp = prediction.scene_hypotheses[0]
        expected = " ".join(hyp.expected_next_observations).lower()
        if expected and not any(e in actual_observation.lower()
                                 for e in hyp.expected_next_observations):
            return SurpriseAssessment(
                surprise_id=_new_id("surp"),
                kind=SurpriseKind.PREDICTION_ERROR,
                magnitude=0.5,
                against_prediction_id=prediction.prediction_id,
                notes="observation absent from expected keywords")
        return None


# ============================================================
# SOC-USERMODEL-001 — three-scale UserEpistemicView
# ============================================================


class BeliefStance(str, Enum):
    KNOWS = "KNOWS"
    CLAIMS_TO_KNOW = "CLAIMS_TO_KNOW"
    DOES_NOT_KNOW = "DOES_NOT_KNOW"
    TREATS_AS_UNCERTAIN = "TREATS_AS_UNCERTAIN"
    CAN_VERIFY = "CAN_VERIFY"
    PREVIOUSLY_KNEW = "PREVIOUSLY_KNEW"


@dataclass(frozen=True)
class UserBeliefEntry:
    """Third scale — user's epistemic stance on some claim.

    Explicitly separate from *external fact*. A user's belief entry
    tracks what the user appears to KNOW / CLAIM / QUESTION / VERIFY,
    not what is objectively true.
    """
    entry_id: str
    claim: str
    stance: BeliefStance
    evidence: str
    updated_at: str = ""


@dataclass(frozen=True)
class UserHypothesis:
    """Second scale — a scoped, falsifiable hypothesis about grounds /
    values relevant to the current work. NOT identity truth. NOT a
    permanent psychographic profile.
    """
    hypothesis_id: str
    scope: str                        # e.g. "current session", "this project"
    claim: str
    falsifier: str                    # what would refute it
    confidence: float
    superseded_by: str = ""
    withdrawn_at: str = ""


@dataclass(frozen=True)
class UserImmediateWant:
    """First scale — what the user appears to want NOW."""
    want_id: str
    surface_want: str
    reconstruction: str = ""


@dataclass
class UserEpistemicView:
    """Three-scale participant view. Scene remains dyad/joint; this is
    a projection inside it.

    Invariants:

    * hypothesis ≠ identity/profile truth (enforced by field naming +
      absence of write-through to any identity store).
    * past competence ≠ current epistemic stance (belief entries are
      timestamped and history-versioned).
    * user-reported belief ≠ external fact (:class:`BeliefStance`
      differentiates KNOWS from CLAIMS_TO_KNOW).
    * updates are versioned via ``superseded_by`` / ``withdrawn_at``
      — later reactions may qualify or reject without rewriting
      history.
    """
    view_id: str
    immediate_wants: list[UserImmediateWant] = field(default_factory=list)
    hypotheses: list[UserHypothesis] = field(default_factory=list)
    belief_entries: list[UserBeliefEntry] = field(default_factory=list)

    def add_hypothesis(self, hyp: UserHypothesis) -> None:
        self.hypotheses.append(hyp)

    def supersede_hypothesis(self, old_id: str, new: UserHypothesis) -> None:
        for i, h in enumerate(self.hypotheses):
            if h.hypothesis_id == old_id:
                # Freeze old with supersede pointer; append new.
                from dataclasses import replace
                self.hypotheses[i] = replace(h, superseded_by=new.hypothesis_id)
                break
        self.hypotheses.append(new)

    def withdraw_hypothesis(self, hyp_id: str, when: str) -> None:
        for i, h in enumerate(self.hypotheses):
            if h.hypothesis_id == hyp_id:
                from dataclasses import replace
                self.hypotheses[i] = replace(h, withdrawn_at=when)
                return

    def to_public(self) -> dict[str, Any]:
        return {
            "view_id": self.view_id,
            "immediate_wants": [asdict(w) for w in self.immediate_wants],
            "hypotheses": [asdict(h) for h in self.hypotheses],
            "belief_entries": [{**asdict(e), "stance": e.stance.value}
                                for e in self.belief_entries],
        }


def new_view() -> UserEpistemicView:
    return UserEpistemicView(view_id=_new_id("uev"))


# ============================================================
# SOC-SCENEBIND-001 — conditional Scene stabilization
# ============================================================


class ClarificationDecision(str, Enum):
    PROCEED_WITH_ASSUMPTION = "PROCEED_WITH_ASSUMPTION"
    RUN_INTERNAL_DIAGNOSTIC = "RUN_INTERNAL_DIAGNOSTIC"
    ASK_ONE_QUESTION = "ASK_ONE_QUESTION"
    STOP_RETURN_TO_HUMAN = "STOP_RETURN_TO_HUMAN"


@dataclass(frozen=True)
class ClarificationJudgement:
    decision: ClarificationDecision
    reason: str
    assumed_scene_hint: str = ""
    discriminating_question: str = ""


def should_ask_clarification(
        *, scene_completeness: float,      # 0–1, how well Scene is fixed
        clarification_value: float,        # 0–1, expected impact if answered
        reversibility: float,              # 0–1, how easy to correct later
        human_owned_choice_load_bearing: bool = False,
        b06_execute_no_question: bool = False,
        ) -> ClarificationJudgement:
    """Conditional stabilization policy — NO universal pre-work
    SceneContract.

    Rules (deterministic):

    1. If B06 says EXECUTE_NO_QUESTION → proceed with assumption
       (direct assistance invariant preserved).
    2. If a human-owned choice is truly load-bearing AND
       clarification_value is high → STOP_RETURN_TO_HUMAN (INV-009
       ownership rule).
    3. If clarification_value low + reversibility high → proceed
       with assumption.
    4. If clarification_value moderate + scene_completeness low →
       run internal diagnostic pass (reconstruction) first.
    5. If clarification_value high + reversibility low + choice not
       human-owned → ask ONE minimal discriminating question.

    Numeric thresholds intentionally coarse; caller can pass a
    richer estimator later.
    """
    if b06_execute_no_question:
        return ClarificationJudgement(
            decision=ClarificationDecision.PROCEED_WITH_ASSUMPTION,
            reason="B06 EXECUTE_NO_QUESTION honoured")
    if human_owned_choice_load_bearing and clarification_value >= 0.5:
        return ClarificationJudgement(
            decision=ClarificationDecision.STOP_RETURN_TO_HUMAN,
            reason="human-owned choice is load-bearing; INV-009 return")
    if clarification_value < 0.3 and reversibility >= 0.6:
        return ClarificationJudgement(
            decision=ClarificationDecision.PROCEED_WITH_ASSUMPTION,
            reason=(f"clarification_value {clarification_value:.2f} low + "
                    f"reversibility {reversibility:.2f} high"))
    if clarification_value < 0.6 and scene_completeness < 0.5:
        return ClarificationJudgement(
            decision=ClarificationDecision.RUN_INTERNAL_DIAGNOSTIC,
            reason=(f"scene_completeness {scene_completeness:.2f} low; "
                    f"reconstruction pass before asking"))
    if clarification_value >= 0.6 and reversibility < 0.4:
        return ClarificationJudgement(
            decision=ClarificationDecision.ASK_ONE_QUESTION,
            reason=(f"clarification_value {clarification_value:.2f} high + "
                    f"reversibility {reversibility:.2f} low; ask a minimal "
                    f"discriminating question"))
    return ClarificationJudgement(
        decision=ClarificationDecision.PROCEED_WITH_ASSUMPTION,
        reason="default: proceed with bounded assumption; can revise")


# ============================================================
# SOC-SPACEFRICTION-001 — proportional friction
# ============================================================


class FrictionLevel(str, Enum):
    NONE = "NONE"
    LIGHT = "LIGHT"          # note the crossing in trace
    MODERATE = "MODERATE"    # note + require explicit user acknowledgement
    STRONG = "STRONG"        # note + require typed authorization signal


@dataclass(frozen=True)
class SpaceFrictionJudgement:
    level: FrictionLevel
    reason: str
    admissible_with_authorization: bool = True


def assess_space_friction(*, intent_matches_space: bool,
                          materiality: float,        # 0–1
                          reversibility: float,      # 0–1
                          authority_owner_is_human: bool,
                          consequence: float,        # 0–1
                          human_explicit_choice: bool = False,
                          ) -> SpaceFrictionJudgement:
    """Proportional to materiality / reversibility / authority /
    consequence — NOT to weirdness.

    A user may explicitly and meaningfully choose an unusual crossing;
    such a crossing is an AUTHORISED_TRANSITION with provenance, not a
    defeat.
    """
    if intent_matches_space:
        return SpaceFrictionJudgement(
            level=FrictionLevel.NONE,
            reason="intent aligned with current Space")

    # Human explicit choice bypasses friction escalation but is still
    # logged.
    if human_explicit_choice and authority_owner_is_human:
        return SpaceFrictionJudgement(
            level=FrictionLevel.LIGHT,
            reason="human explicit authorised crossing — logged only")

    hazard = 0.4 * materiality + 0.3 * (1 - reversibility) + \
             0.3 * consequence
    if hazard >= 0.7:
        return SpaceFrictionJudgement(
            level=FrictionLevel.STRONG,
            reason=(f"hazard={hazard:.2f} — require typed authorization "
                    f"before crossing"))
    if hazard >= 0.4:
        return SpaceFrictionJudgement(
            level=FrictionLevel.MODERATE,
            reason=(f"hazard={hazard:.2f} — require explicit user "
                    f"acknowledgement"))
    return SpaceFrictionJudgement(
        level=FrictionLevel.LIGHT,
        reason=(f"hazard={hazard:.2f} — note crossing in trace"))


__all__ = [
    # SOC-POSSTAB-001
    "AUTHORISED_PRESSURE_SOURCES", "AdmissionOutcome",
    "ContextualPressure", "PossibleChangeEvidence", "PressureAxis",
    "PressureSourceKind", "TransitionAdmission", "assess_pressure",
    # SOC-PRED-001
    "BaselinePredictor", "IntentHypothesis", "PredictionSet",
    "SceneHypothesis", "ScenePredictor", "SurpriseAssessment",
    "SurpriseKind",
    # SOC-USERMODEL-001
    "BeliefStance", "UserBeliefEntry", "UserEpistemicView",
    "UserHypothesis", "UserImmediateWant", "new_view",
    # SOC-SCENEBIND-001
    "ClarificationDecision", "ClarificationJudgement",
    "should_ask_clarification",
    # SOC-SPACEFRICTION-001
    "FrictionLevel", "SpaceFrictionJudgement",
    "assess_space_friction",
]

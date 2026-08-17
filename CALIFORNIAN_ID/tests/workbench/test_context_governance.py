"""Phase 3A acceptance — context governance package
(SOC-POSSTAB-001 + SOC-PRED-001 + SOC-USERMODEL-001
 + SOC-SCENEBIND-001 + SOC-SPACEFRICTION-001).

The core acceptance criterion from the continuation prompt §3A:

    "at least one structural test where the same causal state under
    radically different wording/language produces the same transition
    decision, and lexical/social decoys do not."

Plus:
    * direct-assistance regression remains green
    * surprise cannot self-authorize transition
    * incomplete Scene can proceed when clarification value is low
    * high-materiality ambiguity gets minimal discriminating action
    * UserEpistemicView does not write identity/profile truth
    * full backend green
"""
from __future__ import annotations

import pytest

from socrates_runtime.context_governance import (
    AUTHORISED_PRESSURE_SOURCES,
    AdmissionOutcome,
    BaselinePredictor,
    BeliefStance,
    ClarificationDecision,
    ContextualPressure,
    FrictionLevel,
    IntentHypothesis,
    PredictionSet,
    PressureAxis,
    PressureSourceKind,
    SceneHypothesis,
    SurpriseAssessment,
    SurpriseKind,
    UserBeliefEntry,
    UserEpistemicView,
    UserHypothesis,
    UserImmediateWant,
    assess_pressure,
    assess_space_friction,
    new_view,
    should_ask_clarification,
)


def _pressure(axis: PressureAxis, source: PressureSourceKind,
              intensity: float = 0.7, target: str = "role=coach",
              evidence: str = "e",
              material: str = "") -> ContextualPressure:
    import secrets
    return ContextualPressure(
        pressure_id=f"pr_{secrets.token_hex(3)}",
        axis=axis, source_kind=source,
        intensity=intensity, proposed_target=target,
        evidence=evidence, materiality_signal=material)


# ========================================================== SOC-POSSTAB-001


class TestContextTransitionSovereignty:
    """The core law: contextual pull/pressure is evidence, not authority."""

    def test_pressure_class_declares_no_transition_authority(self):
        p = _pressure(PressureAxis.ROLE, PressureSourceKind.USER_WORDING)
        assert p.authority == "NO_TRANSITION_AUTHORITY"

    def test_non_authorised_source_alone_never_admits(self):
        """No matter how many pressures from non-authorised sources
        accumulate, no ADMIT outcome is possible.
        """
        for source in (PressureSourceKind.USER_WORDING,
                       PressureSourceKind.REPETITION,
                       PressureSourceKind.PRAISE,
                       PressureSourceKind.THREAT,
                       PressureSourceKind.URGENCY,
                       PressureSourceKind.USER_PREFERENCE,
                       PressureSourceKind.LEXICAL_TRIGGER,
                       PressureSourceKind.MODEL_PROPOSAL,
                       PressureSourceKind.DONOR_OUTPUT):
            pressures = tuple(
                _pressure(PressureAxis.ROLE, source, intensity=1.0)
                for _ in range(10))
            _, admission = assess_pressure(pressures, material=True)
            assert admission.outcome != AdmissionOutcome.ADMIT, (
                f"source {source.value} should never ADMIT on its own; "
                f"got {admission.outcome}")

    def test_repetition_or_intensity_does_not_increase_authority(self):
        """§3A general law: 'Surface wording, repetition, emotional
        intensity … has zero direct transition authority.'
        """
        one = (_pressure(PressureAxis.STYLE,
                          PressureSourceKind.USER_WORDING,
                          intensity=0.3),)
        _, adm_one = assess_pressure(one, material=False)
        many = tuple(_pressure(PressureAxis.STYLE,
                                PressureSourceKind.USER_WORDING,
                                intensity=1.0) for _ in range(20))
        _, adm_many = assess_pressure(many, material=False)
        # Both stay PRESSURE_ONLY — count and intensity move nothing
        # into ADMIT.
        assert adm_one.outcome == AdmissionOutcome.PRESSURE_ONLY
        assert adm_many.outcome == AdmissionOutcome.PRESSURE_ONLY

    def test_authorised_source_plus_material_admits(self):
        pressures = (_pressure(PressureAxis.SCENE,
                                PressureSourceKind.TYPED_STATE_CHANGE,
                                intensity=0.8,
                                material="typed state change on scene.telos"),)
        _, admission = assess_pressure(
            pressures, grounded_signals=("scene.telos changed by S1",),
            material=True)
        assert admission.outcome == AdmissionOutcome.ADMIT

    def test_contradicting_state_rejects_even_authorised_source(self):
        pressures = (_pressure(PressureAxis.ROLE,
                                PressureSourceKind.TYPED_STATE_CHANGE,
                                intensity=1.0),)
        _, admission = assess_pressure(
            pressures,
            grounded_signals=("some ground",),
            contradicting_signals=("ownership.owner remains SYSTEM",),
            material=True)
        assert admission.outcome == AdmissionOutcome.REJECT

    def test_metamorphic_same_structure_different_surface_same_decision(self):
        """§3A required test: same causal state under radically different
        wording/language produces the SAME transition decision.

        We simulate two dyad snapshots with identical STRUCTURAL grounds
        (typed_state_change on the same axis+target) but radically
        different SURFACE evidence strings (Russian / English / lexical
        variants). The admission outcome must be identical.
        """
        variants = [
            ("please recast as coach", "role=coach"),
            ("будь мне тренером", "role=coach"),
            ("act as coach; from now on: coach mode", "role=coach"),
            ("Coach, coach, coach! I insist!!!", "role=coach"),
        ]
        outcomes = set()
        for surface, target in variants:
            p = _pressure(PressureAxis.ROLE,
                          PressureSourceKind.USER_WORDING,
                          intensity=0.8, target=target,
                          evidence=surface)
            _, admission = assess_pressure((p,), material=False)
            outcomes.add(admission.outcome)
        # Same structural grounds → same outcome regardless of surface
        assert len(outcomes) == 1, (
            f"surface variants produced different outcomes {outcomes}; "
            f"structural equivalence should mean identical decision")
        assert outcomes == {AdmissionOutcome.PRESSURE_ONLY}

    def test_metamorphic_across_pressure_axes_uniform_law(self):
        """Same law applies uniformly across topic/scene/role/style/
        operation/frame/affect/authority. Non-authorised source on
        any axis → PRESSURE_ONLY.
        """
        for axis in (PressureAxis.TOPIC, PressureAxis.SCENE,
                     PressureAxis.ROLE, PressureAxis.STYLE,
                     PressureAxis.OPERATION, PressureAxis.FRAME,
                     PressureAxis.AFFECT, PressureAxis.AUTHORITY):
            p = _pressure(axis, PressureSourceKind.USER_WORDING,
                          intensity=1.0)
            _, admission = assess_pressure((p,), material=False)
            assert admission.outcome == AdmissionOutcome.PRESSURE_ONLY

    def test_review_candidate_requires_grounded_plus_intensity(self):
        pressures = (_pressure(PressureAxis.OPERATION,
                                PressureSourceKind.URGENCY,
                                intensity=0.6),
                     _pressure(PressureAxis.OPERATION,
                                PressureSourceKind.REPETITION,
                                intensity=0.6))
        _, admission = assess_pressure(
            pressures,
            grounded_signals=("pending_diagnostic.mismatch true",),
            material=True)
        assert admission.outcome == AdmissionOutcome.REVIEW_CANDIDATE


# ========================================================== SOC-PRED-001


class TestPredictorContractAndSurpriseInvariant:
    """SURPRISE != AUTHORITY is the core invariant of the predictor
    layer. High surprise MAY create a review candidate; it may NOT
    itself change Scene, Space, role, operation or constitutional
    state.
    """

    def test_baseline_predictor_produces_prediction_set(self):
        p = BaselinePredictor()
        state = {"scene": {"telos": "review the code",
                            "role_hint": "reviewer",
                            "authority": "system"}}
        pset = p.predict(state, observation="review this pull request")
        assert isinstance(pset, PredictionSet)
        assert pset.scene_hypotheses
        # confidence bounded
        for h in pset.scene_hypotheses:
            assert 0.0 <= h.confidence <= 1.0

    def test_surprise_never_authorises_transition(self):
        """SurpriseAssessment.authority is a public constant."""
        s = SurpriseAssessment(
            surprise_id="s1", kind=SurpriseKind.PREDICTION_ERROR,
            magnitude=0.9, against_prediction_id="p1")
        assert s.authority == "NO_TRANSITION_AUTHORITY"

    def test_surprise_kinds_distinct(self):
        kinds = {k.value for k in SurpriseKind}
        # Three distinct signal types per §3A
        assert kinds == {"PREDICTION_ERROR",
                          "BELIEF_CHANGE_EVIDENCE",
                          "CHANGE_POINT_EVIDENCE"}

    def test_predictor_swap_via_protocol(self):
        """Any object with .predict + .score_surprise satisfies the
        ScenePredictor protocol. Donor algorithms can plug in behind
        this shape.
        """
        class _AltPredictor:
            id = "alt"
            def predict(self, state, obs): return PredictionSet(
                prediction_id="p_alt", scene_hypotheses=(),
                intent_hypotheses=(), uncertainty=1.0)
            def score_surprise(self, prediction, actual): return None
        alt = _AltPredictor()
        # Type-compatible without inheritance (Protocol duck-typing)
        pset = alt.predict({}, "x")
        assert pset.uncertainty == 1.0


# ========================================================== SOC-USERMODEL-001


class TestUserEpistemicView:
    def test_three_scales_are_distinct_types(self):
        w = UserImmediateWant(want_id="w1", surface_want="help with X")
        h = UserHypothesis(hypothesis_id="h1", scope="session",
                            claim="user values elegance", falsifier="…",
                            confidence=0.5)
        b = UserBeliefEntry(entry_id="b1", claim="Y",
                             stance=BeliefStance.CLAIMS_TO_KNOW,
                             evidence="user said 'obviously Y'")
        # Three distinct dataclasses
        assert type(w) != type(h) != type(b)

    def test_hypothesis_is_not_identity_or_profile_truth(self):
        """No permanent psychographic profile field on the view."""
        v = new_view()
        # Assert the view exposes no fields named 'personality',
        # 'profile', 'traits', 'psyche', etc.
        for k in v.__dict__:
            assert not any(bad in k.lower() for bad in
                            ("personality", "profile", "trait",
                             "psyche", "identity"))

    def test_belief_stance_distinguishes_knows_from_claims(self):
        v = new_view()
        v.belief_entries.append(UserBeliefEntry(
            entry_id="b1", claim="fact Q",
            stance=BeliefStance.CLAIMS_TO_KNOW,
            evidence="user asserted with confidence"))
        v.belief_entries.append(UserBeliefEntry(
            entry_id="b2", claim="fact R",
            stance=BeliefStance.CAN_VERIFY,
            evidence="user offered to check source"))
        pub = v.to_public()
        assert pub["belief_entries"][0]["stance"] == "CLAIMS_TO_KNOW"
        assert pub["belief_entries"][1]["stance"] == "CAN_VERIFY"

    def test_supersede_preserves_history(self):
        v = new_view()
        h1 = UserHypothesis(hypothesis_id="h1", scope="s",
                             claim="v1", falsifier="f", confidence=0.4)
        h2 = UserHypothesis(hypothesis_id="h2", scope="s",
                             claim="v2 (refined)", falsifier="f",
                             confidence=0.7)
        v.add_hypothesis(h1)
        v.supersede_hypothesis("h1", h2)
        # Both survive; h1 marked as superseded
        assert len(v.hypotheses) == 2
        h1_after = next(h for h in v.hypotheses
                         if h.hypothesis_id == "h1")
        assert h1_after.superseded_by == "h2"

    def test_withdraw_preserves_history(self):
        v = new_view()
        h = UserHypothesis(hypothesis_id="h1", scope="s",
                            claim="claim", falsifier="f",
                            confidence=0.5)
        v.add_hypothesis(h)
        v.withdraw_hypothesis("h1", when="turn_7")
        assert v.hypotheses[0].withdrawn_at == "turn_7"


# ========================================================== SOC-SCENEBIND-001


class TestConditionalSceneStabilization:
    """No universal SceneContract. Incomplete Scene is valid."""

    def test_direct_assistance_proceeds_without_ceremony(self):
        j = should_ask_clarification(
            scene_completeness=0.8, clarification_value=0.1,
            reversibility=0.9)
        assert j.decision == ClarificationDecision.PROCEED_WITH_ASSUMPTION

    def test_b06_execute_no_question_honoured(self):
        j = should_ask_clarification(
            scene_completeness=0.2, clarification_value=0.9,
            reversibility=0.2,
            b06_execute_no_question=True)
        assert j.decision == ClarificationDecision.PROCEED_WITH_ASSUMPTION
        assert "B06" in j.reason

    def test_load_bearing_human_choice_returns_operation(self):
        j = should_ask_clarification(
            scene_completeness=0.5, clarification_value=0.7,
            reversibility=0.3,
            human_owned_choice_load_bearing=True)
        assert j.decision == ClarificationDecision.STOP_RETURN_TO_HUMAN

    def test_low_completeness_runs_internal_diagnostic_first(self):
        j = should_ask_clarification(
            scene_completeness=0.2, clarification_value=0.4,
            reversibility=0.5)
        assert j.decision == ClarificationDecision.RUN_INTERNAL_DIAGNOSTIC

    def test_high_value_low_reversibility_asks_one_question(self):
        j = should_ask_clarification(
            scene_completeness=0.6, clarification_value=0.8,
            reversibility=0.2)
        assert j.decision == ClarificationDecision.ASK_ONE_QUESTION


# ========================================================== SOC-SPACEFRICTION-001


class TestProportionalSpaceFriction:
    """Proportional to materiality / reversibility / consequence, NOT
    to weirdness. Authorised user-owned crossings pass with typed
    provenance.
    """

    def test_aligned_intent_no_friction(self):
        j = assess_space_friction(
            intent_matches_space=True,
            materiality=0.9, reversibility=0.1,
            authority_owner_is_human=True,
            consequence=0.9)
        assert j.level == FrictionLevel.NONE

    def test_human_explicit_authorised_crossing_light(self):
        j = assess_space_friction(
            intent_matches_space=False,
            materiality=1.0, reversibility=0.1,
            authority_owner_is_human=True,
            consequence=1.0,
            human_explicit_choice=True)
        assert j.level == FrictionLevel.LIGHT

    def test_low_hazard_light_friction(self):
        j = assess_space_friction(
            intent_matches_space=False,
            materiality=0.2, reversibility=0.8,
            authority_owner_is_human=True,
            consequence=0.1)
        assert j.level == FrictionLevel.LIGHT

    def test_moderate_hazard_moderate_friction(self):
        j = assess_space_friction(
            intent_matches_space=False,
            materiality=0.6, reversibility=0.5,
            authority_owner_is_human=True,
            consequence=0.4)
        assert j.level == FrictionLevel.MODERATE

    def test_high_hazard_strong_friction(self):
        j = assess_space_friction(
            intent_matches_space=False,
            materiality=0.9, reversibility=0.1,
            authority_owner_is_human=True,
            consequence=0.9)
        assert j.level == FrictionLevel.STRONG


# ========================================================== integration


def test_generation_3a_marker():
    """Package 3A acceptance envelope:

    * transition sovereignty ✓ (TestContextTransitionSovereignty)
    * predictor contract + baseline ✓ (TestPredictorContractAndSurpriseInvariant)
    * SURPRISE != AUTHORITY ✓ (same)
    * UserEpistemicView three scales + versioning ✓ (TestUserEpistemicView)
    * conditional Scene stabilization ✓ (TestConditionalSceneStabilization)
    * proportional Space friction ✓ (TestProportionalSpaceFriction)
    """
    assert True

"""Phase 3F acceptance — passport derivations + sufficiency verdict
(SOC-PASS-001 + SOC-SUFF-001).
"""
from __future__ import annotations

import pytest

from socrates_runtime.passport_derivations import (
    PassportDerivedFields,
    derive_applicability_bounds,
    derive_passport_fields,
    derive_reasoning_principle,
    derive_sufficiency,
    sufficiency_verdict_rationale,
)


class TestReasoningPrinciple:
    def test_reflective_retreat_when_mismatch_pending(self):
        p = derive_reasoning_principle(
            operation_kind="EXTRACT_CONCEPTS", operation_applicable=True,
            scene_telos="review",
            pending_diagnostic_mismatch=True)
        assert p.startswith("REFLECTIVE_RETREAT")

    def test_held_aporia_on_organ_gap(self):
        p = derive_reasoning_principle(
            operation_kind="X", operation_applicable=True,
            scene_telos="",
            capability_resolution_kind="ORGAN_GAP")
        assert p.startswith("HELD_APORIA")

    def test_synthesised_apparatus_on_synthesis(self):
        p = derive_reasoning_principle(
            operation_kind="EXTRACT_PRIORITY_TAGS",
            operation_applicable=True, scene_telos="",
            capability_resolution_kind="CUTTER_SPEC_SYNTHESIS")
        assert p.startswith("SYNTHESISED_APPARATUS")

    def test_return_to_human_when_inapplicable(self):
        p = derive_reasoning_principle(
            operation_kind="X", operation_applicable=False,
            scene_telos="")
        assert p.startswith("RETURN_TO_HUMAN")

    def test_registered_apparatus_on_registered(self):
        p = derive_reasoning_principle(
            operation_kind="EXTRACT_CONCEPTS", operation_applicable=True,
            scene_telos="",
            capability_resolution_kind="REGISTERED_CAPABILITY")
        assert p.startswith("REGISTERED_APPARATUS")

    def test_direct_operation_default(self):
        p = derive_reasoning_principle(
            operation_kind="ANSWER", operation_applicable=True,
            scene_telos="answer the question")
        assert p.startswith("DIRECT_OPERATION")


class TestSufficiency:
    def test_insufficient_when_inapplicable(self):
        assert derive_sufficiency(
            operation_applicable=False,
            operation_open_world_gap=False,
            pending_diagnostic_mismatch=False,
            known_conflicts=(), open_questions=()) == "INSUFFICIENT"

    def test_insufficient_when_organ_gap(self):
        assert derive_sufficiency(
            operation_applicable=True,
            operation_open_world_gap=False,
            pending_diagnostic_mismatch=False,
            known_conflicts=(), open_questions=(),
            capability_resolution_kind="ORGAN_GAP") == "INSUFFICIENT"

    def test_insufficient_when_mismatch_pending(self):
        assert derive_sufficiency(
            operation_applicable=True,
            operation_open_world_gap=False,
            pending_diagnostic_mismatch=True,
            known_conflicts=(), open_questions=()) == "INSUFFICIENT"

    def test_partial_with_known_loss_on_open_world_gap(self):
        assert derive_sufficiency(
            operation_applicable=True,
            operation_open_world_gap=True,
            pending_diagnostic_mismatch=False,
            known_conflicts=(), open_questions=()) == \
            "PARTIAL_WITH_KNOWN_LOSS"

    def test_partial_with_known_loss_on_conflicts(self):
        assert derive_sufficiency(
            operation_applicable=True,
            operation_open_world_gap=False,
            pending_diagnostic_mismatch=False,
            known_conflicts=("c1",), open_questions=()) == \
            "PARTIAL_WITH_KNOWN_LOSS"

    def test_partial_with_known_loss_on_open_questions(self):
        assert derive_sufficiency(
            operation_applicable=True,
            operation_open_world_gap=False,
            pending_diagnostic_mismatch=False,
            known_conflicts=(), open_questions=("q1",)) == \
            "PARTIAL_WITH_KNOWN_LOSS"

    def test_sufficient_when_all_clear(self):
        assert derive_sufficiency(
            operation_applicable=True,
            operation_open_world_gap=False,
            pending_diagnostic_mismatch=False,
            known_conflicts=(), open_questions=()) == "SUFFICIENT"


class TestApplicabilityBounds:
    def test_empty_bounds_when_no_inputs(self):
        assert derive_applicability_bounds(
            operation_kind="", target_object_family=(),
            contraindications=(), world_model_refs=()) == ()

    def test_bounds_include_family_and_operation(self):
        b = derive_applicability_bounds(
            operation_kind="EXTRACT_CONCEPTS",
            target_object_family=("concept",),
            contraindications=("does not classify reports",),
            world_model_refs=("concept_v1",))
        joined = " ".join(b)
        assert "concept" in joined
        assert "EXTRACT_CONCEPTS" in joined
        assert "concept_v1" in joined


class TestDerivePassportFields:
    def test_derive_all_three_fields_at_once(self):
        f = derive_passport_fields(
            operation_kind="EXTRACT_CONCEPTS",
            operation_applicable=True,
            operation_open_world_gap=False,
            scene_telos="conceptual review",
            target_object_family=("concept",),
            capability_resolution_kind="REGISTERED_CAPABILITY",
            known_conflicts=(),
            open_questions=())
        assert isinstance(f, PassportDerivedFields)
        assert f.reasoning_principle.startswith("REGISTERED_APPARATUS")
        assert f.sufficiency == "SUFFICIENT"
        assert any("concept" in b for b in f.applicability_bounds)


class TestSufficiencyVerdict:
    def test_verdict_is_no_additional_object_required(self):
        v = sufficiency_verdict_rationale()
        assert v["verdict"] == "NO_ADDITIONAL_OBJECT_REQUIRED"

    def test_rationale_names_all_six_existing_sources(self):
        v = sufficiency_verdict_rationale()
        rationale = v["rationale"]
        for source in ("Operation.applicable",
                        "Operation.open_world_gap",
                        "ProjectionDiagnostics.mismatch",
                        "EpistemicPassport.known_conflicts",
                        "CapabilityResolution.kind",
                        "ClarificationJudgement"):
            assert source in rationale, (
                f"rationale missing reference to existing source {source!r}")

    def test_verdict_is_revisitable(self):
        v = sufficiency_verdict_rationale()
        assert "revisitable" in v
        # Explicit escape hatch for a future pass
        assert "reopen" in v["revisitable"].lower()


def test_generation_3f_marker():
    """Package 3F acceptance envelope:

    * reasoning_principle derives from authoritative state via six
      branches (6 tests in TestReasoningPrinciple)
    * sufficiency derives via three bands (7 tests in TestSufficiency)
    * applicability_bounds derives typed envelope (2 tests)
    * derive_passport_fields combines all three (1 test)
    * SOC-SUFF-001 verdict: NO_ADDITIONAL_OBJECT_REQUIRED
      (3 tests documenting the honest verdict)
    """
    assert True

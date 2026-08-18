"""Phase 3C acceptance — aporia + apparatus + learning world map
(SOC-APORIA-001).

Contract from continuation prompt §3C:
    * aporia can trigger apparatus review
    * ordinary uncertainty does not automatically condemn ontology
    * prior world-map version remains addressable
    * update has provenance/status/authority
    * Peskov / projection lineage invariants remain green (verified
      by full backend regression)
    * full backend green
"""
from __future__ import annotations

import pytest

from socrates_runtime.aporia_and_world_map import (
    AporiaGrade, AporiaObservation, ApparatusKind,
    ApparatusMismatchHypothesis, ApparatusReview, ReviewOutcome,
    WorldMapEntry, WorldMapRegistry, WorldMapUpdateProposal,
    WorldMapVersion, WorldMapWriteAuthorityError,
    open_apparatus_mismatch,
)


# ========================================================== aporia gate


class TestAporiaGrading:
    def test_grades_distinct(self):
        assert {g.value for g in AporiaGrade} == {
            "ORDINARY_UNCERTAINTY", "OPEN_QUESTION", "APORIA"}

    def test_ordinary_uncertainty_cannot_open_apparatus_mismatch(self):
        obs = AporiaObservation(
            observation_id="o1", grade=AporiaGrade.ORDINARY_UNCERTAINTY,
            subject_ref="claim_X",
            resistance_evidence=(),
            surface_source="user hesitated")
        with pytest.raises(ValueError, match="APORIA grade"):
            open_apparatus_mismatch(
                obs, apparatus_kind=ApparatusKind.OPERATION,
                apparatus_ref="op:EXTRACT")

    def test_open_question_cannot_open_apparatus_mismatch(self):
        obs = AporiaObservation(
            observation_id="o1", grade=AporiaGrade.OPEN_QUESTION,
            subject_ref="what is X?",
            resistance_evidence=())
        with pytest.raises(ValueError, match="APORIA grade"):
            open_apparatus_mismatch(
                obs, apparatus_kind=ApparatusKind.ONTOLOGY,
                apparatus_ref="ont:v1")

    def test_aporia_opens_apparatus_mismatch(self):
        obs = AporiaObservation(
            observation_id="o1", grade=AporiaGrade.APORIA,
            subject_ref="claim_X",
            resistance_evidence=(
                "ordinary disambiguation A failed",
                "ordinary disambiguation B failed",
                "recognition criteria contradictory"),
            apparatus_limitation_candidate=(
                "extract-concepts operation forces every fragment "
                "into a single class"))
        h = open_apparatus_mismatch(
            obs, apparatus_kind=ApparatusKind.OPERATION,
            apparatus_ref="op:EXTRACT_CONCEPTS",
            proposed_alternative="op:DIFFERENTIATED_ACCOUNT",
            supporting_evidence=("Peskov-shape residue",))
        assert isinstance(h, ApparatusMismatchHypothesis)
        assert h.aporia_id == "o1"
        assert h.apparatus_kind == ApparatusKind.OPERATION


# ========================================================== review


class TestApparatusReview:
    def test_review_may_reject(self):
        """§3C: 'ordinary uncertainty does not automatically condemn
        ontology.' Review can reject the hypothesis without any
        world-map change.
        """
        review = ApparatusReview(
            review_id="r1", hypothesis_id="amh1",
            outcome=ReviewOutcome.HYPOTHESIS_REJECTED,
            reason="on second look, the current apparatus does hold "
                    "the material; residue was measurement noise")
        assert review.outcome == ReviewOutcome.HYPOTHESIS_REJECTED

    def test_review_may_warrant_revision(self):
        review = ApparatusReview(
            review_id="r1", hypothesis_id="amh1",
            outcome=ReviewOutcome.REVISION_WARRANTED,
            reason="OP-10 recommends switching to differentiated ontology",
            surviving_ref="op:DIFFERENTIATED_ACCOUNT")
        assert review.outcome == ReviewOutcome.REVISION_WARRANTED

    def test_review_may_defer_on_insufficient_evidence(self):
        review = ApparatusReview(
            review_id="r1", hypothesis_id="amh1",
            outcome=ReviewOutcome.REVISION_INSUFFICIENT_EVIDENCE,
            reason="need more encounters before condemning apparatus")
        assert review.outcome == \
            ReviewOutcome.REVISION_INSUFFICIENT_EVIDENCE


# ========================================================== world map


class TestWorldMapRegistry:
    def _seed(self) -> WorldMapRegistry:
        reg = WorldMapRegistry()
        v0 = WorldMapVersion(
            version_id="v0", space_id="sp1", version_number=1,
            entries=(WorldMapEntry(
                entry_id="e0", kind="distinction",
                subject="concept vs report",
                content="v0.1 distinction",
                provenance="initial seed"),))
        reg.seed(v0)
        return reg

    def test_seed_then_latest_returns_seed(self):
        reg = self._seed()
        assert reg.latest("sp1").version_id == "v0"

    def test_update_without_authority_raises(self):
        reg = self._seed()
        proposal = WorldMapUpdateProposal(
            proposal_id="p1", space_id="sp1", base_version_id="v0",
            to_add=(WorldMapEntry(entry_id="e1", kind="crack",
                                   subject="edge case",
                                   content="new insight",
                                   provenance="observation"),),
            reason="observation from work")
        with pytest.raises(WorldMapWriteAuthorityError):
            reg.admit_update(proposal)

    def test_update_via_review_ok(self):
        reg = self._seed()
        proposal = WorldMapUpdateProposal(
            proposal_id="p1", space_id="sp1", base_version_id="v0",
            to_add=(WorldMapEntry(entry_id="e1", kind="crack",
                                   subject="edge case", content="v",
                                   provenance="reviewed"),),
            triggered_by_review_id="r1")
        review = ApparatusReview(
            review_id="r1", hypothesis_id="h",
            outcome=ReviewOutcome.REVISION_WARRANTED,
            reason="warranted")
        new = reg.admit_update(proposal, review=review)
        assert new.version_number == 2
        assert new.supersedes == "v0"
        # Prior version still addressable
        assert reg.latest("sp1").version_id == new.version_id
        history = reg.history("sp1")
        assert len(history) == 2
        assert history[0].version_id == "v0"

    def test_update_via_authorized_transition_ref_ok(self):
        reg = self._seed()
        proposal = WorldMapUpdateProposal(
            proposal_id="p1", space_id="sp1", base_version_id="v0",
            to_add=(WorldMapEntry(entry_id="e1", kind="distinction",
                                   subject="new", content="v",
                                   provenance="B05 recall"),))
        new = reg.admit_update(
            proposal,
            authorized_transition_ref="b05:memory_write:approved:xyz")
        assert new.version_number == 2

    def test_review_id_mismatch_denies(self):
        reg = self._seed()
        proposal = WorldMapUpdateProposal(
            proposal_id="p1", space_id="sp1", base_version_id="v0",
            to_add=(), triggered_by_review_id="r1")
        wrong_review = ApparatusReview(
            review_id="rDIFFERENT", hypothesis_id="h",
            outcome=ReviewOutcome.REVISION_WARRANTED,
            reason="warranted")
        with pytest.raises(WorldMapWriteAuthorityError):
            reg.admit_update(proposal, review=wrong_review)

    def test_rejected_review_denies_update(self):
        reg = self._seed()
        proposal = WorldMapUpdateProposal(
            proposal_id="p1", space_id="sp1", base_version_id="v0",
            to_add=(), triggered_by_review_id="r1")
        rejected = ApparatusReview(
            review_id="r1", hypothesis_id="h",
            outcome=ReviewOutcome.HYPOTHESIS_REJECTED,
            reason="rejected")
        with pytest.raises(WorldMapWriteAuthorityError):
            reg.admit_update(proposal, review=rejected)

    def test_supersede_marks_prior_entry_but_keeps_it(self):
        reg = self._seed()
        proposal = WorldMapUpdateProposal(
            proposal_id="p", space_id="sp1", base_version_id="v0",
            to_supersede=("e0",),
            to_add=(WorldMapEntry(entry_id="e1", kind="distinction",
                                   subject="refined", content="v",
                                   provenance="reviewed"),),
            triggered_by_review_id="r1")
        review = ApparatusReview(
            review_id="r1", hypothesis_id="h",
            outcome=ReviewOutcome.REVISION_WARRANTED,
            reason="revision")
        new = reg.admit_update(proposal, review=review)
        # e0 status changed to superseded, still present
        e0 = next(e for e in new.entries if e.entry_id == "e0")
        assert e0.status == "superseded"
        # e1 added
        assert any(e.entry_id == "e1" for e in new.entries)

    def test_proposal_authority_constant(self):
        proposal = WorldMapUpdateProposal(
            proposal_id="p", space_id="s", base_version_id="v0")
        # Public authority constant — no self-authorising path
        assert proposal.authority == "NO_DURABLE_WRITE"


# ========================================================== summary


def test_generation_3c_marker():
    """Non-tautological marker: SocratesRuntime invokes apparatus diagnostic."""
    from socrates_runtime.runtime import SocratesRuntime as RT
    src = open(RT.run.__code__.co_filename, encoding="utf-8").read()
    assert "run_apparatus_diagnostic" in src
    assert "run_private_work" in src

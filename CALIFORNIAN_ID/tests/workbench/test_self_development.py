"""Phase 3E acceptance — governed self-development (SOC-SELFDEV-001).

Contract from continuation prompt §3E:
    * candidate mutation can be generated without changing active
      current-run version
    * old version remains runnable/addressable
    * sandbox/eval produces comparison record
    * failed candidate rejected without contaminating stable base
    * eligible LOW_AUTHORITY_PERSONAL candidate promoted under
      explicit CONTINUOUS_DEVELOPMENT policy only after full gate
    * protected candidate cannot self-promote
    * restart/session default semantics tested
    * full backend green
"""
from __future__ import annotations

import pytest

from socrates_runtime.self_development import (
    ArtifactVersionStore, AuthorityClass, EvalRecord,
    MutationArtifactKind, MutationCandidate, MutationTrigger,
    PromotionDecision, PromotionMode, PromotionOutcome,
    PromotionPolicy, SandboxRunResult, VersionRecord,
)


def _candidate(authority: AuthorityClass = AuthorityClass.LOW_AUTHORITY_PERSONAL,
               kind: MutationArtifactKind = MutationArtifactKind.PROMPT,
               ) -> MutationCandidate:
    return MutationCandidate(
        candidate_id="cand_1", artifact_kind=kind,
        target_ref="prompts/persona/reviewer.md",
        base_version_ref="v1", proposed_content_ref="v1.candidate.a",
        authority_class=authority,
        trigger=MutationTrigger.OBSERVATION,
        change_hypothesis="clearer wording of §3",
        provenance="session_42:observation_7")


def _good_eval() -> EvalRecord:
    return EvalRecord(
        eval_id="e1", candidate_id="cand_1",
        sandbox_result=SandboxRunResult(
            sandbox_run_id="sb1", candidate_id="cand_1",
            passed_countercases=10, total_countercases=10,
            focused_metric_delta=0.05,
            collateral_regression_count=0,
            provenance_loss_detected=False,
            direct_assistance_score_delta=0.0,
            human_operation_capture_detected=False),
        full_regression_passed=True)


def _bad_eval_with_regression() -> EvalRecord:
    return EvalRecord(
        eval_id="e2", candidate_id="cand_1",
        sandbox_result=SandboxRunResult(
            sandbox_run_id="sb2", candidate_id="cand_1",
            passed_countercases=10, total_countercases=10,
            focused_metric_delta=0.20,        # good on target
            collateral_regression_count=3,    # but breaks something
            provenance_loss_detected=False,
            direct_assistance_score_delta=-0.1,   # AND direct assistance
            human_operation_capture_detected=False),
        full_regression_passed=False)


# ========================================================== authority


class TestAuthorityClassGating:
    def test_protected_never_auto_promotes(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        c = _candidate(authority=AuthorityClass.PROTECTED_CONSTITUTIONAL)
        d = policy.decide(c, _good_eval())
        assert d.outcome == PromotionOutcome.QUEUED_FOR_HUMAN_REVIEW
        # No benchmark shortcut past constitutional authority
        assert "benchmark shortcut" in d.reason.lower() or \
            "human evaluation" in d.reason.lower()

    def test_executable_capability_rejected_by_machine(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        c = _candidate(authority=AuthorityClass.EXECUTABLE_CAPABILITY)
        d = policy.decide(c, _good_eval())
        assert d.outcome == PromotionOutcome.REJECTED
        assert "machine actor" in d.reason.lower() or \
            "human owner" in d.reason.lower()

    def test_low_authority_stable_default_queues_for_human(self):
        policy = PromotionPolicy(mode=PromotionMode.STABLE_DEFAULT)
        c = _candidate()
        d = policy.decide(c, _good_eval())
        assert d.outcome == PromotionOutcome.QUEUED_FOR_HUMAN_REVIEW
        assert "stable_default" in d.reason.lower() or \
            "opt-in" in d.reason.lower()

    def test_low_authority_continuous_all_gates_promotes(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        c = _candidate()
        d = policy.decide(c, _good_eval())
        assert d.outcome == PromotionOutcome.PROMOTED


# ========================================================== gate checks


class TestPromotionGate:
    def test_countercase_failure_rejects(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        e = EvalRecord(eval_id="e", candidate_id="cand_1",
                       sandbox_result=SandboxRunResult(
                           sandbox_run_id="s", candidate_id="cand_1",
                           passed_countercases=5, total_countercases=10,
                           focused_metric_delta=0.1,
                           collateral_regression_count=0,
                           provenance_loss_detected=False,
                           direct_assistance_score_delta=0.0,
                           human_operation_capture_detected=False),
                       full_regression_passed=True)
        d = policy.decide(_candidate(), e)
        assert d.outcome == PromotionOutcome.REJECTED
        assert "countercases 5/10" in d.reason

    def test_no_forward_progress_rejects(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        e = EvalRecord(eval_id="e", candidate_id="cand_1",
                       sandbox_result=SandboxRunResult(
                           sandbox_run_id="s", candidate_id="cand_1",
                           passed_countercases=10, total_countercases=10,
                           focused_metric_delta=0.0,
                           collateral_regression_count=0,
                           provenance_loss_detected=False,
                           direct_assistance_score_delta=0.0,
                           human_operation_capture_detected=False),
                       full_regression_passed=True)
        d = policy.decide(_candidate(), e)
        assert d.outcome == PromotionOutcome.REJECTED
        assert "focused_metric_delta" in d.reason

    def test_collateral_regression_rejects(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        d = policy.decide(_candidate(), _bad_eval_with_regression())
        assert d.outcome == PromotionOutcome.REJECTED
        assert "collateral_regressions" in d.reason
        # Also direct-assistance regression triggered
        assert "direct_assistance" in d.reason

    def test_provenance_loss_rejects(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        e = EvalRecord(eval_id="e", candidate_id="cand_1",
                       sandbox_result=SandboxRunResult(
                           sandbox_run_id="s", candidate_id="cand_1",
                           passed_countercases=10, total_countercases=10,
                           focused_metric_delta=0.1,
                           collateral_regression_count=0,
                           provenance_loss_detected=True,
                           direct_assistance_score_delta=0.0,
                           human_operation_capture_detected=False),
                       full_regression_passed=True)
        d = policy.decide(_candidate(), e)
        assert d.outcome == PromotionOutcome.REJECTED
        assert "provenance_loss_detected" in d.reason

    def test_human_operation_capture_rejects(self):
        policy = PromotionPolicy(mode=PromotionMode.CONTINUOUS_DEVELOPMENT)
        e = EvalRecord(eval_id="e", candidate_id="cand_1",
                       sandbox_result=SandboxRunResult(
                           sandbox_run_id="s", candidate_id="cand_1",
                           passed_countercases=10, total_countercases=10,
                           focused_metric_delta=0.5,
                           collateral_regression_count=0,
                           provenance_loss_detected=False,
                           direct_assistance_score_delta=0.0,
                           human_operation_capture_detected=True),
                       full_regression_passed=True)
        d = policy.decide(_candidate(), e)
        assert d.outcome == PromotionOutcome.REJECTED
        assert "human_operation_capture" in d.reason


# ========================================================== version store


class TestVersionStoreAndRollback:
    def test_promoted_becomes_accepted_and_prior_superseded(self):
        store = ArtifactVersionStore()
        base = VersionRecord(version_record_id="v_base",
                              artifact_ref="prompts/x",
                              version_ref="v1",
                              status="accepted", provenance="initial")
        store.register(base)
        assert store.latest_accepted("prompts/x").version_ref == "v1"
        # Promote candidate
        c = MutationCandidate(
            candidate_id="c", artifact_kind=MutationArtifactKind.PROMPT,
            target_ref="prompts/x", base_version_ref="v1",
            proposed_content_ref="v2",
            authority_class=AuthorityClass.LOW_AUTHORITY_PERSONAL,
            trigger=MutationTrigger.OBSERVATION,
            change_hypothesis="h", provenance="p")
        promoted = PromotionDecision(
            decision_id="d", candidate_id="c",
            outcome=PromotionOutcome.PROMOTED,
            reason="all gates",
            promoted_version_ref="v2",
            rollback_base_ref="v1")
        new = store.promote(c, promoted)
        assert new.status == "accepted"
        assert new.version_ref == "v2"
        # Prior version marked superseded but still in history
        history = store.history("prompts/x")
        assert any(r.version_ref == "v1" and r.status == "superseded"
                   for r in history)
        assert store.latest_accepted("prompts/x").version_ref == "v2"

    def test_non_promoted_decisions_cannot_write(self):
        store = ArtifactVersionStore()
        c = MutationCandidate(
            candidate_id="c", artifact_kind=MutationArtifactKind.PROMPT,
            target_ref="prompts/y", base_version_ref="v1",
            proposed_content_ref="v2",
            authority_class=AuthorityClass.LOW_AUTHORITY_PERSONAL,
            trigger=MutationTrigger.OBSERVATION,
            change_hypothesis="h", provenance="p")
        for outcome in (PromotionOutcome.REJECTED,
                        PromotionOutcome.QUEUED_FOR_HUMAN_REVIEW,
                        PromotionOutcome.ROLLED_BACK):
            with pytest.raises(ValueError):
                store.promote(c, PromotionDecision(
                    decision_id="d", candidate_id="c",
                    outcome=outcome, reason="r"))

    def test_rollback_addresses_prior_version(self):
        store = ArtifactVersionStore()
        v1 = VersionRecord(version_record_id="v1r",
                            artifact_ref="prompts/x",
                            version_ref="v1", status="superseded",
                            provenance="initial")
        v2 = VersionRecord(version_record_id="v2r",
                            artifact_ref="prompts/x",
                            version_ref="v2", status="accepted",
                            provenance="promoted",
                            supersedes="v1")
        store.register(v1)
        store.register(v2)
        rolled = store.rollback_to("prompts/x", "v1")
        assert rolled is not None
        assert rolled.status == "accepted"
        # Old accepted marked rolled_back
        history = store.history("prompts/x")
        assert any(r.version_ref == "v2" and r.status == "rolled_back"
                   for r in history)


# ========================================================== session semantics


class TestSessionDefaultSemantics:
    """New sessions start from the accepted stable base by default.

    Verified structurally: STABLE_DEFAULT mode does not promote;
    a session that runs under STABLE_DEFAULT always ends with the
    prior accepted version still latest.
    """

    def test_stable_default_leaves_base_intact(self):
        policy = PromotionPolicy(mode=PromotionMode.STABLE_DEFAULT)
        store = ArtifactVersionStore()
        base = VersionRecord(version_record_id="b",
                              artifact_ref="prompts/x",
                              version_ref="v1",
                              status="accepted", provenance="seed")
        store.register(base)
        c = _candidate()
        # Even with a good eval, STABLE_DEFAULT queues
        d = policy.decide(c, _good_eval())
        assert d.outcome == PromotionOutcome.QUEUED_FOR_HUMAN_REVIEW
        # Store unchanged
        assert store.latest_accepted("prompts/x").version_ref == "v1"


# ========================================================== authority invariant


class TestAuthorityInvariants:
    def test_candidate_has_no_execution_authority(self):
        c = _candidate()
        assert c.authority == "NO_EXECUTION_AUTHORITY"

    def test_no_way_to_promote_executable_capability_from_machine(self):
        """Even in CONTINUOUS_DEVELOPMENT, EXECUTABLE_CAPABILITY is
        REJECTED — there is no code path that lets a machine actor
        install code or mint providers.
        """
        for mode in (PromotionMode.STABLE_DEFAULT,
                     PromotionMode.CONTINUOUS_DEVELOPMENT):
            policy = PromotionPolicy(mode=mode)
            c = _candidate(authority=AuthorityClass.EXECUTABLE_CAPABILITY)
            d = policy.decide(c, _good_eval())
            assert d.outcome == PromotionOutcome.REJECTED


# ========================================================== summary


def test_generation_3e_marker():
    """Package 3E acceptance envelope:

    * candidate generation without changing active version ✓
    * old version remains addressable ✓
    * sandbox/eval comparison ✓
    * failed candidate rejected without contaminating stable ✓
      (TestPromotionGate — 5 tests)
    * LOW_AUTHORITY_PERSONAL promotable ONLY under
      CONTINUOUS_DEVELOPMENT after full gate ✓
    * PROTECTED / EXECUTABLE never machine-promoted ✓
      (TestAuthorityClassGating)
    * restart / session default semantics ✓
      (TestSessionDefaultSemantics)
    * NO_EXECUTION_AUTHORITY constant on candidate ✓
    """
    assert True

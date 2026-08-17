"""G-BD.6 tests — runtime consumers of the G-BD.2 typed epistemic model.

Proves:

    * Scene DAG operations (fork_scene_branch, activate_branch) preserve
      trunk isolation.
    * emit_context_transduction enforces the §6.6 loss-report discipline
      structurally (TRANSDUCTION with no loss report raises).
    * check_cross_scope_access implements the four CrossScopePolicy modes
      correctly.
    * open_conflict enforces §6.7 (HOLD requires discriminator;
      ARBITRATE_ACTION requires action_arbitration).
    * render_passport surfaces held conflicts by default.
    * should_return_to_ordinary correctly detects the OP-18 clean state.
"""
from __future__ import annotations

import pytest

from socrates_runtime.epistemic_model import (
    ConflictFamily, ConflictHandlingMode, ConstructionStatus,
    CrossScopePolicy, MemoryValidityScope, MountMode, TransductionKind,
    WorldModelMount, EpistemicSpace, build_default_workspace_space,
)
from socrates_runtime.epistemic_ops import (
    activate_branch,
    check_cross_scope_access,
    emit_context_transduction,
    fork_scene_branch,
    open_conflict,
    render_passport,
    should_return_to_ordinary,
)
from socrates_runtime.state import PipelineState


@pytest.fixture()
def state():
    s = PipelineState(run_id="r1", input_text="hi")
    s.space_registry.register(build_default_workspace_space())
    return s


# ---------------------------------------------------------- Scene DAG


class TestSceneDAG:
    def test_fork_creates_sibling_branch_preserving_trunk(self, state):
        b1 = fork_scene_branch(state, hypothesis="X",
                                local_facts=("fact-x",))
        # Trunk pointer unchanged; branch is a sibling.
        assert state.branch_id == ""
        assert state.scene_id != ""
        assert b1.branch_id
        assert b1.scene_id == state.scene_id
        assert b1.hypothesis == "X"

    def test_two_incompatible_branches_do_not_contaminate(self, state):
        b1 = fork_scene_branch(state, hypothesis="X",
                                local_facts=("fact-x",))
        b2 = fork_scene_branch(state, hypothesis="Y",
                                local_facts=("fact-y",))
        # Same parent scene, different branches, different local facts.
        assert b1.scene_id == b2.scene_id
        assert b1.branch_id != b2.branch_id
        assert "fact-x" not in b2.local_facts
        assert "fact-y" not in b1.local_facts

    def test_activate_branch_sets_pointer(self, state):
        b = fork_scene_branch(state, hypothesis="X")
        activate_branch(state, b.branch_id)
        assert state.branch_id == b.branch_id


# ---------------------------------------------------------- transduction


class TestContextTransduction:
    def test_translation_without_loss_report_ok(self, state):
        rec = emit_context_transduction(
            state, kind=TransductionKind.TRANSLATION,
            preserved=("core",))
        assert rec.kind == TransductionKind.TRANSLATION

    def test_transduction_without_loss_report_raises(self, state):
        with pytest.raises(ValueError, match="TRANSDUCTION"):
            emit_context_transduction(
                state, kind=TransductionKind.TRANSDUCTION,
                preserved=("x",))

    def test_transduction_with_dropped_ok(self, state):
        rec = emit_context_transduction(
            state, kind=TransductionKind.TRANSDUCTION,
            preserved=("core",), dropped=("Z",),
            newly_created=("new medium object",),
            loss_report="Z dropped because target medium cannot carry")
        assert rec.dropped == ("Z",)
        assert state.context_transductions[-1] is rec

    def test_ontological_transfer_requires_change(self, state):
        with pytest.raises(ValueError, match="ONTOLOGICAL_TRANSFER"):
            emit_context_transduction(
                state, kind=TransductionKind.ONTOLOGICAL_TRANSFER,
                preserved=("x",))


# ---------------------------------------------------------- cross-scope


class TestCrossScopeAccess:
    def test_same_scope_always_allowed(self):
        allowed, reason = check_cross_scope_access(
            MemoryValidityScope.SCENE, MemoryValidityScope.SCENE,
            CrossScopePolicy.FORBID)
        assert allowed
        assert "same scope" in reason

    def test_forbid_denies(self):
        allowed, _ = check_cross_scope_access(
            MemoryValidityScope.BRANCH, MemoryValidityScope.PROJECT,
            CrossScopePolicy.FORBID)
        assert not allowed

    def test_require_explicit_bridge_denies_without_bridge(self):
        allowed, reason = check_cross_scope_access(
            MemoryValidityScope.BRANCH, MemoryValidityScope.PROJECT,
            CrossScopePolicy.REQUIRE_EXPLICIT_BRIDGE)
        assert not allowed
        assert "bridge" in reason

    def test_allow_readonly_permits(self):
        allowed, reason = check_cross_scope_access(
            MemoryValidityScope.SCENE, MemoryValidityScope.PROJECT,
            CrossScopePolicy.ALLOW_READONLY)
        assert allowed
        assert "read only" in reason

    def test_allow_with_transduction_permits(self):
        allowed, reason = check_cross_scope_access(
            MemoryValidityScope.SCENE, MemoryValidityScope.SPACE_OR_DOMAIN,
            CrossScopePolicy.ALLOW_WITH_TRANSDUCTION)
        assert allowed


# ---------------------------------------------------------- conflict


class TestOpenConflict:
    def test_hold_without_discriminator_raises(self, state):
        with pytest.raises(ValueError, match="HOLD"):
            open_conflict(state, family=ConflictFamily.ONTOLOGY,
                          handling_mode=ConflictHandlingMode.HOLD,
                          description="two grounded incompatible models")

    def test_hold_with_discriminator_ok(self, state):
        c = open_conflict(
            state, family=ConflictFamily.ONTOLOGY,
            handling_mode=ConflictHandlingMode.HOLD,
            description="two grounded incompatible models",
            discriminating_evidence_required=(
                "evidence that could falsify one",))
        assert c.family == ConflictFamily.ONTOLOGY
        assert c in state.conflict_registry.all()

    def test_arbitrate_action_requires_action_arbitration(self, state):
        with pytest.raises(ValueError, match="ARBITRATE_ACTION"):
            open_conflict(
                state, family=ConflictFamily.OPERATION,
                handling_mode=ConflictHandlingMode.ARBITRATE_ACTION,
                description="two operations disagree on next step")

    def test_reject_bypasses_both(self, state):
        c = open_conflict(
            state, family=ConflictFamily.IDENTITY_RULE,
            handling_mode=ConflictHandlingMode.REJECT,
            description="board seam transfer detected")
        assert c.handling_mode == ConflictHandlingMode.REJECT


# ---------------------------------------------------------- passport


class TestPassport:
    def test_passport_surfaces_held_conflicts_when_not_supplied(self, state):
        open_conflict(
            state, family=ConflictFamily.AUTHORITY,
            handling_mode=ConflictHandlingMode.HOLD,
            description="who owns this decision?",
            discriminating_evidence_required=("explicit user declaration",))
        p = render_passport(state, subject_object_id="obj_x",
                            construction_status=ConstructionStatus.HYBRID)
        assert any("AUTHORITY" in kc for kc in p.known_conflicts)

    def test_passport_respects_caller_supplied_conflicts(self, state):
        open_conflict(
            state, family=ConflictFamily.AUTHORITY,
            handling_mode=ConflictHandlingMode.HOLD,
            description="x", discriminating_evidence_required=("y",))
        p = render_passport(
            state, subject_object_id="obj_y",
            construction_status=ConstructionStatus.SOURCE_OWNED,
            known_conflicts=("caller-supplied",))
        # Caller-supplied list wins; automatic surfacing is a fallback.
        assert p.known_conflicts == ("caller-supplied",)

    def test_passport_records_current_space_scene_branch(self, state):
        b = fork_scene_branch(state, hypothesis="H")
        activate_branch(state, b.branch_id)
        p = render_passport(state, subject_object_id="obj_z")
        assert p.space_id == state.space_id
        assert p.scene_id == state.scene_id
        assert p.branch_id == b.branch_id

    def test_passport_exposes_no_upgrade_method(self):
        from socrates_runtime.epistemic_model import EpistemicPassport
        for meth in ("upgrade", "authorize", "activate",
                     "commit", "install"):
            assert not hasattr(EpistemicPassport, meth)


# ---------------------------------------------------------- return-to-ordinary


class TestReturnToOrdinary:
    def test_clean_state_returns_to_ordinary(self, state):
        assert should_return_to_ordinary(state)

    def test_pending_diagnostic_blocks(self, state):
        from socrates_runtime.projection import (
            ProjectionDiagnostics, DiagnosticSignal)
        state.pending_diagnostic = ProjectionDiagnostics(
            projection_id="p", signals=(DiagnosticSignal.OPERATION_MISMATCH,),
            reason="", residue_ratio=0.5, recognition_failure_count=1)
        assert not should_return_to_ordinary(state)

    def test_held_conflict_blocks(self, state):
        open_conflict(
            state, family=ConflictFamily.VALUE,
            handling_mode=ConflictHandlingMode.HOLD,
            description="values disagree",
            discriminating_evidence_required=("evidence x",))
        assert not should_return_to_ordinary(state)

    def test_active_branch_blocks(self, state):
        b = fork_scene_branch(state, hypothesis="X")
        activate_branch(state, b.branch_id)
        assert not should_return_to_ordinary(state)

    def test_transduction_blocks(self, state):
        emit_context_transduction(
            state, kind=TransductionKind.TRANSLATION, preserved=("x",))
        assert not should_return_to_ordinary(state)

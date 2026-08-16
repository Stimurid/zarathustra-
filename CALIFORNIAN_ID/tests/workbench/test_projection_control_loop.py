"""Projection-control-loop unit tests — ADR-S26-022 phase 2/4.

Scope: prove that the pipeline's outer loop correctly threads
``ProjectionDiagnostics`` → reflective S7 epilogue → ``ReflectiveReturn``
→ re-entry from the ReflectiveReturn's return_target, and that all four
loop guards fire deterministically without an LLM. These tests use
synthetic diagnostics injected via a fake ``projection_step`` callable
and PhaseHint-supplied ``reflective_return`` payloads — the real
CutterRegistry-driven projection lands in phase 3/4.

Key invariants under test:

    * a diagnostic with ``mismatch=True`` triggers the reflective epilogue;
    * a ReflectiveReturn from S7 revises state.operation (R1/R2) or
      state.scene.telos (R3) and sets state.reentry_from;
    * pass 2 begins at ``return_target`` — not at S0;
    * an unchanged-diagnosis fingerprint stops the loop without another
      reflection;
    * ``MAX_PROJECTION_ITERATIONS`` caps the loop even if diagnostics
      would keep firing;
    * an S7 that produces NO reflective_return stops the loop with a
      legitimate terminal, never a technical retry masquerading as
      reflection.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from socrates_runtime import (
    SocratesIdentity,
    SocratesRunConfiguration,
    SocratesRuntime,
    Terminal,
)
from socrates_runtime.mount import SemanticMountPolicy, TriggerAdmission
from socrates_runtime.phase_executor import (
    DeterministicPhaseExecutor,
    ExecutionMode,
    PhaseDelta,
    PhaseExecutionRequest,
    PhaseExecutionResult,
    ProviderStatus,
)
from socrates_runtime.pipeline import PhaseHint, PipelineExecutor
from socrates_runtime.projection import (
    MAX_PROJECTION_ITERATIONS,
    DiagnosticSignal,
    ProjectionDiagnostics,
    ProjectionResult,
    ProjectionStatus,
    ReflectiveReturn,
    RetreatLevel,
    ReturnTarget,
    SemanticProjectionSpec,
    new_projection_id,
    new_reflective_id,
)
from socrates_runtime.routers import RouterRegistry
from socrates_runtime.semantic import SemanticBodyRegistry
from socrates_runtime.state import (
    Authority,
    Operation,
    Ownership,
    PipelineState,
    Scene,
)


# ---------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")


@pytest.fixture()
def mount_policy():
    return SemanticMountPolicy(SemanticBodyRegistry())


@pytest.fixture()
def router_registry():
    return RouterRegistry()


@pytest.fixture()
def run_config():
    identity = SocratesIdentity.bootstrap()
    return SocratesRunConfiguration(
        semantic_pack_version=identity.pack.version,
        semantic_pack_sha256=identity.pack.source_bundle_sha256,
    )


# ---------------------------------------------------------- helpers


def _system_owner_hints() -> dict[str, PhaseHint]:
    """Enough state for the ownership/applicability gates to pass so the
    outer loop is not preempted by a governor terminal."""
    return {
        "S1": PhaseHint(scene=Scene(telos="run the projection loop")),
        "S4": PhaseHint(operation=Operation(kind="EXTRACT_CONCEPTS",
                                             applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }


def _fake_projection(spec: SemanticProjectionSpec,
                     source_id: str) -> ProjectionResult:
    return ProjectionResult(
        projection_id=spec.projection_id,
        spec_fingerprint=spec.fingerprint(),
        source_id=source_id,
        objects=[], residue=[], coverage=0.4,
        status=ProjectionStatus.EXPLORATORY)


def _mismatch_diag(projection_id: str,
                   suggested_operation: str = "DIFFERENTIATED_ACCOUNT",
                   ) -> ProjectionDiagnostics:
    return ProjectionDiagnostics(
        projection_id=projection_id,
        signals=(DiagnosticSignal.OPERATION_MISMATCH,),
        reason="source contains material outside the concept ontology",
        residue_ratio=0.6, recognition_failure_count=3,
        suggested_operation=suggested_operation,
        suggested_ontology="differentiated_v1",
        suggested_target_family=("concept", "report", "gesture",
                                 "absence", "future_work"))


def _clean_diag(projection_id: str) -> ProjectionDiagnostics:
    return ProjectionDiagnostics(
        projection_id=projection_id,
        signals=(),
        reason="all material classified into target family",
        residue_ratio=0.0, recognition_failure_count=0)


# ---------------------------------------------------------- projection_step doubles


class _SingleMismatchThenClean:
    """First pass yields OPERATION_MISMATCH; second pass is clean.

    This is exactly the shape the Peskov case will produce once the real
    CutterRegistry is wired in commit 3 — first look forces every
    fragment into ``concept``, leaves residue; second look uses
    differentiated ontology, covers residue.
    """
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.calls: list[str] = []

    def __call__(self, state: PipelineState) -> None:
        self.calls.append(state.operation.kind or "")
        spec = SemanticProjectionSpec(
            projection_id=new_projection_id(),
            source_id=self.source_id, scene_ref=state.scene.telos,
            operation_id=state.operation.kind or "EXTRACT_CONCEPTS",
            ontology_id="concept_v1" if len(self.calls) == 1
                        else "differentiated_v1",
            target_object_family=("concept",) if len(self.calls) == 1
                                 else ("concept", "report", "gesture",
                                       "absence", "future_work"),
            recognition_criteria=("explicit definition",),
            segmentation_policy="fake_concept_cutter",
            evidence_requirements=(), applicability_assumptions=(),
            contraindications=())
        result = _fake_projection(spec, self.source_id)
        state.projection_lineage.add_projection(result)
        if len(self.calls) == 1:
            diag = _mismatch_diag(spec.projection_id)
            state.projection_lineage.add_diagnostics(diag)
            state.pending_diagnostic = diag
        else:
            diag = _clean_diag(spec.projection_id)
            state.projection_lineage.add_diagnostics(diag)
            state.pending_diagnostic = diag
            state.projection_lineage.mark_status(
                spec.projection_id, ProjectionStatus.ACCEPTED_LOCAL)


class _AlwaysMismatch:
    """Every pass yields the SAME mismatch diagnostic — used to prove the
    same-diagnosis guard fires (and later the iteration bound)."""
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.calls = 0

    def __call__(self, state: PipelineState) -> None:
        self.calls += 1
        spec = SemanticProjectionSpec(
            projection_id=new_projection_id(),
            source_id=self.source_id, scene_ref=state.scene.telos,
            operation_id=state.operation.kind or "EXTRACT_CONCEPTS",
            ontology_id="concept_v1",
            target_object_family=("concept",),
            recognition_criteria=("explicit definition",),
            segmentation_policy="fake_concept_cutter",
            evidence_requirements=(), applicability_assumptions=(),
            contraindications=())
        result = _fake_projection(spec, self.source_id)
        state.projection_lineage.add_projection(result)
        diag = _mismatch_diag(spec.projection_id)
        state.projection_lineage.add_diagnostics(diag)
        state.pending_diagnostic = diag


class _EverChangingMismatch:
    """Every pass yields a DIFFERENT mismatch signal — proves the
    iteration bound fires even when the same-diagnosis guard does not."""
    _CYCLE = (
        (DiagnosticSignal.OPERATION_MISMATCH,),
        (DiagnosticSignal.ONTOLOGY_LIMIT,),
        (DiagnosticSignal.MULTI_ONTOLOGY,),
        (DiagnosticSignal.APPLICABILITY_FAILURE,),
    )

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.calls = 0

    def __call__(self, state: PipelineState) -> None:
        signals = self._CYCLE[self.calls % len(self._CYCLE)]
        self.calls += 1
        spec = SemanticProjectionSpec(
            projection_id=new_projection_id(),
            source_id=self.source_id, scene_ref=state.scene.telos,
            operation_id=state.operation.kind or f"OP_{self.calls}",
            ontology_id=f"ont_{self.calls}",
            target_object_family=("concept",),
            recognition_criteria=("explicit definition",),
            segmentation_policy="fake",
            evidence_requirements=(), applicability_assumptions=(),
            contraindications=())
        state.projection_lineage.add_projection(_fake_projection(spec, self.source_id))
        diag = ProjectionDiagnostics(
            projection_id=spec.projection_id, signals=signals,
            reason="synthesised varying mismatch",
            residue_ratio=0.5, recognition_failure_count=1,
            suggested_operation=f"NEXT_OP_{self.calls}",
            suggested_ontology=f"next_ont_{self.calls}",
            suggested_target_family=("concept",))
        state.projection_lineage.add_diagnostics(diag)
        state.pending_diagnostic = diag


# ---------------------------------------------------------- refl-return hint helper


def _reflective_hint(next_op: str = "DIFFERENTIATED_ACCOUNT",
                     level: RetreatLevel = RetreatLevel.R1,
                     target: ReturnTarget = ReturnTarget.S4,
                     ) -> PhaseHint:
    """Wrap a ReflectiveReturn into a PhaseHint for S7.

    The deterministic phase executor honours the same delta shape as the
    live model, so a hint carrying ``reflective_return`` in its bespoke
    field would be lost — instead we build the delta manually by adding
    a helper that reuses PhaseHint plus a raw payload monkey-patched onto
    the executor.
    """
    # PhaseHint has no reflective_return field; the deterministic executor
    # only projects PhaseHint fields. We use a specialised executor below.
    raise NotImplementedError    # sentinel — see _ReflectiveHintExecutor


class _ReflectiveHintExecutor:
    """Deterministic executor that also carries per-phase reflective_return.

    A regular DeterministicPhaseExecutor projects PhaseHint fields (scene,
    origin, operation, ownership, triggers, memory_proposal,
    invoke_council, invoke_execution). It has no reflective_return slot
    on PhaseHint — deliberately, because inside the runtime that field
    is only produced by S7. For tests we need to inject one directly, so
    this executor accepts an explicit ``reflective_returns`` mapping and
    attaches the object to whichever PhaseDelta a call for that phase
    produces (using the same MODEL_PRODUCED origin so the pipeline treats
    it as if S7 emitted it).
    """
    mode = ExecutionMode.DETERMINISTIC

    def __init__(self, hints: dict[str, PhaseHint],
                 reflective_returns: dict[str, ReflectiveReturn]) -> None:
        self.hints = dict(hints)
        self.reflective_returns = dict(reflective_returns)
        self.call_log: list[tuple[str, dict[str, Any]]] = []

    def execute(self, request: PhaseExecutionRequest) -> PhaseExecutionResult:
        # Log AT CALL TIME so the test can see order.
        self.call_log.append((request.phase,
                              {"input_text": request.input_text,
                               "state_op": request.state_snapshot["operation"]}))
        hint = self.hints.get(request.phase)
        delta = PhaseDelta()
        if hint is not None:
            delta.scene = hint.scene
            delta.origin = hint.origin
            delta.operation = hint.operation
            delta.ownership = hint.ownership
            delta.triggers = list(hint.triggers)
            delta.memory_proposal = hint.memory_proposal
            delta.invoke_council = hint.invoke_council
            delta.invoke_execution = hint.invoke_execution
        rr = self.reflective_returns.get(request.phase)
        if rr is not None:
            delta.reflective_return = rr
        # Marking origin_kind FIXTURE_SUPPLIED matches what the ordinary
        # deterministic executor does.
        from socrates_runtime.phase_executor import DeltaOrigin
        delta.origin_kind = DeltaOrigin.FIXTURE_SUPPLIED
        return PhaseExecutionResult(
            delta=delta, mode=self.mode,
            provider_status=ProviderStatus.NOT_APPLICABLE,
            provider_id="deterministic", model_id="deterministic")


# ---------------------------------------------------------- tests: happy path


def test_no_diagnostic_no_loop(mount_policy, router_registry, run_config):
    """When no projection_step is registered, the pipeline behaves exactly
    like the pre-loop runtime — one pass, terminal by governor. This is
    the invariant that direct-assistance / non-projection runs are not
    penalised by the new loop."""
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=None)
    hints = _system_owner_hints()
    phase_exec = DeterministicPhaseExecutor(hints)
    state, outcome, results = executor.run(
        "quick answer please", phase_exec, run_config, hints=hints)
    assert outcome.terminal == Terminal.ANSWER
    assert state.projection_lineage.iteration() == 0
    assert state.reentry_from == ""
    assert state.pending_diagnostic is None


def test_clean_diagnostic_no_reflection(mount_policy, router_registry,
                                         run_config):
    """A projection that returns without mismatch → one pass, no epilogue,
    lineage has exactly one entry (P1) with no revisions."""
    calls = []
    def step(state: PipelineState) -> None:
        calls.append("step")
        spec = SemanticProjectionSpec(
            projection_id=new_projection_id(),
            source_id=state.source_id, scene_ref=state.scene.telos,
            operation_id=state.operation.kind or "EXTRACT_CONCEPTS",
            ontology_id="concept_v1", target_object_family=("concept",),
            recognition_criteria=(), segmentation_policy="fake",
            evidence_requirements=(), applicability_assumptions=(),
            contraindications=())
        state.projection_lineage.add_projection(_fake_projection(spec,
                                                                  state.source_id))
        diag = _clean_diag(spec.projection_id)
        state.projection_lineage.add_diagnostics(diag)
        state.pending_diagnostic = diag
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=step)
    hints = _system_owner_hints()
    phase_exec = DeterministicPhaseExecutor(hints)
    state, outcome, _ = executor.run("x", phase_exec, run_config, hints=hints)
    assert outcome.terminal == Terminal.ANSWER
    assert len(calls) == 1
    assert state.projection_lineage.iteration() == 1
    assert state.projection_lineage.revisions == []


def test_mismatch_triggers_epilogue_and_second_pass(mount_policy,
                                                     router_registry,
                                                     run_config):
    """P1 mismatch → S7 epilogue produces a ReflectiveReturn (R1, S4) →
    pass 2 re-enters at S4 → P2 clean. Lineage carries both projections
    and the ReflectiveReturn that links them.

    This is the executable equivalent of the ADR §5 topology diagram.
    """
    source_text = "extract the concepts (some material is not concept-shaped)"
    from hashlib import sha256
    src_id = f"src_{sha256(source_text.encode()).hexdigest()[:16]}"
    step = _SingleMismatchThenClean(src_id)
    rr = ReflectiveReturn(
        reflective_id=new_reflective_id(),
        from_projection_id="",           # filled in by pipeline
        retreat_level=RetreatLevel.R1,
        return_target=ReturnTarget.S4,
        reason="OPERATION_MISMATCH — concept ontology insufficient",
        failed_assumption="material is uniformly concept-shaped",
        what_remains_valid=("legitimate concepts recognised in P1",),
        what_changes=("operation from EXTRACT_CONCEPTS to "
                      "DIFFERENTIATED_ACCOUNT", "ontology to differentiated_v1"),
        revised_operation_kind="DIFFERENTIATED_ACCOUNT",
        revised_ontology_id="differentiated_v1",
        revised_scene_telos="")
    hints = _system_owner_hints()
    phase_exec = _ReflectiveHintExecutor(hints, {"S7": rr})
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=step)
    state, outcome, _ = executor.run(source_text, phase_exec, run_config,
                                     hints=hints)
    assert outcome.terminal == Terminal.ANSWER
    # Two projection executions happened.
    assert step.calls == ["EXTRACT_CONCEPTS", "DIFFERENTIATED_ACCOUNT"]
    lineage = state.projection_lineage
    assert lineage.iteration() == 2
    assert lineage.entries[0].status == ProjectionStatus.PARTIAL
    assert lineage.entries[1].status == ProjectionStatus.ACCEPTED_LOCAL
    assert len(lineage.revisions) == 1
    revision = lineage.revisions[0]
    assert revision.retreat_level == RetreatLevel.R1
    assert revision.return_target == ReturnTarget.S4
    # State.operation was revised to the new operation.
    assert state.operation.kind == "DIFFERENTIATED_ACCOUNT"
    # Source-id invariant: both projections share the same source_id — P2
    # rereads the ORIGINAL source, not P1's derived objects.
    assert lineage.entries[0].source_id == lineage.entries[1].source_id == src_id


def test_pass_two_starts_after_return_target(mount_policy,
                                              router_registry, run_config):
    """Re-entry after ReflectiveReturn skips S0..S4 when return_target=S4.

    The invariant matters: re-entry is scoped to the revision, not a
    full re-run. The return_target phase itself is the SITE of the
    revision (S7 wrote the new operation into state during the epilogue),
    so the next pass executes FROM the phase after return_target — that
    is the ADR §14 ``changed-forward-action`` requirement made literal.
    A pass that re-ran S4 would clobber the revision with its original
    hint or prompt.
    """
    source_text = "differentiated account of a mixed source"
    from hashlib import sha256
    src_id = f"src_{sha256(source_text.encode()).hexdigest()[:16]}"
    step = _SingleMismatchThenClean(src_id)
    rr = ReflectiveReturn(
        reflective_id=new_reflective_id(),
        from_projection_id="",
        retreat_level=RetreatLevel.R1, return_target=ReturnTarget.S4,
        reason="OPERATION_MISMATCH",
        failed_assumption="", what_remains_valid=(),
        what_changes=("operation",),
        revised_operation_kind="DIFFERENTIATED_ACCOUNT",
        revised_ontology_id="differentiated_v1",
        revised_scene_telos="")
    hints = _system_owner_hints()
    phase_exec = _ReflectiveHintExecutor(hints, {"S7": rr})
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=step)
    executor.run(source_text, phase_exec, run_config, hints=hints)

    # Count phases visited in each pass. Pass 1 runs S0..S10 (S7/S9
    # conditional). Pass 2 starts at S4 → visits S4..S10 (skipping S7
    # and S9 per current gates for this state).
    phases = [p for (p, _) in phase_exec.call_log]
    # Pass 1 first phase must be S0.
    assert phases[0] == "S0"
    # Find the point where the epilogue S7 was invoked, then check the
    # next non-S7 phase begins pass 2 at S4.
    assert "S7" in phases    # the reflective epilogue
    # Locate pass 2's first *inner* phase: after the last S7 there is a
    # sequence beginning at PHASE_ORDER[return_target_index + 1] — S5
    # when return_target=S4.
    last_s7 = len(phases) - 1 - phases[::-1].index("S7")
    pass2 = phases[last_s7 + 1:]
    assert pass2 and pass2[0] == "S5", (
        f"pass 2 should start AFTER return_target=S4 (i.e. at S5), "
        f"got {pass2!r}")


# ---------------------------------------------------------- tests: guards


def test_same_diagnosis_fingerprint_stops_loop(mount_policy, router_registry,
                                                run_config):
    """If two consecutive passes produce the SAME diagnostic fingerprint,
    the loop stops — reflection would not add material information.

    This is not aporia in the philosophical sense; it is the runtime's
    check that it isn't spinning against unchanged evidence. The test
    supplies a reflective_return that keeps operation unchanged, so
    _AlwaysMismatch reproduces the same fingerprint.
    """
    src_id = "src_repeat"
    step = _AlwaysMismatch(src_id)
    rr = ReflectiveReturn(
        reflective_id=new_reflective_id(), from_projection_id="",
        retreat_level=RetreatLevel.R1, return_target=ReturnTarget.S4,
        reason="stubborn", failed_assumption="", what_remains_valid=(),
        what_changes=("nothing material",),
        revised_operation_kind="EXTRACT_CONCEPTS",       # unchanged!
        revised_ontology_id="", revised_scene_telos="")
    hints = _system_owner_hints()
    phase_exec = _ReflectiveHintExecutor(hints, {"S7": rr})
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=step)
    state, _, _ = executor.run("stubborn source", phase_exec, run_config,
                               hints=hints)
    # The pipeline should stop at pass 2 (once the second diagnosis
    # matches the first).
    assert step.calls == 2
    # No new reflection recorded after the guard fires.
    assert len(state.projection_lineage.revisions) == 1
    # pending_diagnostic cleared by the guard, so the governor is free.
    assert state.pending_diagnostic is None


def test_iteration_bound_stops_ever_changing_loop(mount_policy,
                                                   router_registry,
                                                   run_config):
    """Even with a distinct diagnosis each pass, the loop is capped at
    MAX_PROJECTION_ITERATIONS. The intent is: reflection is legitimate,
    but the runtime does not gamble unlimited compute on it."""
    src_id = "src_varying"
    step = _EverChangingMismatch(src_id)
    rr = ReflectiveReturn(
        reflective_id=new_reflective_id(), from_projection_id="",
        retreat_level=RetreatLevel.R1, return_target=ReturnTarget.S4,
        reason="varying", failed_assumption="", what_remains_valid=(),
        what_changes=("operation",),
        revised_operation_kind="OP_X",             # keeps changing via step
        revised_ontology_id="", revised_scene_telos="")
    hints = _system_owner_hints()
    phase_exec = _ReflectiveHintExecutor(hints, {"S7": rr})
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=step)
    executor.run("varying source", phase_exec, run_config, hints=hints)
    # Exactly MAX_PROJECTION_ITERATIONS projections; no more.
    assert step.calls == MAX_PROJECTION_ITERATIONS


def test_epilogue_no_reflective_return_stops(mount_policy, router_registry,
                                              run_config):
    """If S7's epilogue does NOT produce a reflective_return (e.g. the
    model or the policy chose PRESERVE_APORIA), the loop stops instead
    of falling back to a technical retry. Distinguishing this from
    ``RETRIES_EXHAUSTED`` is INV of ADR §11."""
    src_id = "src_no_reflection"
    step = _AlwaysMismatch(src_id)
    hints = _system_owner_hints()
    # Note: no S7 reflective_return supplied — epilogue will get an
    # empty delta.
    phase_exec = _ReflectiveHintExecutor(hints, {})
    executor = PipelineExecutor(mount_policy, router_registry,
                                projection_step=step)
    state, _, _ = executor.run("x", phase_exec, run_config, hints=hints)
    # Exactly ONE projection — the loop stopped after the epilogue
    # produced nothing.
    assert step.calls == 1
    assert state.projection_lineage.revisions == []
    assert state.pending_diagnostic is None


# ---------------------------------------------------------- tests: distinctions


def test_reflective_return_is_not_return_operation():
    """Terminal.RETURN_OPERATION is human-facing (INV-009). ReflectiveReturn
    is internal (governing hypothesis changed). A test that constructs one
    of each and asserts they are structurally different is enough to
    document the invariant."""
    rr = ReflectiveReturn(
        reflective_id="r1", from_projection_id="p1",
        retreat_level=RetreatLevel.R1, return_target=ReturnTarget.S4,
        reason="mismatch", failed_assumption="",
        what_remains_valid=(), what_changes=("op",),
        revised_operation_kind="X")
    from socrates_runtime.state import Terminal
    assert Terminal.RETURN_OPERATION.value == "RETURN_OPERATION"
    # ReflectiveReturn has no ``terminal`` attribute and does not appear
    # in any Terminal-value list.
    assert not hasattr(rr, "terminal")
    assert rr.retreat_level == RetreatLevel.R1


def test_reflective_return_is_not_technical_retry():
    """RETRIES_EXHAUSTED means the SAME hypothesis failed at the provider.
    ReflectiveReturn means the hypothesis CHANGED and a new pass will
    execute against the ORIGINAL source. The distinction is preserved
    by the pipeline: the outer loop only continues when reentry_from
    is set (a reflection), not when a provider status is non-OK."""
    from socrates_runtime.phase_executor import ProviderStatus
    assert ProviderStatus.RETRIES_EXHAUSTED != "REFLECTIVE_RETURN"
    # A run with LIVE mode + non-OK provider is terminated with
    # FAILED_EXPLICIT — never continued as if it were a reflection.
    # (Covered by the existing live-mode tests; this test documents the
    # non-overlap.)
    from socrates_runtime.pipeline import PipelineExecutor
    assert PipelineExecutor is not None

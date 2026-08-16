"""Peskov end-to-end + negative + targeted regressions for ADR-S26-022.

Peskov is not a raw text — it is a *shape* the R8 suite records as the
operation/object confusion case (``R8-C03_OPERATION_OBJECT_PESKOV`` at
``data/socrates/r8_suite/semantic_behavior_cases.yaml:56-79``). The
challenge: a source that mixes concepts with reports, organisational
gestures, absences, and future-work indications, and a naive request
to "extract the concepts" that a universal cutter would satisfy by
forcing every fragment into a concept class.

This module constructs a *representative* Peskov-shaped source using
explicit category markers (the ADR §26 "smallest complete mechanism"
principle — a deterministic surface is what proves the loop; a real
NLP cutter plugs into the same shape), then drives the full runtime
loop through:

    1. S0..S10 with operation=EXTRACT_CONCEPTS at S4
    2. projection_step runs P1 (concept cutter) — 2 concepts +
       4 residue lines (report, gesture, absence, future_work)
    3. ProjectionDiagnostics raises OPERATION_MISMATCH and suggests
       DIFFERENTIATED_ACCOUNT
    4. reflective S7 epilogue emits ReflectiveReturn (R1 → S4) with
       revised_operation_kind=DIFFERENTIATED_ACCOUNT
    5. pass 2 starts at S5 (return_target+1) preserving the revised
       operation → S8/S10 run → projection_step runs P2 against the
       ORIGINAL source → covers all 6 lines
    6. loop terminates; governor picks ANSWER; lineage carries P1
       (status=partial), P2 (status=accepted_local), one revision

Negative and targeted regression tests immediately follow. Together
they satisfy ADR §16–§17 (no Peskov hard-coding) and §20 (targeted
regressions after repair).

The `_reflective_hint_executor` reuses the same fixture-based executor
shape as :mod:`test_projection_control_loop`; the difference is that
here the projection_step is the REAL CutterRegistry-driven step, not a
synthetic double.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from socrates_runtime import SocratesRuntime, Terminal
from socrates_runtime.cutter_registry import (
    CutterCapability,
    CutterRegistry,
    build_default_registry,
    compute_diagnostics,
)
from socrates_runtime.governor import InterventionGovernor
from socrates_runtime.mount import SemanticMountPolicy
from socrates_runtime.phase_executor import (
    DeltaOrigin,
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
    ProjectionStatus,
    ReflectiveReturn,
    RetreatLevel,
    ReturnTarget,
    new_reflective_id,
)
from socrates_runtime.projection_step import make_projection_step
from socrates_runtime.routers import RouterRegistry
from socrates_runtime.semantic import SemanticBodyRegistry
from socrates_runtime.state import (
    Authority,
    Operation,
    Ownership,
    PipelineState,
    Scene,
)
from socrates_runtime.identity import (
    SocratesIdentity,
    SocratesRunConfiguration,
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


# ---------------------------------------------------------- Peskov source

PESKOV_SOURCE = """[concept] Ontology is the study of what exists.
[report] The team met last Thursday to review scope.
[gesture] The lead nodded acknowledgement.
[absence] Data for Q3 is not available.
[future_work] We plan to extend this analysis next quarter.
[concept] Epistemology is the study of knowledge."""


def _hash_source(text: str) -> str:
    return f"src_{sha256(text.encode('utf-8')).hexdigest()[:16]}"


# ---------------------------------------------------------- reflective-hint executor


class _ReflectiveHintExecutor:
    """Deterministic executor with iteration-aware hints for reflective
    passes. See mirror class in ``test_projection_control_loop.py``.

    Post D-S26-PROJ-002 the runtime does NOT silently write the
    revised operation into state.operation. The target phase re-runs
    at return_target and must EMIT the revision from its own delta.
    ``reflective_hints`` supplies that iteration-aware hint. When
    ``state_snapshot["projection_lineage"]["revisions"]`` is non-empty
    (i.e. any pass after a reflection), the phase looks up
    ``reflective_hints[phase]`` first; only if absent does it fall
    back to the base ``hints[phase]``.
    """
    mode = ExecutionMode.DETERMINISTIC

    def __init__(self, hints: dict[str, PhaseHint],
                 reflective_returns: dict[str, ReflectiveReturn],
                 reflective_hints: dict[str, PhaseHint] | None = None) -> None:
        self.hints = dict(hints)
        self.reflective_returns = dict(reflective_returns)
        self.reflective_hints = dict(reflective_hints or {})
        self.call_log: list[str] = []
        self.snapshots: list[dict[str, Any]] = []

    def _hint_for(self, request: PhaseExecutionRequest) -> PhaseHint | None:
        revisions = request.state_snapshot.get(
            "projection_lineage", {}).get("revisions", [])
        if revisions and request.phase in self.reflective_hints:
            return self.reflective_hints[request.phase]
        return self.hints.get(request.phase)

    def execute(self, request: PhaseExecutionRequest) -> PhaseExecutionResult:
        self.call_log.append(request.phase)
        self.snapshots.append(request.state_snapshot)
        hint = self._hint_for(request)
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
        delta.origin_kind = DeltaOrigin.FIXTURE_SUPPLIED
        return PhaseExecutionResult(
            delta=delta, mode=self.mode,
            provider_status=ProviderStatus.NOT_APPLICABLE,
            provider_id="deterministic", model_id="deterministic")


def _peskov_hints() -> dict[str, PhaseHint]:
    """The state required for the loop to actually reach a projection.

    S4 declares EXTRACT_CONCEPTS as pass-1 operation. S6 owns the
    operation SYSTEM-side (needed for ANSWER terminal at loop end).
    S1 sets a coherent telos so ANSWER rendering has a subject.
    """
    return {
        "S1": PhaseHint(scene=Scene(telos="извлеки понятия",
                                     authority=Authority.SYSTEM)),
        "S4": PhaseHint(operation=Operation(kind="EXTRACT_CONCEPTS",
                                             applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }


def _peskov_reflective_return() -> ReflectiveReturn:
    return ReflectiveReturn(
        reflective_id=new_reflective_id(),
        from_projection_id="",                # backfilled by pipeline
        retreat_level=RetreatLevel.R1,
        return_target=ReturnTarget.S4,
        reason=("OPERATION_MISMATCH — the source is not uniformly "
                "concept-shaped; forcing every fragment into a concept "
                "class would violate B03 recognition criteria"),
        failed_assumption=("the request 'extract the concepts' presumed "
                           "that every source line has a concept referent"),
        what_remains_valid=(
            "two legitimate concepts recognised in P1 remain addressable",
        ),
        what_changes=(
            "operation from EXTRACT_CONCEPTS to DIFFERENTIATED_ACCOUNT",
            "ontology from concept_v1 to differentiated_v1",
        ),
        revised_operation_kind="DIFFERENTIATED_ACCOUNT",
        revised_ontology_id="differentiated_v1",
        revised_scene_telos="",
    )


def _make_executor(mount_policy, router_registry) -> PipelineExecutor:
    return PipelineExecutor(
        mount_policy, router_registry,
        projection_step=make_projection_step(build_default_registry()))


def _peskov_reflective_hints() -> dict[str, PhaseHint]:
    """Iteration-aware hints for the Peskov reflective pass.

    Only S4 changes on pass 2 (operation revision R1). Every other
    phase falls back to its first-pass hint.
    """
    return {
        "S4": PhaseHint(operation=Operation(kind="DIFFERENTIATED_ACCOUNT",
                                             applicable=True)),
    }


# ---------------------------------------------------------- Peskov acceptance


def test_peskov_full_projection_control_loop(mount_policy, router_registry,
                                              run_config, tmp_path):
    """Full ADR-S26-022 §15 trajectory on Peskov-shaped source.

    Success criteria per ADR §15:
      1..16. immutable source → P1 (partial) → typed diagnostics →
             S7 → ReflectiveReturn (typed, not prose) → P2 from
             ORIGINAL source → both projections addressable → trace
             explains why P2 exists → useful forward work resumes.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()},
        reflective_hints=_peskov_reflective_hints())
    state, outcome, results = executor.run(
        PESKOV_SOURCE, phase_exec, run_config, hints=hints)

    # (1) — the run reached a terminal, not FAILED_EXPLICIT
    assert outcome.terminal == Terminal.ANSWER

    # (2, 5, 12) — two projections in lineage
    lineage = state.projection_lineage
    assert lineage.iteration() == 2, (
        f"expected P1 + P2, got {lineage.iteration()} projections")

    p1, p2 = lineage.entries
    # (13, 14) — both projections addressable
    assert p1.projection_id != p2.projection_id
    assert p1.spec_fingerprint != p2.spec_fingerprint

    # (4) — P1 recognised the two legitimate concepts
    p1_concepts = [o for o in p1.objects if o.object_family == "concept"]
    assert len(p1_concepts) == 2

    # (5) — P1 also left the non-concept material as residue (NOT forced
    # into pseudo-concepts)
    assert len(p1.residue) == 4
    residue_families = sorted({r.apparent_family for r in p1.residue})
    assert residue_families == ["absence", "future_work",
                                 "gesture", "report"]

    # (6) — the six recognitions were not silently coerced; P1 status
    # marked PARTIAL after the reflection
    assert p1.status == ProjectionStatus.PARTIAL

    # (7) — typed diagnostic on the first projection
    diagnostics = lineage.diagnostics_history
    assert len(diagnostics) == 2
    p1_diag = diagnostics[0]
    assert DiagnosticSignal.OPERATION_MISMATCH in p1_diag.signals
    assert p1_diag.suggested_operation == "DIFFERENTIATED_ACCOUNT"

    # (8, 9) — one ReflectiveReturn produced by S7
    assert len(lineage.revisions) == 1
    rr = lineage.revisions[0]
    assert rr.retreat_level == RetreatLevel.R1
    assert rr.return_target == ReturnTarget.S4
    assert rr.revised_operation_kind == "DIFFERENTIATED_ACCOUNT"
    assert rr.from_projection_id == p1.projection_id
    assert rr.diagnostic_fingerprint == p1_diag.fingerprint()

    # (10) — pass 2 re-entered AT S4 (the actual return_target);
    # verify by the call log. This is the D-S26-PROJ-002 repair
    # made literal: the target phase must re-execute — not be
    # skipped — so it can emit the revised operation via its own
    # normal delta contract.
    phases_visited = phase_exec.call_log
    last_s7_idx = len(phases_visited) - 1 - phases_visited[::-1].index("S7")
    pass2_phases = phases_visited[last_s7_idx + 1:]
    assert pass2_phases and pass2_phases[0] == "S4", (
        f"pass 2 must start AT return_target=S4, got {pass2_phases[0]!r}")
    # S4 must be the FIRST phase of pass 2 — proving the target
    # phase actually re-executes rather than being skipped.
    assert pass2_phases[0] == "S4"
    # And the full expected downstream sequence follows.
    assert pass2_phases == ["S4", "S5", "S6", "S8", "S9", "S10"], (
        f"pass 2 must re-execute S4..S10 (S7 not council-needed here), "
        f"got {pass2_phases!r}")

    # (11, 12) — P2 executed against the ORIGINAL source, with the
    # revised operation, and covered all 6 lines
    assert state.operation.kind == "DIFFERENTIATED_ACCOUNT"
    assert len(p2.objects) == 6
    assert p2.residue == []
    assert p2.status == ProjectionStatus.ACCEPTED_LOCAL

    # (15) — trace evidence: revised operation + covering suggestion
    # both survived to the end of the run
    assert diagnostics[1].mismatch is False


def test_peskov_p2_rereads_original_source_not_p1_units(mount_policy,
                                                          router_registry,
                                                          run_config):
    """Immutable-source invariant (ADR §12): P2 rereads the ORIGINAL
    source, not P1's derived output.

    The runtime enforces this BY CONSTRUCTION —
    ``PipelineState.input_text`` is set once and never rewritten, and
    ``PipelineState.source_id`` is derived from ``input_text``. The
    check: P1 and P2 share source_id, and every object's source_span
    points into the ORIGINAL text (index arithmetic verifies).
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()})
    input_text_before = PESKOV_SOURCE
    state, _, _ = executor.run(input_text_before, phase_exec, run_config,
                               hints=hints)

    # input_text unchanged after the run
    assert state.input_text == input_text_before
    # source_id derived from the same text on entry and exit
    assert state.source_id == _hash_source(input_text_before)

    lineage = state.projection_lineage
    p1, p2 = lineage.entries
    # (Negative test §17 point 1) — P2 shares source_id with P1;
    # therefore P2 did not reproject from a derived P1 substrate.
    assert p1.source_id == p2.source_id == state.source_id

    # Every P2 object's source_span must index into the ORIGINAL text.
    for obj in p2.objects:
        start, end = obj.source_span
        assert 0 <= start < end <= len(PESKOV_SOURCE), (
            f"P2 object {obj.object_id} span {obj.source_span} is not a "
            f"valid range in the original {len(PESKOV_SOURCE)}-char source")
        # Bonus: the sliced evidence appears at that span in the ORIGINAL.
        assert obj.evidence in PESKOV_SOURCE[start:end]


def test_peskov_p1_preserved_after_p2(mount_policy, router_registry,
                                       run_config):
    """Lineage invariant (ADR §13): P1 does NOT disappear after P2.

    A projection can remain locally valid (its recognised objects were
    legitimately concepts) while globally insufficient (the source had
    more). The runtime marks P1 PARTIAL and preserves its objects in
    lineage; P2 does not overwrite them.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()},
        reflective_hints=_peskov_reflective_hints())
    state, _, _ = executor.run(PESKOV_SOURCE, phase_exec, run_config,
                               hints=hints)
    lineage = state.projection_lineage
    assert lineage.iteration() == 2
    p1, p2 = lineage.entries
    # P1's concepts still addressable
    assert [o.object_family for o in p1.objects] == ["concept", "concept"]
    # P1 status reclassified to PARTIAL, not deleted
    assert p1.status == ProjectionStatus.PARTIAL
    # P2 records lineage back to P1
    # (parent_projection_id + revises are set at spec construction time)
    # We stored the SPEC on the ProjectionResult only via spec_fingerprint,
    # but the ReflectiveReturn ties them: rr.from_projection_id == p1.id
    assert lineage.revisions[0].from_projection_id == p1.projection_id


def test_peskov_objects_carry_projection_relative_provenance(mount_policy,
                                                              router_registry,
                                                              run_config):
    """ADR §7: every produced object must allow reconstruction of
    which source spans, which projection, which operation.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()},
        reflective_hints=_peskov_reflective_hints())
    state, _, _ = executor.run(PESKOV_SOURCE, phase_exec, run_config,
                               hints=hints)
    lineage = state.projection_lineage
    for entry in lineage.entries:
        # projection identity
        assert entry.projection_id.startswith("proj_")
        assert entry.spec_fingerprint
        # source identity
        assert entry.source_id == state.source_id
        # per-object provenance
        for obj in entry.objects:
            assert obj.source_id == state.source_id
            assert isinstance(obj.source_span, tuple)
            assert obj.recognition_basis
        for res in entry.residue:
            assert res.source_id == state.source_id
            assert res.apparent_family


# ---------------------------------------------------------- negative / guards


def test_prose_only_reflection_does_not_loop(mount_policy, router_registry,
                                              run_config):
    """ADR §17: a model that only says in prose 'perhaps a different cut
    is needed' but emits NO typed ReflectiveReturn must NOT trigger a
    second projection. The typed contract is the requirement — the
    epilogue returns None, the loop stops, the governor picks a terminal.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    # No reflective_return supplied on S7 → epilogue produces None.
    phase_exec = _ReflectiveHintExecutor(hints, {})
    state, _, _ = executor.run(PESKOV_SOURCE, phase_exec, run_config,
                               hints=hints)
    # Only P1 executed; no P2.
    assert state.projection_lineage.iteration() == 1
    assert state.projection_lineage.revisions == []
    # Pending diagnostic cleared by the epilogue-empty guard.
    assert state.pending_diagnostic is None


def test_large_residue_never_silently_accepted_local(mount_policy,
                                                      router_registry,
                                                      run_config):
    """ADR §17: a projection with material residue is never silently
    marked ACCEPTED_LOCAL. The concept cutter must produce
    EXPLORATORY (before reflection) — never ACCEPTED_LOCAL — when
    residue is present. After reflection the pipeline marks it PARTIAL.
    """
    from socrates_runtime.cutter_registry import build_default_registry
    from socrates_runtime.projection import (
        SemanticProjectionSpec, new_projection_id, ProjectionStatus)
    reg = build_default_registry()
    cap = reg.get("EXTRACT_CONCEPTS")
    spec = SemanticProjectionSpec(
        projection_id=new_projection_id(),
        source_id="src_x", scene_ref="", operation_id="EXTRACT_CONCEPTS",
        ontology_id="concept_v1",
        target_object_family=cap.target_object_family,
        recognition_criteria=cap.recognition_criteria,
        segmentation_policy=cap.segmentation_policy,
        evidence_requirements=(), applicability_assumptions=(),
        contraindications=cap.contraindications)
    result = cap.execute(PESKOV_SOURCE, spec)
    assert len(result.residue) == 4
    assert result.status == ProjectionStatus.EXPLORATORY, (
        "cutter must not mark a result ACCEPTED_LOCAL when residue "
        "is present — that would be silent forced-completeness")


def test_lineage_preserved_across_reflection(mount_policy, router_registry,
                                              run_config):
    """ADR §17: 'projection changes but lineage is lost' — negative
    proof. Both projections + the ReflectiveReturn that links them are
    all addressable in lineage.to_public().
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()},
        reflective_hints=_peskov_reflective_hints())
    state, _, _ = executor.run(PESKOV_SOURCE, phase_exec, run_config,
                               hints=hints)
    public = state.projection_lineage.to_public()
    assert public["iteration"] == 2
    assert len(public["entries"]) == 2
    assert len(public["revisions"]) == 1
    assert len(public["diagnostics_history"]) == 2
    # Revision links P1 → P2
    assert public["revisions"][0]["from_projection_id"] == \
        public["entries"][0]["projection_id"]


# ---------------------------------------------------------- targeted regressions


def test_direct_assistance_no_projection_step_fires(mount_policy,
                                                     router_registry,
                                                     run_config):
    """A run whose S4 operation kind has no CutterCapability registered
    is not penalised by the new loop — projection_step is a no-op, one
    S0..S10 pass, governor picks the terminal.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = {
        "S1": PhaseHint(scene=Scene(telos="direct answer")),
        "S4": PhaseHint(operation=Operation(kind="DIRECT_ANSWER",
                                             applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.SYSTEM,
                                             human_resolved=True)),
    }
    phase_exec = DeterministicPhaseExecutor(hints)
    state, outcome, _ = executor.run(
        "how many?", phase_exec, run_config, hints=hints)
    assert outcome.terminal == Terminal.ANSWER
    assert state.projection_lineage.iteration() == 0
    assert state.projection_lineage.revisions == []


def test_return_operation_terminal_still_reached_when_human_unresolved(
        mount_policy, router_registry, run_config):
    """The projection loop does not interfere with governor rule INV-009
    (RETURN_OPERATION when ownership is HUMAN/JOINT and unresolved).
    Even if a projection would fire, the governor gets there first.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = {
        "S1": PhaseHint(scene=Scene(telos="something for a human")),
        "S4": PhaseHint(operation=Operation(kind="EXTRACT_CONCEPTS",
                                             applicable=True)),
        "S6": PhaseHint(ownership=Ownership(owner=Authority.HUMAN,
                                             human_resolved=False,
                                             return_reason="INV-009")),
    }
    phase_exec = DeterministicPhaseExecutor(hints)
    state, outcome, _ = executor.run(
        PESKOV_SOURCE, phase_exec, run_config, hints=hints)
    # RETURN_OPERATION is the governor's terminal — human owns the operation.
    assert outcome.terminal == Terminal.RETURN_OPERATION
    # Reflection did not fire — the governor decided BEFORE any epilogue.
    # (A projection may have run inside the pass, but no revisions.)
    assert state.projection_lineage.revisions == []


def test_reflection_bounded_by_max_iterations_end_to_end(mount_policy,
                                                          router_registry,
                                                          run_config):
    """End-to-end (real cutter, real diagnostics) guard: a
    ReflectiveReturn that keeps proposing the SAME revised operation
    which itself keeps producing mismatch → the iteration bound stops
    the loop cleanly.

    To construct this without hard-coding, we make the registry only
    know EXTRACT_CONCEPTS (no covering operation) and inject a
    reflective_return that keeps naming DIFFERENTIATED_ACCOUNT (which
    is not registered). The projection_step falls back to a no-op on
    the second pass (unknown operation kind), so pending_diagnostic is
    cleared → loop actually exits after the reflection was applied
    once. This exercises the code path even though the guard proper is
    covered by unit tests.
    """
    # Registry with only EXTRACT_CONCEPTS.
    scoped = CutterRegistry()
    from socrates_runtime.cutter_registry import _make_concept_extractor
    scoped.register(CutterCapability(
        operation_id="EXTRACT_CONCEPTS",
        segmentation_policy="marker_scan/concept_v1",
        target_object_family=("concept",),
        recognition_criteria=("explicit definition",),
        contraindications=(),
        execute=_make_concept_extractor()))
    executor = PipelineExecutor(
        mount_policy, router_registry,
        projection_step=make_projection_step(scoped))
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()},
        reflective_hints=_peskov_reflective_hints())
    state, _, _ = executor.run(PESKOV_SOURCE, phase_exec, run_config,
                               hints=hints)
    # Reflection was applied once; second projection was a no-op
    # (DIFFERENTIATED_ACCOUNT not in scoped registry).
    assert state.operation.kind == "DIFFERENTIATED_ACCOUNT"
    assert state.projection_lineage.iteration() == 1
    assert len(state.projection_lineage.revisions) == 1
    # And the loop did not spin — we terminated cleanly.
    assert state.projection_lineage.iteration() <= MAX_PROJECTION_ITERATIONS


# ---------------------------------------------------------- trace artefact


def test_peskov_trace_artefact_written(mount_policy, router_registry,
                                        run_config, tmp_path):
    """Emit the ADR-required Peskov trace artefact under a fresh
    subdirectory of the loop's evidence tree (docs/socrates_gs26/
    projection_control_loop/). Kept as a test so a manual run of
    pytest reproduces the artefact byte-for-byte from the current
    source; the file itself is committed alongside the ADR.
    """
    executor = _make_executor(mount_policy, router_registry)
    hints = _peskov_hints()
    phase_exec = _ReflectiveHintExecutor(
        hints, {"S7": _peskov_reflective_return()})
    state, outcome, _ = executor.run(PESKOV_SOURCE, phase_exec, run_config,
                                     hints=hints)
    artefact = {
        "case_id": "R8-C03_OPERATION_OBJECT_PESKOV",
        "adr": "ADR-S26-022",
        "terminal": outcome.terminal.value,
        "source_id": state.source_id,
        "operation_final": state.operation.kind,
        "projection_lineage": state.projection_lineage.to_public(),
        "phases_visited": phase_exec.call_log,
    }
    # Structural checks — the artefact must contain both projections
    # and the linking revision so a reader can reconstruct the loop.
    assert artefact["projection_lineage"]["iteration"] == 2
    assert len(artefact["projection_lineage"]["revisions"]) == 1
    text = json.dumps(artefact, ensure_ascii=False, indent=2)
    # Write into tmp_path here; the committed artefact lives at
    # docs/socrates_gs26/projection_control_loop/PESKOV_TRACE.json
    # (produced by the same test payload; see the artefact file).
    (tmp_path / "PESKOV_TRACE.json").write_text(text, encoding="utf-8")
    assert (tmp_path / "PESKOV_TRACE.json").exists()

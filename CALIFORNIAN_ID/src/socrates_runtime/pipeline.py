"""S0..S10 state machine — driven by a :class:`PhaseExecutor`.

The executor is a *seam*: the pipeline sends it a
:class:`PhaseExecutionRequest`, gets back a :class:`PhaseDelta`, and mutates
:class:`PipelineState` through the phase's jurisdiction. Three seams share
the same shape:

    DeterministicPhaseExecutor   — reads caller-supplied ``PhaseHint``s
    LiveModelPhaseExecutor       — calls the real provider
    TestDoublePhaseExecutor      — the live code path with a canned provider

Rules the pipeline enforces regardless of which executor runs:

    * S7 stays CONDITIONAL — invoked only on typed council triggers or
      an explicit ``invoke_council`` from a phase output;
    * S9 stays CONDITIONAL on SYSTEM authority + applicability + no
      open-world gap;
    * a phase's delta may only touch fields inside its jurisdiction
      (enforced by the parser; the pipeline additionally rejects any
      illegal-mutation deltas that slip past);
    * a phase whose executor returns ``PROVIDER_UNAVAILABLE`` /
      ``RETRIES_EXHAUSTED`` / ``INVALID_OUTPUT`` in LIVE mode ends the run
      with an explicit ``FAILED_EXPLICIT`` terminal — the pipeline never
      silently substitutes deterministic values for a failed provider.
"""
from __future__ import annotations

import copy
import secrets
from dataclasses import dataclass, field
from typing import Any

from .errors import (
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
)
from .governor import GovernorDecision, InterventionGovernor, apply_decision
from .mount import MountedContext, SemanticMountPolicy, TriggerAdmission
from .phase_contracts import jurisdiction_for
from .phase_executor import (
    DeltaOrigin,
    DeterministicPhaseExecutor,
    ExecutionMode,
    PhaseDelta,
    PhaseExecutionRequest,
    PhaseExecutionResult,
    PhaseExecutor,
    ProviderStatus,
)
from .projection import (
    MAX_PROJECTION_ITERATIONS,
    ProjectionDiagnostics,
    ProjectionStatus,
    ReflectiveReturn,
    RetreatLevel,
    ReturnTarget,
)
from .routers import RouterRegistry, RouterSpec
from .state import (
    Authority,
    MemoryProposal,
    Operation,
    Origin,
    Ownership,
    PipelineState,
    ProvenanceStatus,
    Scene,
    Terminal,
    TerminalOutcome,
)


@dataclass
class PhaseHint:
    """Backward-compat typed delta a fixture can supply.

    The pipeline itself no longer reads hints directly — they reach it via
    :class:`DeterministicPhaseExecutor`. Kept as a class because existing
    tests + Arena participants build it explicitly.
    """
    scene: Scene | None = None
    origin: Origin | None = None
    operation: Operation | None = None
    ownership: Ownership | None = None
    triggers: list[TriggerAdmission] = field(default_factory=list)
    memory_proposal: MemoryProposal | None = None
    invoke_council: bool = False
    invoke_execution: bool = False


PHASE_ORDER = ("S0", "S1", "S2", "S3", "S4", "S5",
               "S6", "S7", "S8", "S9", "S10")

#: Phase order lookup used by the reflective-return re-entry logic. A
#: return_target of "S4" starts the next pass at S4 and continues through
#: S10. The invariant: re-entry never re-runs S0 (context ok is a run-level
#: precondition, not a per-pass one) and always ends by re-executing S9
#: (that is where the new projection actually happens).
PHASE_INDEX: dict[str, int] = {p: i for i, p in enumerate(PHASE_ORDER)}


@dataclass
class PhaseResult:
    phase: str
    router: RouterSpec
    mount: MountedContext
    execution: PhaseExecutionResult


class PipelineExecutor:
    """One executor per run — sequences S0..S10 through a PhaseExecutor.

    Two loop layers:

        inner  — the linear ``for phase in PHASE_ORDER`` sequence
                  (:meth:`_run_phase_sequence`). Ends after S10 or at the
                  first hard-stop terminal.
        outer  — the projection control loop (:meth:`run`). After each
                  inner pass, if a projection produced a material-mismatch
                  diagnostic and no legitimate terminal has fired yet, an
                  epilogue reflective S7 is invoked. Its
                  :class:`ReflectiveReturn` (typed and distinct from
                  ``Terminal.RETURN_OPERATION`` and from technical
                  ``RETRIES_EXHAUSTED``) selects the next pass's re-entry
                  phase. Bounded by :data:`MAX_PROJECTION_ITERATIONS` and
                  by unchanged-diagnosis / unchanged-spec guards so a
                  runaway model cannot force the loop to spin.
    """

    def __init__(self, mount_policy: SemanticMountPolicy,
                 router_registry: RouterRegistry,
                 governor: InterventionGovernor | None = None,
                 projection_step: Any = None) -> None:
        self.mount_policy = mount_policy
        self.routers = router_registry
        self.governor = governor or InterventionGovernor()
        #: Optional callable ``(state) -> None`` that runs after the
        #: linear S0..S10 pass. It is where the CutterRegistry actually
        #: executes a projection against ``state.input_text`` (ORIGINAL
        #: source, never P1 outputs) and updates
        #: ``state.projection_lineage`` + ``state.pending_diagnostic``.
        #: Kept as a seam so commit 2 can exercise the loop with a
        #: synthetic step; commit 3 wires the real registry.
        self.projection_step = projection_step

    # ------------------------------------------------------------------

    def run(self, input_text: str,
            phase_executor: PhaseExecutor,
            run_configuration,                               # SocratesRunConfiguration
            *,
            hints: dict[str, PhaseHint] | None = None,
            trace=None,
            skip_phases: frozenset[str] = frozenset(),
            ) -> tuple[PipelineState, TerminalOutcome, list[PhaseResult]]:
        """Execute S0..S10 with the projection control loop wrapped around.

        ``hints`` is honoured only by the deterministic executor; the live
        executor ignores it. Passing hints in a LIVE run does not change
        the run — it just gets recorded as unused fixture data in the
        trace, which is what we want (a caller can't smuggle fixture
        semantics into live behaviour).
        """
        state = PipelineState(
            run_id=f"srun_{secrets.token_hex(8)}",
            input_text=input_text)
        results: list[PhaseResult] = []

        for pass_number in range(1, MAX_PROJECTION_ITERATIONS + 1):
            start_from = state.reentry_from or "S0"
            state.reentry_from = ""
            if trace is not None and pass_number > 1:
                trace.record("projection_pass_started",
                             pass_number=pass_number,
                             start_from=start_from,
                             source_id=state.source_id)

            pass_results, hard_stop = self._run_phase_sequence(
                state, phase_executor, run_configuration,
                hints=hints, trace=trace, skip_phases=skip_phases,
                start_from=start_from, input_text=input_text)
            results.extend(pass_results)
            if hard_stop is not None:
                return state, hard_stop, results

            # An in-pass S7 may have already emitted a ReflectiveReturn —
            # if so it set ``reentry_from`` and revised state; skip the
            # projection step and go straight to the next pass.
            if state.reentry_from:
                if pass_number >= MAX_PROJECTION_ITERATIONS:
                    self._on_loop_bound_reached(state, trace, None)
                    state.reentry_from = ""
                    break
                continue

            # After the inner S0..S10 pass, the projection step (if any)
            # runs the CutterRegistry against ORIGINAL input_text — never
            # against any prior projection's output — and updates
            # state.projection_lineage / state.pending_diagnostic.
            if self.projection_step is not None:
                self.projection_step(state)
                if trace is not None:
                    trace.record("projection_step",
                                 pass_number=pass_number,
                                 lineage=state.projection_lineage.to_public(),
                                 pending=(state.pending_diagnostic.to_public()
                                          if state.pending_diagnostic
                                          else None))

            diag: ProjectionDiagnostics | None = state.pending_diagnostic
            if diag is None or not diag.mismatch:
                # No reflective retreat needed — the run is done.
                break
            if pass_number >= MAX_PROJECTION_ITERATIONS:
                # Guard: iteration bound reached. Preserve aporia rather
                # than force another look with unchanged evidence.
                self._on_loop_bound_reached(state, trace, diag)
                break

            # Loop guard: same diagnosis fingerprint as a previous pass →
            # reflection would not add material information; stop and let
            # the governor pick a legitimate terminal (typically DWELL /
            # PRESERVE_APORIA).
            if diag.fingerprint() in (
                    state.projection_lineage.previous_diagnostic_fingerprints()[:-1]):
                self._on_repeat_diagnosis(state, trace, diag)
                break

            reflective_return = self._invoke_reflective_epilogue(
                state, phase_executor, run_configuration,
                hints=hints, trace=trace)
            if reflective_return is None:
                # S7 could not produce a valid ReflectiveReturn from the
                # diagnostic. Stop — this is aporia, not a technical bug.
                self._on_epilogue_empty(state, trace, diag)
                break

            self._apply_reflective_return(state, reflective_return, trace=trace)

        decision = self.governor.decide(state)
        if trace is not None:
            trace.record_governor(decision)
        outcome = apply_decision(state, decision,
                                 response_text=self._render_response(state, decision))
        return state, outcome, results

    # ------------------------------------------------------------------
    # inner: one linear S0..S10 pass
    # ------------------------------------------------------------------

    def _run_phase_sequence(self, state: PipelineState,
                            phase_executor: PhaseExecutor,
                            run_configuration,
                            *,
                            hints: dict[str, PhaseHint] | None,
                            trace,
                            skip_phases: frozenset[str],
                            start_from: str,
                            input_text: str,
                            ) -> tuple[list[PhaseResult],
                                       TerminalOutcome | None]:
        """One S0..S10 pass, starting at ``start_from`` (default S0).

        Returns ``(results, hard_stop_terminal_or_None)``. When
        ``hard_stop_terminal_or_None`` is set, the outer loop must return
        that terminal verbatim — a live-mode phase failure is a hard stop.
        """
        results: list[PhaseResult] = []
        start_idx = PHASE_INDEX.get(start_from, 0)
        # On a reflective re-entry the return_target phase was itself the
        # site of the revision (S7 wrote the revised operation / scene
        # directly into state via _apply_reflective_return). Re-running
        # that phase with its fixture hint or an unrevised prompt would
        # clobber the revision. Per ADR-S26-022 "changed forward action",
        # the revision IS the change; the next pass executes FROM the
        # phase after return_target so downstream work observes the
        # revised state. First pass always starts at S0.
        first_pass = (start_from in ("", "S0"))
        if not first_pass:
            start_idx = min(start_idx + 1, len(PHASE_ORDER))

        for phase in PHASE_ORDER[start_idx:]:
            if phase in skip_phases:
                continue
            if phase == "S7" and not self._council_needed(state):
                continue
            if phase == "S9" and not self._execution_authorized(state):
                continue

            router = self.routers.router_for_phase(phase)
            state_before = self._clone(state)
            try:
                mount = self.mount_policy.mount(router.module_id, phase)
            except (SemanticMountMissing, SemanticContextBudgetExceeded) as exc:
                early_terminal = (Terminal.SEMANTIC_MOUNT_MISSING
                                  if "not present" in str(exc)
                                  or "body" in str(exc)
                                  else Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED)
                if trace is not None:
                    trace.record_failure(early_terminal.value, str(exc),
                                         extra={"phase": phase,
                                                "router": router.module_id})
                state.phase = phase
                return results, TerminalOutcome(
                    terminal=early_terminal, response_text="",
                    rationale=str(exc))

            request = PhaseExecutionRequest(
                phase=phase, router=router, mounted=mount,
                input_text=input_text,
                state_snapshot=state.to_public(),
                run_configuration=run_configuration,
                max_retries=1,
            )
            execution = phase_executor.execute(request)

            # In LIVE mode, a non-OK provider status is a hard stop —
            # never a deterministic pretend-success.
            if (execution.mode == ExecutionMode.LIVE
                    and execution.provider_status != ProviderStatus.OK):
                if trace is not None:
                    trace.record_failure(
                        f"live_phase_{execution.provider_status.lower()}",
                        execution.error,
                        extra={"phase": phase, "router": router.module_id,
                               "attempts": execution.attempts,
                               "provider": execution.provider_id,
                               "model": execution.model_id})
                    trace.record("phase_executed", phase=phase,
                                 router_id=router.module_id,
                                 mount=mount.to_public(),
                                 execution=execution.to_public())
                state.phase = phase
                return results, TerminalOutcome(
                    terminal=Terminal.FAILED_EXPLICIT, response_text="",
                    rationale=(f"live phase {phase} failed: "
                               f"{execution.provider_status}: "
                               f"{execution.error}"))

            self._apply_delta(phase, state, execution.delta)
            state.phase = phase
            results.append(PhaseResult(phase=phase, router=router,
                                        mount=mount, execution=execution))
            if trace is not None:
                trace.record("phase_executed", phase=phase,
                             router_id=router.module_id,
                             mount=mount.to_public(),
                             execution=execution.to_public(),
                             state_diff=_diff_public(state_before.to_public(),
                                                     state.to_public()))
        return results, None

    # ------------------------------------------------------------------
    # reflective epilogue: dedicated S7 invocation for the loop
    # ------------------------------------------------------------------

    def _invoke_reflective_epilogue(self, state: PipelineState,
                                    phase_executor: PhaseExecutor,
                                    run_configuration,
                                    *,
                                    hints: dict[str, PhaseHint] | None,
                                    trace) -> ReflectiveReturn | None:
        """Run S7 in reflective mode against the current pending diagnostic.

        Distinct from the S7 CONDITIONAL invocation inside the inner pass
        (which is council-only): here we invoke S7 with the explicit
        expectation that it will emit a :class:`ReflectiveReturn` for the
        current ``state.pending_diagnostic``. The distinction matters —
        this is where the "reflective" branch of B07 becomes executable
        rather than only describable.
        """
        router = self.routers.router_for_phase("S7")
        try:
            mount = self.mount_policy.mount(router.module_id, "S7")
        except (SemanticMountMissing, SemanticContextBudgetExceeded) as exc:
            if trace is not None:
                trace.record_failure(
                    "reflective_epilogue_mount_failed", str(exc),
                    extra={"router": router.module_id})
            return None

        request = PhaseExecutionRequest(
            phase="S7", router=router, mounted=mount,
            input_text=state.input_text,
            state_snapshot=state.to_public(),
            run_configuration=run_configuration,
            max_retries=1,
        )
        execution = phase_executor.execute(request)

        if (execution.mode == ExecutionMode.LIVE
                and execution.provider_status != ProviderStatus.OK):
            if trace is not None:
                trace.record_failure(
                    f"reflective_epilogue_{execution.provider_status.lower()}",
                    execution.error,
                    extra={"attempts": execution.attempts,
                           "provider": execution.provider_id,
                           "model": execution.model_id})
            return None

        if trace is not None:
            trace.record("reflective_epilogue_executed",
                         router_id=router.module_id,
                         execution=execution.to_public())

        rr = execution.delta.reflective_return
        if rr is None:
            return None
        # Backfill from_projection_id and diagnostic fingerprint if the
        # executor did not populate them — the runtime knows both.
        diag = state.pending_diagnostic
        if diag is not None:
            if not rr.from_projection_id:
                rr.from_projection_id = diag.projection_id
            if not rr.diagnostic_fingerprint:
                rr.diagnostic_fingerprint = diag.fingerprint()
        return rr

    def _apply_reflective_return(self, state: PipelineState,
                                 rr: ReflectiveReturn,
                                 *, trace) -> None:
        """Record the ReflectiveReturn in lineage and revise state.

        This is where the governing hypothesis actually changes: the
        state.operation / scene / origin fields are overwritten with the
        revised values from ``rr``. The previous P1 record is marked
        PARTIAL (its objects remain addressable in the lineage); the
        pending diagnostic is cleared; the outer loop then re-enters
        from ``rr.return_target``.
        """
        state.projection_lineage.add_reflective_return(rr)
        # Mark the projection that triggered this reflection as PARTIAL —
        # its objects are still addressable; only its adequacy claim was
        # withdrawn.
        state.projection_lineage.mark_status(rr.from_projection_id,
                                             ProjectionStatus.PARTIAL)
        # Apply the revised governing hypothesis, per retreat level.
        if rr.retreat_level in (RetreatLevel.R1, RetreatLevel.R2):
            if rr.revised_operation_kind:
                state.operation = Operation(
                    kind=rr.revised_operation_kind,
                    applicable=True, why_not="", open_world_gap=False)
        if rr.retreat_level == RetreatLevel.R3 and rr.revised_scene_telos:
            state.scene.telos = rr.revised_scene_telos
        # ontology_id is not a state field today — it is carried on the
        # ProjectionSpec of the next projection. The CutterRegistry
        # reads rr.revised_ontology_id when it constructs P2's spec.
        state.reentry_from = rr.return_target.value
        state.pending_diagnostic = None
        if trace is not None:
            trace.record("reflective_return_applied",
                         reflective_return=rr.to_public(),
                         reentry_from=state.reentry_from,
                         lineage=state.projection_lineage.to_public())

    # ------------------------------------------------------------------
    # loop-guard events (all deterministic, no LLM)
    # ------------------------------------------------------------------

    @staticmethod
    def _on_loop_bound_reached(state: PipelineState, trace,
                               diag: ProjectionDiagnostics | None) -> None:
        if trace is not None:
            trace.record("projection_loop_bound_reached",
                         iterations=state.projection_lineage.iteration(),
                         final_diagnostic=(diag.to_public()
                                           if diag is not None else None))
        state.pending_diagnostic = None

    @staticmethod
    def _on_repeat_diagnosis(state: PipelineState, trace,
                             diag: ProjectionDiagnostics) -> None:
        if trace is not None:
            trace.record("projection_repeat_diagnosis",
                         fingerprint=diag.fingerprint(),
                         diagnostic=diag.to_public())
        state.pending_diagnostic = None

    @staticmethod
    def _on_epilogue_empty(state: PipelineState, trace,
                           diag: ProjectionDiagnostics) -> None:
        if trace is not None:
            trace.record("reflective_epilogue_empty",
                         diagnostic=diag.to_public())
        state.pending_diagnostic = None

    # ------------------------------------------------------------------

    @staticmethod
    def _council_needed(state: PipelineState) -> bool:
        council_causes = {"COUNCIL_REQUIRED", "TYPED_VETO", "MINORITY_MATERIAL"}
        return bool(set(state.admitted_trigger_causes) & council_causes)

    @staticmethod
    def _execution_authorized(state: PipelineState) -> bool:
        return (state.ownership.owner == Authority.SYSTEM
                and state.operation.applicable
                and not state.operation.open_world_gap)

    def _apply_delta(self, phase: str, state: PipelineState,
                     delta: PhaseDelta) -> None:
        """Mutate state through the phase's jurisdiction.

        A delta produced by a well-formed parser only carries fields the
        phase owns; we re-check here as a defense in depth against a future
        executor that constructs deltas directly.
        """
        juris = jurisdiction_for(phase)
        if delta.scene is not None and "scene" in juris:
            state.scene = delta.scene
        if delta.origin is not None and "origin" in juris:
            state.origin = delta.origin
        if delta.operation is not None and "operation" in juris:
            state.operation = delta.operation
        if delta.ownership is not None and "ownership" in juris:
            state.ownership = delta.ownership
        if delta.triggers and "triggers" in juris:
            state.admitted_trigger_causes = tuple(
                dict.fromkeys(list(state.admitted_trigger_causes)
                              + [t.trigger_id for t in delta.triggers]))
        if delta.memory_proposal is not None and "memory_proposal" in juris:
            state.memory_proposal = delta.memory_proposal
        if delta.invoke_council and "invoke_council" in juris:
            state.council_invoked = True
        if delta.invoke_execution and "invoke_execution" in juris:
            state.execution_invoked = True
        # A phase may emit a ReflectiveReturn *inside* the pass (rather
        # than only in the epilogue). The application is idempotent —
        # record + mark P1 partial + revise state.operation/scene per
        # retreat_level + set ``reentry_from``. The outer loop uses
        # ``reentry_from`` as the sole marker that another pass is due.
        if delta.reflective_return is not None and "reflective_return" in juris:
            self._apply_reflective_return(state, delta.reflective_return,
                                          trace=None)

    @staticmethod
    def _clone(state: PipelineState) -> PipelineState:
        return copy.deepcopy(state)

    @staticmethod
    def _render_response(state: PipelineState,
                         decision: GovernorDecision) -> str:
        # A diagnostic surface — the live renderer (see
        # :func:`socrates_runtime.renderer.render_terminal`) uses B10 when a
        # provider is available; this fallback keeps runs debuggable when
        # no live path is wired.
        if decision.terminal == Terminal.ANSWER:
            return (f"[ANSWER] {state.scene.telos or state.input_text}"
                    if state.scene.telos else "[ANSWER] (deterministic)")
        if decision.terminal == Terminal.RETURN_OPERATION:
            reason = state.ownership.return_reason or state.operation.why_not
            return (f"[RETURN_OPERATION] {reason}" if reason
                    else "[RETURN_OPERATION]")
        if decision.terminal == Terminal.PRESERVE_APORIA:
            return "[PRESERVE_APORIA] сохраняем неопределённость"
        if decision.terminal == Terminal.CHALLENGE:
            return "[CHALLENGE] источник/статус утверждения оспорены"
        return f"[{decision.terminal.value}]"


def _diff_public(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        if b != a:
            out[key] = {"before": b, "after": a}
    return out

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


@dataclass
class PhaseResult:
    phase: str
    router: RouterSpec
    mount: MountedContext
    execution: PhaseExecutionResult


class PipelineExecutor:
    """One executor per run — sequences S0..S10 through a PhaseExecutor."""

    def __init__(self, mount_policy: SemanticMountPolicy,
                 router_registry: RouterRegistry,
                 governor: InterventionGovernor | None = None) -> None:
        self.mount_policy = mount_policy
        self.routers = router_registry
        self.governor = governor or InterventionGovernor()

    # ------------------------------------------------------------------

    def run(self, input_text: str,
            phase_executor: PhaseExecutor,
            run_configuration,                               # SocratesRunConfiguration
            *,
            hints: dict[str, PhaseHint] | None = None,
            trace=None,
            skip_phases: frozenset[str] = frozenset(),
            ) -> tuple[PipelineState, TerminalOutcome, list[PhaseResult]]:
        """Execute S0..S10 through ``phase_executor``.

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

        for phase in PHASE_ORDER:
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
                return state, TerminalOutcome(
                    terminal=early_terminal, response_text="",
                    rationale=str(exc)), results

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
                return state, TerminalOutcome(
                    terminal=Terminal.FAILED_EXPLICIT, response_text="",
                    rationale=(f"live phase {phase} failed: "
                               f"{execution.provider_status}: "
                               f"{execution.error}")), results

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

        decision = self.governor.decide(state)
        if trace is not None:
            trace.record_governor(decision)
        outcome = apply_decision(state, decision,
                                 response_text=self._render_response(state, decision))
        return state, outcome, results

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

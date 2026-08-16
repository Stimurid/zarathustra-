"""S0..S10 state machine — the operational shape of one Socrates run.

Executes the phases in order, but treats S7 (council) and S9 (execution)
as CONDITIONAL: the pipeline may go S6 → S8 → S10 without ever entering
the council, and may pause at S6 with a HUMAN return before S8/S9.

For every phase the executor:

    1. asks the mount policy for the required + admitted-conditional bodies,
    2. updates the typed state with the phase's contribution,
    3. records a trace event with mount + state diff.

Semantic bodies exist as text; without a live LLM they cannot literally be
executed. What can be executed deterministically is the *state machine*:
mount is applied, contracts are checked, transitions are typed. When a
live provider is later attached, the router bodies become the prompts fed
to it — the pipeline shape does not change.

The parameter that gives a caller control over how a phase updates state is
:class:`PhaseHint`. In deterministic mode the hints come from the caller's
fixture; in a live mode they will come from a model call parsed against the
router's output contract. The pipeline itself sees only typed data.
"""
from __future__ import annotations

import copy
import secrets
from dataclasses import dataclass, field
from typing import Any

from .errors import (
    ConditionalTriggerRejected,
    SemanticContextBudgetExceeded,
    SemanticMountMissing,
)
from .governor import GovernorDecision, InterventionGovernor, apply_decision
from .mount import MountedContext, SemanticMountPolicy, TriggerAdmission
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
    """Typed input a phase applies to state.

    All fields are optional; a phase without a hint leaves state unchanged
    (except for the phase marker). This is how the pipeline is executable
    end-to-end without a model — a caller supplies typed hints in tests, and
    the phase applies them deterministically. A live LLM executor would
    produce the same hints from parsed structured output.
    """
    scene: Scene | None = None
    origin: Origin | None = None
    operation: Operation | None = None
    ownership: Ownership | None = None
    triggers: list[TriggerAdmission] = field(default_factory=list)
    memory_proposal: MemoryProposal | None = None
    #: Phases that legitimately fold their outcome into a state field.
    invoke_council: bool = False
    invoke_execution: bool = False


PHASE_ORDER = ("S0", "S1", "S2", "S3", "S4", "S5",
               "S6", "S7", "S8", "S9", "S10")


@dataclass
class PhaseResult:
    phase: str
    router: RouterSpec
    mount: MountedContext


class PipelineExecutor:
    """One executor per run — orchestrates S0..S10 with typed hints."""

    def __init__(self, mount_policy: SemanticMountPolicy,
                 router_registry: RouterRegistry,
                 governor: InterventionGovernor | None = None) -> None:
        self.mount_policy = mount_policy
        self.routers = router_registry
        self.governor = governor or InterventionGovernor()

    # ------------------------------------------------------------------

    def run(self, input_text: str,
            hints: dict[str, PhaseHint] | None = None,
            *,
            trace=None,
            skip_phases: frozenset[str] = frozenset()) -> tuple[
                PipelineState, TerminalOutcome, list[PhaseResult]]:
        """Execute S0..S10 with typed hints, return (state, outcome, phases)."""
        hints = hints or {}
        state = PipelineState(
            run_id=f"srun_{secrets.token_hex(8)}",
            input_text=input_text)
        results: list[PhaseResult] = []
        early_terminal: Terminal | None = None

        for phase in PHASE_ORDER:
            if phase in skip_phases:
                continue
            # S7 (council) is CONDITIONAL — only invoked when a prior phase
            # asked for it OR the current state legitimately needs it.
            if phase == "S7" and not self._council_needed(state, hints):
                continue
            # S9 (execution) is CONDITIONAL on authority and applicability.
            if phase == "S9" and not self._execution_authorized(state):
                continue

            router = self.routers.router_for_phase(phase)
            hint = hints.get(phase, PhaseHint())
            state_before = self._clone(state)
            try:
                mount = self.mount_policy.mount(
                    router.module_id, phase,
                    proposed_triggers=hint.triggers)
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

            self._apply_hint(state, hint)
            state.phase = phase
            results.append(PhaseResult(phase=phase, router=router, mount=mount))
            if trace is not None:
                trace.record_phase(phase, router.module_id, mount,
                                   state_before, state)

        decision = self.governor.decide(state)
        if trace is not None:
            trace.record_governor(decision)
        outcome = apply_decision(state, decision,
                                 response_text=self._render_response(state, decision))
        return state, outcome, results

    # ------------------------------------------------------------------

    @staticmethod
    def _council_needed(state: PipelineState, hints: dict[str, PhaseHint]) -> bool:
        # Legitimate invocations: explicit hint, or an admitted trigger family
        # like COUNCIL_REQUIRED / TYPED_VETO / MINORITY_MATERIAL.
        if hints.get("S7") and hints["S7"].invoke_council:
            return True
        council_causes = {"COUNCIL_REQUIRED", "TYPED_VETO", "MINORITY_MATERIAL"}
        return bool(set(state.admitted_trigger_causes) & council_causes)

    @staticmethod
    def _execution_authorized(state: PipelineState) -> bool:
        # S9 = Tinkuy execution. Only run when SYSTEM owns AND operation
        # remains applicable AND there is no open-world gap that would make
        # execution premature.
        return (state.ownership.owner == Authority.SYSTEM
                and state.operation.applicable
                and not state.operation.open_world_gap)

    def _apply_hint(self, state: PipelineState, hint: PhaseHint) -> None:
        if hint.scene is not None:
            state.scene = hint.scene
        if hint.origin is not None:
            state.origin = hint.origin
        if hint.operation is not None:
            state.operation = hint.operation
        if hint.ownership is not None:
            state.ownership = hint.ownership
        if hint.triggers:
            state.admitted_trigger_causes = tuple(
                dict.fromkeys(list(state.admitted_trigger_causes)
                              + [t.trigger_id for t in hint.triggers]))
        if hint.memory_proposal is not None:
            state.memory_proposal = hint.memory_proposal
        if hint.invoke_council:
            state.council_invoked = True
        if hint.invoke_execution:
            state.execution_invoked = True

    @staticmethod
    def _clone(state: PipelineState) -> PipelineState:
        return copy.deepcopy(state)

    @staticmethod
    def _render_response(state: PipelineState,
                         decision: GovernorDecision) -> str:
        # Deterministic rendering: a short, honest sentence that names the
        # terminal and any rationale. A live LLM executor would produce a
        # nicer surface here from B10; without it, we do not synthesise.
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



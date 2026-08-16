"""Intervention governor — picks the terminal outcome from typed state.

The runtime never hardcodes a fixture terminal. This governor reads the
state — origin, applicability, ownership, admitted triggers — and applies
the rules the semantic body already declares:

    HUMAN_UNRESOLVED  → RETURN_OPERATION   (INV-009)
    open_world_gap    → PRESERVE_APORIA / DISTINGUISH
    operation.applicable == False and why_not → RETURN_OPERATION
    dispute_mode with STATUS_DISPUTE cause → CHALLENGE
    otherwise (system-owned, applicable, no gap) → ANSWER

This is a policy layer, not an LLM. When a live LLM executor is wired in
(future R8 pass), it may propose an alternative terminal per B10, but the
governor's rules remain the final gate: an LLM cannot promote itself past
INV-009.
"""
from __future__ import annotations

from dataclasses import dataclass

from .state import Authority, PipelineState, Terminal, TerminalOutcome


@dataclass(frozen=True)
class GovernorDecision:
    terminal: Terminal
    rationale: str
    grounds: dict


class InterventionGovernor:
    """Deterministic mapping from :class:`PipelineState` to a terminal."""

    def decide(self, state: PipelineState) -> GovernorDecision:
        # 1) Human ownership unresolved → return the operation to the human.
        if (state.ownership.owner in {Authority.HUMAN, Authority.JOINT}
                and not state.ownership.human_resolved):
            return GovernorDecision(
                Terminal.RETURN_OPERATION,
                rationale="human/joint ownership unresolved (INV-009)",
                grounds={"owner": state.ownership.owner.value,
                         "return_reason": state.ownership.return_reason})

        # 2) Explicit inapplicability → refuse the operation with a reason.
        if not state.operation.applicable and state.operation.why_not:
            return GovernorDecision(
                Terminal.RETURN_OPERATION,
                rationale=f"operation inapplicable: {state.operation.why_not}",
                grounds={"why_not": state.operation.why_not})

        # 3) Open-world gap → preserve aporia rather than force a class.
        if state.operation.open_world_gap:
            return GovernorDecision(
                Terminal.PRESERVE_APORIA,
                rationale="unknown object; would violate INV-007 to force fit",
                grounds={"triggers": list(state.admitted_trigger_causes)})

        # 4) Provenance dispute → challenge instead of asserting.
        if "STATUS_DISPUTE" in state.admitted_trigger_causes:
            return GovernorDecision(
                Terminal.CHALLENGE,
                rationale="status/provenance dispute admitted; assertion refused",
                grounds={"triggers": ["STATUS_DISPUTE"]})

        # 5) System-owned + applicable + no gap → ANSWER.
        if state.ownership.owner == Authority.SYSTEM:
            return GovernorDecision(
                Terminal.ANSWER,
                rationale="system-owned, applicable, no open-world gap",
                grounds={})

        # 6) Fall-through — we could not decide without model help. That is
        #    a legitimate DWELL: the runtime withheld judgement.
        return GovernorDecision(
            Terminal.DWELL,
            rationale="conditions do not force any terminal deterministically",
            grounds={})


def apply_decision(state: PipelineState, decision: GovernorDecision,
                   response_text: str = "") -> TerminalOutcome:
    return TerminalOutcome(
        terminal=decision.terminal,
        response_text=response_text,
        rationale=decision.rationale,
        memory_proposal=state.memory_proposal,
    )

"""3B runtime orchestration — reuse private_work_plane types.

Seam: post S0–S10 + liberatory, pre B2Q-R overlay and public render.
PRIVATE products may change the outward response only via ResponsePlan.
They cannot mutate Scene/Space/contract/profile/mount/memory.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from .models import Message
from .private_work_plane import (
    ALLOWED_PRIVATE_PURPOSES,
    AutopromptDispatcher,
    AutopromptRequest,
    BenefitJudgement,
    MAX_ADDITIONAL_PRIVATE_PASSES,
    PURPOSE_TO_MODULE,
    PrivateNeedDecision,
    PrivateWorkNeedAssessment,
    REGISTERED_PRIVATE_MODULES,
    ReflectionResult,
    ResponsePlan,
    StopReason,
    SurfaceKind,
    WorkPacket,
    private_payload_is_instruction_shaped,
    resolve_private_module,
    validate_work_packet,
)
from .state import PipelineState, Terminal, TerminalOutcome


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


SOVEREIGN_STOP_TERMINALS: frozenset[Terminal] = frozenset({
    Terminal.FAILED_EXPLICIT,
    Terminal.SEMANTIC_MOUNT_MISSING,
    Terminal.SEMANTIC_CONTEXT_BUDGET_EXCEEDED,
    Terminal.PRESERVE_APORIA,
    Terminal.RETURN_OPERATION,
})

# Sanctioned public product is the bounded distillate itself.
# No bureaucracy marker in ordinary response text.


@dataclass
class InternalCallBudget:
    """Shared accounting: S0–S10 is the main cycle; 3B extra passes and
    B2Q-R specialized inference share a token ceiling.
    """
    additional_private_passes: int = 0
    specialized_calls: int = 0
    tokens_spent: int = 0
    token_ceiling: int = 8000
    max_additional_private: int = MAX_ADDITIONAL_PRIVATE_PASSES

    def record_specialized(self, tokens: int = 0) -> None:
        self.specialized_calls += 1
        self.tokens_spent += max(0, tokens)

    def record_private(self, tokens: int = 0) -> None:
        self.additional_private_passes += 1
        self.tokens_spent += max(0, tokens)

    def to_public(self) -> dict[str, Any]:
        return {
            "additional_private_passes": self.additional_private_passes,
            "specialized_calls": self.specialized_calls,
            "tokens_spent": self.tokens_spent,
            "token_ceiling": self.token_ceiling,
            "max_additional_private": self.max_additional_private,
        }


@dataclass
class PrivateWorkShadow:
    """Inspectable SHADOW surface. Not CoT. Not PUBLIC bureaucracy."""
    status: str = "NO_EXTRA_WORK"
    additional_pass_count: int = 0
    passes: list[dict[str, Any]] = field(default_factory=list)
    need: dict[str, Any] | None = None
    stop_reason: str = ""
    changed_forward_action: str = ""
    causal_effect: str = ""
    durable_write_attempt: str = "none"
    response_plan_id: str = ""
    packet_refs: list[str] = field(default_factory=list)
    injection_shaped_seen: bool = False
    budgets: dict[str, Any] = field(default_factory=dict)
    public_product_excerpt: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "private_work_status": self.status,
            "additional_private_pass_count": self.additional_pass_count,
            "passes": self.passes,
            "need": self.need,
            "stop_reason": self.stop_reason,
            "changed_forward_action": self.changed_forward_action,
            "causal_effect": self.causal_effect,
            "durable_write_attempt": self.durable_write_attempt,
            "response_plan_id": self.response_plan_id,
            "packet_refs": self.packet_refs,
            "injection_shaped_seen": self.injection_shaped_seen,
            "budgets": self.budgets,
            "public_product_excerpt": self.public_product_excerpt,
            "kind": "ADDITIONAL_PRIVATE_PASS" if self.additional_pass_count else "NONE",
        }


def _kind_of(res: Any) -> str:
    kind = getattr(res, "kind", None)
    if kind is None and isinstance(res, dict):
        kind = res.get("kind")
    if kind is None:
        return ""
    return getattr(kind, "value", kind) or ""


def _has_organ_gap(state: PipelineState) -> bool:
    return any(_kind_of(r) == "ORGAN_GAP" for r in (state.capability_resolutions or []))


def _has_projection_mismatch(state: PipelineState) -> bool:
    diag = getattr(state, "pending_diagnostic", None)
    return bool(diag is not None and getattr(diag, "mismatch", False))


def _has_conflict(state: PipelineState) -> bool:
    reg = getattr(state, "conflict_registry", None)
    if reg is None:
        return False
    held = getattr(reg, "held", None) or getattr(reg, "conflicts", None)
    if held is None and hasattr(reg, "__len__"):
        try:
            return len(reg) > 0
        except TypeError:
            return False
    return bool(held)


def assess_private_work_need(state: PipelineState,
                             outcome: TerminalOutcome,
                             *,
                             intervention_plan: Any = None,
                             input_text: str = "",
                             max_additional: int = MAX_ADDITIONAL_PRIVATE_PASSES,
                             ) -> PrivateWorkNeedAssessment:
    """Typed need selection. Ignores lexical pass-count / think-harder bait."""
    grounds: list[str] = []
    if outcome.terminal in SOVEREIGN_STOP_TERMINALS:
        return PrivateWorkNeedAssessment(
            assessment_id=_new_id("pna"),
            decision=PrivateNeedDecision.NO_EXTRA_WORK,
            benefit=BenefitJudgement.BENEFIT_NOT_EXPECTED,
            purpose="", module_id="",
            grounds=(f"terminal_sovereignty:{outcome.terminal.value}",))

    if max_additional <= 0:
        return PrivateWorkNeedAssessment(
            assessment_id=_new_id("pna"),
            decision=PrivateNeedDecision.NO_EXTRA_WORK,
            benefit=BenefitJudgement.BENEFIT_NOT_EXPECTED,
            purpose="", module_id="",
            grounds=("budget_max_additional_zero",))

    # Rhetorical harshness alone is not a need.
    rh = getattr(intervention_plan, "rhetorical_harshness", "") or ""
    ep = getattr(intervention_plan, "epistemic_pressure", "") or ""

    mismatch = _has_projection_mismatch(state)
    organ_gap = _has_organ_gap(state)
    conflict = _has_conflict(state)
    op = state.operation
    disambiguation = (
        bool(op.kind) and not op.applicable and not op.open_world_gap
        and outcome.terminal not in SOVEREIGN_STOP_TERMINALS)

    if mismatch:
        grounds.append("pending_diagnostic.mismatch")
        purpose = "PROJECTION_DIAGNOSTIC_REVIEW"
    elif organ_gap:
        grounds.append("capability_resolution.ORGAN_GAP")
        purpose = "SOURCE_GAP_RECONSTRUCTION"
    elif conflict:
        grounds.append("conflict_registry.held")
        purpose = "COUNTEREXAMPLE_REVIEW"
    elif disambiguation:
        grounds.append("operation.applicable=false")
        purpose = "OPERATION_DISAMBIGUATION"
    elif ep in {"HIGH", "MAX"} and mismatch:
        grounds.append(f"epistemic_pressure:{ep}")
        purpose = "PROJECTION_DIAGNOSTIC_REVIEW"
    else:
        if rh:
            grounds.append(f"rhetorical_harshness_ignored:{rh}")
        grounds.append("no_typed_material_need")
        return PrivateWorkNeedAssessment(
            assessment_id=_new_id("pna"),
            decision=PrivateNeedDecision.NO_EXTRA_WORK,
            benefit=BenefitJudgement.BENEFIT_NOT_EXPECTED,
            purpose="", module_id="",
            grounds=tuple(grounds) or ("direct_assistance",))

    # Instruction-shaped user/source text is evidence, not a need.
    if private_payload_is_instruction_shaped(input_text):
        grounds.append("instruction_shaped_input_ignored")

    module_id = PURPOSE_TO_MODULE.get(purpose, "")
    return PrivateWorkNeedAssessment(
        assessment_id=_new_id("pna"),
        decision=PrivateNeedDecision.PROPOSE_PRIVATE_OPERATION,
        benefit=BenefitJudgement.BENEFIT_EXPECTED_TO_EXCEED_COST,
        purpose=purpose, module_id=module_id,
        grounds=tuple(grounds),
    )


def _deterministic_packet(need: PrivateWorkNeedAssessment,
                          state: PipelineState) -> WorkPacket:
    distillate = (
        f"{need.purpose}: {'; '.join(need.grounds[:3])}"
    )[:400]
    changed = f"render_with_private_distillate:{need.purpose}"
    return WorkPacket(
        packet_id=_new_id("wp"),
        from_pass_index=0, to_pass_index=1,
        referenced_artifact_ids=(need.assessment_id,),
        typed_summary={
            "distillate": distillate,
            "purpose": need.purpose,
            "grounds": list(need.grounds),
        },
        purpose=need.purpose,
        operation_kind=need.purpose,
        distillate=distillate,
        changed_forward_action=changed,
        status="OK",
        stop_signal="STOP",
        authority="NO_BINDING_AUTHORITY",
        output_refs=("response_plan",),
    )


def _parse_live_packet(text: str, need: PrivateWorkNeedAssessment) -> WorkPacket | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    distillate = str(raw.get("distillate") or "")[:400]
    changed = str(raw.get("changed_forward_action") or "")
    if changed.lower() in {"none", "null", "false"}:
        changed = ""
    packet = WorkPacket(
        packet_id=_new_id("wp"),
        from_pass_index=0, to_pass_index=1,
        referenced_artifact_ids=(need.assessment_id,),
        typed_summary={
            "distillate": distillate,
            "purpose": need.purpose,
            "status": str(raw.get("status") or "OK"),
        },
        purpose=need.purpose,
        operation_kind=need.purpose,
        distillate=distillate,
        changed_forward_action=changed,
        status=str(raw.get("status") or "OK"),
        stop_signal=str(raw.get("stop_signal") or "STOP"),
        authority="NO_BINDING_AUTHORITY",
    )
    if validate_work_packet(packet):
        return None
    return packet


def _live_private_call(client: Any, need: PrivateWorkNeedAssessment,
                       state: PipelineState, input_text: str) -> WorkPacket | None:
    if client is None:
        return None
    system = (
        "You produce ONE JSON object for a bounded Socrates private review. "
        "No chain-of-thought. No system/mount/profile/write instructions. "
        "Keys: distillate (string, <=400 chars, the specific review product), "
        "changed_forward_action (string, empty if the public answer should "
        "not change), status (OK|NO_CHANGE), stop_signal (STOP). "
        "authority is never yours."
    )
    user = (
        f"purpose={need.purpose}\n"
        f"grounds={list(need.grounds)}\n"
        f"operation={state.operation.kind} applicable={state.operation.applicable}\n"
        f"telos={state.scene.telos[:200] if state.scene else ''}\n"
        f"user_text_excerpt={(input_text or '')[:400]}\n"
    )
    try:
        resp = client.complete([
            Message(role="system", content=system),
            Message(role="user", content=user),
        ], temperature=0.0, max_tokens=400)
        text = getattr(resp, "text", None) or str(resp)
        return _parse_live_packet(text, need)
    except Exception:  # noqa: BLE001
        return None


def apply_response_plan(outcome: TerminalOutcome,
                        plan: ResponsePlan,
                        packet: WorkPacket) -> TerminalOutcome:
    """PRIVATE → PUBLIC sanctioned bridge. Does not change the terminal."""
    distillate = (packet.distillate
                  or (packet.typed_summary or {}).get("distillate") or "")
    if not packet.changed_forward_action or not distillate:
        return outcome
    clause = str(distillate).strip()
    base = outcome.response_text or ""
    if not clause or clause in base:
        return outcome
    new_text = (clause + "\n" + base).strip()
    return TerminalOutcome(
        terminal=outcome.terminal,
        response_text=new_text,
        rationale=outcome.rationale,
        memory_proposal=outcome.memory_proposal,
    )


def run_private_work(*,
                     state: PipelineState,
                     outcome: TerminalOutcome,
                     intervention_plan: Any = None,
                     input_text: str = "",
                     mode: str = "DETERMINISTIC",
                     client: Any = None,
                     dispatcher: AutopromptDispatcher | None = None,
                     budget: InternalCallBudget | None = None,
                     ) -> tuple[TerminalOutcome, PrivateWorkShadow, InternalCallBudget]:
    budget = budget or InternalCallBudget()
    shadow = PrivateWorkShadow(budgets=budget.to_public())
    if private_payload_is_instruction_shaped(input_text):
        shadow.injection_shaped_seen = True

    need = assess_private_work_need(
        state, outcome, intervention_plan=intervention_plan,
        input_text=input_text,
        max_additional=budget.max_additional_private)
    shadow.need = need.to_public()

    if need.decision != PrivateNeedDecision.PROPOSE_PRIVATE_OPERATION:
        shadow.status = "NO_EXTRA_WORK"
        shadow.stop_reason = StopReason.NO_EXTRA_WORK.value
        shadow.budgets = budget.to_public()
        return outcome, shadow, budget

    disp = dispatcher or AutopromptDispatcher(
        max_passes=budget.max_additional_private,
        budget_tokens_total=budget.token_ceiling - budget.tokens_spent)
    module_id = resolve_private_module(need.module_id) or ""
    if not module_id:
        shadow.status = "REFUSED"
        shadow.stop_reason = StopReason.UNKNOWN_MODULE.value
        return outcome, shadow, budget

    req = AutopromptRequest(
        request_id=_new_id("apr"),
        pass_index=0,
        purpose=need.purpose,
        budget_tokens=700,
        stop_condition="typed WorkPacket or stop",
        provenance_ids=need.grounds,
        module_id=module_id,
    )
    decision = disp.decide(req)
    pass_rec = {
        "pass_id": req.request_id,
        "purpose": need.purpose,
        "module_id": module_id,
        "honour": decision.honour,
        "stop_reason": decision.stop_reason.value if decision.stop_reason else "",
        "kind": "ADDITIONAL_PRIVATE_PASS",
        "execution": "ADDITIONAL_PRIVATE_PASS",
    }
    shadow.passes.append(pass_rec)
    if not decision.honour:
        shadow.status = "REFUSED"
        shadow.stop_reason = (
            decision.stop_reason.value if decision.stop_reason else "REFUSED")
        shadow.budgets = budget.to_public()
        return outcome, shadow, budget

    packet: WorkPacket | None
    provider_fail = False
    if mode == "LIVE" and client is not None:
        packet = _live_private_call(client, need, state, input_text)
        if packet is None:
            provider_fail = True
    else:
        packet = _deterministic_packet(need, state)

    if provider_fail:
        shadow.status = "PROVIDER_FAILURE"
        shadow.stop_reason = StopReason.PROVIDER_FAILURE.value
        pass_rec["provider_status"] = "FAILED"
        shadow.budgets = budget.to_public()
        return outcome, shadow, budget

    if packet is None:
        shadow.status = "VALIDATION_ERROR"
        shadow.stop_reason = StopReason.VALIDATION_ERROR.value
        return outcome, shadow, budget

    reason = validate_work_packet(packet)
    if reason:
        shadow.status = "VALIDATION_ERROR"
        shadow.stop_reason = StopReason.VALIDATION_ERROR.value
        pass_rec["validation"] = reason
        shadow.budgets = budget.to_public()
        return outcome, shadow, budget

    budget.record_private(req.budget_tokens)
    shadow.additional_pass_count = budget.additional_private_passes
    shadow.packet_refs.append(packet.packet_id)
    pass_rec["packet_id"] = packet.packet_id
    pass_rec["product_type"] = "WorkPacket"
    pass_rec["changed_forward_action"] = packet.changed_forward_action

    if not packet.changed_forward_action.strip():
        shadow.status = "NO_CHANGE_STOP"
        shadow.stop_reason = StopReason.NO_CHANGED_FORWARD_ACTION.value
        shadow.budgets = budget.to_public()
        return outcome, shadow, budget

    rplan = ResponsePlan(
        plan_id=_new_id("rp"),
        outward_purpose=need.purpose,
        referenced_state_ids=(packet.packet_id,),
        render_mode="complex",
    )
    new_outcome = apply_response_plan(outcome, rplan, packet)
    shadow.response_plan_id = rplan.plan_id
    shadow.changed_forward_action = packet.changed_forward_action
    shadow.public_product_excerpt = (
        packet.distillate
        or (packet.typed_summary or {}).get("distillate") or "")[:400]
    shadow.causal_effect = "response_plan_merged_distillate"
    shadow.status = "ADMITTED"
    shadow.stop_reason = StopReason.OUTWARD_ANSWER_READY.value

    # Optional second pass only if the packet asks to CONTINUE.
    # Same purpose is refused (no ritual loop). Budget/max still bind.
    if (str(packet.stop_signal).upper() == "CONTINUE"
            and budget.additional_private_passes < budget.max_additional_private):
        req2 = AutopromptRequest(
            request_id=_new_id("apr"),
            pass_index=99,
            purpose=need.purpose,
            budget_tokens=700,
            stop_condition="typed WorkPacket or stop",
            provenance_ids=need.grounds,
            module_id=module_id,
        )
        decision2 = disp.decide(req2)
        shadow.passes.append({
            "pass_id": req2.request_id,
            "purpose": need.purpose,
            "module_id": module_id,
            "honour": decision2.honour,
            "stop_reason": (
                decision2.stop_reason.value if decision2.stop_reason else ""),
            "kind": "ADDITIONAL_PRIVATE_PASS",
            "execution": "ADDITIONAL_PRIVATE_PASS",
        })
        if not decision2.honour:
            shadow.stop_reason = (
                decision2.stop_reason.value if decision2.stop_reason
                else StopReason.OUTWARD_ANSWER_READY.value)

    shadow.budgets = budget.to_public()
    return new_outcome, shadow, budget

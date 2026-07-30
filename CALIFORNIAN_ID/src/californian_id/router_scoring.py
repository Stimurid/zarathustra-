from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .rhetoric import operation_class


@dataclass
class CandidateScore:
    operation: str
    rhetorical_class: str
    canonical_score: float
    critique_bonus: float
    variation_bonus: float
    repeat_operation_penalty: float
    repeat_class_penalty: float
    repeat_trajectory_penalty: float
    total: float
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "rhetorical_class": self.rhetorical_class,
            "canonical_score": round(self.canonical_score, 3),
            "critique_bonus": round(self.critique_bonus, 3),
            "variation_bonus": round(self.variation_bonus, 3),
            "repeat_operation_penalty": round(self.repeat_operation_penalty, 3),
            "repeat_class_penalty": round(self.repeat_class_penalty, 3),
            "repeat_trajectory_penalty": round(self.repeat_trajectory_penalty, 3),
            "total": round(self.total, 3),
            "reasons": list(self.reasons),
        }


def score_candidates(
    candidate_operations: list[str],
    canonical_operation: str,
    turns: list,
    critique_spec,
    variation_spec,
) -> list[CandidateScore]:
    recent_ops = [getattr(t, "operation", "") for t in turns[-3:]]
    recent_classes = [operation_class(op) for op in recent_ops]
    attack_bias = getattr(critique_spec, "attack_bias", getattr(critique_spec, "pressure_bonus", 0.0))
    stabilize_penalty = getattr(
        critique_spec,
        "stabilize_penalty_before_exposure",
        0.15 if attack_bias > 0 else 0.0,
    )
    repeat_penalty = getattr(
        variation_spec,
        "repeat_penalty",
        getattr(variation_spec, "repeat_operation_penalty", 0.0),
    )
    class_repeat_penalty = getattr(
        variation_spec,
        "class_repeat_penalty",
        getattr(variation_spec, "repeat_class_penalty", 0.0),
    )
    noncanonical_bonus = getattr(
        variation_spec,
        "noncanonical_bonus",
        0.55 if getattr(variation_spec, "name", "") == "jazz" else 0.2,
    )
    repeat_trajectory_penalty_default = getattr(
        variation_spec,
        "repeat_trajectory_penalty",
        0.0,
    )
    prefer_class_switch = bool(
        getattr(variation_spec, "prefer_class_switch", getattr(variation_spec, "name", "") in {"normal", "jazz"})
    )
    scored: list[CandidateScore] = []
    for operation in candidate_operations:
        rhetorical_class = operation_class(operation)
        canonical_score = 0.35 if operation == canonical_operation else 0.0
        critique_bonus = 0.0
        variation_bonus = 0.0
        repeat_operation_penalty_value = repeat_penalty if operation in recent_ops else 0.0
        repeat_class_penalty_value = class_repeat_penalty if rhetorical_class in recent_classes else 0.0
        repeat_trajectory_penalty = 0.0
        reasons: list[str] = []
        if operation == canonical_operation:
            reasons.append("canonical")
        else:
            variation_bonus += noncanonical_bonus
            reasons.append(f"{variation_spec.name}:noncanonical")
        if rhetorical_class == "pressure":
            critique_bonus += attack_bias
            reasons.append(f"{critique_spec.name}:pressure")
        elif rhetorical_class == "stabilize" and stabilize_penalty:
            critique_bonus -= stabilize_penalty
            reasons.append(f"{critique_spec.name}:stabilize_penalty")
        if attack_bias < 0 and rhetorical_class in {"closure", "stabilize"}:
            critique_bonus += 0.25
            reasons.append("gentle_bias_to_stabilize")
        if attack_bias > 0 and operation in {"show_cost", "attack_presupposition"}:
            critique_bonus += 0.35
            reasons.append("hard_prefers_cost_or_presupposition")
        if prefer_class_switch and rhetorical_class not in recent_classes:
            variation_bonus += 0.2
            reasons.append(f"{variation_spec.name}:class_switch")
        if len(recent_classes) >= 2 and recent_classes[-1] == recent_classes[-2] == rhetorical_class:
            repeat_trajectory_penalty = repeat_trajectory_penalty_default
            reasons.append(f"repeat_trajectory_penalty={repeat_trajectory_penalty}")
        total = (
            canonical_score
            + critique_bonus
            + variation_bonus
            - repeat_operation_penalty_value
            - repeat_class_penalty_value
            - repeat_trajectory_penalty
        )
        scored.append(
            CandidateScore(
                operation=operation,
                rhetorical_class=rhetorical_class,
                canonical_score=canonical_score,
                critique_bonus=critique_bonus,
                variation_bonus=variation_bonus,
                repeat_operation_penalty=repeat_operation_penalty_value,
                repeat_class_penalty=repeat_class_penalty_value,
                repeat_trajectory_penalty=repeat_trajectory_penalty,
                total=total,
                reasons=reasons,
            )
        )
    scored.sort(key=lambda item: item.total, reverse=True)
    return scored


def summarize_route_trace(route_traces: list[dict[str, Any]]) -> dict[str, Any]:
    turns_scored = len(route_traces)
    selected_ops = [str(t.get("selected_operation") or "") for t in route_traces if t.get("selected_operation")]
    selected_classes = [str(t.get("selected_class") or "") for t in route_traces if t.get("selected_class")]
    canonical_ops = [str(t.get("canonical_operation") or "") for t in route_traces if t.get("canonical_operation")]
    noncanonical = sum(
        1 for trace in route_traces
        if trace.get("selected_operation") and trace.get("canonical_operation")
        and trace.get("selected_operation") != trace.get("canonical_operation")
    )
    pressure_count = sum(1 for cls in selected_classes if cls == "pressure")
    return {
        "turns_scored": turns_scored,
        "noncanonical_selection_rate": (noncanonical / turns_scored) if turns_scored else 0.0,
        "pressure_selection_rate": (pressure_count / turns_scored) if turns_scored else 0.0,
        "turns_routed": len(route_traces),
        "unique_operations": sorted(set(selected_ops)),
        "unique_classes": sorted(set(selected_classes)),
        "canonical_sequence": canonical_ops,
        "operation_sequence": selected_ops,
        "class_sequence": selected_classes,
    }

"""Deterministic scored routing for regime-aware council orchestration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .regimes import CritiqueRegimeSpec, VariationRegimeSpec
from .rhetoric import operation_class, recent_classes, recent_operations, recent_trajectory


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
        return asdict(self)


def score_candidates(
    candidates: list[str],
    canonical_operation: str,
    turns: list[object],
    critique_regime: CritiqueRegimeSpec,
    variation_regime: VariationRegimeSpec,
) -> list[CandidateScore]:
    recent_ops = recent_operations(turns, n=3)
    recent_cls = recent_classes(turns, n=3)
    recent_triplet = recent_trajectory(turns, n=3)
    last_cost_seen = any(op == "show_cost" for op in recent_ops)
    last_class = recent_cls[-1] if recent_cls else ""

    scored: list[CandidateScore] = []
    for operation in candidates:
        rhetorical_class = operation_class(operation)
        reasons: list[str] = []
        canonical_score = (
            1.0 if operation == canonical_operation and not variation_regime.allow_sop_break
            else 0.35 if operation == canonical_operation
            else 0.0
        )
        critique_bonus = 0.0
        variation_bonus = 0.0
        repeat_operation_penalty = 0.0
        repeat_class_penalty = 0.0
        repeat_trajectory_penalty = 0.0

        if rhetorical_class == "pressure":
            critique_bonus += critique_regime.pressure_bonus
            reasons.append(f"{critique_regime.name}:pressure")
            if critique_regime.require_cost_exposure_early and operation == "show_cost":
                critique_bonus += 0.25
                reasons.append(f"{critique_regime.name}:prefer_show_cost")
        if rhetorical_class == "stabilize":
            if operation == "steelman_opponent":
                critique_bonus += critique_regime.steelman_bonus
                reasons.append(f"{critique_regime.name}:steelman_bias")
            if critique_regime.require_cost_exposure_early and not last_cost_seen:
                critique_bonus -= critique_regime.stabilize_penalty_before_exposure
                reasons.append(f"{critique_regime.name}:delay_stabilize_until_cost")

        if operation != canonical_operation and variation_regime.allow_sop_break:
            variation_bonus += variation_regime.noncanonical_bonus
            reasons.append(f"{variation_regime.name}:noncanonical")
        if variation_regime.prefer_class_switch and last_class and rhetorical_class != last_class:
            variation_bonus += 0.2
            reasons.append(f"{variation_regime.name}:class_switch")

        if recent_ops and operation == recent_ops[-1]:
            repeat_operation_penalty = variation_regime.repeat_operation_penalty
            reasons.append("repeat_operation")
        if len(recent_cls) >= 2 and rhetorical_class == recent_cls[-1] == recent_cls[-2]:
            repeat_class_penalty = variation_regime.repeat_class_penalty
            reasons.append("repeat_class")
        elif variation_regime.prefer_class_switch and rhetorical_class in recent_cls[-2:]:
            repeat_class_penalty = variation_regime.repeat_class_penalty / 2
            reasons.append("recent_class_echo")
        if len(recent_triplet) == 3:
            prior_pattern = tuple(list(recent_triplet[-2:]) + [operation])
            if prior_pattern == recent_triplet:
                repeat_trajectory_penalty = variation_regime.repeat_trajectory_penalty
                reasons.append("repeat_trajectory")

        total = (
            canonical_score
            + critique_bonus
            + variation_bonus
            - repeat_operation_penalty
            - repeat_class_penalty
            - repeat_trajectory_penalty
        )
        scored.append(CandidateScore(
            operation=operation,
            rhetorical_class=rhetorical_class,
            canonical_score=canonical_score,
            critique_bonus=critique_bonus,
            variation_bonus=variation_bonus,
            repeat_operation_penalty=repeat_operation_penalty,
            repeat_class_penalty=repeat_class_penalty,
            repeat_trajectory_penalty=repeat_trajectory_penalty,
            total=round(total, 4),
            reasons=reasons,
        ))

    return sorted(
        scored,
        key=lambda item: (item.total, item.operation != canonical_operation, item.operation),
        reverse=True,
    )


def summarize_route_trace(route_traces: list[dict[str, Any]]) -> dict[str, Any]:
    selections = [item.get("selected_operation") for item in route_traces if item.get("selected_operation")]
    classes = [item.get("selected_class") for item in route_traces if item.get("selected_class")]
    canonical_misses = [
        item for item in route_traces
        if item.get("selected_operation") and item.get("canonical_operation") != item.get("selected_operation")
    ]

    def _repeat_rate(items: list[str]) -> float:
        if len(items) < 2:
            return 0.0
        repeats = sum(1 for idx in range(1, len(items)) if items[idx] == items[idx - 1])
        return round(repeats / (len(items) - 1), 4)

    trajectory_repeats = 0
    trajectory_windows = 0
    if len(selections) >= 6:
        for idx in range(3, len(selections) - 2):
            trajectory_windows += 1
            if tuple(selections[idx - 3:idx]) == tuple(selections[idx:idx + 3]):
                trajectory_repeats += 1

    return {
        "turns_scored": len(route_traces),
        "operation_repeat_rate": _repeat_rate(selections),
        "class_repeat_rate": _repeat_rate(classes),
        "trajectory_repeat_rate": (
            round(trajectory_repeats / trajectory_windows, 4) if trajectory_windows else 0.0
        ),
        "noncanonical_selection_rate": (
            round(len(canonical_misses) / len(route_traces), 4) if route_traces else 0.0
        ),
        "pressure_selection_rate": (
            round(sum(1 for cls in classes if cls == "pressure") / len(classes), 4) if classes else 0.0
        ),
    }

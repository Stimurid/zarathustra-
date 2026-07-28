"""Rhetorical classes and deterministic alternatives for routing."""
from __future__ import annotations

from collections.abc import Sequence


OPERATION_CLASS: dict[str, str] = {
    "initial_position": "stabilize",
    "restore_ground": "stabilize",
    "attack": "pressure",
    "attack_presupposition": "pressure",
    "test_value": "pressure",
    "steelman_opponent": "stabilize",
    "shift_scale": "reframe",
    "shift_temporal_horizon": "reframe",
    "shift_ontology": "reframe",
    "build_counterexample": "pressure",
    "introduce_absent_subject": "reframe",
    "show_cost": "pressure",
    "build_future_image": "constructive",
    "draw_practical_implication": "constructive",
    "problematize_question": "destabilize",
    "create_aporia": "destabilize",
    "defend": "stabilize",
    "propose_alliance": "constructive",
    "refuse_alliance": "destabilize",
    "dispute_completion_form": "destabilize",
    "dispute_zarathustra": "destabilize",
}


OPERATION_ALTERNATIVES: dict[str, list[str]] = {
    "initial_position": ["attack_presupposition", "shift_scale"],
    "restore_ground": ["attack", "show_cost"],
    "attack": ["show_cost", "build_counterexample", "shift_ontology"],
    "attack_presupposition": ["show_cost", "shift_ontology", "build_counterexample"],
    "test_value": ["show_cost", "shift_scale", "build_future_image"],
    "steelman_opponent": ["defend", "attack", "problematize_question"],
    "shift_scale": ["test_value", "show_cost", "introduce_absent_subject"],
    "shift_temporal_horizon": ["build_future_image", "show_cost", "introduce_absent_subject"],
    "shift_ontology": ["problematize_question", "create_aporia", "show_cost"],
    "build_counterexample": ["show_cost", "defend", "shift_scale"],
    "introduce_absent_subject": ["show_cost", "build_future_image", "problematize_question"],
    "show_cost": ["build_counterexample", "shift_scale", "build_future_image"],
    "build_future_image": ["show_cost", "introduce_absent_subject", "draw_practical_implication"],
    "draw_practical_implication": ["show_cost", "propose_alliance", "test_value"],
    "problematize_question": ["create_aporia", "show_cost", "introduce_absent_subject"],
    "create_aporia": ["dispute_completion_form", "problematize_question", "show_cost"],
    "defend": ["show_cost", "test_value", "shift_ontology"],
    "propose_alliance": ["draw_practical_implication", "show_cost", "refuse_alliance"],
    "refuse_alliance": ["problematize_question", "show_cost", "create_aporia"],
    "dispute_completion_form": ["create_aporia", "show_cost", "problematize_question"],
    "dispute_zarathustra": ["restore_ground", "problematize_question", "show_cost"],
}


def operation_class(operation: str) -> str:
    return OPERATION_CLASS.get(operation, "unknown")


def recent_operations(turns: Sequence[object], n: int = 3) -> list[str]:
    return [getattr(turn, "operation", "") for turn in turns[-n:] if getattr(turn, "operation", "")]


def recent_classes(turns: Sequence[object], n: int = 3) -> list[str]:
    return [operation_class(op) for op in recent_operations(turns, n=n)]


def recent_trajectory(turns: Sequence[object], n: int = 3) -> tuple[str, ...]:
    ops = recent_operations(turns, n=n)
    if len(ops) < n:
        return tuple()
    return tuple(ops)

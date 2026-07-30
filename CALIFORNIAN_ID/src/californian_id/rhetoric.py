from __future__ import annotations


_OPERATION_CLASSES = {
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
    "build_future_image": "elaborate",
    "draw_practical_implication": "stabilize",
    "problematize_question": "meta",
    "create_aporia": "meta",
    "defend": "stabilize",
    "propose_alliance": "closure",
    "refuse_alliance": "closure",
    "dispute_completion_form": "meta",
    "dispute_zarathustra": "meta",
}


OPERATION_ALTERNATIVES = {
    "initial_position": ["restore_ground", "build_future_image"],
    "attack_presupposition": ["attack", "test_value", "show_cost"],
    "attack": ["attack_presupposition", "build_counterexample", "show_cost"],
    "test_value": ["show_cost", "steelman_opponent", "shift_scale"],
    "shift_temporal_horizon": ["build_future_image", "show_cost", "shift_scale"],
    "build_future_image": ["show_cost", "draw_practical_implication", "shift_temporal_horizon"],
    "show_cost": ["shift_ontology", "draw_practical_implication", "build_future_image"],
    "problematize_question": ["shift_ontology", "create_aporia", "dispute_completion_form"],
    "defend": ["show_cost", "shift_ontology", "restore_ground", "steelman_opponent", "draw_practical_implication"],
    "propose_alliance": ["draw_practical_implication", "defend", "refuse_alliance"],
    "dispute_completion_form": ["create_aporia", "problematize_question", "defend"],
}


def operation_class(operation: str) -> str:
    return _OPERATION_CLASSES.get(operation, "other")


def recent_operations(turns: list, n: int = 3) -> list[str]:
    return [getattr(t, "operation", "") for t in turns[-n:]]


def recent_classes(turns: list, n: int = 3) -> list[str]:
    return [operation_class(op) for op in recent_operations(turns, n=n)]

"""Formal runtime contracts for critique and variation regimes."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CritiqueRegimeSpec:
    name: str
    pressure_bonus: float
    stabilize_penalty_before_exposure: float
    steelman_bonus: float
    directness_hint: str
    require_cost_exposure_early: bool


@dataclass(frozen=True)
class VariationRegimeSpec:
    name: str
    noncanonical_bonus: float
    repeat_operation_penalty: float
    repeat_class_penalty: float
    repeat_trajectory_penalty: float
    prefer_class_switch: bool
    allow_sop_break: bool
    prompt_hint: str


CRITIQUE_REGIMES: dict[str, CritiqueRegimeSpec] = {
    "gentle": CritiqueRegimeSpec(
        name="gentle",
        pressure_bonus=0.0,
        stabilize_penalty_before_exposure=0.0,
        steelman_bonus=0.45,
        directness_hint=(
            "Начинай с аккуратной реконструкции позиции и не называй слабость "
            "лобовой формулой, если можно вскрыть ее через уточнение."
        ),
        require_cost_exposure_early=False,
    ),
    "balanced": CritiqueRegimeSpec(
        name="balanced",
        pressure_bonus=0.2,
        stabilize_penalty_before_exposure=0.15,
        steelman_bonus=0.1,
        directness_hint=(
            "Держи критическую прямоту, но не жертвуй различимостью оснований и цен."
        ),
        require_cost_exposure_early=False,
    ),
    "hard": CritiqueRegimeSpec(
        name="hard",
        pressure_bonus=1.1,
        stabilize_penalty_before_exposure=0.45,
        steelman_bonus=-0.1,
        directness_hint=(
            "Не смягчай уязвимость, если она обнаружена: сначала назови слабость, "
            "цену или предпосылку, а затем уже допускай защиту."
        ),
        require_cost_exposure_early=True,
    ),
}


VARIATION_REGIMES: dict[str, VariationRegimeSpec] = {
    "strict": VariationRegimeSpec(
        name="strict",
        noncanonical_bonus=0.0,
        repeat_operation_penalty=0.05,
        repeat_class_penalty=0.05,
        repeat_trajectory_penalty=0.05,
        prefer_class_switch=False,
        allow_sop_break=False,
        prompt_hint="Сохраняй канонический порядок совета, если нет явной причины отклониться.",
    ),
    "normal": VariationRegimeSpec(
        name="normal",
        noncanonical_bonus=0.2,
        repeat_operation_penalty=0.2,
        repeat_class_penalty=0.25,
        repeat_trajectory_penalty=0.3,
        prefer_class_switch=True,
        allow_sop_break=True,
        prompt_hint="Меняй класс хода, когда повтор уже заметен, но не ломай сцену ради эффекта.",
    ),
    "jazz": VariationRegimeSpec(
        name="jazz",
        noncanonical_bonus=0.55,
        repeat_operation_penalty=0.45,
        repeat_class_penalty=0.7,
        repeat_trajectory_penalty=0.85,
        prefer_class_switch=True,
        allow_sop_break=True,
        prompt_hint=(
            "Не повторяй один и тот же риторический паттерн два цикла подряд: "
            "при прочих равных предпочитай контрастный, но релевантный класс хода."
        ),
    ),
}

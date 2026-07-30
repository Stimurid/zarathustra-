from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CritiqueRegime:
    name: str
    directness_hint: str
    attack_bias: float


@dataclass(frozen=True)
class VariationRegime:
    name: str
    prompt_hint: str
    repeat_penalty: float
    class_repeat_penalty: float


CRITIQUE_REGIMES: dict[str, CritiqueRegime] = {
    "gentle": CritiqueRegime(
        name="gentle",
        directness_hint="Критикуй мягко: сначала реконструируй сильную версию позиции, затем возражай без лишней агрессии.",
        attack_bias=-0.4,
    ),
    "balanced": CritiqueRegime(
        name="balanced",
        directness_hint="Критикуй прямо, но по существу: вскрывай допущения, цену и слабости без театральной жестокости.",
        attack_bias=0.0,
    ),
    "hard": CritiqueRegime(
        name="hard",
        directness_hint="Критикуй жёстко: бей в скрытые допущения, цену и внутренние противоречия без смягчающих оборотов.",
        attack_bias=0.8,
    ),
}


VARIATION_REGIMES: dict[str, VariationRegime] = {
    "strict": VariationRegime(
        name="strict",
        prompt_hint="Держи ход близко к канонической операции; избегай лишней импровизации.",
        repeat_penalty=0.2,
        class_repeat_penalty=0.1,
    ),
    "normal": VariationRegime(
        name="normal",
        prompt_hint="Допускай умеренное разнообразие ходов, но не теряй сцепление со сценой.",
        repeat_penalty=0.7,
        class_repeat_penalty=0.35,
    ),
    "jazz": VariationRegime(
        name="jazz",
        prompt_hint="Избегай одинакового риторического паттерна несколько ходов подряд; меняй тип захода и класс операции.",
        repeat_penalty=1.3,
        class_repeat_penalty=0.8,
    ),
}

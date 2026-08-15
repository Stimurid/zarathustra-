from __future__ import annotations

from dataclasses import dataclass

from .prompt_assets import runtime_block


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


# Workbench Stage 0 — the PROMPT_BEHAVIOR half of each regime now comes from
# data/prompt_assets/{critique,variation}.*.md. The DETERMINISTIC_ALGORITHM half
# (attack_bias, repeat penalties) is deliberately left exactly where it was:
# a hybrid control is represented with several effects, never split or moved.
CRITIQUE_REGIMES: dict[str, CritiqueRegime] = {
    "gentle": CritiqueRegime(
        name="gentle",
        directness_hint=runtime_block("critique.gentle"),
        attack_bias=-0.4,
    ),
    "balanced": CritiqueRegime(
        name="balanced",
        directness_hint=runtime_block("critique.balanced"),
        attack_bias=0.0,
    ),
    "hard": CritiqueRegime(
        name="hard",
        directness_hint=runtime_block("critique.hard"),
        attack_bias=0.8,
    ),
}


VARIATION_REGIMES: dict[str, VariationRegime] = {
    "strict": VariationRegime(
        name="strict",
        prompt_hint=runtime_block("variation.strict"),
        repeat_penalty=0.2,
        class_repeat_penalty=0.1,
    ),
    "normal": VariationRegime(
        name="normal",
        prompt_hint=runtime_block("variation.normal"),
        repeat_penalty=0.7,
        class_repeat_penalty=0.35,
    ),
    "jazz": VariationRegime(
        name="jazz",
        prompt_hint=runtime_block("variation.jazz"),
        repeat_penalty=1.3,
        class_repeat_penalty=0.8,
    ),
}

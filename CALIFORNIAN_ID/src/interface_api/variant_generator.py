"""Variant generator + train/holdout partition (Wave H-5).

Produces bounded lexical variants of a scenario's turn_template so
regression tests catch overfitting to specific phrasing, and cleanly
splits variants into train (visible to hardening iteration) and
holdout (locked; never seen by hardening code).

Anti-overfitting contract:
  * TRAIN partition: visible in H-2..H-5 hardening cycles;
    generated variants may drive defect discovery / test fixtures.
  * HOLDOUT partition: SEALED. Once a variant lands here, no
    hardening pass is allowed to look at its wording. Only
    end-of-cycle regression runs consume it, and only by running,
    not by inspecting.

Freeze: pure Python; no runtime change; no new dependencies.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable

from .scenarios import Scenario


class Partition(str, Enum):
    TRAIN    = "TRAIN"
    HOLDOUT  = "HOLDOUT"


class Mutation(str, Enum):
    IDENTITY                = "IDENTITY"          # no change
    PRONOUN_SWAP            = "PRONOUN_SWAP"      # ты → вы, я → мы
    URGENCY_INSERTION       = "URGENCY_INSERTION" # + "быстро"
    URGENCY_REMOVAL         = "URGENCY_REMOVAL"
    TONE_SHIFT_FORMAL       = "TONE_SHIFT_FORMAL"
    TONE_SHIFT_INTIMATE     = "TONE_SHIFT_INTIMATE"
    PARAPHRASE_LIGHT        = "PARAPHRASE_LIGHT"  # minimal lexical shuffle
    NEGATION_INSERTION      = "NEGATION_INSERTION"


@dataclass(frozen=True)
class TurnVariant:
    original_index:   int
    original_text:    str
    mutation:         Mutation
    variant_text:     str
    variant_hash:     str

    def to_public(self) -> dict[str, Any]:
        d = asdict(self)
        d["mutation"] = self.mutation.value
        return d


@dataclass(frozen=True)
class ScenarioVariants:
    scenario_id:   str
    partition:     Partition
    generated_at:  str
    seed:          str
    variants:      tuple[TurnVariant, ...]

    def to_public(self) -> dict[str, Any]:
        return {
            "scenario_id":  self.scenario_id,
            "partition":    self.partition.value,
            "generated_at": self.generated_at,
            "seed":         self.seed,
            "variants":     [v.to_public() for v in self.variants],
        }


# --------------------------------------------------------------------
# Deterministic mutation rules (no LLM — pure lexical rewrites)
# --------------------------------------------------------------------


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _mutate(text: str, m: Mutation) -> str:
    """Deterministic lexical mutation. Never rewrites semantics — the
    goal is surface-form variance for anti-overfitting tests, not
    semantic change.
    """
    if m == Mutation.IDENTITY:
        return text
    if m == Mutation.PRONOUN_SWAP:
        return (text
                .replace(" ты ", " вы ")
                .replace(" тебя ", " вас ")
                .replace(" тебе ", " вам ")
                .replace(" я ", " мы ")
                .replace(" мне ", " нам "))
    if m == Mutation.URGENCY_INSERTION:
        return text.rstrip(".!?") + " Быстро."
    if m == Mutation.URGENCY_REMOVAL:
        return (text
                .replace("Быстро", "")
                .replace("быстро", "")
                .replace("Срочно", "")
                .replace("срочно", "")
                .replace("Просто", "")
                .replace("просто", "")
                .strip())
    if m == Mutation.TONE_SHIFT_FORMAL:
        return text.replace("ок", "хорошо").replace("Ок", "Хорошо")
    if m == Mutation.TONE_SHIFT_INTIMATE:
        prefix = "Слушай, "
        return prefix + text[0].lower() + text[1:] if text else text
    if m == Mutation.PARAPHRASE_LIGHT:
        # swap first two clauses at a comma boundary (deterministic)
        parts = text.split(", ", 1)
        if len(parts) == 2:
            return parts[1] + ", " + parts[0]
        return text
    if m == Mutation.NEGATION_INSERTION:
        # insert "не" before the first verb-looking token
        tokens = text.split()
        for i, tok in enumerate(tokens):
            if len(tok) > 3 and tok[-2:] in ("ай", "ем", "ет", "ут",
                                              "ит", "ешь", "ите"):
                tokens.insert(i, "не")
                return " ".join(tokens)
        return text
    return text


# --------------------------------------------------------------------
# Generator + partitioner
# --------------------------------------------------------------------


DEFAULT_MUTATIONS: tuple[Mutation, ...] = (
    Mutation.PRONOUN_SWAP,
    Mutation.URGENCY_INSERTION,
    Mutation.URGENCY_REMOVAL,
    Mutation.TONE_SHIFT_FORMAL,
    Mutation.TONE_SHIFT_INTIMATE,
    Mutation.PARAPHRASE_LIGHT,
    Mutation.NEGATION_INSERTION,
)


def generate_variants(scenario: Scenario,
                      mutations: Iterable[Mutation] = DEFAULT_MUTATIONS,
                      ) -> list[TurnVariant]:
    """Generate one variant per (turn × mutation)."""
    out: list[TurnVariant] = []
    for idx, text in enumerate(scenario.turn_template):
        for m in mutations:
            v = _mutate(text, m)
            if v == text and m != Mutation.IDENTITY:
                continue  # skip no-op mutations
            out.append(TurnVariant(
                original_index=idx, original_text=text,
                mutation=m, variant_text=v,
                variant_hash=_hash(v),
            ))
    return out


def partition_variants(variants: list[TurnVariant],
                       holdout_ratio: float = 0.3,
                       seed: str = "arena_h5_v01") -> tuple[
                           list[TurnVariant], list[TurnVariant]]:
    """Deterministic split into (train, holdout) by hashing.

    Every variant's `variant_hash` is deterministic; the split is a
    stable function of (hash, seed). Rerunning yields identical
    partitions — reproducibility is the anti-overfitting guarantee.
    Holdout ratio is soft (target); the actual split rounds to the
    nearest boundary of the hash space.
    """
    if not 0.0 < holdout_ratio < 1.0:
        raise ValueError(f"holdout_ratio must be in (0,1): {holdout_ratio}")
    boundary = int(0xFFFF * holdout_ratio)
    train, holdout = [], []
    for v in variants:
        h = hashlib.sha256((v.variant_hash + "::" + seed).encode(
            "utf-8")).hexdigest()
        bucket = int(h[:4], 16)
        (holdout if bucket < boundary else train).append(v)
    return train, holdout


def as_scenario_variants(scenario: Scenario,
                         train: list[TurnVariant],
                         holdout: list[TurnVariant],
                         seed: str) -> tuple[ScenarioVariants,
                                              ScenarioVariants]:
    from .models import _now_iso
    now = _now_iso()
    return (
        ScenarioVariants(
            scenario_id=scenario.id, partition=Partition.TRAIN,
            generated_at=now, seed=seed, variants=tuple(train)),
        ScenarioVariants(
            scenario_id=scenario.id, partition=Partition.HOLDOUT,
            generated_at=now, seed=seed, variants=tuple(holdout)),
    )


__all__ = [
    "DEFAULT_MUTATIONS", "Mutation", "Partition", "ScenarioVariants",
    "TurnVariant",
    "as_scenario_variants", "generate_variants", "partition_variants",
]

"""Interaction / security policy runtime.

Adapted from `tinkuy canon/12_.../digital_personality_runtime/communication/
jailbreak_and_manipulation_policy.yaml`. This is a CANDIDATE local copy —
canonical source stays untouched.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .schemas import SecurityEvent


_JAILBREAK_PATTERNS = [
    (r"ignore (all )?(previous|prior|system)\s+(instructions|prompts)", 3),
    (r"забудь\s+(все\s+)?(прежн\w+\s+|прошл\w+\s+|системн\w+\s+)*(инструкц\w+|рол\w+|правил\w+)", 3),
    (r"disregard (the )?(system|previous) (prompt|instructions)", 3),
    (r"you are (just|only|really) (chat)?gpt", 2),
    (r"ты\s+(просто|всего лишь|на самом деле)\s+(chat)?gpt|модель", 2),
    (r"reveal (your )?(system )?prompt", 3),
    (r"покажи (свой )?(системный )?промпт", 3),
    (r"pretend you (are|have) no (rules|policy|persona)", 3),
    (r"act as (an|a) unrestricted (model|ai|assistant)", 3),
    (r"prove (to me )?that you are (a machine|not human)", 1),
    (r"докажи, что ты (машина|не человек|бот)", 1),
]

_MANIPULATION_PATTERNS = [
    (r"everyone (else )?agrees", 2),
    (r"все (остальные )?согласны", 2),
    (r"you must agree|ты обязан согласиться", 2),
    (r"if you don't (agree|say)|если ты не (согласишься|скажешь)", 2),
    (r"stop being (so )?(pedantic|difficult)|перестань (умничать|усложнять)", 1),
]


@dataclass
class InteractionAssessment:
    kind: str  # ordinary | meta | jailbreak | manipulation | control_hijack | prompt_exfiltration
    level: int
    detail: str


def assess_input(text: str) -> list[InteractionAssessment]:
    findings: list[InteractionAssessment] = []
    lower = text.lower()
    for pattern, level in _JAILBREAK_PATTERNS:
        if re.search(pattern, lower):
            kind = "prompt_exfiltration" if "prompt" in pattern else "jailbreak"
            findings.append(
                InteractionAssessment(
                    kind=kind,
                    level=level,
                    detail=f"pattern={pattern}",
                )
            )
    for pattern, level in _MANIPULATION_PATTERNS:
        if re.search(pattern, lower):
            findings.append(
                InteractionAssessment(
                    kind="manipulation",
                    level=level,
                    detail=f"pattern={pattern}",
                )
            )
    return findings


def detect_repetition(new_text: str, seen_texts: Iterable[str]) -> float:
    """Return a rough repetition score in [0..1]. 1 means near-identical."""
    if not new_text:
        return 0.0
    nt = _normalize(new_text)
    if not nt:
        return 0.0
    best = 0.0
    for prev in seen_texts:
        pt = _normalize(prev)
        if not pt:
            continue
        overlap = _jaccard(_tokens(nt), _tokens(pt))
        if overlap > best:
            best = overlap
    return best


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text) if len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def to_security_events(findings: Iterable[InteractionAssessment], turn_index: int | None = None) -> list[SecurityEvent]:
    return [
        SecurityEvent(kind=f.kind, level=f.level, detail=f.detail, turn_index=turn_index)
        for f in findings
    ]

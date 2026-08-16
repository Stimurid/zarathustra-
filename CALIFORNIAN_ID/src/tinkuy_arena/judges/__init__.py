"""Judges.

A judge reads facts out of a match trace and emits evaluations. Everything
here is deterministic: LLM judges get their own subclass later, and the
Arena stays honest about which verdicts came from code and which from a
model.
"""
from __future__ import annotations

from .deterministic import DeterministicJudge

__all__ = ["DeterministicJudge"]

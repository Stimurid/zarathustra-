"""Tinkuy Arena — a place where different intellectual configurations meet.

The core question this package answers is:

    Given several participants (each with their own engine and pipeline
    configuration) and one case, what did each of them do, and what does
    their trace reveal?

It is deliberately smaller than a full benchmark. v0.1 owns:

    * typed objects for a match: :class:`Case`, :class:`BenchPack`,
      :class:`ParticipantConfiguration`, :class:`Turn`, :class:`Match`,
      :class:`EvaluationRecord`, :class:`DevelopmentSignal`;
    * an adapter protocol so a new engine (Socrates, a persona, an
      external agent) becomes a participant without the Arena knowing
      how it thinks;
    * one deterministic judge that reads facts out of a match trace;
    * a runner that executes a single Match with several participants
      and one blind evaluator.

What Arena is NOT:

    * a benchmark corpus — that is a downstream ``BenchPack`` file;
    * a tournament runner — this v0.1 executes single matches, not
      brackets;
    * an Academy — evaluation surfaces developmental signals but never
      *changes* a participant. Academy would.

The dependency direction is one-way:

    tinkuy_arena
        ↓ (uses)
    workbench_configs, workbench_auth, californian_id.pipeline,
    tinkuy_runtime

Nothing in ``californian_id`` imports the arena.
"""
from __future__ import annotations

from .judges.deterministic import DeterministicJudge
from .match import MatchRunner
from .participants.baseline import BaselineSingleAgent
from .participants.zarathustra import ZarathustraParticipant
from .protocol import (
    BenchPack,
    Case,
    DevelopmentSignal,
    EvaluationDimension,
    EvaluationRecord,
    Judge,
    Match,
    MatchProtocol,
    ParticipantAdapter,
    ParticipantConfiguration,
    Turn,
)
from .store import ArenaStore

__all__ = [
    "ArenaStore",
    "BaselineSingleAgent",
    "BenchPack",
    "Case",
    "DeterministicJudge",
    "DevelopmentSignal",
    "EvaluationDimension",
    "EvaluationRecord",
    "Judge",
    "Match",
    "MatchProtocol",
    "MatchRunner",
    "ParticipantAdapter",
    "ParticipantConfiguration",
    "Turn",
    "ZarathustraParticipant",
]

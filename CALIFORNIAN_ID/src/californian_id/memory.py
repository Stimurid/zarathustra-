"""Conversation memory. Minimal in-run store; disk persistence via trace."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .schemas import TurnRecord


@dataclass
class ConversationMemory:
    topic: str = ""
    voices_called: list[str] = field(default_factory=list)
    arguments_seen: list[str] = field(default_factory=list)
    positions_changed: list[dict[str, Any]] = field(default_factory=list)
    unresolved_conflicts: list[dict[str, Any]] = field(default_factory=list)
    final_position: str | None = None
    security_events: list[dict[str, Any]] = field(default_factory=list)

    def observe_turn(self, turn: TurnRecord) -> None:
        if turn.persona_id not in self.voices_called:
            self.voices_called.append(turn.persona_id)
        if turn.utterance and turn.utterance not in self.arguments_seen:
            self.arguments_seen.append(turn.utterance[:400])

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "voices_called": list(self.voices_called),
            "arguments_seen": list(self.arguments_seen),
            "positions_changed": list(self.positions_changed),
            "unresolved_conflicts": list(self.unresolved_conflicts),
            "final_position": self.final_position,
            "security_events": list(self.security_events),
        }

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .schemas import (
    ArgumentMap,
    BodyProjection,
    CompletionOutcome,
    SecurityEvent,
    SituationAnalysis,
    Synthesis,
    TurnRecord,
    to_plain,
)


RUN_STATES = (
    "RECEIVED",
    "ANALYZED",
    "CAST_SELECTED",
    "COUNCIL_RUNNING",
    "STOPPING_CHECK",
    "COMPLETING",           # renamed SYNTHESIZING: choosing form + assembling completion
    "VALIDATING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
)


class InvalidTransition(RuntimeError):
    pass


_ALLOWED = {
    "RECEIVED": {"ANALYZED", "FAILED", "CANCELLED"},
    "ANALYZED": {"CAST_SELECTED", "FAILED", "CANCELLED"},
    "CAST_SELECTED": {"COUNCIL_RUNNING", "FAILED", "CANCELLED"},
    "COUNCIL_RUNNING": {"STOPPING_CHECK", "FAILED", "CANCELLED"},
    "STOPPING_CHECK": {"COUNCIL_RUNNING", "COMPLETING", "FAILED", "CANCELLED"},
    "COMPLETING": {"VALIDATING", "FAILED", "CANCELLED"},
    "VALIDATING": {"COMPLETED", "FAILED", "CANCELLED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


@dataclass
class RunState:
    run_id: str
    mode: str
    input_text: str
    situation: SituationAnalysis | None = None
    persona_registry_snapshot: dict[str, str] = field(default_factory=dict)
    selected_personas: list[str] = field(default_factory=list)
    turns: list[TurnRecord] = field(default_factory=list)
    argument_map: ArgumentMap = field(default_factory=ArgumentMap)
    body: BodyProjection = field(default_factory=BodyProjection)
    security_events: list[SecurityEvent] = field(default_factory=list)
    stopping_reason: str | None = None
    novelty_scores: list[float] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    completion: CompletionOutcome | None = None
    # backward-compat: kept populated only when completion.form == "synthesis"
    synthesis: Synthesis | None = None
    errors: list[str] = field(default_factory=list)
    status: str = "RECEIVED"
    timestamps: dict[str, str] = field(default_factory=dict)

    def stamp(self, label: str) -> None:
        self.timestamps[label] = datetime.now(timezone.utc).isoformat()

    def transition(self, new_state: str) -> None:
        if new_state not in RUN_STATES:
            raise InvalidTransition(f"Unknown state {new_state}")
        if new_state not in _ALLOWED[self.status]:
            raise InvalidTransition(
                f"Illegal transition {self.status} -> {new_state}"
            )
        self.status = new_state
        self.stamp(f"entered_{new_state}")

    def as_json(self) -> dict[str, Any]:
        return to_plain(self)

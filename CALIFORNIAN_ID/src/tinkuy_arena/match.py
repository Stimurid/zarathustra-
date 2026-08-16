"""MatchRunner — executes one Match with N participants and M judges.

v0.1 executes participants sequentially. Concurrency lands when it stops
being a distraction from the acceptance question: does the Arena hold the
shape it promises?
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Iterable

from .protocol import (
    Case,
    EvaluationRecord,
    Judge,
    Match,
    MatchProtocol,
    ParticipantAdapter,
    ParticipantConfiguration,
    Turn,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MatchRunner:
    """Owns the sequence — request participant, then judge.

    The runner is deliberately dumb. It does not know:
        * which engine any participant runs;
        * which dimension any judge produces;
        * whether the case has a "right answer";
        * what to do with the evaluations after they land.
    That last point matters — outcomes belong to whoever displays them
    (Workbench today, Academy tomorrow), not to this runner.
    """

    def __init__(self, adapters: dict[str, ParticipantAdapter],
                 judges: list[Judge]) -> None:
        self.adapters = dict(adapters)
        self.judges = list(judges)

    def run_match(self, bench_id: str, case: Case,
                  configs: Iterable[ParticipantConfiguration],
                  protocol: MatchProtocol | None = None) -> Match:
        configs = list(configs)
        if not configs:
            raise ValueError("match requires at least one participant")
        proto = protocol or MatchProtocol()

        match_id = f"match_{secrets.token_hex(8)}"
        match = Match(
            match_id=match_id, bench_id=bench_id, case=case,
            participants=configs, protocol=proto,
            status="running", started_at=_now())

        # --- turns ---
        for config in configs:
            adapter = self.adapters.get(config.participant_id)
            if adapter is None:
                match.turns.append(Turn(
                    turn_id=f"turn_{match_id}_{config.participant_id}_0",
                    match_id=match_id,
                    participant_id=config.participant_id,
                    request_index=0,
                    request_text=case.text,
                    response_text="",
                    error=f"no adapter registered for participant "
                          f"{config.participant_id!r}",
                ))
                continue
            match.turns.append(
                adapter.respond(config, case, match_id, request_index=0))

        # --- judgment ---
        for config in configs:
            for judge in self.judges:
                match.evaluations.extend(judge.evaluate(match, config.participant_id))

        match.status = "completed"
        match.finished_at = _now()
        return match

    def evaluation_matrix(self, match: Match) -> dict[str, dict[str, str]]:
        """Compact view: {participant_id: {dim_id: verdict}}."""
        out: dict[str, dict[str, str]] = {}
        for e in match.evaluations:
            out.setdefault(e.participant_id, {})[e.dim_id] = e.verdict
        return out

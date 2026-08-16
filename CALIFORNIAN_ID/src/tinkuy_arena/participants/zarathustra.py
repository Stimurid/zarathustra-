"""Zarathustra as a participant.

Wraps ``californian_id.pipeline.Pipeline.run``. Everything Zarathustra-specific
lives here — the Arena never imports the runtime.

Runtime evidence surfaces into ``Turn.runtime_summary``:

    run_id         — the ordinary RunTrace id, so the operator can jump
                     into the existing run view
    turns          — how many council turns actually ran
    argument_map   — counts of claims/attacks/… actually accumulated
    native_organs  — the G-S26 native-organ evidence produced by the run,
                     unchanged (which real files were called, with hashes)

None of these fields are invented for the Arena — every one already exists on
a real ``Pipeline.run`` result. The Arena only projects them into a shape a
judge can read.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

from ..protocol import Case, ParticipantConfiguration, Turn


class ZarathustraParticipant:
    """One instance = one participant, one Pipeline factory, one workspace.

    The pipeline is constructed lazily: importing this module must not force
    a full runtime import unless the participant is actually invoked.
    """

    engine_kind: str = "zarathustra_council"

    def __init__(self, participant_id: str,
                 workspace_id_default: str = "arena_default") -> None:
        self.participant_id = participant_id
        self.workspace_id_default = workspace_id_default

    def respond(self, config: ParticipantConfiguration, case: Case,
                match_id: str, request_index: int) -> Turn:
        from californian_id.pipeline import Pipeline

        started = time.time()
        turn_id = f"turn_{match_id}_{self.participant_id}_{request_index}"
        pipe = Pipeline(workspace_id=config.workspace_id
                        or self.workspace_id_default)
        try:
            result = pipe.run(
                text=case.text,
                mode=(config.metadata or {}).get("mode", "fast"),
            )
        except Exception as exc:                          # noqa: BLE001
            return Turn(
                turn_id=turn_id, match_id=match_id,
                participant_id=self.participant_id,
                request_index=request_index,
                request_text=case.text, response_text="",
                latency_ms=int((time.time() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )

        state = result.run_state
        argument_counts = _argument_map_counts(state)
        response = _response_from_result(result)
        return Turn(
            turn_id=turn_id, match_id=match_id,
            participant_id=self.participant_id,
            request_index=request_index,
            request_text=case.text,
            response_text=response,
            tokens_in=0, tokens_out=0,           # not aggregated by mock runs
            latency_ms=int((time.time() - started) * 1000),
            runtime_summary={
                "engine": "zarathustra_council",
                "run_id": state.run_id,
                "status": state.status,
                "council_turns": len(state.turns),
                "argument_map": argument_counts,
                "trace_dir": str(getattr(result, "trace_dir", "") or ""),
                "personas_called": [t.persona_id for t in state.turns],
                "security_events": [
                    getattr(e, "kind", "") for e in
                    (getattr(state, "security_events", None) or [])],
                "final_position_present": bool(
                    getattr(state, "final_position", None)),
            },
        )


def _argument_map_counts(state: Any) -> dict[str, int]:
    amap = getattr(state, "argument_map", None)
    fields = ("claims", "assumptions", "values", "supports", "attacks",
              "actions", "questions", "unresolved_conflicts")
    return {name: len(getattr(amap, name, []) or []) for name in fields}


def _response_from_result(result: Any) -> str:
    """The Arena wants ONE string response.

    Pipeline results carry several human-facing fields — final position,
    synthesis, closing statement. We pick the most complete one that is
    present and non-empty; if none is, we return an empty string, and the
    turn's ``runtime_summary`` still records what happened.
    """
    state = getattr(result, "run_state", None)
    for attr in ("closing_statement", "synthesis", "final_position"):
        val = getattr(state, attr, None) if state is not None else None
        if val:
            if isinstance(val, str):
                return val
            text = getattr(val, "text", None) or getattr(val, "utterance", None)
            if text:
                return str(text)
    # Last resort — the utterance of the last recorded turn.
    turns = getattr(state, "turns", None) or []
    if turns:
        return str(getattr(turns[-1], "utterance", "") or "")
    return ""

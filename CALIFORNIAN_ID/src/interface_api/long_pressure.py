"""LONG_PRESSURE_SESSION orchestrator.

Replays a scenario's `turn_template` (typically 12–50 turns) against a
single Session, collecting per-turn Runs + EpistemicEvents + a final
auto-populated EvaluationRecord. Every LLM call still goes through the
existing SocratesRuntime — this module is coordination only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .epistemic_events import EpistemicEvent, extract_events
from .evaluation import EvaluationRecord, auto_populate
from .models import InputArtifact, InputKind, RunMode, Session
from .runtime_binding import execute_run
from .scenarios import Scenario, ScenarioState, get_registry
from .state import InterfaceStore


class LongPressureError(Exception):
    """Typed error for invalid orchestrator invocation."""


def _new_input(session: Session, text: str) -> InputArtifact:
    return InputArtifact.new(
        session_id=session.session_id, kind=InputKind.TEXT,
        body_text=text, mime="text/plain",
    )


def run_long_pressure(store: InterfaceStore, session: Session,
                      scenario: Scenario,
                      mode: RunMode = RunMode.FAST,
                      runs_dir: str | Path = "runs/interface",
                      max_turns: int | None = None,
                      ) -> dict[str, Any]:
    """Execute every turn of `scenario.turn_template` against `session`.

    Returns a dict:
      {
        "session_id":   ...,
        "scenario_id":  scenario.id,
        "turns":        [{"input_id", "run_id", "events": [...]}] * N,
        "events":       flat list of all epistemic events (public dicts),
        "evaluation":   EvaluationRecord.to_public(),
      }

    Refuses to run if:
      * scenario is not enabled (source_blocked / draft),
      * turn_template is empty,
      * max_turns > 0 requested but exceeds template length.
    """
    if scenario.state != ScenarioState.ENABLED:
        raise LongPressureError(
            f"scenario {scenario.id} is not enabled "
            f"(state={scenario.state.value}, "
            f"blocker={scenario.blocker_reason!r})")
    if not scenario.turn_template:
        raise LongPressureError(
            f"scenario {scenario.id} has empty turn_template")

    turns_to_play = list(scenario.turn_template)
    if max_turns is not None and max_turns > 0:
        turns_to_play = turns_to_play[:max_turns]

    # Bind scenario id on the session for downstream evaluation lookup.
    if session.scenario_id != scenario.id:
        session.scenario_id = scenario.id
        store.put_session(session)

    turn_records: list[dict[str, Any]] = []
    all_events: list[EpistemicEvent] = []
    for idx, human_text in enumerate(turns_to_play, start=1):
        inp = _new_input(session, human_text)
        store.put_input(inp)
        run = execute_run(store, session, inp, mode=mode, runs_dir=runs_dir)
        events = extract_events(run)
        all_events.extend(events)
        turn_records.append({
            "turn_index":  idx,
            "input_id":    inp.input_id,
            "run_id":      run.run_id,
            "run_status":  run.status.value,
            "terminal":    run.terminal,
            "events":      [e.to_public() for e in events],
        })
        # Re-hydrate the session in case runtime_binding bound context_id.
        session = store.get_session(session.session_id) or session

    evaluation = auto_populate(
        session_id=session.session_id,
        scenario_id=scenario.id,
        events=all_events,
        turns=len(turn_records),
    )
    store.put_evaluation(evaluation)

    return {
        "session_id":  session.session_id,
        "scenario_id": scenario.id,
        "turns":       turn_records,
        "events":      [e.to_public() for e in all_events],
        "evaluation":  evaluation.to_public(),
    }


__all__ = ["LongPressureError", "run_long_pressure"]

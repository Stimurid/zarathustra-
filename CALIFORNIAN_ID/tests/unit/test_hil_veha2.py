"""B-5.5 Веха 2 — steer / sliders / user_voice injection."""
from __future__ import annotations

import threading
import time

import pytest

from californian_id import runtime_control as rc


# ---------- Zarathustra.route_next ----------

def test_route_next_respects_steer_override():
    from californian_id.zarathustra import Zarathustra
    from californian_id.models.mock import MockClient
    from californian_id.schemas import SituationAnalysis

    z = Zarathustra()
    client = MockClient()
    situation = SituationAnalysis(topic="test", genre="statement")
    registry = ["LENS_A", "LENS_B", "LENS_C"]
    decision = z.route_next(
        client, registry, already_called=[], turns=[], situation=situation,
        steer_override={"persona_id": "LENS_C", "operation": "attack",
                        "reason": "user picked C"},
    )
    assert decision.next_persona == "LENS_C"
    assert decision.operation == "attack"
    assert "user_steer" in decision.reason
    assert decision.trace["user_steer"] is True


def test_route_next_ignores_steer_for_unknown_persona():
    from californian_id.zarathustra import Zarathustra
    from californian_id.models.mock import MockClient
    from californian_id.schemas import SituationAnalysis

    z = Zarathustra()
    client = MockClient()
    situation = SituationAnalysis(topic="test", genre="statement")
    decision = z.route_next(
        client, ["LENS_A", "LENS_B"], already_called=[], turns=[],
        situation=situation,
        steer_override={"persona_id": "LENS_Z_UNKNOWN", "operation": "attack"},
    )
    # override должен быть проигнорирован — фолбэк на нормальный route
    assert decision.next_persona in {"LENS_A", "LENS_B"}


def test_route_next_filters_persona_by_slider_weight():
    from californian_id.zarathustra import Zarathustra
    from californian_id.models.mock import MockClient
    from californian_id.schemas import SituationAnalysis

    z = Zarathustra()
    client = MockClient()
    situation = SituationAnalysis(topic="test", genre="statement")
    registry = ["LENS_A", "LENS_B", "LENS_C"]
    # LENS_A замучен (weight=0.05 ≤ threshold)
    decision = z.route_next(
        client, registry, already_called=[], turns=[], situation=situation,
        persona_weights={"LENS_A": 0.05, "LENS_B": 1.0, "LENS_C": 1.0},
    )
    assert decision.next_persona in {"LENS_B", "LENS_C"}
    assert decision.next_persona != "LENS_A"


def test_route_next_keeps_all_when_all_weights_muted():
    """Edge case: если ВСЕ silenced — не exclude'ить никого (фолбэк)."""
    from californian_id.zarathustra import Zarathustra
    from californian_id.models.mock import MockClient
    from californian_id.schemas import SituationAnalysis

    z = Zarathustra()
    client = MockClient()
    situation = SituationAnalysis(topic="test", genre="statement")
    registry = ["LENS_A", "LENS_B"]
    decision = z.route_next(
        client, registry, already_called=[], turns=[], situation=situation,
        persona_weights={"LENS_A": 0.05, "LENS_B": 0.05},
    )
    assert decision.next_persona in registry


# ---------- Pipeline._consume_pending ----------

def test_pipeline_consume_pending_returns_defaults_for_unknown_run(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.pipeline import Pipeline
    p = Pipeline()
    result = p._consume_pending("unknown-run-id")
    assert result == {"steer_override": None, "user_voices": [],
                      "attachments": [], "persona_weights": {}}


def test_pipeline_consume_pending_drains_and_returns(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.pipeline import Pipeline
    p = Pipeline()
    st = rc.register("r_pend", "default")
    try:
        rc.signal("r_pend", "steer", "alice",
                  payload={"persona_id": "LENS_X", "operation": "attack"})
        rc.signal("r_pend", "user_voice", "bob",
                  payload={"utterance": "I disagree", "author": "bob"})
        rc.signal("r_pend", "slider", "alice",
                  payload={"weights": {"LENS_X": 0.5}})
        pending = p._consume_pending("r_pend")
        assert pending["steer_override"]["persona_id"] == "LENS_X"
        assert len(pending["user_voices"]) == 1
        assert pending["user_voices"][0]["utterance"] == "I disagree"
        assert pending["persona_weights"] == {"LENS_X": 0.5}
        # После consume queue пуста для steer/user_voice; sliders остаются.
        with st.lock:
            assert st.pending_steer == []
            assert st.pending_user_voice == []
            assert st.persona_weights == {"LENS_X": 0.5}
    finally:
        rc.unregister("r_pend")


def test_pipeline_inject_user_voice_appends_turn(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.pipeline import Pipeline
    from californian_id.state import RunState
    from californian_id.schemas import ArgumentMap
    from californian_id.memory import ConversationMemory

    p = Pipeline()
    state = RunState(run_id="r_inj", mode="fast", input_text="x")
    memory = ConversationMemory(topic="x")
    amap = ArgumentMap()

    events: list[dict] = []
    p.event_sink = lambda evt: events.append(evt)

    p._inject_user_voice(state, amap, memory, {
        "utterance": "Мой аргумент",
        "author": "alice",
        "attach_to_persona": "LENS_A",
    }, turn_index=1)

    assert len(state.turns) == 1
    t = state.turns[0]
    assert t.persona_id == "USER_VOICE"
    assert t.utterance == "Мой аргумент"
    assert t.model_provider == "human"
    assert t.model_name == "user:alice"
    assert len(amap.claims) == 1
    assert any(e["kind"] == "user_voice_injected" for e in events)


def test_pipeline_inject_user_voice_ignores_empty_utterance(monkeypatch, tmp_path):
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    from californian_id.pipeline import Pipeline
    from californian_id.state import RunState
    from californian_id.schemas import ArgumentMap
    from californian_id.memory import ConversationMemory

    p = Pipeline()
    state = RunState(run_id="r_empty", mode="fast", input_text="x")
    p._inject_user_voice(state, ArgumentMap(), ConversationMemory(topic="x"),
                         {"utterance": "  "}, turn_index=1)
    assert len(state.turns) == 0


# ---------- E2E: steer + slider влияет на реальный ран ----------

def test_end_to_end_steer_affects_pipeline_output(monkeypatch, tmp_path):
    """Steer после первого turn'а должен перевести следующий на выбранную персону."""
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")

    from californian_id.pipeline import Pipeline
    pipe = Pipeline()

    events: list[dict] = []
    steered_persona = "LENS_RATIONALIST"
    steer_sent = threading.Event()

    def sink(evt):
        events.append(evt)
        # После первого route_previewed отправляем steer
        if (evt.get("kind") == "route_previewed"
                and evt.get("turn_index") == 0 and not steer_sent.is_set()):
            rc.signal(evt["run_id"], "steer", "test",
                      payload={"persona_id": steered_persona,
                               "operation": "attack",
                               "reason": "test steer"})
            steer_sent.set()

    pipe.event_sink = sink
    result = pipe.run(text="Обсуждаем что-то абстрактное", mode="fast")

    previews = [e for e in events if e.get("kind") == "route_previewed"]
    assert len(previews) >= 1
    # был ли ход с was_user_steer=True — если да, next_persona должна отражать steer
    steered_events = [p for p in previews if p.get("was_user_steer")]
    # Steer применяется только если персона в cast'е. Если нет — просто игнор.
    # Главное: если событие было и steered_events не пусто —
    # persona из steer_override должна попасть в next_persona (когда была в cast).
    cast_events = [e for e in events if e.get("kind") == "cast_selected"]
    if cast_events and steered_persona in cast_events[0].get("personas", []):
        assert steered_events, "steer должен был применяться"
        assert steered_events[0]["next_persona"] == steered_persona

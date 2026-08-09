"""6.B.5 — event_sink emissions + models stream fallback tests."""
from __future__ import annotations

from californian_id.models.mock import MockClient
from californian_id.models.base import Message
from californian_id.models.stream_utils import call_stream, stream_via_generate
from californian_id.pipeline import Pipeline


def test_pipeline_emit_noop_without_sink():
    p = Pipeline()
    assert p.event_sink is None
    # No exception, no error — should be a no-op.
    p._emit("run_started", {"x": 1})


def test_pipeline_emit_calls_sink_with_kind():
    p = Pipeline()
    received: list[dict] = []
    p.event_sink = lambda evt: received.append(evt)
    p._emit("turn_completed", {"turn_index": 0, "persona_id": "X"})
    p._emit("run_completed", {"turns": 3})
    assert received[0]["kind"] == "turn_completed"
    assert received[0]["persona_id"] == "X"
    assert received[1]["kind"] == "run_completed"
    assert received[1]["turns"] == 3


def test_pipeline_emit_swallows_sink_errors():
    p = Pipeline()
    def bad_sink(evt):
        raise RuntimeError("boom")
    p.event_sink = bad_sink
    # Must NOT raise — logger.warning captures it.
    p._emit("anything")


def test_mock_client_streams_chunks():
    c = MockClient()
    seen: list[str] = []
    result = c.generate_stream(
        [Message(role="user", content="topic: consciousness")],
        on_delta=lambda s: seen.append(s),
        settings={"role": "persona_turn", "persona_id": "X", "operation": "initial_position"},
    )
    assert result.text
    assert "".join(seen) == result.text
    assert len(seen) > 1  # actually streamed in pieces


def test_call_stream_falls_back_when_client_lacks_stream():
    class NoStreamClient:
        provider = "nostream"
        model = "n"
        def generate(self, messages, response_schema=None, settings=None):
            from californian_id.models.base import ModelResult
            return ModelResult(text="hello world", provider=self.provider, model=self.model)
    seen: list[str] = []
    result = call_stream(NoStreamClient(), [], lambda s: seen.append(s))
    assert result.text == "hello world"
    assert seen == ["hello world"]


def test_pipeline_workspace_default_is_default_slug():
    p = Pipeline()
    assert p.workspace_id == "default"


def test_pipeline_workspace_id_validated():
    p = Pipeline(workspace_id="alice-team_42")
    assert p.workspace_id == "alice-team_42"

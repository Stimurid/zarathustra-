"""D-S26-LIVE-API-001 acceptance — POST /api/socrates/run invokes
SocratesRuntime, NOT persona_layer.

Handler-level tests. Full end-to-end HTTP tests require a running
server; those live in live smokes on production.
"""
from __future__ import annotations

import json
import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


class _FakeRfile:
    def __init__(self, body: bytes) -> None:
        self._buf = BytesIO(body)

    def read(self, n: int) -> bytes:
        return self._buf.read(n)


class _FakeHandler:
    """Minimal harness that exercises the handler method directly.

    Instead of standing up HTTP, we call the bound method on a
    stub instance that supplies just enough surface for the code
    path under test.
    """
    def __init__(self, body: dict) -> None:
        self.path = "/api/socrates/run"
        raw = json.dumps(body).encode("utf-8")
        self.headers = {"Content-Length": str(len(raw))}
        self.rfile = _FakeRfile(raw)
        self._sent: dict = {}
        self._status = None

    # signature matches _send_json
    def _send_json(self, payload, status=None):
        self._sent = payload
        self._status = status


def _get_handler_method():
    """Import the class' _handle_socrates_run as an unbound method
    so we can call it on our stub instance.
    """
    from californian_id.web_ui import _WebUIHandler
    return _WebUIHandler._handle_socrates_run


def test_handler_dispatches_to_socrates_runtime_deterministic(monkeypatch):
    """Deterministic mode: real SocratesRuntime returns a real terminal
    and the response carries runtime_layer=socrates_runtime."""
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    handler = _FakeHandler({"text": "hello",
                             "execution_mode": "DETERMINISTIC"})
    _get_handler_method()(handler)
    assert handler._status is None                           # HTTP 200
    assert handler._sent["runtime_layer"] == "socrates_runtime"
    assert "run_id" in handler._sent
    assert "trace_id" in handler._sent
    assert "terminal" in handler._sent
    assert handler._sent["execution_mode"] == "DETERMINISTIC"
    # mounted_phases must be a list (may be empty in deterministic
    # with no hints but the field is always present)
    assert isinstance(handler._sent["mounted_phases"], list)


def test_handler_rejects_missing_text(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    handler = _FakeHandler({"execution_mode": "DETERMINISTIC"})
    _get_handler_method()(handler)
    assert handler._sent.get("error")
    assert handler._status is not None                       # HTTP 400
    assert int(handler._status) == 400


def test_handler_rejects_bad_execution_mode(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    handler = _FakeHandler({"text": "hi", "execution_mode": "PERSONA"})
    _get_handler_method()(handler)
    assert handler._sent.get("error")
    assert int(handler._status) == 400


def test_handler_rejects_unknown_intervention_profile(monkeypatch):
    """Explicit activation only — an unknown intervention profile
    is a hard error, never silently normalised."""
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    handler = _FakeHandler({"text": "hi",
                             "execution_mode": "DETERMINISTIC",
                             "intervention_profile": "made_up_name"})
    _get_handler_method()(handler)
    assert handler._sent.get("error")
    assert int(handler._status) == 400


def test_handler_never_calls_persona_layer(monkeypatch):
    """Regression proof: /api/socrates/run does NOT go through
    run_web_request (the persona_layer entrypoint)."""
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")

    from californian_id import web_ui
    called = {"persona_layer": False}
    real_run = web_ui.run_web_request

    def _fake_run(*a, **kw):
        called["persona_layer"] = True
        return real_run(*a, **kw)

    monkeypatch.setattr(web_ui, "run_web_request", _fake_run)
    handler = _FakeHandler({"text": "hi",
                             "execution_mode": "DETERMINISTIC"})
    _get_handler_method()(handler)
    assert called["persona_layer"] is False
    assert handler._sent["runtime_layer"] == "socrates_runtime"


def test_response_never_carries_hidden_cot_field(monkeypatch):
    """Public response must expose only public typed fields —
    never a raw chain-of-thought / internal_reasoning blob."""
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    handler = _FakeHandler({"text": "hi",
                             "execution_mode": "DETERMINISTIC"})
    _get_handler_method()(handler)
    for banned_key in ("chain_of_thought", "internal_reasoning",
                        "raw_thought", "hidden_cot", "cot"):
        assert banned_key not in handler._sent


def test_response_carries_intervention_profile_echo(monkeypatch):
    """The response echoes which profile ran (default 'normal')."""
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    handler = _FakeHandler({"text": "hi",
                             "execution_mode": "DETERMINISTIC"})
    _get_handler_method()(handler)
    assert handler._sent["intervention_profile"] == "normal"


def test_route_registered_on_dispatch_table(monkeypatch):
    """The do_POST dispatcher recognises /api/socrates/run."""
    from californian_id import web_ui
    import inspect
    src = inspect.getsource(web_ui._WebUIHandler.do_POST)
    assert '"/api/socrates/run"' in src
    assert "_handle_socrates_run" in src

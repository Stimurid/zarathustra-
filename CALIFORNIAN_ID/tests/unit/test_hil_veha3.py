"""B-5.5 Веха 3 — WebSocket handshake, auth, ping/pong, intervention roundtrip.

Использует asyncio + websockets client library для интеграционных тестов.
Если websockets не установлена — все тесты skipped.
"""
from __future__ import annotations

import asyncio
import json
import socket
import time

import pytest


def _find_free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
    HAS_WS = True
except ImportError:
    HAS_WS = False


pytestmark = pytest.mark.skipif(not HAS_WS,
                                 reason="websockets library not installed")


@pytest.fixture
def ws_server(monkeypatch, tmp_path):
    """Запускает WS-сервер на свободном порту, возвращает (host, port)."""
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.setenv("CALIFORNIAN_ID_AUTH_DISABLED", "1")
    port = _find_free_port()
    from californian_id import ws_endpoint
    # Reset globals для чистого запуска
    ws_endpoint._server_thread = None
    ws_endpoint._loop = None
    ws_endpoint._subscribers.clear()
    ws_endpoint.start_ws_server(host="127.0.0.1", port=port)
    # give server time to bind
    time.sleep(0.4)
    yield "127.0.0.1", port


async def _connect(host: str, port: int, run_id: str, token: str = "") -> Any:
    query = f"?token={token}" if token else ""
    return await ws_connect(f"ws://{host}:{port}/ws/run/{run_id}{query}")


def test_ws_handshake_and_hello(ws_server):
    host, port = ws_server
    async def go():
        ws = await _connect(host, port, "run-test-1")
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(msg)
            assert data["kind"] == "hello"
            assert data["run_id"] == "run-test-1"
            assert "state_snapshot" in data
        finally:
            await ws.close()
    asyncio.run(go())


def test_ws_ping_pong(ws_server):
    host, port = ws_server
    async def go():
        ws = await _connect(host, port, "run-ping")
        try:
            await ws.recv()  # hello
            await ws.send(json.dumps({"cmd": "ping", "ts": 12345}))
            reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(reply)
            assert data["kind"] == "pong"
            assert data["ts"] == 12345
        finally:
            await ws.close()
    asyncio.run(go())


def test_ws_intervention_roundtrip(ws_server):
    host, port = ws_server
    from californian_id import runtime_control as rc
    rc.register("run-iv", "default")
    try:
        async def go():
            ws = await _connect(host, port, "run-iv")
            try:
                await ws.recv()  # hello
                await ws.send(json.dumps({"cmd": "pause", "payload": {}}))
                reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(reply)
                assert data["kind"] == "intervention_accepted"
                assert data["kind_"] == "pause"
                # verify state изменилось
                assert not rc.get("run-iv").run_event.is_set()
            finally:
                await ws.close()
        asyncio.run(go())
    finally:
        rc.unregister("run-iv")


def test_ws_unknown_cmd_returns_error(ws_server):
    host, port = ws_server
    async def go():
        ws = await _connect(host, port, "run-err")
        try:
            await ws.recv()  # hello
            await ws.send(json.dumps({"cmd": "banana"}))
            reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(reply)
            assert data["kind"] == "error"
            assert "banana" in data["error"]
        finally:
            await ws.close()
    asyncio.run(go())


def test_ws_bad_path_closes(ws_server):
    host, port = ws_server
    async def go():
        # без /ws/run/<id> префикса
        with pytest.raises(Exception):
            ws = await ws_connect(f"ws://{host}:{port}/wrong/path")
            await ws.recv()
    asyncio.run(go())


def test_ws_auth_rejects_missing_token(monkeypatch, tmp_path):
    """Отдельный ws_server без AUTH_DISABLED — должен требовать token."""
    monkeypatch.setattr("californian_id.workspaces.RUNS_DIR", tmp_path)
    monkeypatch.delenv("CALIFORNIAN_ID_AUTH_DISABLED", raising=False)
    port = _find_free_port()
    from californian_id import ws_endpoint
    ws_endpoint._server_thread = None
    ws_endpoint._loop = None
    ws_endpoint._subscribers.clear()
    ws_endpoint.start_ws_server(host="127.0.0.1", port=port)
    time.sleep(0.4)

    async def go():
        with pytest.raises(Exception):
            ws = await ws_connect(f"ws://127.0.0.1:{port}/ws/run/r1")
            await ws.recv()
    asyncio.run(go())


def test_ws_broadcast_from_event_sink(ws_server):
    """Events, посланные через register_event_sink, доставляются подписчикам."""
    host, port = ws_server
    from californian_id import ws_endpoint

    async def go():
        ws = await _connect(host, port, "run-broadcast")
        try:
            await ws.recv()  # hello
            # шлём event через bridge (симулирует pipeline)
            ws_endpoint.register_event_sink("run-broadcast", {
                "kind": "turn_completed", "turn_index": 0,
                "persona_id": "LENS_X", "run_id": "run-broadcast",
            })
            reply = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(reply)
            assert data["kind"] == "turn_completed"
            assert data["persona_id"] == "LENS_X"
        finally:
            await ws.close()
    asyncio.run(go())

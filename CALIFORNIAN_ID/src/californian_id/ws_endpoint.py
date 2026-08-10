"""B-5.5 Веха 3 — WebSocket endpoint.

Duplex-канал для live-совета:
  Server → Client: события pipeline (те же что SSE) + hello/state_snapshot.
  Client → Server: cmd frames pause/resume/cancel/steer/slider/user_voice + ping.

Транспорт: библиотека `websockets` (asyncio). Bridge к threading pipeline
через queue.Queue + `asyncio.run_coroutine_threadsafe`.

Auth: JWT в query param `?token=...`. Если задан env `CALIFORNIAN_ID_AUTH_DISABLED`
— пропускаем. Иначе — verify_token; при провале — close 1008.

Использование: serve() запускает asyncio server в отдельном thread'е.
Основной ThreadingHTTPServer живёт как раньше.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import queue as _queue
import threading
from typing import Any

try:
    import websockets
    from websockets.asyncio.server import serve as ws_serve, ServerConnection
    from websockets.exceptions import ConnectionClosed
    HAS_WEBSOCKETS = True
except ImportError:  # pragma: no cover
    HAS_WEBSOCKETS = False


logger = logging.getLogger("californian_id.ws_endpoint")

# in-memory: run_id → set[ServerConnection]. Subscriber-фанаут.
_subscribers: dict[str, set[Any]] = {}
_subs_lock = threading.Lock()

# Основной asyncio event loop, живущий в отдельном thread'е.
# Используется для run_coroutine_threadsafe из pipeline event_sink.
_loop: asyncio.AbstractEventLoop | None = None


def register_event_sink(run_id: str, evt: dict) -> None:
    """Вызывается из pipeline event_sink (sync-контекст, любой thread).
    Отправляет event всем подписчикам на run_id.
    """
    if _loop is None:
        return
    with _subs_lock:
        conns = list(_subscribers.get(run_id, set()))
    if not conns:
        return
    payload = json.dumps(evt, ensure_ascii=False)
    # Планируем broadcast в event loop
    asyncio.run_coroutine_threadsafe(_broadcast(conns, payload), _loop)


async def _broadcast(conns: list[Any], payload: str) -> None:
    for c in conns:
        try:
            await c.send(payload)
        except Exception:
            pass


async def _handle_connection(websocket) -> None:
    """WS handler: auth → subscribe to run_id → пересылка cmd в runtime_control."""
    try:
        path = websocket.request.path if hasattr(websocket, "request") else "/ws"
    except Exception:
        path = "/ws"
    # ожидаем `/ws/run/<run_id>?token=...`
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(path)
    parts = [p for p in parsed.path.split("/") if p]
    # ["ws", "run", "<run_id>"]
    if len(parts) < 3 or parts[0] != "ws" or parts[1] != "run":
        await websocket.close(code=1008, reason="bad path")
        return
    run_id = parts[2]

    # AUTH
    auth_disabled = (os.environ.get("CALIFORNIAN_ID_AUTH_DISABLED") or "").lower() \
        in {"1", "true", "yes"}
    author = "anonymous"
    if not auth_disabled:
        token = (parse_qs(parsed.query).get("token") or [""])[0]
        if not token:
            await websocket.close(code=1008, reason="token required"); return
        from . import jwt_auth
        try:
            payload_jwt = jwt_auth.verify_token(token)
            author = str(payload_jwt.get("sub") or "anonymous")
        except jwt_auth.JWTError as ex:
            await websocket.close(code=1008, reason=f"bad token: {ex}"); return

    with _subs_lock:
        _subscribers.setdefault(run_id, set()).add(websocket)

    # hello + snapshot
    from . import runtime_control
    snap = runtime_control.snapshot_state(run_id)
    await websocket.send(json.dumps({
        "kind": "hello",
        "run_id": run_id,
        "author": author,
        "state_snapshot": snap,
    }, ensure_ascii=False))

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception:
                await websocket.send(json.dumps({
                    "kind": "error", "error": "bad json"
                }))
                continue
            cmd = (data.get("cmd") or "").strip().lower()
            if cmd == "ping":
                await websocket.send(json.dumps({"kind": "pong",
                                                  "ts": data.get("ts")}))
                continue
            if cmd in runtime_control.INTERVENTION_KINDS:
                try:
                    iv = runtime_control.signal(
                        run_id=run_id, kind=cmd, author=author,
                        payload=data.get("payload") or {},
                    )
                    await websocket.send(json.dumps({
                        "kind": "intervention_accepted",
                        "intervention_id": iv.intervention_id,
                        "kind_": iv.kind,
                    }))
                except Exception as ex:
                    await websocket.send(json.dumps({
                        "kind": "error", "error": str(ex),
                    }))
                continue
            if cmd == "state_snapshot":
                await websocket.send(json.dumps({
                    "kind": "state_snapshot",
                    "run_state": runtime_control.snapshot_state(run_id),
                }))
                continue
            await websocket.send(json.dumps({
                "kind": "error",
                "error": f"unknown cmd: {cmd}",
            }))
    except ConnectionClosed:
        pass
    except Exception as ex:
        logger.warning("ws handler error: %s", ex)
    finally:
        with _subs_lock:
            subs = _subscribers.get(run_id)
            if subs is not None:
                subs.discard(websocket)
                if not subs:
                    _subscribers.pop(run_id, None)


async def _serve_forever(host: str, port: int) -> None:
    async with ws_serve(_handle_connection, host, port):
        logger.info("WebSocket endpoint listening on ws://%s:%d/ws/run/<run_id>",
                    host, port)
        await asyncio.Future()  # run forever


_server_thread: threading.Thread | None = None


def start_ws_server(host: str = "127.0.0.1", port: int = 8086) -> None:
    """Запуск WS-сервера в отдельном thread'е с собственным event loop."""
    global _loop, _server_thread
    if not HAS_WEBSOCKETS:
        logger.warning("websockets library not installed — WS endpoint disabled")
        return
    if _server_thread is not None:
        return  # уже запущен

    def _runner():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        try:
            _loop.run_until_complete(_serve_forever(host, port))
        except Exception as ex:
            logger.error("WS server crashed: %s", ex)

    _server_thread = threading.Thread(target=_runner, name="tinkuy-ws",
                                       daemon=True)
    _server_thread.start()


def is_running() -> bool:
    return _server_thread is not None and _server_thread.is_alive()

"""B-5.5 Веха 1 — Runtime control (pause/resume/cancel + intervention log).

Модель: cooperative checkpoint. Pipeline._checkpoint() вызывается между
turn'ами, читает pending interventions, применяет их или блокируется в pause.

Хранение: per-workspace SQLite `interventions.sqlite3` (audit log)
+ in-memory `RunState`-per-run с threading.Event для pause/resume.

Kinds:
  pause    — переводит run в PAUSED (event.clear())
  resume   — event.set(), продолжает после ближайшего checkpoint
  cancel   — cancel_flag=True, checkpoint бросает RuntimeCancelled
  steer    — override следующего route_next (Веха 2)
  slider   — обновляет persona_weights (Веха 2)
  user_voice — инжектит USER_VOICE turn (Веха 2)
  attach_file — boost persona с extracted text (Веха 5)
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspaces import DEFAULT_WORKSPACE_ID, validate_workspace_id, workspace_dir


INTERVENTION_KINDS = {
    "pause", "resume", "cancel",
    "steer", "slider", "user_voice", "attach_file",
}


class RuntimeCancelled(RuntimeError):
    """Raised by _checkpoint when cancel signal received."""


@dataclass
class Intervention:
    intervention_id: str
    run_id: str
    workspace_id: str
    kind: str
    author: str
    payload: dict[str, Any] = field(default_factory=dict)
    at_turn_index: int | None = None
    applied: bool = False
    applied_at: str = ""
    created_at: str = ""


_DDL = """
CREATE TABLE IF NOT EXISTS intervention (
    intervention_id  TEXT PRIMARY KEY,
    run_id           TEXT NOT NULL,
    workspace_id     TEXT NOT NULL,
    kind             TEXT NOT NULL,
    author           TEXT NOT NULL,
    payload_json     TEXT,
    at_turn_index    INTEGER,
    applied          INTEGER NOT NULL DEFAULT 0,
    applied_at       TEXT,
    created_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_iv_run ON intervention(run_id);
CREATE INDEX IF NOT EXISTS idx_iv_author ON intervention(author);
CREATE INDEX IF NOT EXISTS idx_iv_created ON intervention(created_at DESC);
"""


def _store_path(ws: str) -> Path:
    return workspace_dir(ws) / "interventions.sqlite3"


class InterventionStore:
    """Persistent audit log интервенций (SQLite per-workspace)."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_DDL)
        self._conn.commit()

    @classmethod
    def for_workspace(cls, ws: str | None = None) -> "InterventionStore":
        return cls(_store_path(validate_workspace_id(ws or DEFAULT_WORKSPACE_ID)))

    def save(self, iv: Intervention) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO intervention "
            "(intervention_id, run_id, workspace_id, kind, author, payload_json, "
            " at_turn_index, applied, applied_at, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (iv.intervention_id, iv.run_id, iv.workspace_id, iv.kind, iv.author,
             json.dumps(iv.payload, ensure_ascii=False),
             iv.at_turn_index,
             1 if iv.applied else 0,
             iv.applied_at,
             iv.created_at or datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def list_for_run(self, run_id: str) -> list[Intervention]:
        rows = self._conn.execute(
            "SELECT intervention_id, run_id, workspace_id, kind, author, payload_json, "
            " at_turn_index, applied, applied_at, created_at "
            "FROM intervention WHERE run_id=? ORDER BY created_at ASC", (run_id,),
        ).fetchall()
        return [_row_to_iv(r) for r in rows]

    def close(self) -> None:
        self._conn.close()


def _row_to_iv(r: tuple) -> Intervention:
    return Intervention(
        intervention_id=r[0], run_id=r[1], workspace_id=r[2], kind=r[3],
        author=r[4], payload=json.loads(r[5] or "{}"),
        at_turn_index=r[6], applied=bool(r[7]),
        applied_at=r[8] or "", created_at=r[9] or "",
    )


def new_intervention_id(run_id: str, kind: str, author: str) -> str:
    seed = f"{run_id}|{kind}|{author}|{datetime.now(timezone.utc).timestamp()}"
    return "iv_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


# ============================================================================
# In-memory per-run control state (для чтения из Pipeline._checkpoint).
# ============================================================================

@dataclass
class _RunControlState:
    """In-memory состояние runtime control одного идущего рана."""
    run_id: str
    workspace_id: str
    # threading.Event: set=RUNNING, clear=PAUSED. Изначально set.
    run_event: threading.Event = field(default_factory=lambda: _make_set_event())
    cancel_flag: bool = False
    cancel_reason: str = ""
    # Pending interventions (Веха 2), FIFO.
    pending_steer: list[dict[str, Any]] = field(default_factory=list)
    pending_user_voice: list[dict[str, Any]] = field(default_factory=list)
    pending_attach: list[dict[str, Any]] = field(default_factory=list)
    # Sliders — persona_id → weight [0..3]. Обновляется slider-интервенцией.
    persona_weights: dict[str, float] = field(default_factory=dict)
    # Applied interventions — для audit при финализации.
    applied_ids: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _make_set_event() -> threading.Event:
    e = threading.Event()
    e.set()
    return e


_registry: dict[str, _RunControlState] = {}
_registry_lock = threading.Lock()


def register(run_id: str, workspace_id: str) -> _RunControlState:
    """Регистрация нового рана — создаёт in-memory control state."""
    with _registry_lock:
        st = _RunControlState(run_id=run_id,
                              workspace_id=validate_workspace_id(workspace_id))
        _registry[run_id] = st
        return st


def unregister(run_id: str) -> None:
    """Убрать in-memory state (после финализации)."""
    with _registry_lock:
        _registry.pop(run_id, None)


def get(run_id: str) -> _RunControlState | None:
    with _registry_lock:
        return _registry.get(run_id)


def signal(
    run_id: str,
    kind: str,
    author: str,
    payload: dict[str, Any] | None = None,
    persist: bool = True,
) -> Intervention:
    """Приём интервенции от endpoint. Обновляет in-memory + persists в SQLite.

    Возвращает Intervention (с id). Не блокируется.
    """
    if kind not in INTERVENTION_KINDS:
        raise ValueError(f"unknown intervention kind: {kind}")
    st = get(run_id)
    iv_id = new_intervention_id(run_id, kind, author)
    iv = Intervention(
        intervention_id=iv_id,
        run_id=run_id,
        workspace_id=st.workspace_id if st else DEFAULT_WORKSPACE_ID,
        kind=kind,
        author=author or "anonymous",
        payload=payload or {},
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    if st is None:
        # ран не зарегистрирован — только persist в audit, no-op в runtime
        if persist:
            _persist(iv)
        return iv

    with st.lock:
        if kind == "pause":
            st.run_event.clear()
        elif kind == "resume":
            st.run_event.set()
        elif kind == "cancel":
            st.cancel_flag = True
            st.cancel_reason = str(payload.get("reason", "") if payload else "")
            st.run_event.set()  # разблокировать checkpoint если он ждёт в pause
        elif kind == "steer":
            st.pending_steer.append(dict(payload or {}))
        elif kind == "slider":
            weights = (payload or {}).get("weights") or {}
            for pid, w in weights.items():
                try:
                    st.persona_weights[str(pid)] = max(0.05, min(3.0, float(w)))
                except (TypeError, ValueError):
                    continue
        elif kind == "user_voice":
            st.pending_user_voice.append(dict(payload or {}))
        elif kind == "attach_file":
            st.pending_attach.append(dict(payload or {}))

    if persist:
        _persist(iv)
    return iv


def _persist(iv: Intervention) -> None:
    try:
        store = InterventionStore.for_workspace(iv.workspace_id)
        try:
            store.save(iv)
        finally:
            store.close()
    except Exception:
        pass


def mark_applied(iv_id: str, workspace_id: str, at_turn_index: int) -> None:
    """Пометить в SQLite интервенцию как applied. Best-effort."""
    try:
        store = InterventionStore.for_workspace(workspace_id)
        try:
            store._conn.execute(
                "UPDATE intervention SET applied=1, applied_at=?, at_turn_index=? "
                "WHERE intervention_id=?",
                (datetime.now(timezone.utc).isoformat(), at_turn_index, iv_id),
            )
            store._conn.commit()
        finally:
            store.close()
    except Exception:
        pass


def snapshot_state(run_id: str) -> dict[str, Any]:
    """Возвращает публичный snapshot для UI / event stream."""
    st = get(run_id)
    if st is None:
        return {"run_id": run_id, "state": "UNKNOWN"}
    with st.lock:
        return {
            "run_id": run_id,
            "workspace_id": st.workspace_id,
            "state": ("CANCELLING" if st.cancel_flag else
                      ("RUNNING" if st.run_event.is_set() else "PAUSED")),
            "persona_weights": dict(st.persona_weights),
            "pending_steer_count": len(st.pending_steer),
            "pending_user_voice_count": len(st.pending_user_voice),
            "pending_attach_count": len(st.pending_attach),
            "applied_ids": list(st.applied_ids),
        }


def wait_if_paused(run_id: str, timeout_sec: float = 60.0) -> str:
    """Блокирующий wait для _checkpoint.

    Возвращает: 'running' | 'cancelled' | 'timeout'.
    Если ран не зарегистрирован — 'running' немедленно.
    """
    st = get(run_id)
    if st is None:
        return "running"
    if st.cancel_flag:
        return "cancelled"
    # быстрый путь — сразу running
    if st.run_event.is_set():
        return "running"
    # ждём — но с timeout на случай застревания
    ok = st.run_event.wait(timeout=timeout_sec)
    if st.cancel_flag:
        return "cancelled"
    if not ok:
        return "timeout"
    return "running"

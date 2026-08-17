"""Host adapter — durable SQLite ContextStore for web/API layer.

Second allowlisted californian_id module that may import socrates_runtime
(alongside :mod:`socrates_bridge`). Keeps SQL out of the runtime package.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

from socrates_runtime.context_store import SocratesContext, new_context_id


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class SQLiteContextStore:
    """File-backed durable context store (host adapter)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS socrates_contexts (
                    context_id TEXT PRIMARY KEY,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def create(self) -> SocratesContext:
        cid = new_context_id()
        now = _now_iso()
        ctx = SocratesContext(
            context_id=cid, created_at=now, updated_at=now,
            provenance="server_created")
        self.save(ctx)
        return ctx

    def load(self, context_id: str) -> SocratesContext | None:
        if not context_id or not isinstance(context_id, str):
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT snapshot_json FROM socrates_contexts WHERE context_id=?",
                (context_id,)).fetchone()
        if row is None:
            return None
        try:
            return SocratesContext.from_json(row[0], context_id=context_id)
        except (ValueError, KeyError):
            return None

    def save(self, context: SocratesContext) -> None:
        context.updated_at = _now_iso()
        if not context.created_at:
            context.created_at = context.updated_at
        raw = context.to_json()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO socrates_contexts
                   (context_id, snapshot_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(context_id) DO UPDATE SET
                     snapshot_json=excluded.snapshot_json,
                     updated_at=excluded.updated_at""",
                (context.context_id, raw,
                 context.created_at, context.updated_at))
            conn.commit()

    def exists(self, context_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM socrates_contexts WHERE context_id=? LIMIT 1",
                (context_id,)).fetchone()
        return row is not None


_default_store: SQLiteContextStore | None = None


def default_context_store() -> SQLiteContextStore:
    """Process-wide default store path from env or runs dir."""
    global _default_store
    if _default_store is not None:
        return _default_store
    base = os.environ.get("SOCRATES_CONTEXT_STORE_DIR")
    if base:
        path = Path(base) / "socrates_contexts.db"
    else:
        runs = os.environ.get("CALIFORNIAN_ID_RUNS_DIR") or "runs"
        path = Path(runs) / "socrates_contexts.db"
    _default_store = SQLiteContextStore(path)
    return _default_store


def reset_default_context_store(store: SQLiteContextStore | None = None) -> None:
    """Test helper — replace the process default store."""
    global _default_store
    _default_store = store

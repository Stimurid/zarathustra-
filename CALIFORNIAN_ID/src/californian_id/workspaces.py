"""Пик 6.A — workspace-скоуп хранения.

Один workspace = одно место, где живёт своя фабрика ткани, свои раны,
своя история совета. По канону Tinkuy (документы 025-034, WORKSPACE).

MVP: FS-организация под RUNS_DIR/workspaces/<workspace_id>/.
   - fabric.sqlite3   — FabricStore этого workspace
   - runs.sqlite3     — RunStore (метаданные ранов)
   - runs/<run_id>/   — trace_dir (RunState, argument_map, turns)

Workspace_id — короткий slug (ASCII, [a-z0-9_-], без слэшей). "default" —
implicit fallback для одиночного пользователя.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RUNS_DIR


DEFAULT_WORKSPACE_ID = "default"
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def validate_workspace_id(ws_id: str) -> str:
    """Строгая валидация workspace_id — anti path-traversal."""
    if not ws_id:
        return DEFAULT_WORKSPACE_ID
    s = ws_id.strip().lower()
    if not _SLUG_RE.match(s):
        raise ValueError(
            f"invalid workspace_id {ws_id!r}: must match {_SLUG_RE.pattern}"
        )
    return s


def workspace_dir(ws_id: str, root: Path | None = None) -> Path:
    """Абсолютный путь директории workspace. Создаётся при первом обращении."""
    ws_id = validate_workspace_id(ws_id)
    base = (root or RUNS_DIR) / "workspaces" / ws_id
    base.mkdir(parents=True, exist_ok=True)
    return base


def fabric_store_path(ws_id: str, root: Path | None = None) -> Path:
    return workspace_dir(ws_id, root) / "fabric.sqlite3"


def run_store_path(ws_id: str, root: Path | None = None) -> Path:
    return workspace_dir(ws_id, root) / "runs.sqlite3"


def run_trace_dir(ws_id: str, run_id: str, root: Path | None = None) -> Path:
    d = workspace_dir(ws_id, root) / "runs" / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class RunMetadata:
    """Компактная сводка одного запуска — для истории/index."""
    run_id: str
    workspace_id: str
    mode: str
    status: str                     # COMPLETED | ERROR | RUNNING
    stopping_reason: str = ""
    completion_form: str = ""       # synthesis | aporia | ... | ""
    input_mode: str = ""            # raw | raw+fabric | semantic-units | ...
    input_summary: str = ""         # первые ~200 символов
    snapshot_id: str = ""           # если через fabric — id ткани
    trace_dir: str = ""
    turn_count: int = 0
    voices_used: list[str] = field(default_factory=list)
    created_at: str = ""
    finished_at: str = ""
    error: str = ""


_RUN_DDL = """
CREATE TABLE IF NOT EXISTS run (
    run_id           TEXT PRIMARY KEY,
    workspace_id     TEXT NOT NULL,
    mode             TEXT,
    status           TEXT,
    stopping_reason  TEXT,
    completion_form  TEXT,
    input_mode       TEXT,
    input_summary    TEXT,
    snapshot_id      TEXT,
    trace_dir        TEXT,
    turn_count       INTEGER,
    voices_used_json TEXT,
    created_at       TEXT,
    finished_at      TEXT,
    error            TEXT,
    payload          TEXT
);
CREATE INDEX IF NOT EXISTS idx_run_workspace ON run(workspace_id);
CREATE INDEX IF NOT EXISTS idx_run_created   ON run(created_at DESC);
"""


class RunStore:
    """Компактный per-workspace store метаданных ранов."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_RUN_DDL)
        self._conn.commit()

    @classmethod
    def for_workspace(cls, ws_id: str, root: Path | None = None) -> "RunStore":
        return cls(run_store_path(ws_id, root))

    def save(self, meta: RunMetadata, extra_payload: dict[str, Any] | None = None) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO run "
            "(run_id, workspace_id, mode, status, stopping_reason, completion_form, "
            " input_mode, input_summary, snapshot_id, trace_dir, turn_count, voices_used_json, "
            " created_at, finished_at, error, payload) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                meta.run_id, meta.workspace_id, meta.mode, meta.status,
                meta.stopping_reason, meta.completion_form,
                meta.input_mode, meta.input_summary, meta.snapshot_id, meta.trace_dir,
                meta.turn_count, json.dumps(meta.voices_used, ensure_ascii=False),
                meta.created_at or datetime.now(timezone.utc).isoformat(),
                meta.finished_at, meta.error,
                json.dumps(extra_payload or {}, ensure_ascii=False),
            ),
        )
        self._conn.commit()

    def get(self, run_id: str) -> RunMetadata | None:
        row = self._conn.execute(
            "SELECT run_id, workspace_id, mode, status, stopping_reason, completion_form, "
            " input_mode, input_summary, snapshot_id, trace_dir, turn_count, voices_used_json, "
            " created_at, finished_at, error FROM run WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if not row:
            return None
        return RunMetadata(
            run_id=row[0], workspace_id=row[1], mode=row[2] or "",
            status=row[3] or "", stopping_reason=row[4] or "",
            completion_form=row[5] or "", input_mode=row[6] or "",
            input_summary=row[7] or "", snapshot_id=row[8] or "",
            trace_dir=row[9] or "", turn_count=int(row[10] or 0),
            voices_used=json.loads(row[11] or "[]"),
            created_at=row[12] or "", finished_at=row[13] or "",
            error=row[14] or "",
        )

    def list(self, limit: int = 100) -> list[RunMetadata]:
        rows = self._conn.execute(
            "SELECT run_id, workspace_id, mode, status, stopping_reason, completion_form, "
            " input_mode, input_summary, snapshot_id, trace_dir, turn_count, voices_used_json, "
            " created_at, finished_at, error FROM run "
            "ORDER BY created_at DESC LIMIT ?", (limit,),
        ).fetchall()
        out: list[RunMetadata] = []
        for row in rows:
            out.append(RunMetadata(
                run_id=row[0], workspace_id=row[1], mode=row[2] or "",
                status=row[3] or "", stopping_reason=row[4] or "",
                completion_form=row[5] or "", input_mode=row[6] or "",
                input_summary=row[7] or "", snapshot_id=row[8] or "",
                trace_dir=row[9] or "", turn_count=int(row[10] or 0),
                voices_used=json.loads(row[11] or "[]"),
                created_at=row[12] or "", finished_at=row[13] or "",
                error=row[14] or "",
            ))
        return out

    def close(self) -> None:
        self._conn.close()


def list_workspaces(root: Path | None = None) -> list[dict[str, Any]]:
    """Перечисляет workspace-директории с базовой сводкой."""
    base = (root or RUNS_DIR) / "workspaces"
    if not base.exists():
        return []
    out = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        wsid = entry.name
        fab = entry / "fabric.sqlite3"
        runs = entry / "runs.sqlite3"
        n_runs = 0
        if runs.exists():
            try:
                with sqlite3.connect(runs) as c:
                    n_runs = c.execute("SELECT COUNT(*) FROM run").fetchone()[0]
            except sqlite3.Error:
                pass
        out.append({
            "workspace_id": wsid,
            "fabric_db_bytes": fab.stat().st_size if fab.exists() else 0,
            "runs_db_bytes": runs.stat().st_size if runs.exists() else 0,
            "n_runs": n_runs,
        })
    return out

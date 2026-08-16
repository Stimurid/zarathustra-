"""Arena persistence — one row per match, everything else as JSON.

The reason a match is persisted at all is not history for its own sake — it
is so the same Workbench that runs Zarathustra can later show what happened
in a match without a separate storage layer. Kept flat, no migrations.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .protocol import (
    Case,
    DevelopmentSignal,
    EvaluationRecord,
    Match,
    MatchProtocol,
    ParticipantConfiguration,
    Turn,
)

_DDL = """
CREATE TABLE IF NOT EXISTS arena_match (
    match_id     TEXT PRIMARY KEY,
    bench_id     TEXT NOT NULL,
    case_id      TEXT NOT NULL,
    status       TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_match_bench ON arena_match(bench_id, started_at DESC);
"""


class ArenaStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._conn.executescript(_DDL)

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    def save_match(self, match: Match) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO arena_match "
            "(match_id, bench_id, case_id, status, started_at, finished_at, "
            "payload_json) VALUES (?,?,?,?,?,?,?)",
            (match.match_id, match.bench_id, match.case.case_id,
             match.status, match.started_at, match.finished_at,
             json.dumps(match.to_public(), ensure_ascii=False)),
        )

    def load_match(self, match_id: str) -> Match | None:
        row = self._conn.execute(
            "SELECT payload_json FROM arena_match WHERE match_id=?",
            (match_id,),
        ).fetchone()
        return _payload_to_match(json.loads(row[0])) if row else None

    def list_matches(self, bench_id: str | None = None,
                     limit: int = 50) -> list[dict[str, Any]]:
        sql = ("SELECT match_id, bench_id, case_id, status, started_at, "
               "finished_at FROM arena_match ")
        args: tuple = ()
        if bench_id:
            sql += "WHERE bench_id=? "
            args = (bench_id,)
        sql += "ORDER BY started_at DESC LIMIT ?"
        rows = self._conn.execute(sql, (*args, limit)).fetchall()
        return [{"match_id": r[0], "bench_id": r[1], "case_id": r[2],
                 "status": r[3], "started_at": r[4], "finished_at": r[5]}
                for r in rows]

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


def _payload_to_match(d: dict[str, Any]) -> Match:
    case = Case(case_id=d["case"]["case_id"],
                text=d["case"]["text"],
                tags=tuple(d["case"].get("tags") or ()),
                expectations=d["case"].get("expectations") or {},
                source=d["case"].get("source", ""))
    proto = MatchProtocol(**d["protocol"])
    participants = [ParticipantConfiguration(**p) for p in d["participants"]]
    turns = [Turn(**t) for t in d["turns"]]
    evaluations = [EvaluationRecord(**e) for e in d["evaluations"]]
    signals = [DevelopmentSignal(**s) for s in d.get("signals") or []]
    return Match(
        match_id=d["match_id"], bench_id=d["bench_id"], case=case,
        participants=participants, protocol=proto,
        turns=turns, evaluations=evaluations, signals=signals,
        started_at=d["started_at"], finished_at=d["finished_at"],
        status=d["status"],
    )

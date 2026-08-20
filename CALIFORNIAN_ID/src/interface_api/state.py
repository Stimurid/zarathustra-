"""SQLite persistence for the vertical-slice Interaction Model.

Single file `<runs_dir>/interface_state.sqlite` on production;
tmp-path per-test in test harness. Five tables mirror the five
objects. `CREATE TABLE IF NOT EXISTS` on first connection; no
migration framework.

Persistence contract: after the process restarts, every object
previously written by `put_*` is retrievable by `get_*` with the
same shape.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .models import (
    Artifact, ArtifactKind, Decision, DecisionAction,
    InputArtifact, InputKind, Run, RunMode, RunStatus,
    Session, SessionStatus,
)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    have        TEXT NOT NULL,
    want        TEXT NOT NULL,
    actor       TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inputs (
    input_id     TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    kind         TEXT NOT NULL,
    body_text    TEXT NOT NULL,
    mime         TEXT NOT NULL,
    length_chars INTEGER NOT NULL,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);
CREATE INDEX IF NOT EXISTS inputs_session_idx ON inputs (session_id);

CREATE TABLE IF NOT EXISTS runs (
    run_id           TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL,
    input_id         TEXT NOT NULL,
    mode             TEXT NOT NULL,
    status           TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT NOT NULL,
    terminal         TEXT NOT NULL,
    response_text    TEXT NOT NULL,
    dyad_causal      TEXT NOT NULL,
    apparatus_class  TEXT NOT NULL,
    sd_status        TEXT NOT NULL,
    sd_authority     TEXT NOT NULL,
    provider_id      TEXT NOT NULL,
    model_id         TEXT NOT NULL,
    duration_ms      INTEGER NOT NULL,
    error            TEXT NOT NULL,
    trace_ref        TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);
CREATE INDEX IF NOT EXISTS runs_session_idx ON runs (session_id);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id  TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    run_id       TEXT NOT NULL,
    kind         TEXT NOT NULL,
    title        TEXT NOT NULL,
    body_md      TEXT NOT NULL,
    provenance   TEXT NOT NULL,     -- json
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);
CREATE INDEX IF NOT EXISTS artifacts_session_idx ON artifacts (session_id);
CREATE INDEX IF NOT EXISTS artifacts_run_idx     ON artifacts (run_id);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id  TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL,
    actor        TEXT NOT NULL,
    target_kind  TEXT NOT NULL,
    target_id    TEXT NOT NULL,
    action       TEXT NOT NULL,
    payload      TEXT NOT NULL,     -- json
    created_at   TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
);
CREATE INDEX IF NOT EXISTS decisions_session_idx ON decisions (session_id);
"""


class InterfaceStore:
    """Simple SQLite CRUD wrapper.

    Not thread-safe for writes, but the vertical-slice server uses a
    single mutex around every mutation. Reads are safe on a per-cursor
    basis.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, isolation_level=None)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -------------------- sessions --------------------

    def put_session(self, s: Session) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions "
            "(session_id, have, want, actor, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (s.session_id, s.have, s.want, s.actor, s.status.value,
             s.created_at, s.updated_at),
        )

    def get_session(self, session_id: str) -> Session | None:
        row = self._conn.execute(
            "SELECT session_id, have, want, actor, status, created_at, "
            "updated_at FROM sessions WHERE session_id=?",
            (session_id,)).fetchone()
        if row is None:
            return None
        return Session(
            session_id=row[0], have=row[1], want=row[2], actor=row[3],
            status=SessionStatus(row[4]),
            created_at=row[5], updated_at=row[6],
        )

    def update_session_status(self, session_id: str,
                              status: SessionStatus) -> None:
        from .models import _now_iso
        self._conn.execute(
            "UPDATE sessions SET status=?, updated_at=? WHERE session_id=?",
            (status.value, _now_iso(), session_id),
        )

    # -------------------- inputs --------------------

    def put_input(self, x: InputArtifact) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO inputs "
            "(input_id, session_id, kind, body_text, mime, length_chars, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (x.input_id, x.session_id, x.kind.value, x.body_text, x.mime,
             x.length_chars, x.created_at),
        )

    def get_input(self, input_id: str) -> InputArtifact | None:
        row = self._conn.execute(
            "SELECT input_id, session_id, kind, body_text, mime, "
            "length_chars, created_at FROM inputs WHERE input_id=?",
            (input_id,)).fetchone()
        if row is None:
            return None
        return InputArtifact(
            input_id=row[0], session_id=row[1], kind=InputKind(row[2]),
            body_text=row[3], mime=row[4], length_chars=row[5],
            created_at=row[6],
        )

    def list_inputs(self, session_id: str) -> list[InputArtifact]:
        rows = self._conn.execute(
            "SELECT input_id, session_id, kind, body_text, mime, "
            "length_chars, created_at FROM inputs WHERE session_id=? "
            "ORDER BY created_at ASC",
            (session_id,)).fetchall()
        return [InputArtifact(
            input_id=r[0], session_id=r[1], kind=InputKind(r[2]),
            body_text=r[3], mime=r[4], length_chars=r[5], created_at=r[6],
        ) for r in rows]

    # -------------------- runs --------------------

    def put_run(self, r: Run) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs "
            "(run_id, session_id, input_id, mode, status, started_at, "
            "finished_at, terminal, response_text, dyad_causal, "
            "apparatus_class, sd_status, sd_authority, provider_id, "
            "model_id, duration_ms, error, trace_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (r.run_id, r.session_id, r.input_id, r.mode.value,
             r.status.value, r.started_at, r.finished_at, r.terminal,
             r.response_text, r.dyad_causal, r.apparatus_class,
             r.sd_status, r.sd_authority, r.provider_id, r.model_id,
             r.duration_ms, r.error, r.trace_ref),
        )

    def get_run(self, run_id: str) -> Run | None:
        row = self._conn.execute(
            "SELECT run_id, session_id, input_id, mode, status, started_at, "
            "finished_at, terminal, response_text, dyad_causal, "
            "apparatus_class, sd_status, sd_authority, provider_id, "
            "model_id, duration_ms, error, trace_ref "
            "FROM runs WHERE run_id=?",
            (run_id,)).fetchone()
        if row is None:
            return None
        return Run(
            run_id=row[0], session_id=row[1], input_id=row[2],
            mode=RunMode(row[3]), status=RunStatus(row[4]),
            started_at=row[5], finished_at=row[6], terminal=row[7],
            response_text=row[8], dyad_causal=row[9],
            apparatus_class=row[10], sd_status=row[11],
            sd_authority=row[12], provider_id=row[13], model_id=row[14],
            duration_ms=row[15], error=row[16], trace_ref=row[17],
        )

    def list_runs(self, session_id: str) -> list[Run]:
        rows = self._conn.execute(
            "SELECT run_id FROM runs WHERE session_id=? "
            "ORDER BY started_at ASC", (session_id,)).fetchall()
        return [self.get_run(r[0]) for r in rows if self.get_run(r[0])]

    # -------------------- artifacts --------------------

    def put_artifact(self, a: Artifact) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO artifacts "
            "(artifact_id, session_id, run_id, kind, title, body_md, "
            "provenance, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (a.artifact_id, a.session_id, a.run_id, a.kind.value,
             a.title, a.body_md, json.dumps(a.provenance, ensure_ascii=False),
             a.created_at),
        )

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        row = self._conn.execute(
            "SELECT artifact_id, session_id, run_id, kind, title, body_md, "
            "provenance, created_at FROM artifacts WHERE artifact_id=?",
            (artifact_id,)).fetchone()
        if row is None:
            return None
        return Artifact(
            artifact_id=row[0], session_id=row[1], run_id=row[2],
            kind=ArtifactKind(row[3]), title=row[4], body_md=row[5],
            provenance=json.loads(row[6] or "{}"), created_at=row[7],
        )

    def list_artifacts(self, session_id: str) -> list[Artifact]:
        rows = self._conn.execute(
            "SELECT artifact_id FROM artifacts WHERE session_id=? "
            "ORDER BY created_at ASC", (session_id,)).fetchall()
        return [self.get_artifact(r[0]) for r in rows if self.get_artifact(r[0])]

    # -------------------- decisions --------------------

    def put_decision(self, d: Decision) -> None:
        self._conn.execute(
            "INSERT INTO decisions "
            "(decision_id, session_id, actor, target_kind, target_id, "
            "action, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (d.decision_id, d.session_id, d.actor, d.target_kind,
             d.target_id, d.action.value,
             json.dumps(d.payload, ensure_ascii=False), d.created_at),
        )

    def list_decisions(self, session_id: str) -> list[Decision]:
        rows = self._conn.execute(
            "SELECT decision_id, session_id, actor, target_kind, "
            "target_id, action, payload, created_at "
            "FROM decisions WHERE session_id=? ORDER BY created_at ASC",
            (session_id,)).fetchall()
        return [Decision(
            decision_id=r[0], session_id=r[1], actor=r[2],
            target_kind=r[3], target_id=r[4],
            action=DecisionAction(r[5]),
            payload=json.loads(r[6] or "{}"), created_at=r[7],
        ) for r in rows]


__all__ = ["InterfaceStore"]

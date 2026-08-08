"""FabricStore — SQLite JSON1 хранилище семантической ткани.

Одна база на TinkuyWorkspace (или одна общая для всех запусков MVP).
Таблицы плоские, всё содержимое объектов ткани — в поле `payload` типа
TEXT (JSON), индексы — по идентификаторам и типам.

Round-trip: FabricSnapshot → save → load → эквивалентный FabricSnapshot.

Не ORM, не миграции, не транзакции сложнее одной. MVP.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .schemas import (
    FabricBlock,
    FabricEvidenceFragment,
    FabricRelation,
    FabricSceneState,
    FabricSnapshot,
    FabricSourceSpan,
    FabricThread,
    FabricUnit,
)


_DDL = """
CREATE TABLE IF NOT EXISTS source_artifact (
    source_id       TEXT PRIMARY KEY,
    title           TEXT,
    kind            TEXT,           -- transcript | article | note | ...
    original_bytes  INTEGER,
    created_at      TEXT,
    metadata_json   TEXT
);

CREATE TABLE IF NOT EXISTS source_version (
    source_id       TEXT NOT NULL,
    version         TEXT NOT NULL,
    text_sha256     TEXT,
    n_chars         INTEGER,
    created_at      TEXT,
    text_content    TEXT,           -- полный текст версии (можно вынести в fs, но пока inline)
    PRIMARY KEY (source_id, version),
    FOREIGN KEY (source_id) REFERENCES source_artifact(source_id)
);

CREATE TABLE IF NOT EXISTS source_span (
    span_id         TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    version         TEXT,
    char_start      INTEGER,
    char_end        INTEGER,
    locator         TEXT,
    payload         TEXT            -- полный dataclass как JSON
);

CREATE TABLE IF NOT EXISTS evidence_fragment (
    fragment_id     TEXT PRIMARY KEY,
    span_id         TEXT NOT NULL,
    verbatim        TEXT,
    payload         TEXT
);

CREATE TABLE IF NOT EXISTS fabric_unit (
    unit_id         TEXT PRIMARY KEY,
    snapshot_id     TEXT NOT NULL,
    intention       TEXT,
    text            TEXT,
    confidence      REAL,
    interpretation_status TEXT,
    payload         TEXT
);

CREATE TABLE IF NOT EXISTS fabric_block (
    block_id        TEXT PRIMARY KEY,
    snapshot_id     TEXT NOT NULL,
    block_type      TEXT,
    title           TEXT,
    interpretation_status TEXT,
    payload         TEXT
);

CREATE TABLE IF NOT EXISTS fabric_relation (
    relation_id     TEXT PRIMARY KEY,
    snapshot_id     TEXT NOT NULL,
    relation_type   TEXT,
    source_id_ref   TEXT,
    target_id_ref   TEXT,
    interpretation_status TEXT,
    payload         TEXT
);

CREATE TABLE IF NOT EXISTS fabric_thread (
    thread_id       TEXT PRIMARY KEY,
    snapshot_id     TEXT NOT NULL,
    thread_type     TEXT,
    label           TEXT,
    interpretation_status TEXT,
    payload         TEXT
);

CREATE TABLE IF NOT EXISTS fabric_snapshot (
    snapshot_id     TEXT PRIMARY KEY,
    source_id       TEXT,
    source_version  TEXT,
    created_at      TEXT,
    parser_run_id   TEXT,
    stats_json      TEXT,
    scene_json      TEXT
);

CREATE INDEX IF NOT EXISTS idx_unit_snapshot     ON fabric_unit(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_block_snapshot    ON fabric_block(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_relation_snapshot ON fabric_relation(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_thread_snapshot   ON fabric_thread(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_span_source       ON source_span(source_id);
"""


class FabricStore:
    """Открывает / создаёт SQLite базу, сохраняет и загружает snapshot'ы."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_DDL)
        self._conn.commit()

    # ---------- Sources ----------
    def register_source(
        self,
        source_id: str,
        title: str,
        kind: str,
        text_content: str,
        version: str = "v1",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        import hashlib
        now = datetime.now(timezone.utc).isoformat()
        sha = hashlib.sha256(text_content.encode("utf-8")).hexdigest()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO source_artifact (source_id, title, kind, original_bytes, created_at, metadata_json) "
            "VALUES (?,?,?,?,?,?)",
            (source_id, title, kind, len(text_content.encode("utf-8")), now,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        cur.execute(
            "INSERT OR REPLACE INTO source_version (source_id, version, text_sha256, n_chars, created_at, text_content) "
            "VALUES (?,?,?,?,?,?)",
            (source_id, version, sha, len(text_content), now, text_content),
        )
        self._conn.commit()

    def load_source_text(self, source_id: str, version: str = "v1") -> str | None:
        row = self._conn.execute(
            "SELECT text_content FROM source_version WHERE source_id=? AND version=?",
            (source_id, version),
        ).fetchone()
        return row[0] if row else None

    # ---------- Snapshot save ----------
    def save_snapshot(self, snap: FabricSnapshot) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO fabric_snapshot "
            "(snapshot_id, source_id, source_version, created_at, parser_run_id, stats_json, scene_json) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                snap.snapshot_id,
                snap.source_id,
                snap.source_version,
                snap.created_at or datetime.now(timezone.utc).isoformat(),
                snap.parser_run_id,
                json.dumps(snap.stats, ensure_ascii=False),
                json.dumps(asdict(snap.scene) if snap.scene else None, ensure_ascii=False),
            ),
        )
        for sp in snap.spans:
            cur.execute(
                "INSERT OR REPLACE INTO source_span "
                "(span_id, source_id, version, char_start, char_end, locator, payload) VALUES (?,?,?,?,?,?,?)",
                (sp.span_id, sp.source_id, sp.version, sp.char_start, sp.char_end, sp.locator,
                 json.dumps(asdict(sp), ensure_ascii=False)),
            )
        for ev in snap.evidence:
            cur.execute(
                "INSERT OR REPLACE INTO evidence_fragment (fragment_id, span_id, verbatim, payload) VALUES (?,?,?,?)",
                (ev.fragment_id, ev.span.span_id, ev.verbatim,
                 json.dumps(asdict(ev), ensure_ascii=False)),
            )
        for u in snap.units:
            cur.execute(
                "INSERT OR REPLACE INTO fabric_unit "
                "(unit_id, snapshot_id, intention, text, confidence, interpretation_status, payload) VALUES (?,?,?,?,?,?,?)",
                (u.unit_id, snap.snapshot_id, u.intention, u.text, u.confidence, u.interpretation_status,
                 json.dumps(asdict(u), ensure_ascii=False)),
            )
        for b in snap.blocks:
            cur.execute(
                "INSERT OR REPLACE INTO fabric_block "
                "(block_id, snapshot_id, block_type, title, interpretation_status, payload) VALUES (?,?,?,?,?,?)",
                (b.block_id, snap.snapshot_id, b.block_type, b.title, b.interpretation_status,
                 json.dumps(asdict(b), ensure_ascii=False)),
            )
        for r in snap.relations:
            cur.execute(
                "INSERT OR REPLACE INTO fabric_relation "
                "(relation_id, snapshot_id, relation_type, source_id_ref, target_id_ref, interpretation_status, payload) "
                "VALUES (?,?,?,?,?,?,?)",
                (r.relation_id, snap.snapshot_id, r.relation_type, r.source_id, r.target_id, r.interpretation_status,
                 json.dumps(asdict(r), ensure_ascii=False)),
            )
        for t in snap.threads:
            cur.execute(
                "INSERT OR REPLACE INTO fabric_thread "
                "(thread_id, snapshot_id, thread_type, label, interpretation_status, payload) VALUES (?,?,?,?,?,?)",
                (t.thread_id, snap.snapshot_id, t.thread_type, t.label, t.interpretation_status,
                 json.dumps(asdict(t), ensure_ascii=False)),
            )
        self._conn.commit()

    # ---------- Snapshot load ----------
    def load_snapshot(self, snapshot_id: str) -> FabricSnapshot | None:
        row = self._conn.execute(
            "SELECT source_id, source_version, created_at, parser_run_id, stats_json, scene_json "
            "FROM fabric_snapshot WHERE snapshot_id=?",
            (snapshot_id,),
        ).fetchone()
        if not row:
            return None
        source_id, source_version, created_at, parser_run_id, stats_json, scene_json = row

        def _rows_of(sql: str, ctor):
            out = []
            for (payload,) in self._conn.execute(sql, (snapshot_id,)):
                d = json.loads(payload)
                if ctor is FabricEvidenceFragment:
                    d["span"] = FabricSourceSpan(**d["span"])
                out.append(ctor(**d))
            return out

        units = _rows_of("SELECT payload FROM fabric_unit WHERE snapshot_id=?", FabricUnit)
        blocks = _rows_of("SELECT payload FROM fabric_block WHERE snapshot_id=?", FabricBlock)
        relations = _rows_of("SELECT payload FROM fabric_relation WHERE snapshot_id=?", FabricRelation)
        threads = _rows_of("SELECT payload FROM fabric_thread WHERE snapshot_id=?", FabricThread)

        # spans могут принадлежать нескольким snapshot'ам — грузим все для source
        spans: list[FabricSourceSpan] = []
        for (payload,) in self._conn.execute(
            "SELECT payload FROM source_span WHERE source_id=?", (source_id,)
        ):
            d = json.loads(payload)
            spans.append(FabricSourceSpan(**d))
        evidence: list[FabricEvidenceFragment] = []
        for (payload,) in self._conn.execute(
            "SELECT payload FROM evidence_fragment"
        ):
            d = json.loads(payload)
            d["span"] = FabricSourceSpan(**d["span"])
            evidence.append(FabricEvidenceFragment(**d))

        scene = None
        if scene_json and scene_json != "null":
            scene = FabricSceneState(**json.loads(scene_json))

        return FabricSnapshot(
            snapshot_id=snapshot_id,
            source_id=source_id,
            source_version=source_version or "",
            created_at=created_at or "",
            parser_run_id=parser_run_id or "",
            units=units,
            blocks=blocks,
            relations=relations,
            threads=threads,
            spans=spans,
            evidence=evidence,
            scene=scene,
            stats=json.loads(stats_json) if stats_json else {},
        )

    def list_snapshots(self, source_id: str | None = None) -> list[dict[str, Any]]:
        sql = ("SELECT snapshot_id, source_id, source_version, created_at, parser_run_id, stats_json "
               "FROM fabric_snapshot")
        args: tuple = ()
        if source_id:
            sql += " WHERE source_id=?"
            args = (source_id,)
        sql += " ORDER BY created_at DESC"
        out = []
        for row in self._conn.execute(sql, args):
            out.append({
                "snapshot_id": row[0],
                "source_id": row[1],
                "source_version": row[2],
                "created_at": row[3],
                "parser_run_id": row[4],
                "stats": json.loads(row[5]) if row[5] else {},
            })
        return out

    def close(self) -> None:
        self._conn.close()

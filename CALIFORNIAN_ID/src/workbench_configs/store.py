"""Persistence for :class:`PipelineConfig` — SQLite, one row per build.

Kept flat: three tables (configs, personal_active pointers, line_default
pointers). Fragment overlays and selection lists live inline as JSON blobs
because they never need to be queried across configs.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    ConfigStatus,
    ConstitutionalStatus,
    PipelineConfig,
    PromptFragmentOverlay,
    PromptVariantSelection,
    RAGProfileSelection,
    SemanticControlOverride,
)


_DDL = """
CREATE TABLE IF NOT EXISTS pipeline_config (
    config_id             TEXT PRIMARY KEY,
    owner_id              TEXT NOT NULL,
    workspace_id          TEXT NOT NULL,
    branch                TEXT NOT NULL,
    name                  TEXT NOT NULL,
    description           TEXT NOT NULL DEFAULT '',
    status                TEXT NOT NULL,
    parent_config_id      TEXT NOT NULL DEFAULT '',
    prompt_selections     TEXT NOT NULL DEFAULT '[]',
    prompt_overlays       TEXT NOT NULL DEFAULT '[]',
    rag_selections        TEXT NOT NULL DEFAULT '[]',
    semantic_overrides    TEXT NOT NULL DEFAULT '[]',
    model_binding         TEXT NOT NULL DEFAULT '{}',
    constitutional_status TEXT NOT NULL DEFAULT 'standard',
    protected_edits       TEXT NOT NULL DEFAULT '[]',
    schema_version        TEXT NOT NULL DEFAULT '0.1.0',
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    UNIQUE (owner_id, branch, name)
);

CREATE INDEX IF NOT EXISTS idx_config_owner_branch
    ON pipeline_config(owner_id, branch);

CREATE TABLE IF NOT EXISTS personal_active (
    owner_id     TEXT NOT NULL,
    branch       TEXT NOT NULL,
    config_id    TEXT NOT NULL,
    activated_at TEXT NOT NULL,
    PRIMARY KEY (owner_id, branch)
);

CREATE TABLE IF NOT EXISTS line_default (
    branch          TEXT PRIMARY KEY,
    config_id       TEXT NOT NULL,
    published_by    TEXT NOT NULL,
    published_at    TEXT NOT NULL,
    previous_id     TEXT NOT NULL DEFAULT ''
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_config_id() -> str:
    return "cfg_" + secrets.token_hex(8)


class PipelineConfigStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        # Initialise schema once from whichever thread built the store.
        self._conn.executescript(_DDL)

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    # ---------------- configs ----------------

    def save(self, cfg: PipelineConfig, *, is_new: bool) -> None:
        payload = (
            cfg.owner_id, cfg.workspace_id, cfg.branch, cfg.name, cfg.description,
            cfg.status, cfg.parent_config_id,
            json.dumps([{"asset_id": s.asset_id, "variant_id": s.variant_id}
                        for s in cfg.prompt_variant_selections],
                       ensure_ascii=False),
            json.dumps([{"asset_id": o.asset_id, "region_id": o.region_id,
                         "text": o.text, "source_hash": o.hashed().source_hash}
                        for o in cfg.prompt_fragment_overlays], ensure_ascii=False),
            json.dumps([{"engine_id": s.engine_id, "profile_id": s.profile_id}
                        for s in cfg.rag_profile_selections], ensure_ascii=False),
            json.dumps([{"control_id": o.control_id, "value": o.value}
                        for o in cfg.semantic_control_overrides], ensure_ascii=False),
            json.dumps(cfg.model_binding, ensure_ascii=False),
            cfg.constitutional_status,
            json.dumps([list(p) for p in cfg.protected_edits], ensure_ascii=False),
            cfg.schema_version,
        )
        if is_new:
            self._conn.execute(
                "INSERT INTO pipeline_config (config_id, owner_id, workspace_id, "
                "branch, name, description, status, parent_config_id, "
                "prompt_selections, prompt_overlays, rag_selections, "
                "semantic_overrides, model_binding, constitutional_status, "
                "protected_edits, schema_version, created_at, updated_at) "
                "VALUES (?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, ?,?)",
                (cfg.config_id, *payload, cfg.created_at, cfg.updated_at),
            )
        else:
            self._conn.execute(
                "UPDATE pipeline_config SET owner_id=?, workspace_id=?, branch=?, "
                "name=?, description=?, status=?, parent_config_id=?, "
                "prompt_selections=?, prompt_overlays=?, rag_selections=?, "
                "semantic_overrides=?, model_binding=?, constitutional_status=?, "
                "protected_edits=?, schema_version=?, updated_at=? "
                "WHERE config_id=?",
                (*payload, cfg.updated_at, cfg.config_id),
            )

    def new_config_id(self) -> str:
        return _new_config_id()

    def get(self, config_id: str) -> PipelineConfig | None:
        row = self._conn.execute(
            "SELECT config_id, owner_id, workspace_id, branch, name, description, "
            "status, parent_config_id, prompt_selections, prompt_overlays, "
            "rag_selections, semantic_overrides, model_binding, "
            "constitutional_status, protected_edits, schema_version, "
            "created_at, updated_at FROM pipeline_config WHERE config_id=?",
            (config_id,),
        ).fetchone()
        return self._row_to_config(row) if row else None

    def list_for_owner(self, owner_id: str, branch: str | None = None
                       ) -> list[PipelineConfig]:
        sql = ("SELECT config_id, owner_id, workspace_id, branch, name, description, "
               "status, parent_config_id, prompt_selections, prompt_overlays, "
               "rag_selections, semantic_overrides, model_binding, "
               "constitutional_status, protected_edits, schema_version, "
               "created_at, updated_at FROM pipeline_config WHERE owner_id=? ")
        args: tuple = (owner_id,)
        if branch:
            sql += "AND branch=? "
            args = (owner_id, branch)
        sql += "ORDER BY updated_at DESC"
        return [self._row_to_config(r) for r in self._conn.execute(sql, args)]

    def delete(self, config_id: str) -> None:
        self._conn.execute("DELETE FROM pipeline_config WHERE config_id=?", (config_id,))
        self._conn.execute("DELETE FROM personal_active WHERE config_id=?", (config_id,))

    # ---------------- personal active ----------------

    def set_personal_active(self, owner_id: str, branch: str,
                            config_id: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO personal_active "
            "(owner_id, branch, config_id, activated_at) VALUES (?,?,?,?)",
            (owner_id, branch, config_id, _now()),
        )

    def clear_personal_active(self, owner_id: str, branch: str) -> None:
        self._conn.execute(
            "DELETE FROM personal_active WHERE owner_id=? AND branch=?",
            (owner_id, branch))

    def get_personal_active(self, owner_id: str, branch: str) -> str | None:
        row = self._conn.execute(
            "SELECT config_id FROM personal_active WHERE owner_id=? AND branch=?",
            (owner_id, branch),
        ).fetchone()
        return row[0] if row else None

    # ---------------- line default ----------------

    def set_line_default(self, branch: str, config_id: str,
                         published_by: str) -> None:
        prev = self.get_line_default(branch) or ""
        self._conn.execute(
            "INSERT OR REPLACE INTO line_default "
            "(branch, config_id, published_by, published_at, previous_id) "
            "VALUES (?,?,?,?,?)",
            (branch, config_id, published_by, _now(), prev),
        )

    def get_line_default(self, branch: str) -> str | None:
        row = self._conn.execute(
            "SELECT config_id FROM line_default WHERE branch=?", (branch,),
        ).fetchone()
        return row[0] if row else None

    def line_default_history(self, branch: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT config_id, published_by, published_at, previous_id "
            "FROM line_default WHERE branch=?", (branch,),
        ).fetchone()
        if not row:
            return {"branch": branch, "config_id": None}
        return {"branch": branch, "config_id": row[0], "published_by": row[1],
                "published_at": row[2], "previous_id": row[3] or None}

    # ---------------- helpers ----------------

    @staticmethod
    def _row_to_config(row: tuple) -> PipelineConfig:
        return PipelineConfig(
            config_id=row[0], owner_id=row[1], workspace_id=row[2],
            branch=row[3], name=row[4], description=row[5], status=row[6],
            parent_config_id=row[7],
            prompt_variant_selections=tuple(
                PromptVariantSelection(**d) for d in json.loads(row[8] or "[]")),
            prompt_fragment_overlays=tuple(
                PromptFragmentOverlay(**d) for d in json.loads(row[9] or "[]")),
            rag_profile_selections=tuple(
                RAGProfileSelection(**d) for d in json.loads(row[10] or "[]")),
            semantic_control_overrides=tuple(
                SemanticControlOverride(**d) for d in json.loads(row[11] or "[]")),
            model_binding=json.loads(row[12] or "{}"),
            constitutional_status=row[13],
            protected_edits=tuple(tuple(p) for p in json.loads(row[14] or "[]")),
            schema_version=row[15],
            created_at=row[16], updated_at=row[17],
        )

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


__all__ = ["PipelineConfigStore"]

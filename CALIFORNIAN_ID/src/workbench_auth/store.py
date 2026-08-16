"""SQLite persistence for Workbench identity — one database, four tables.

Lives in ``<workbench_state>/auth.sqlite3``. Kept flat and unmigrated by
choice: the existing repositories that mattered (``FabricStore``,
``NarrativeStore``, ``UserStore``) all follow the same shape, and Workbench
identity has no reason to be more elaborate than the runtime it configures.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import AuthCode, Role, User


_DDL = """
CREATE TABLE IF NOT EXISTS workbench_user (
    user_id       TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL UNIQUE,
    roles_json    TEXT NOT NULL,
    pw_hash       BLOB,           -- empty for code-redemption-only accounts
    pw_salt       BLOB,
    pw_iters      INTEGER NOT NULL DEFAULT 0,
    disabled      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workbench_auth_code (
    code          TEXT PRIMARY KEY,
    roles_json    TEXT NOT NULL,
    minted_by     TEXT NOT NULL,
    minted_at     TEXT NOT NULL,
    expires_at    TEXT,
    redeemed_by   TEXT,
    redeemed_at   TEXT,
    note          TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_code_redeemed
    ON workbench_auth_code(redeemed_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_user_id() -> str:
    return "u_" + secrets.token_hex(8)


def _new_code() -> str:
    # 4-4-4 grouping, uppercase, no confusable characters.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


class WorkbenchAuthStore:
    """Owns the ``auth.sqlite3`` file. Nothing else does."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Thread-local connections. The HTTP server serves handlers on many
        # threads; sqlite3 connections cannot be shared across threads, so
        # each thread opens its own connection to the same file. WAL means
        # readers do not block writers and writes serialise inside sqlite.
        self._local = threading.local()
        # Initialise schema once, from whichever thread built the store.
        self._conn.executescript(_DDL)

    @property
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return conn

    # ---------------- users ----------------

    def add_user(self, display_name: str, roles: Iterable[str],
                 pw_hash: bytes = b"", pw_salt: bytes = b"",
                 pw_iters: int = 0) -> User:
        display_name = (display_name or "").strip()
        if not display_name:
            raise ValueError("display_name required")
        if len(display_name) > 64:
            raise ValueError("display_name too long (max 64)")
        role_list = sorted({Role.normalise(r) for r in roles} or {Role.USER})
        user_id = _new_user_id()
        created = _now()
        try:
            self._conn.execute(
                "INSERT INTO workbench_user (user_id, display_name, roles_json, "
                "pw_hash, pw_salt, pw_iters, disabled, created_at) "
                "VALUES (?,?,?,?,?,?,0,?)",
                (user_id, display_name,
                 json.dumps(role_list, ensure_ascii=False),
                 pw_hash, pw_salt, pw_iters, created),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"display_name {display_name!r} already taken") from exc
        return User(user_id=user_id, display_name=display_name,
                    roles=tuple(role_list), created_at=created, disabled=False)

    def get_user(self, user_id: str) -> User | None:
        row = self._conn.execute(
            "SELECT user_id, display_name, roles_json, disabled, created_at "
            "FROM workbench_user WHERE user_id=?", (user_id,),
        ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_name(self, display_name: str) -> User | None:
        row = self._conn.execute(
            "SELECT user_id, display_name, roles_json, disabled, created_at "
            "FROM workbench_user WHERE display_name=?",
            ((display_name or "").strip(),),
        ).fetchone()
        return self._row_to_user(row) if row else None

    def get_password_material(self, user_id: str) -> tuple[bytes, bytes, int] | None:
        row = self._conn.execute(
            "SELECT pw_hash, pw_salt, pw_iters FROM workbench_user WHERE user_id=?",
            (user_id,),
        ).fetchone()
        return (row[0], row[1], row[2]) if row else None

    def set_password(self, user_id: str, pw_hash: bytes, pw_salt: bytes,
                     pw_iters: int) -> None:
        self._conn.execute(
            "UPDATE workbench_user SET pw_hash=?, pw_salt=?, pw_iters=? "
            "WHERE user_id=?", (pw_hash, pw_salt, pw_iters, user_id),
        )

    def set_roles(self, user_id: str, roles: Iterable[str]) -> User | None:
        role_list = sorted({Role.normalise(r) for r in roles} or {Role.USER})
        self._conn.execute(
            "UPDATE workbench_user SET roles_json=? WHERE user_id=?",
            (json.dumps(role_list, ensure_ascii=False), user_id),
        )
        return self.get_user(user_id)

    def list_users(self, limit: int = 200) -> list[User]:
        rows = self._conn.execute(
            "SELECT user_id, display_name, roles_json, disabled, created_at "
            "FROM workbench_user ORDER BY created_at DESC LIMIT ?", (limit,),
        ).fetchall()
        return [self._row_to_user(r) for r in rows]

    # ---------------- codes ----------------

    def mint_code(self, roles: Iterable[str], minted_by: str,
                  expires_at: str = "", note: str = "") -> AuthCode:
        role_list = sorted({Role.normalise(r) for r in roles} or {Role.USER})
        # collisions on a 12-char alphabet are practically zero; retry once
        # anyway, keep the second attempt honest.
        for _ in range(2):
            code = _new_code()
            try:
                self._conn.execute(
                    "INSERT INTO workbench_auth_code (code, roles_json, minted_by, "
                    "minted_at, expires_at, note) VALUES (?,?,?,?,?,?)",
                    (code, json.dumps(role_list, ensure_ascii=False), minted_by,
                     _now(), expires_at or "", note),
                )
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise RuntimeError("could not mint unique auth code")
        return self.get_code(code)                 # type: ignore[return-value]

    def get_code(self, code: str) -> AuthCode | None:
        row = self._conn.execute(
            "SELECT code, roles_json, minted_by, minted_at, expires_at, "
            "redeemed_by, redeemed_at, note FROM workbench_auth_code WHERE code=?",
            ((code or "").strip().upper(),),
        ).fetchone()
        return self._row_to_code(row) if row else None

    def mark_redeemed(self, code: str, user_id: str) -> None:
        self._conn.execute(
            "UPDATE workbench_auth_code SET redeemed_by=?, redeemed_at=? "
            "WHERE code=?", (user_id, _now(), (code or "").strip().upper()),
        )

    def list_codes(self, only_unredeemed: bool = False,
                   limit: int = 200) -> list[AuthCode]:
        sql = ("SELECT code, roles_json, minted_by, minted_at, expires_at, "
               "redeemed_by, redeemed_at, note FROM workbench_auth_code ")
        if only_unredeemed:
            sql += "WHERE redeemed_by IS NULL OR redeemed_by='' "
        sql += "ORDER BY minted_at DESC LIMIT ?"
        rows = self._conn.execute(sql, (limit,)).fetchall()
        return [self._row_to_code(r) for r in rows]

    # ---------------- helpers ----------------

    @staticmethod
    def _row_to_user(row: tuple) -> User:
        return User(
            user_id=row[0], display_name=row[1],
            roles=tuple(json.loads(row[2] or "[]")),
            disabled=bool(row[3]),
            created_at=row[4],
        )

    @staticmethod
    def _row_to_code(row: tuple) -> AuthCode:
        return AuthCode(
            code=row[0], roles=tuple(json.loads(row[1] or "[]")),
            minted_by=row[2], minted_at=row[3], expires_at=row[4] or "",
            redeemed_by=row[5] or "", redeemed_at=row[6] or "",
            note=row[7] or "",
        )

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

"""Пик 6.4.1 — SQLite user table + password hashing (pbkdf2_hmac stdlib).

Store — SQLite в RUNS_DIR/users.sqlite3 (shared across workspaces).
Schema:
  user(username PRIMARY KEY, pw_hash, pw_salt, iters, roles_json,
       rate_limit_per_min, created_at, disabled)

Password: pbkdf2_hmac('sha256', password, salt, iters, 32). 200k iterations.
Passwords никогда не хранятся, только derived hash + salt.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import RUNS_DIR


ITERATIONS = 200_000
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")


def _users_db_path() -> Path:
    return RUNS_DIR / "users.sqlite3"


def _hash_password(password: str, salt: bytes | None = None,
                   iters: int = ITERATIONS) -> tuple[bytes, bytes, int]:
    if salt is None:
        salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters, 32)
    return h, salt, iters


def _verify_password(password: str, pw_hash: bytes, salt: bytes, iters: int) -> bool:
    h, _, _ = _hash_password(password, salt=salt, iters=iters)
    return hmac.compare_digest(h, pw_hash)


@dataclass
class User:
    username: str
    roles: list[str] = field(default_factory=list)
    rate_limit_per_min: int | None = None  # override для этого юзера
    disabled: bool = False
    created_at: str = ""


_DDL = """
CREATE TABLE IF NOT EXISTS user (
    username           TEXT PRIMARY KEY,
    pw_hash            BLOB NOT NULL,
    pw_salt            BLOB NOT NULL,
    iters              INTEGER NOT NULL,
    roles_json         TEXT,
    rate_limit_per_min INTEGER,
    disabled           INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT
);
"""


class UserStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _users_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_DDL)
        self._conn.commit()

    def add(self, username: str, password: str,
            roles: list[str] | None = None,
            rate_limit_per_min: int | None = None) -> User:
        if not _USERNAME_RE.match(username):
            raise ValueError(
                f"invalid username {username!r}: must match {_USERNAME_RE.pattern}"
            )
        if not password or len(password) < 8:
            raise ValueError("password too short (min 8 chars)")
        h, salt, iters = _hash_password(password)
        roles = roles or ["user"]
        now = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                "INSERT INTO user (username, pw_hash, pw_salt, iters, roles_json, "
                " rate_limit_per_min, disabled, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (username, h, salt, iters,
                 json.dumps(roles, ensure_ascii=False),
                 rate_limit_per_min, 0, now),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"user {username!r} already exists")
        return User(username=username, roles=roles,
                    rate_limit_per_min=rate_limit_per_min,
                    disabled=False, created_at=now)

    def verify(self, username: str, password: str) -> User | None:
        row = self._conn.execute(
            "SELECT pw_hash, pw_salt, iters, roles_json, rate_limit_per_min, "
            " disabled, created_at FROM user WHERE username=?",
            (username,),
        ).fetchone()
        if not row:
            return None
        pw_hash, pw_salt, iters, roles_json, rl, disabled, created_at = row
        if disabled:
            return None
        if not _verify_password(password, bytes(pw_hash), bytes(pw_salt), int(iters)):
            return None
        return User(
            username=username,
            roles=json.loads(roles_json or '["user"]'),
            rate_limit_per_min=rl,
            disabled=bool(disabled),
            created_at=created_at or "",
        )

    def get(self, username: str) -> User | None:
        row = self._conn.execute(
            "SELECT roles_json, rate_limit_per_min, disabled, created_at "
            "FROM user WHERE username=?", (username,),
        ).fetchone()
        if not row:
            return None
        return User(
            username=username,
            roles=json.loads(row[0] or '["user"]'),
            rate_limit_per_min=row[1],
            disabled=bool(row[2]),
            created_at=row[3] or "",
        )

    def list(self) -> list[User]:
        rows = self._conn.execute(
            "SELECT username, roles_json, rate_limit_per_min, disabled, created_at "
            "FROM user ORDER BY username"
        ).fetchall()
        return [
            User(username=r[0], roles=json.loads(r[1] or '["user"]'),
                 rate_limit_per_min=r[2], disabled=bool(r[3]),
                 created_at=r[4] or "")
            for r in rows
        ]

    def delete(self, username: str) -> bool:
        cur = self._conn.execute("DELETE FROM user WHERE username=?", (username,))
        self._conn.commit()
        return cur.rowcount > 0

    def set_disabled(self, username: str, disabled: bool) -> bool:
        cur = self._conn.execute(
            "UPDATE user SET disabled=? WHERE username=?",
            (1 if disabled else 0, username),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def close(self) -> None:
        self._conn.close()

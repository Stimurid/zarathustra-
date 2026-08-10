"""Пик 9.1 — Persistent narrative memory Zarathustra.

Хранит narrative notes Заратустры: заметки о повторяющихся паттернах, найденных
различениях, противоречиях между ранами. Позволяет накапливать понимание
между сессиями и предъявлять его юзеру.

Store — SQLite per-workspace, файл `narrative.sqlite3` рядом с fabric/runs.

Kind ∈ {observation, distinction, recurring_pattern, contradiction, hypothesis}.
related_run_ids — JSON list; used for cross-run reflection.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspaces import DEFAULT_WORKSPACE_ID, validate_workspace_id, workspace_dir


NOTE_KINDS = {"observation", "distinction", "recurring_pattern",
              "contradiction", "hypothesis"}


@dataclass
class NarrativeNote:
    note_id: str
    workspace_id: str
    kind: str
    text: str
    related_run_ids: list[str] = field(default_factory=list)
    author: str = "zarathustra"
    created_at: str = ""


_DDL = """
CREATE TABLE IF NOT EXISTS narrative_note (
    note_id           TEXT PRIMARY KEY,
    workspace_id      TEXT NOT NULL,
    kind              TEXT NOT NULL,
    text              TEXT NOT NULL,
    related_run_ids   TEXT,
    author            TEXT,
    created_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_note_workspace ON narrative_note(workspace_id);
CREATE INDEX IF NOT EXISTS idx_note_kind ON narrative_note(kind);
CREATE INDEX IF NOT EXISTS idx_note_created ON narrative_note(created_at DESC);
"""


def _store_path(ws: str) -> Path:
    return workspace_dir(ws) / "narrative.sqlite3"


class NarrativeStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_DDL)
        self._conn.commit()

    @classmethod
    def for_workspace(cls, ws: str | None = None) -> "NarrativeStore":
        return cls(_store_path(validate_workspace_id(ws or DEFAULT_WORKSPACE_ID)))

    def add(self, note: NarrativeNote) -> None:
        if note.kind not in NOTE_KINDS:
            raise ValueError(f"unknown note kind: {note.kind}")
        if not note.text or not note.text.strip():
            raise ValueError("note text required")
        self._conn.execute(
            "INSERT OR REPLACE INTO narrative_note "
            "(note_id, workspace_id, kind, text, related_run_ids, author, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (note.note_id, note.workspace_id, note.kind, note.text,
             json.dumps(note.related_run_ids or [], ensure_ascii=False),
             note.author or "zarathustra",
             note.created_at or datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def get(self, note_id: str) -> NarrativeNote | None:
        row = self._conn.execute(
            "SELECT note_id, workspace_id, kind, text, related_run_ids, author, created_at "
            "FROM narrative_note WHERE note_id=?", (note_id,),
        ).fetchone()
        return _row_to_note(row) if row else None

    def list(self, kind: str | None = None, limit: int = 100) -> list[NarrativeNote]:
        if kind:
            rows = self._conn.execute(
                "SELECT note_id, workspace_id, kind, text, related_run_ids, author, created_at "
                "FROM narrative_note WHERE kind=? "
                "ORDER BY created_at DESC LIMIT ?", (kind, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT note_id, workspace_id, kind, text, related_run_ids, author, created_at "
                "FROM narrative_note ORDER BY created_at DESC LIMIT ?", (limit,),
            ).fetchall()
        return [_row_to_note(r) for r in rows]

    def by_related_run(self, run_id: str) -> list[NarrativeNote]:
        # SQLite JSON1: JSON1 might not be enabled; simple LIKE fallback.
        rows = self._conn.execute(
            "SELECT note_id, workspace_id, kind, text, related_run_ids, author, created_at "
            "FROM narrative_note WHERE related_run_ids LIKE ? "
            "ORDER BY created_at DESC", (f'%"{run_id}"%',),
        ).fetchall()
        return [_row_to_note(r) for r in rows]

    def close(self) -> None:
        self._conn.close()


def _row_to_note(row: tuple) -> NarrativeNote:
    return NarrativeNote(
        note_id=row[0], workspace_id=row[1], kind=row[2], text=row[3],
        related_run_ids=json.loads(row[4] or "[]"),
        author=row[5] or "zarathustra",
        created_at=row[6] or "",
    )


def _short_note_id(workspace_id: str, run_id: str, kind: str) -> str:
    import hashlib
    seed = f"{workspace_id}|{run_id}|{kind}|{datetime.now(timezone.utc).timestamp()}"
    return "n_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def auto_record_observation(
    workspace_id: str,
    run_id: str,
    completion_form: str,
    stopping_reason: str,
    voices_used: list[str],
) -> NarrativeNote | None:
    """Дёргается из Pipeline._finalize_council. Записывает observation-note.

    Не бросает — если store fails, возвращает None и молча пишет warning.
    """
    import logging
    try:
        text = (
            f"Ран {run_id}: форма '{completion_form}', причина остановки "
            f"'{stopping_reason}'. Голоса: {', '.join(voices_used) or '—'}."
        )
        note = NarrativeNote(
            note_id=_short_note_id(workspace_id, run_id, "observation"),
            workspace_id=validate_workspace_id(workspace_id),
            kind="observation",
            text=text,
            related_run_ids=[run_id],
            author="zarathustra_auto",
        )
        store = NarrativeStore.for_workspace(workspace_id)
        try:
            store.add(note)
        finally:
            store.close()
        return note
    except Exception as ex:  # noqa: BLE001
        logging.getLogger("californian_id.narrative_memory").warning(
            "auto_record_observation failed: %s", ex)
        return None


def reflect_over_window(
    workspace_id: str,
    window: int = 10,
) -> dict[str, Any]:
    """LLM-driven рефлексия над последними N ранами workspace.

    Возвращает structured JSON с найденными паттернами / противоречиями /
    гипотезами. Автоматически создаёт narrative notes соответствующих kind'ов.
    """
    from .config import load_config
    from .models import Message, build_client
    from .workspaces import RunStore

    ws = validate_workspace_id(workspace_id)
    store = RunStore.for_workspace(ws)
    try:
        runs = store.list(limit=window)
    finally:
        store.close()

    if not runs:
        return {"workspace_id": ws, "window": window, "note_count": 0,
                "text": "нет ранов для рефлексии"}

    runs_summary = [
        {"run_id": m.run_id, "form": m.completion_form,
         "input_summary": m.input_summary[:200], "voices": m.voices_used}
        for m in runs
    ]

    cfg = load_config()
    provider_name = cfg.role_provider("synthesis")
    client = build_client(provider_name, cfg.provider_config(provider_name))

    system = (
        "Ты — Заратустра, глядящий на историю ранов совета в одном workspace. "
        "Найди: (1) повторяющиеся паттерны формы завершения; (2) противоречия "
        "между ранами; (3) гипотезы о том, что удерживает пользователя. "
        "Возврати JSON с ключами: recurring_patterns[], contradictions[], "
        "hypotheses[]. Каждый пункт — короткая строка (1-2 предложения)."
    )
    user = json.dumps({"workspace_id": ws, "runs": runs_summary}, ensure_ascii=False)
    messages = [Message(role="system", content=system), Message(role="user", content=user)]

    try:
        result = client.generate(messages, settings={"role": "narrative_reflect"})
        text = (result.text or "").strip()
        parsed: dict[str, Any] = {}
        # Try to extract JSON
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                parsed = {"raw_text": text}
        else:
            parsed = {"raw_text": text}
    except Exception as ex:
        return {"workspace_id": ws, "window": window, "error": str(ex)}

    # Записываем каждую как note.
    added: list[NarrativeNote] = []
    ns = NarrativeStore.for_workspace(ws)
    try:
        for kind, key in [("recurring_pattern", "recurring_patterns"),
                          ("contradiction", "contradictions"),
                          ("hypothesis", "hypotheses")]:
            for i, item in enumerate(parsed.get(key) or []):
                if not isinstance(item, str) or not item.strip():
                    continue
                note = NarrativeNote(
                    note_id=_short_note_id(ws, f"reflect_{kind}_{i}", kind),
                    workspace_id=ws,
                    kind=kind,
                    text=item.strip(),
                    related_run_ids=[m.run_id for m in runs],
                    author="zarathustra_reflect",
                )
                ns.add(note)
                added.append(note)
    finally:
        ns.close()

    return {
        "workspace_id": ws,
        "window": window,
        "runs_scanned": len(runs),
        "note_count": len(added),
        "notes": [asdict(n) for n in added],
        "raw_parsed": parsed,
        "provider": getattr(client, "provider", "?"),
    }

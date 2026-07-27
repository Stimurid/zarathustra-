"""Append-only trace recorder. One JSONL per run + one final state.json."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RUNS_DIR


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{ts}_{uuid.uuid4().hex[:8]}"


class TraceRecorder:
    def __init__(self, run_id: str, root: Path = RUNS_DIR):
        self.run_id = run_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self.dir / "events.jsonl"

    def event(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "kind": kind,
            "payload": payload or {},
        }
        with self._events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def dump_state(self, state: dict[str, Any], name: str = "state.json") -> Path:
        path = self.dir / name
        with path.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
        return path

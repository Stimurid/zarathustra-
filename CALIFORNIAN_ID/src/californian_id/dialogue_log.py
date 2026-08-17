"""Append-only dialogue log for production diagnostics.

One JSON object per line. Path from env ``TINKUY_DIALOGUE_LOG`` —
if the env var is unset OR the directory cannot be written, logging
silently no-ops. Logging failure MUST NOT affect the response.

Written for the owner's ability to pull dialogues from the VM
without a UI surface. Fields kept flat and small — enough to
reproduce a request and check what came back.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any


_ENV_VAR = "TINKUY_DIALOGUE_LOG"
_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _path() -> str | None:
    p = os.environ.get(_ENV_VAR, "").strip()
    return p or None


def log_dialogue(*, source: str, input_text: str,
                  response: dict[str, Any] | None = None,
                  error: str | None = None,
                  extra: dict[str, Any] | None = None) -> None:
    """Append one dialogue event.

    `source` — short tag like 'socrates', 'run', 'run_async',
    'v1_chat'. `input_text` — the caller's prompt (truncated for
    safety). `response` — the JSON payload returned to the caller.
    `error` — exception summary if the request failed. `extra` —
    any additional context (workspace_id, run_id).
    """
    path = _path()
    if not path:
        return
    try:
        response = response or {}
        rendering = response.get("rendering") or {}
        terminal = response.get("terminal") or {}
        terminal_name = (terminal.get("terminal")
                          if isinstance(terminal, dict) else str(terminal))
        record: dict[str, Any] = {
            "ts": _now_iso(),
            "source": source,
            "run_id": response.get("run_id"),
            "trace_id": response.get("trace_id"),
            "runtime_layer": response.get("runtime_layer"),
            "execution_mode": response.get("execution_mode"),
            "provider_id": response.get("provider_id"),
            "model_id": response.get("model_id"),
            "terminal": terminal_name,
            "intervention_profile": response.get("intervention_profile"),
            "duration_ms": response.get("duration_ms"),
            "input_text": (input_text or "")[:8192],
            "rendering_text": (rendering.get("text") if isinstance(rendering, dict) else None) or response.get("response_text") or "",
        }
        if error:
            record["error"] = error[:2000]
        if extra:
            for k, v in extra.items():
                if k not in record:
                    record[k] = v
        line = json.dumps(record, ensure_ascii=False,
                           separators=(",", ":")) + "\n"
        directory = os.path.dirname(path) or "."
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception:
            pass
        with _LOCK:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
    except Exception:
        # Logging must never affect the request path.
        return


__all__ = ["log_dialogue"]

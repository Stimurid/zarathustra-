"""6.3 — Async job queue.

Модель: пользователь POST'ит `/api/run/async` → мы регистрируем job в
per-workspace RunStore (status=RUNNING, created_at=now), запускаем worker
в ThreadPoolExecutor, немедленно возвращаем `{run_id}` (202).

Worker выполняет полный pipeline, потом:
  - обновляет RunMetadata (status=COMPLETED|ERROR, finished_at, form, turns…)
  - дампит полный payload в `<workspace>/results/<run_id>.json`

GET `/api/run/<run_id>/status` → метаданные из RunStore.
GET `/api/run/<run_id>/result` → payload из файла.

Юзер может закрыть браузер и вернуться — job живёт независимо (пока
процесс не помрёт; на restart незавершённые становятся ORPHANED).
"""
from __future__ import annotations

import json
import logging
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .workspaces import (
    DEFAULT_WORKSPACE_ID,
    RunMetadata,
    RunStore,
    validate_workspace_id,
    workspace_dir,
)


logger = logging.getLogger("californian_id.async_jobs")

# Один глобальный пул — worker'ы одинаковы, отличаются input'ом.
_MAX_WORKERS = 4
_pool = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="tinkuy-async")
_lock = threading.Lock()


def _results_dir(workspace_id: str) -> Path:
    d = workspace_dir(workspace_id) / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def result_path(workspace_id: str, run_id: str) -> Path:
    return _results_dir(workspace_id) / f"{run_id}.json"


def register_pending(
    workspace_id: str,
    run_id: str,
    input_summary: str,
    input_mode: str,
    mode: str,
) -> None:
    """Записать job как RUNNING до запуска worker'а."""
    workspace_id = validate_workspace_id(workspace_id)
    store = RunStore.for_workspace(workspace_id)
    try:
        store.save(RunMetadata(
            run_id=run_id, workspace_id=workspace_id, mode=mode,
            status="RUNNING", stopping_reason="", completion_form="",
            input_mode=input_mode, input_summary=input_summary[:200],
            trace_dir="", turn_count=0, voices_used=[],
            created_at=datetime.now(timezone.utc).isoformat(),
        ))
    finally:
        store.close()


def submit(
    workspace_id: str | None,
    run_id: str,
    job_fn: Callable[[], dict[str, Any]],
    input_summary: str,
    input_mode: str,
    mode: str,
) -> str:
    """Register + enqueue. Returns run_id.

    B-5.5 race-fix (v2): регистрируем run в runtime_control ДО _pool.submit,
    чтобы WS-subscribers, дошедшие раньше worker'а, видели зарегистрированный
    state (не UNKNOWN) и попадали в _subscribers[run_id] до эмиссии первых
    событий pipeline.
    """
    workspace_id = validate_workspace_id(workspace_id or DEFAULT_WORKSPACE_ID)
    register_pending(workspace_id, run_id, input_summary, input_mode, mode)

    # runtime_control pre-register — subscribe хватает state до worker'а
    try:
        from . import runtime_control as _rc
        _rc.register(run_id, workspace_id)
    except Exception:
        pass  # best-effort; Pipeline register тоже вызовет

    def _worker() -> None:
        try:
            payload = job_fn()
            _finalize_success(workspace_id, run_id, payload)
        except Exception as ex:  # noqa: BLE001
            logger.exception("async job %s failed", run_id)
            _finalize_error(workspace_id, run_id, ex)

    _pool.submit(_worker)
    return run_id


_CLIENT_RUN_ID_RE = None
def is_valid_client_run_id(run_id: str) -> bool:
    """B-5.5 race-fix: client-provided run_id должен матчить строгий шаблон.

    Формат: `run_` + 8-56 char slug из [a-z0-9_-]. Общий размер 12-60.
    """
    import re
    global _CLIENT_RUN_ID_RE
    if _CLIENT_RUN_ID_RE is None:
        _CLIENT_RUN_ID_RE = re.compile(r"^run_[a-z0-9_-]{8,56}$")
    return bool(run_id and _CLIENT_RUN_ID_RE.match(run_id))


def run_id_conflict(workspace_id: str, run_id: str) -> bool:
    """Проверяет что run_id ещё не занят (нет в RunStore + не в live registry)."""
    from . import runtime_control as _rc
    if _rc.get(run_id) is not None:
        return True
    return get_status(workspace_id, run_id) is not None


def _finalize_success(workspace_id: str, run_id: str, payload: dict[str, Any]) -> None:
    # Payload contains completion/turns/voices — persist and update RunStore.
    p = result_path(workspace_id, run_id)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                 encoding="utf-8")

    store = RunStore.for_workspace(workspace_id)
    try:
        existing = store.get(run_id)
        base = existing or RunMetadata(
            run_id=run_id, workspace_id=workspace_id,
            mode=payload.get("mode", ""), status="",
        )
        base.status = str(payload.get("status") or "COMPLETED")
        base.stopping_reason = str(payload.get("stopping_reason") or "")
        completion = payload.get("completion") or {}
        base.completion_form = str(completion.get("form") or "")
        base.turn_count = int(payload.get("turn_count") or 0)
        base.voices_used = list(payload.get("voices_used") or [])
        base.trace_dir = str(payload.get("trace_dir") or "")
        base.input_mode = str(payload.get("input_mode") or base.input_mode)
        base.finished_at = datetime.now(timezone.utc).isoformat()
        base.error = "; ".join(payload.get("errors") or [])
        store.save(base, extra_payload={"result_file": str(p)})
    finally:
        store.close()


def _finalize_error(workspace_id: str, run_id: str, ex: Exception) -> None:
    tb = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))[-2000:]
    p = result_path(workspace_id, run_id)
    p.write_text(json.dumps({
        "error": f"{type(ex).__name__}: {ex}",
        "traceback": tb,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    store = RunStore.for_workspace(workspace_id)
    try:
        existing = store.get(run_id)
        base = existing or RunMetadata(
            run_id=run_id, workspace_id=workspace_id, mode="", status="",
        )
        base.status = "ERROR"
        base.finished_at = datetime.now(timezone.utc).isoformat()
        base.error = f"{type(ex).__name__}: {ex}"[:500]
        store.save(base, extra_payload={"result_file": str(p)})
    finally:
        store.close()


def get_status(workspace_id: str, run_id: str) -> dict[str, Any] | None:
    workspace_id = validate_workspace_id(workspace_id)
    store = RunStore.for_workspace(workspace_id)
    try:
        m = store.get(run_id)
    finally:
        store.close()
    if not m:
        return None
    return asdict(m)


def get_result(workspace_id: str, run_id: str) -> dict[str, Any] | None:
    p = result_path(validate_workspace_id(workspace_id), run_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

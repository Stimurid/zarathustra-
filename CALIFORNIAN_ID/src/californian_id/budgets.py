"""Пик 9.2 — Cost budgets enforcement (soft/hard, per-workspace).

Модель: budgets определяются в YAML файле (путь через env
`CALIFORNIAN_ID_BUDGETS_YAML`). Формат:

    default:
      soft: 100   # предупреждение
      hard: 1000  # отказ
    alice:
      soft: 500
      hard: 5000

Метрика — число ранов в workspace (из RunStore). Простая, честная.

Enforcement:
  - `check(workspace_id) -> BudgetStatus`
  - `should_deny(...)` — True если hard превышен
  - `should_warn(...)` — True если soft превышен

Опция `CALIFORNIAN_ID_BUDGETS_DISABLED=1` полностью отключает enforcement.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .workspaces import RunStore, validate_workspace_id


ENV_PATH = "CALIFORNIAN_ID_BUDGETS_YAML"
ENV_DISABLE = "CALIFORNIAN_ID_BUDGETS_DISABLED"


@dataclass
class BudgetStatus:
    workspace_id: str
    runs_count: int
    soft_limit: int | None
    hard_limit: int | None
    soft_exceeded: bool
    hard_exceeded: bool


@lru_cache(maxsize=1)
def _load_budgets() -> dict[str, dict[str, int]]:
    p = os.environ.get(ENV_PATH)
    if not p:
        return {}
    path = Path(p)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        # only accept clean shape {ws: {soft:int, hard:int}}
        out: dict[str, dict[str, int]] = {}
        for ws, spec in raw.items():
            if not isinstance(spec, dict):
                continue
            entry: dict[str, int] = {}
            if "soft" in spec:
                try:
                    entry["soft"] = int(spec["soft"])
                except (TypeError, ValueError):
                    pass
            if "hard" in spec:
                try:
                    entry["hard"] = int(spec["hard"])
                except (TypeError, ValueError):
                    pass
            if entry:
                out[str(ws)] = entry
        return out
    except Exception:
        return {}


def is_disabled() -> bool:
    return (os.environ.get(ENV_DISABLE) or "").lower() in {"1", "true", "yes"}


def _limits_for(workspace_id: str) -> dict[str, int]:
    budgets = _load_budgets()
    return budgets.get(workspace_id) or budgets.get("default") or {}


def check(workspace_id: str) -> BudgetStatus:
    ws = validate_workspace_id(workspace_id)
    if is_disabled() or not _load_budgets():
        return BudgetStatus(ws, 0, None, None, False, False)

    store = RunStore.for_workspace(ws)
    try:
        runs = store.list(limit=100000)
    finally:
        store.close()
    n = len(runs)
    limits = _limits_for(ws)
    soft = limits.get("soft")
    hard = limits.get("hard")
    return BudgetStatus(
        workspace_id=ws,
        runs_count=n,
        soft_limit=soft,
        hard_limit=hard,
        soft_exceeded=bool(soft is not None and n >= soft),
        hard_exceeded=bool(hard is not None and n >= hard),
    )


def should_deny(workspace_id: str) -> tuple[bool, dict[str, Any]]:
    st = check(workspace_id)
    if st.hard_exceeded:
        return True, {
            "reason": "hard budget exceeded",
            "workspace_id": st.workspace_id,
            "runs_count": st.runs_count,
            "hard_limit": st.hard_limit,
        }
    return False, {}


def summary(workspace_id: str | None = None) -> dict[str, Any]:
    if workspace_id:
        st = check(workspace_id)
        return {
            "workspace_id": st.workspace_id, "runs_count": st.runs_count,
            "soft_limit": st.soft_limit, "hard_limit": st.hard_limit,
            "soft_exceeded": st.soft_exceeded,
            "hard_exceeded": st.hard_exceeded,
            "disabled": is_disabled(),
        }
    from .workspaces import list_workspaces
    per_ws = []
    for w in list_workspaces():
        st = check(w["workspace_id"])
        per_ws.append({
            "workspace_id": st.workspace_id, "runs_count": st.runs_count,
            "soft_limit": st.soft_limit, "hard_limit": st.hard_limit,
            "soft_exceeded": st.soft_exceeded,
            "hard_exceeded": st.hard_exceeded,
        })
    return {
        "disabled": is_disabled(),
        "budgets_file": os.environ.get(ENV_PATH) or "",
        "budgets_defined": _load_budgets(),
        "per_workspace": per_ws,
    }

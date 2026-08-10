"""Пик 8.3 — Multi-key auth + rate limit + billing counters.

API keys описываются в env-var `CALIFORNIAN_ID_API_KEYS` в формате:
    key1:label1,key2:label2,...

`TINKUY_COMPAT_API_KEY` — legacy single-key; при наличии добавляется как
label='default'. Отсутствие ключей → all_deny (для prod), но dev-путь всё
равно проходит если явно задан env `CALIFORNIAN_ID_AUTH_DISABLED=1`.

Rate limit — in-memory sliding window (60-sec bucket), per-label. Default
лимит: 30 req/min. Override через `CALIFORNIAN_ID_RATE_LIMIT_PER_MIN`.

Billing — простой in-memory + запись метки в RunMetadata.api_key_label.
Для агрегатов используется RunStore.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock


LEGACY_ENV = "TINKUY_COMPAT_API_KEY"
MULTI_ENV = "CALIFORNIAN_ID_API_KEYS"
DISABLE_ENV = "CALIFORNIAN_ID_AUTH_DISABLED"
LIMIT_ENV = "CALIFORNIAN_ID_RATE_LIMIT_PER_MIN"


@dataclass
class KeyInfo:
    key: str
    label: str


def _parse_multi_keys() -> list[KeyInfo]:
    raw = os.environ.get(MULTI_ENV) or ""
    out: list[KeyInfo] = []
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                k, lbl = part.split(":", 1)
                k = k.strip(); lbl = lbl.strip()
            else:
                k, lbl = part, part[:8]
            if k:
                out.append(KeyInfo(key=k, label=lbl or k[:8]))
    legacy = os.environ.get(LEGACY_ENV) or ""
    if legacy and not any(k.key == legacy for k in out):
        out.append(KeyInfo(key=legacy, label="default"))
    return out


# Cached at import; env-var changes require process restart.
_KEYS = _parse_multi_keys()
_KEY_INDEX = {k.key: k for k in _KEYS}


def is_disabled() -> bool:
    return (os.environ.get(DISABLE_ENV) or "").lower() in {"1", "true", "yes"}


def any_keys_configured() -> bool:
    return bool(_KEYS)


def label_for_bearer(bearer: str) -> str | None:
    """Возвращает label ключа, если bearer валиден; None иначе."""
    if not bearer:
        return None
    info = _KEY_INDEX.get(bearer)
    return info.label if info else None


# ---------- Rate limit ----------
_WINDOW_SEC = 60
try:
    _DEFAULT_LIMIT = int(os.environ.get(LIMIT_ENV) or "30")
except ValueError:
    _DEFAULT_LIMIT = 30

_rl_lock = Lock()
_rl_buckets: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(label: str, limit_per_min: int | None = None) -> tuple[bool, int, int]:
    """Возвращает (allowed, remaining, limit).

    Sliding window: держим timestamps последних запросов, отбрасываем те,
    что старше 60 сек. Если len < limit — allow + append.
    """
    limit = limit_per_min if (limit_per_min and limit_per_min > 0) else _DEFAULT_LIMIT
    now = time.monotonic()
    with _rl_lock:
        bucket = _rl_buckets[label]
        # drop old
        while bucket and (now - bucket[0]) > _WINDOW_SEC:
            bucket.popleft()
        if len(bucket) >= limit:
            return False, 0, limit
        bucket.append(now)
        return True, limit - len(bucket), limit


def bucket_snapshot() -> dict[str, dict[str, int]]:
    """Для /api/billing — сколько запросов в последнем окне на label."""
    now = time.monotonic()
    out: dict[str, dict[str, int]] = {}
    with _rl_lock:
        for label, bucket in list(_rl_buckets.items()):
            fresh = [t for t in bucket if (now - t) <= _WINDOW_SEC]
            out[label] = {
                "requests_last_60s": len(fresh),
                "limit_per_min": _DEFAULT_LIMIT,
            }
    return out


# ---------- Billing aggregation ----------
def billing_summary(workspace_id: str | None = None) -> dict:
    """Компонует billing-сводку: rate-limit + завершённые раны из RunStore."""
    from .workspaces import RunStore, list_workspaces, validate_workspace_id
    if workspace_id:
        workspaces = [validate_workspace_id(workspace_id)]
    else:
        workspaces = [w["workspace_id"] for w in list_workspaces()]

    runs_by_key: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total_by_ws: dict[str, int] = defaultdict(int)
    for ws in workspaces:
        try:
            store = RunStore.for_workspace(ws)
        except Exception:
            continue
        try:
            for m in store.list(limit=1000):
                total_by_ws[ws] += 1
                # RunMetadata сейчас нет поля api_key_label — временно берём
                # из workspace_id (пока нет), считаем "unlabelled".
                label = "unlabelled"
                runs_by_key[label][m.status or "UNKNOWN"] += 1
        finally:
            store.close()
    return {
        "rate_limit": bucket_snapshot(),
        "runs_by_key_status": {k: dict(v) for k, v in runs_by_key.items()},
        "runs_by_workspace": dict(total_by_ws),
        "keys_configured": [k.label for k in _KEYS],
    }

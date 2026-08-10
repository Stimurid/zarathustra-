"""Пик 8.2 — Cross-run search + comparison.

Простой lexical поиск по RunStore (per-workspace) — token-overlap на
input_summary + completion_form. Для сравнения двух ранов — LLM-driven,
использует synthesis-role provider (не самый heavy — совет уже свершился).
"""
from __future__ import annotations

import json
import re
from typing import Any

from .async_jobs import get_result
from .workspaces import RunStore, validate_workspace_id


_WORD_RE = re.compile(r"[\w\-]+", re.UNICODE)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _WORD_RE.findall(text or "")}


def search_runs(
    workspace_id: str,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Простой relevance-scored search по RunStore."""
    workspace_id = validate_workspace_id(workspace_id)
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    store = RunStore.for_workspace(workspace_id)
    try:
        all_runs = store.list(limit=500)
    finally:
        store.close()
    scored: list[tuple[float, dict[str, Any]]] = []
    for m in all_runs:
        haystack = " ".join(filter(None, [
            m.input_summary, m.completion_form, m.mode, m.input_mode,
            " ".join(m.voices_used),
        ]))
        h_tokens = _tokenize(haystack)
        if not h_tokens:
            continue
        overlap = len(q_tokens & h_tokens)
        if overlap == 0:
            continue
        # чуть-чуть весим по покрытию query
        score = overlap / max(len(q_tokens), 1)
        scored.append((score, {
            "run_id": m.run_id, "workspace_id": m.workspace_id,
            "mode": m.mode, "status": m.status,
            "completion_form": m.completion_form,
            "input_mode": m.input_mode,
            "input_summary": m.input_summary,
            "turn_count": m.turn_count,
            "voices_used": m.voices_used,
            "created_at": m.created_at,
            "score": round(score, 3),
        }))
    scored.sort(key=lambda x: (-x[0], x[1].get("created_at") or ""), reverse=False)
    scored.sort(key=lambda x: -x[0])  # stable primary by score desc
    return [row for _, row in scored[:limit]]


def _extract_comparable(run_id: str, workspace_id: str) -> dict[str, Any] | None:
    payload = get_result(workspace_id, run_id)
    if not payload:
        return None
    completion = payload.get("completion") or {}
    return {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "form": completion.get("form", ""),
        "rationale": completion.get("rationale", ""),
        "closing_speech": (payload.get("closing_speech") or completion.get("closing_speech") or "")[:2000],
        "conflict_map": completion.get("conflict_map") or [],
        "minority_positions": completion.get("minority_positions") or [],
        "unresolved_questions": completion.get("unresolved_questions") or [],
        "input_summary": (payload.get("input_mode") or "") + " | " + (payload.get("mode") or ""),
        "turn_count": payload.get("turn_count", 0),
        "voices_used": payload.get("voices_used", []),
    }


def compare_runs(
    workspace_id: str,
    run_id_a: str,
    run_id_b: str,
) -> dict[str, Any]:
    """LLM-driven сравнение двух ранов. Возвращает structured JSON.

    HARD_RULES §1: если LLM-провайдер = mock, всё равно возвращаем сравнение,
    но помечаем `provider: mock`. Реальное сравнение будет с реальным LLM.
    """
    workspace_id = validate_workspace_id(workspace_id)
    a = _extract_comparable(run_id_a, workspace_id)
    b = _extract_comparable(run_id_b, workspace_id)
    if a is None or b is None:
        return {"error": "one or both runs not found or not ready",
                "run_a_found": a is not None, "run_b_found": b is not None}

    from .config import load_config
    from .models import build_client, Message

    cfg = load_config()
    provider_name = cfg.role_provider("synthesis")
    client = build_client(provider_name, cfg.provider_config(provider_name))

    system = (
        "Ты — сравнивающий аналитик Тинкуя. Дан результат двух прошедших "
        "советов (совет A и совет B) в одном workspace. Твоя задача — "
        "структурно сравнить их: общее, различия, что один увидел а "
        "другой упустил, эволюция позиции. Выдай ТОЛЬКО валидный JSON."
    )
    user_payload = {
        "A": a, "B": b,
        "output_schema": {
            "shared_ground": "list[str]",
            "key_differences": "list[str]",
            "what_A_saw_that_B_missed": "list[str]",
            "what_B_saw_that_A_missed": "list[str]",
            "position_evolution": "str",
            "recommended_next_move": "str",
        },
    }
    messages = [
        Message(role="system", content=system),
        Message(role="user", content=json.dumps(user_payload, ensure_ascii=False)),
    ]
    try:
        result = client.generate(messages, settings={"role": "cross_run_compare"})
        text = (result.text or "").strip()
        # ищем json-объект в ответе
        parsed: dict[str, Any] | None = None
        for candidate in [text, _strip_fence(text)]:
            try:
                parsed = json.loads(candidate)
                break
            except Exception:
                continue
        if parsed is None:
            parsed = {"raw_text": text[:4000], "note": "LLM did not return valid JSON"}
        parsed["_provider"] = getattr(client, "provider", "?")
        parsed["_model"] = getattr(client, "model", "?")
        parsed["run_a"] = run_id_a
        parsed["run_b"] = run_id_b
        return parsed
    except Exception as ex:
        return {"error": f"compare failed: {type(ex).__name__}: {ex}",
                "run_a": run_id_a, "run_b": run_id_b}


def _strip_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    return stripped

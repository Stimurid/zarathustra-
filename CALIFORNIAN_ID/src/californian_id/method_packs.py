"""Пик 7.1 — MethodPack registry + loader.

MethodPack = универсальная процедура работы над содержанием
(claim analysis, argument reconstruction, conceptual analysis,
ontological reconstruction, problematisation, socratic inquiry).

Хранится в `data/method_packs/`. Не привязан к конкретной персоне —
персона может исполнять любой метод.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from .config import DATA_ROOT


METHOD_PACK_DIR = DATA_ROOT / "method_packs"


@dataclass
class MethodPack:
    method_id: str
    display_name: str
    prompt_file: str
    prompt_text: str = ""
    triggers_on: list[str] = field(default_factory=list)
    outputs_expected: list[str] = field(default_factory=list)


def _load_registry() -> tuple[dict[str, MethodPack], list[str]]:
    reg_path = METHOD_PACK_DIR / "registry.yaml"
    if not reg_path.exists():
        return {}, [f"registry.yaml missing at {reg_path}"]
    with reg_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    issues: list[str] = []
    out: dict[str, MethodPack] = {}
    for mid, spec in (raw.get("methods") or {}).items():
        prompt_file = spec.get("prompt_file")
        prompt_path = METHOD_PACK_DIR / prompt_file if prompt_file else None
        prompt_text = ""
        if prompt_path is None or not prompt_path.exists():
            issues.append(f"method {mid}: prompt_file missing ({prompt_file})")
        else:
            prompt_text = prompt_path.read_text(encoding="utf-8")
        out[mid] = MethodPack(
            method_id=mid,
            display_name=spec.get("display_name") or mid,
            prompt_file=prompt_file or "",
            prompt_text=prompt_text,
            triggers_on=list(spec.get("triggers_on") or []),
            outputs_expected=list(spec.get("outputs_expected") or []),
        )
    return out, issues


@lru_cache(maxsize=1)
def registry() -> dict[str, MethodPack]:
    packs, issues = _load_registry()
    if issues:
        import logging
        logging.getLogger("californian_id.method_packs").warning(
            "MethodPack registry issues: %s", issues
        )
    return packs


def get(method_id: str) -> MethodPack | None:
    return registry().get(method_id)


def list_methods() -> list[dict[str, Any]]:
    return [
        {
            "method_id": m.method_id,
            "display_name": m.display_name,
            "outputs_expected": m.outputs_expected,
        }
        for m in registry().values()
    ]

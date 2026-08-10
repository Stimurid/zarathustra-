"""Пик 7.4 — DialogueProtocol registry (канон 106-111).

Protocol — способ, которым голос слушает и отвечает. Ортогонален operation:
одна и та же операция может исполняться в любом протоколе.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from .config import DATA_ROOT


DIALOGUE_DIR = DATA_ROOT / "dialogue_protocols"


@dataclass
class DialogueProtocol:
    protocol_id: str
    display_name: str
    prompt_file: str
    purpose: str
    prompt_text: str = ""


def _load() -> tuple[dict[str, DialogueProtocol], str, list[str]]:
    reg = DIALOGUE_DIR / "registry.yaml"
    issues: list[str] = []
    if not reg.exists():
        return {}, "", [f"missing {reg}"]
    with reg.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    default = raw.get("default_protocol") or ""
    out: dict[str, DialogueProtocol] = {}
    for pid, spec in (raw.get("protocols") or {}).items():
        pf = spec.get("prompt_file")
        p = DIALOGUE_DIR / pf if pf else None
        text = p.read_text(encoding="utf-8") if (p and p.exists()) else ""
        if not text:
            issues.append(f"protocol {pid}: prompt_file missing")
        out[pid] = DialogueProtocol(
            protocol_id=pid,
            display_name=spec.get("display_name") or pid,
            prompt_file=pf or "",
            purpose=spec.get("purpose") or "",
            prompt_text=text,
        )
    return out, default, issues


@lru_cache(maxsize=1)
def registry() -> dict[str, DialogueProtocol]:
    p, _, issues = _load()
    if issues:
        import logging
        logging.getLogger("californian_id.dialogue_protocols").warning(
            "DialogueProtocol registry issues: %s", issues
        )
    return p


@lru_cache(maxsize=1)
def default_protocol_id() -> str:
    _, d, _ = _load()
    return d


def get(protocol_id: str | None) -> DialogueProtocol | None:
    if not protocol_id:
        return registry().get(default_protocol_id())
    return registry().get(protocol_id)


def list_protocols() -> list[dict]:
    return [
        {
            "protocol_id": p.protocol_id,
            "display_name": p.display_name,
            "purpose": p.purpose,
        }
        for p in registry().values()
    ]

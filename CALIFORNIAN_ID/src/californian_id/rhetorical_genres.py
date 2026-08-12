"""Пик 7.2 — RhetoricalTransformer + registry жанров.

Жанр — способ подачи закрывающей речи Заратустры. Один и тот же completion
в разных жанрах читается принципиально по-разному.

Wire: Zarathustra.compose_closing_speech получает необязательный параметр
`genre_id`; если задан — грузим prompt жанра и подмешиваем в system-стек
перед 13_closing_speech.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from .config import DATA_ROOT


GENRE_DIR = DATA_ROOT / "rhetoric" / "genres"


@dataclass
class RhetoricalGenre:
    genre_id: str
    display_name: str
    prompt_file: str
    voice_register: str = ""
    length: str = ""
    prompt_text: str = ""


def _load() -> tuple[dict[str, RhetoricalGenre], str, list[str]]:
    reg = GENRE_DIR / "registry.yaml"
    issues: list[str] = []
    if not reg.exists():
        return {}, "", [f"missing {reg}"]
    with reg.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    default = raw.get("default_genre") or ""
    out: dict[str, RhetoricalGenre] = {}
    for gid, spec in (raw.get("genres") or {}).items():
        pf = spec.get("prompt_file")
        p = GENRE_DIR / pf if pf else None
        text = ""
        if p is None or not p.exists():
            issues.append(f"genre {gid}: prompt_file missing ({pf})")
        else:
            text = p.read_text(encoding="utf-8")
        out[gid] = RhetoricalGenre(
            genre_id=gid,
            display_name=spec.get("display_name") or gid,
            prompt_file=pf or "",
            voice_register=spec.get("voice_register") or "",
            length=spec.get("length") or "",
            prompt_text=text,
        )
    return out, default, issues


@lru_cache(maxsize=1)
def registry() -> dict[str, RhetoricalGenre]:
    g, _, issues = _load()
    if issues:
        import logging
        logging.getLogger("californian_id.rhetorical_genres").warning(
            "Genre registry issues: %s", issues
        )
    return g


@lru_cache(maxsize=1)
def default_genre_id() -> str:
    _, default, _ = _load()
    return default


def get(genre_id: str | None) -> RhetoricalGenre | None:
    if not genre_id:
        return registry().get(default_genre_id())
    return registry().get(genre_id)


def list_genres() -> list[dict]:
    return [
        {
            "genre_id": g.genre_id,
            "display_name": g.display_name,
            "voice_register": g.voice_register,
            "length": g.length,
        }
        for g in registry().values()
    ]

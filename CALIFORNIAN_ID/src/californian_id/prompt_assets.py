"""Resolver for extracted prompt assets (Workbench Stage 0).

Prompt text that used to live as Python string literals now lives in
``data/prompt_assets/<asset_id>.md`` between ``RUNTIME_PROMPT_START`` and
``RUNTIME_PROMPT_END``. Only that block ever reaches a model; the rest of the
file is registry metadata.

The extraction is behaviour-preserving by construction: the asset files were
generated from the live code by ``scripts/workbench_extract_prompts.py`` and
byte equality is asserted by ``tests/workbench/test_prompt_extraction_golden.py``.
"""
from __future__ import annotations

import threading
from pathlib import Path

ASSET_DIR = Path(__file__).parent / "data" / "prompt_assets"

START = "RUNTIME_PROMPT_START"
END = "RUNTIME_PROMPT_END"

_cache: dict[str, str] = {}
_lock = threading.Lock()


class PromptAssetError(RuntimeError):
    pass


def asset_path(asset_id: str) -> Path:
    return ASSET_DIR / f"{asset_id}.md"


def runtime_block(asset_id: str) -> str:
    """Return the runtime-insertable block of an asset, byte-exact."""
    cached = _cache.get(asset_id)
    if cached is not None:
        return cached
    with _lock:
        cached = _cache.get(asset_id)
        if cached is not None:
            return cached
        path = asset_path(asset_id)
        if not path.exists():
            raise PromptAssetError(f"prompt asset not found: {asset_id} ({path})")
        text = path.read_text(encoding="utf-8")
        block = extract_block(text, asset_id)
        _cache[asset_id] = block
        return block


def extract_block(text: str, asset_id: str = "<inline>") -> str:
    start_hits = text.count(START)
    end_hits = text.count(END)
    # The markers appear once in the prose ("## RUNTIME_PROMPT_START") and once
    # in the policy line; the payload is delimited by the LAST start marker and
    # the FIRST end marker that follows it.
    if start_hits == 0 or end_hits == 0:
        raise PromptAssetError(f"{asset_id}: runtime markers missing")
    start = text.rfind(START)
    end = text.find(END, start + len(START))
    if end < 0:
        raise PromptAssetError(f"{asset_id}: RUNTIME_PROMPT_END after START missing")
    # Markers sit bare on their own lines, so the payload is exactly the text
    # between them minus the two delimiting newlines.
    return text[start + len(START):end].strip("\n")


def invalidate(asset_id: str | None = None) -> None:
    """Drop cached asset text. Used by the Workbench after activation."""
    with _lock:
        if asset_id is None:
            _cache.clear()
        else:
            _cache.pop(asset_id, None)


def list_assets() -> list[str]:
    if not ASSET_DIR.exists():
        return []
    return sorted(p.stem for p in ASSET_DIR.glob("*.md"))

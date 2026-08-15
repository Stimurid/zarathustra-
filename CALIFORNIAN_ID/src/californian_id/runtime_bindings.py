"""Runtime configuration binding seam.

Production code asks this module for effective values instead of carrying
literals. With no resolver installed every call returns the caller's own
default, so behaviour is byte-identical to the pre-seam runtime — that is what
makes the change behaviour-preserving and what
``tests/workbench/test_t2_production_binding.py`` asserts.

The Workbench installs a resolver that answers from the ACTIVE RAGProfile, so
activating a profile changes what the *production* pipeline actually does. There
is deliberately no second retrieval implementation: only the numbers move.
"""
from __future__ import annotations

import threading
from typing import Any, Protocol, runtime_checkable

#: Stable ids for the two retrieval engines that exist in this runtime.
ENGINE_PERSONA_LEXICAL = "tinkuy.persona_lexical_bm25"
ENGINE_CULTURAL_CARDS = "zarathustra.cultural_cards_bm25"


@runtime_checkable
class ConfigResolver(Protocol):
    def retrieval_param(self, engine_id: str, name: str, default: Any) -> Any:
        """Return the effective value, or ``default`` when unbound."""


_resolver: ConfigResolver | None = None
_lock = threading.Lock()


def set_resolver(resolver: ConfigResolver | None) -> None:
    global _resolver
    with _lock:
        _resolver = resolver


def get_resolver() -> ConfigResolver | None:
    return _resolver


def retrieval_param(engine_id: str, name: str, default: Any) -> Any:
    r = _resolver
    if r is None:
        return default
    try:
        value = r.retrieval_param(engine_id, name, default)
    except Exception:
        # A misbehaving resolver must never break a production run.
        return default
    return default if value is None else value


def retrieval_top_k(engine_id: str, default: int) -> int:
    try:
        return int(retrieval_param(engine_id, "top_k", default))
    except (TypeError, ValueError):
        return default

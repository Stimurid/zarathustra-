"""Workbench → production runtime configuration resolver.

Installed into ``californian_id.runtime_bindings`` so that the *production*
pipeline resolves its retrieval parameters from the ACTIVE RAGProfile, or from a
frozen RunConfigurationSnapshot while a run is in flight.

This is the seam that makes the Workbench a control surface rather than a
parallel harness: no retrieval logic lives here, only value resolution.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any

from workbench_core.rag import RAGProfile


class WorkbenchConfigResolver:
    """Resolves effective retrieval parameters.

    Priority:
      1. the snapshot pinned for the current run (thread-local), if any;
      2. the currently ACTIVE RAGProfile;
      3. the caller's own default — so an unbound engine behaves exactly as
         before the seam existed.
    """

    def __init__(self, store) -> None:
        self.store = store
        self._local = threading.local()
        #: Append-only observation of every resolution the production runtime
        #: asked for. Evidence, not control.
        self.calls: list[dict[str, Any]] = []

    # ---- run pinning -------------------------------------------------

    @contextmanager
    def pinned(self, snapshot: dict[str, Any]):
        """Freeze resolution to a run's snapshot for the duration of the run."""
        prev = getattr(self._local, "snapshot", None)
        self._local.snapshot = snapshot
        try:
            yield
        finally:
            self._local.snapshot = prev

    def _pinned_profile(self, engine_id: str) -> RAGProfile | None:
        snap = getattr(self._local, "snapshot", None)
        if not snap:
            return None
        entry = (snap.get("rag_bindings") or {}).get(engine_id)
        if not entry:
            return None
        return self.store.load_rag_profile(entry.get("rag_profile_id"))

    def _active_profile(self, engine_id: str) -> RAGProfile | None:
        pid = self.store.active_rag_profile_id(engine_id)
        return self.store.load_rag_profile(pid) if pid else None

    # ---- ConfigResolver protocol -------------------------------------

    def retrieval_param(self, engine_id: str, name: str, default: Any) -> Any:
        profile = self._pinned_profile(engine_id) or self._active_profile(engine_id)
        resolved = default
        source = "caller_default"
        if profile is not None:
            for section in ("retrieval", "filtering", "scoring", "chunking",
                            "source_bindings", "caching"):
                values = getattr(profile, section, None) or {}
                if name in values:
                    resolved = values[name]
                    source = f"{profile.profile_id}:{section}"
                    break
        self.calls.append({
            "engine_id": engine_id, "name": name, "default": default,
            "resolved": resolved, "source": source,
            "profile_id": profile.profile_id if profile else None,
            "pinned": getattr(self._local, "snapshot", None) is not None,
        })
        return resolved

    def effective(self, engine_id: str, name: str) -> Any:
        """Last value the production runtime actually received."""
        for c in reversed(self.calls):
            if c["engine_id"] == engine_id and c["name"] == name:
                return c["resolved"]
        return None

    def resolved_snapshot_of(self, engine_id: str) -> dict[str, Any] | None:
        p = self._pinned_profile(engine_id) or self._active_profile(engine_id)
        if p is None:
            return None
        return {"rag_profile_id": p.profile_id, "version": p.version,
                "profile_hash": p.source_hash()}

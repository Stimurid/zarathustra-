"""File-backed persistence for variants, activations, evaluations, runs."""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import (
    DRIFT_CATEGORIES,
    ActivationBinding,
    ActivationSnapshot,
    DriftWaiver,
    EvaluationRecord,
    PromptVariant,
    sha256_text,
)

_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


def _slug(value: str) -> str:
    return _SAFE.sub("_", value)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WorkbenchStore:
    """All mutable Workbench state lives under one directory.

    Layout::

        <root>/variants/<asset>/<variant_id>.md        source text
        <root>/variants/<asset>/<variant_id>.json      metadata
        <root>/activations.json                        bindings + revision
        <root>/evaluations.jsonl                       append-only
        <root>/runs/<run_id>.json                      run trace + snapshot
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        (self.root / "variants").mkdir(parents=True, exist_ok=True)
        (self.root / "runs").mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    # ---------------- variants ----------------

    def _variant_dir(self, asset_id: str) -> Path:
        d = self.root / "variants" / _slug(asset_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_variant(self, v: PromptVariant) -> PromptVariant:
        with self._lock:
            d = self._variant_dir(v.asset_id)
            (d / f"{_slug(v.variant_id)}.md").write_text(v.source_text, encoding="utf-8")
            meta = v.to_public(with_source=False)
            (d / f"{_slug(v.variant_id)}.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            return v

    def load_variant(self, asset_id: str, variant_id: str) -> PromptVariant | None:
        d = self._variant_dir(asset_id)
        mp = d / f"{_slug(variant_id)}.json"
        sp = d / f"{_slug(variant_id)}.md"
        if not mp.exists() or not sp.exists():
            return None
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta["source_text"] = sp.read_text(encoding="utf-8")
        return PromptVariant(**meta)

    def list_variants(self, asset_id: str) -> list[PromptVariant]:
        d = self._variant_dir(asset_id)
        out: list[PromptVariant] = []
        for mp in sorted(d.glob("*.json")):
            v = self.load_variant(asset_id, mp.stem)
            if v is not None:
                out.append(v)
        out.sort(key=lambda x: (x.state != "BASELINE", x.created_at))
        return out

    def delete_variant(self, asset_id: str, variant_id: str) -> None:
        d = self._variant_dir(asset_id)
        for suffix in (".json", ".md"):
            p = d / f"{_slug(variant_id)}{suffix}"
            if p.exists():
                p.unlink()

    # ---------------- activations ----------------

    def _activation_path(self) -> Path:
        return self.root / "activations.json"

    def read_activations(self) -> dict[str, Any]:
        p = self._activation_path()
        if not p.exists():
            return {"revision": 0, "bindings": {}, "history": []}
        return json.loads(p.read_text(encoding="utf-8"))

    def write_activations(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._activation_path().write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def bind(self, asset_id: str, variant_id: str, actor: str,
             source_hash: str, profile_id: str) -> ActivationBinding:
        with self._lock:
            data = self.read_activations()
            prev = (data["bindings"].get(asset_id) or {}).get("variant_id")
            data["revision"] = int(data.get("revision", 0)) + 1
            binding = ActivationBinding(
                asset_id=asset_id, variant_id=variant_id, activated_by=actor,
                activated_at=now_iso(), revision=data["revision"],
                previous_variant_id=prev,
            )
            data["bindings"][asset_id] = {
                "variant_id": variant_id,
                "source_hash": source_hash,
                "profile_id": profile_id,
                "activated_at": binding.activated_at,
                "activated_by": actor,
                "previous_variant_id": prev,
            }
            data["history"].append(binding.to_public())
            self.write_activations(data)
            return binding

    def active_variant_id(self, asset_id: str) -> str | None:
        return (self.read_activations()["bindings"].get(asset_id) or {}).get("variant_id")

    def activation_revision(self) -> int:
        return int(self.read_activations().get("revision", 0))

    def take_snapshot(self) -> ActivationSnapshot:
        """Freeze the activation picture for a run. Immutable afterwards."""
        data = self.read_activations()
        rev = int(data.get("revision", 0))
        entries = {
            aid: {
                "variant_id": b.get("variant_id", ""),
                "source_hash": b.get("source_hash", ""),
                "profile_id": b.get("profile_id", ""),
            }
            for aid, b in data.get("bindings", {}).items()
        }
        taken = now_iso()
        payload = json.dumps({"rev": rev, "entries": entries, "taken": taken},
                             ensure_ascii=False, sort_keys=True)
        return ActivationSnapshot(
            snapshot_id="snap_" + sha256_text(payload)[:16],
            activation_revision=rev, taken_at=taken, entries=entries,
        )

    # ---------------- RAG profiles + retrieval events (Stage 2) ----------

    def _rag_dir(self) -> Path:
        d = self.root / "rag_profiles"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_rag_profile(self, profile: "RAGProfile") -> "RAGProfile":
        with self._lock:
            payload = profile.to_public()
            payload["missing_capabilities"] = [
                m.to_public() for m in profile.missing_capabilities]
            (self._rag_dir() / f"{_slug(profile.profile_id)}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return profile

    def load_rag_profile(self, profile_id: str) -> "RAGProfile | None":
        from .rag import MissingCapability, RAGProfile
        p = self._rag_dir() / f"{_slug(profile_id)}.json"
        if not p.exists():
            return None
        raw = json.loads(p.read_text(encoding="utf-8"))
        caps = [MissingCapability(**c) for c in raw.pop("missing_capabilities", [])]
        for derived in ("source_hash", "tunable"):
            raw.pop(derived, None)
        prof = RAGProfile(**raw)
        prof.missing_capabilities = caps
        return prof

    def list_rag_profiles(self, engine_id: str | None = None) -> list["RAGProfile"]:
        out = []
        for f in sorted(self._rag_dir().glob("*.json")):
            prof = self.load_rag_profile(f.stem)
            if prof is None:
                continue
            if engine_id is None or prof.engine_id == engine_id:
                out.append(prof)
        out.sort(key=lambda p: (p.state != "BASELINE", p.created_at))
        return out

    def bind_rag(self, engine_id: str, profile_id: str, actor: str,
                 source_hash: str) -> dict[str, Any]:
        with self._lock:
            data = self.read_activations()
            data.setdefault("rag_bindings", {})
            prev = (data["rag_bindings"].get(engine_id) or {}).get("profile_id")
            data["revision"] = int(data.get("revision", 0)) + 1
            data["rag_bindings"][engine_id] = {
                "profile_id": profile_id, "source_hash": source_hash,
                "activated_at": now_iso(), "activated_by": actor,
                "previous_profile_id": prev, "revision": data["revision"],
            }
            self.write_activations(data)
            return dict(data["rag_bindings"][engine_id])

    def active_rag_profile_id(self, engine_id: str) -> str | None:
        return ((self.read_activations().get("rag_bindings") or {})
                .get(engine_id) or {}).get("profile_id")

    def append_retrieval_event(self, event: "RetrievalEvent") -> None:
        with self._lock:
            with (self.root / "retrieval_events.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_public(), ensure_ascii=False) + "\n")

    def retrieval_events(self, run_id: str | None = None,
                         limit: int = 200) -> list["RetrievalEvent"]:
        from .rag import RetrievalCandidate, RetrievalEvent
        p = self.root / "retrieval_events.jsonl"
        if not p.exists():
            return []
        out: list[RetrievalEvent] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if run_id and raw.get("run_id") != run_id:
                continue
            raw["candidates"] = [RetrievalCandidate(**c) for c in raw.get("candidates", [])]
            out.append(RetrievalEvent(**raw))
        return out[-limit:]

    # ---------------- drift waivers (C1) ----------------

    def _waiver_path(self) -> Path:
        return self.root / "drift_waivers.json"

    def read_waivers(self) -> list[DriftWaiver]:
        p = self._waiver_path()
        if not p.exists():
            return []
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [DriftWaiver(**w) for w in raw.get("waivers", [])]

    def grant_waiver(self, waiver: DriftWaiver) -> DriftWaiver:
        """A waiver is only valid with a reason and an ADR reference."""
        if not waiver.reason.strip() or not waiver.adr_ref.strip():
            raise ValueError("waiver requires both reason and adr_ref")
        if waiver.category not in DRIFT_CATEGORIES:
            raise ValueError(f"unknown drift category: {waiver.category}")
        with self._lock:
            existing = self.read_waivers()
            existing = [w for w in existing
                        if not (w.key() == waiver.key()
                                and w.asset_id == waiver.asset_id)]
            existing.append(waiver)
            self._waiver_path().write_text(
                json.dumps({"waivers": [w.to_public() for w in existing]},
                           ensure_ascii=False, indent=2), encoding="utf-8")
            return waiver

    # ---------------- rejection audit (C2) ----------------

    def append_rejection(self, event: dict[str, Any]) -> None:
        """Append-only log of refused mutations (protected regions, lifecycle)."""
        with self._lock:
            event = {"at": now_iso(), **event}
            with (self.root / "rejections.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    def rejections(self, limit: int = 50) -> list[dict[str, Any]]:
        p = self.root / "rejections.jsonl"
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out[-limit:]

    # ---------------- evaluations ----------------

    def append_evaluation(self, rec: EvaluationRecord) -> None:
        with self._lock:
            p = self.root / "evaluations.jsonl"
            with p.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec.to_public(), ensure_ascii=False) + "\n")

    def evaluations_for(self, variant_id: str) -> list[dict[str, Any]]:
        p = self.root / "evaluations.jsonl"
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("variant_id") == variant_id:
                out.append(rec)
        return out

    def mark_evaluations_stale(self, variant_id: str) -> None:
        p = self.root / "evaluations.jsonl"
        if not p.exists():
            return
        with self._lock:
            lines = p.read_text(encoding="utf-8").splitlines()
            out = []
            for line in lines:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("variant_id") == variant_id:
                    rec["stale"] = True
                out.append(json.dumps(rec, ensure_ascii=False))
            p.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")

    # ---------------- runs ----------------

    def write_run(self, run_id: str, trace: dict[str, Any]) -> None:
        with self._lock:
            (self.root / "runs" / f"{_slug(run_id)}.json").write_text(
                json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    def read_run(self, run_id: str) -> dict[str, Any] | None:
        p = self.root / "runs" / f"{_slug(run_id)}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        runs = sorted((self.root / "runs").glob("*.json"),
                      key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
        out = []
        for p in runs:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return out

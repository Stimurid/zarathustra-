"""Server-side cross-turn context persistence — core contract (host-independent).

Defines :class:`SocratesContext` snapshot contract and :class:`ContextStore`
protocol. Durable SQLite backing lives in the host adapter
``californian_id.socrates_context_store`` — Space ≠ SQLite, Scene ≠ row.
"""
from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from .epistemic_model import SceneRegistry, SpaceRegistry


CONTEXT_SNAPSHOT_VERSION = 1


def _new_context_id() -> str:
    return f"ctx_{secrets.token_hex(16)}"


def new_context_id() -> str:
    return _new_context_id()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class SocratesContext:
    """Minimal typed snapshot for cross-turn Scene/Space/Branch continuity."""

    context_id: str
    context_version: int = CONTEXT_SNAPSHOT_VERSION
    space_id: str = ""
    scene_id: str = ""
    branch_id: str = ""
    space_registry: SpaceRegistry = field(default_factory=SpaceRegistry)
    scene_registry: SceneRegistry = field(default_factory=SceneRegistry)
    active_contract_id: str = ""
    contract_history: list[dict[str, Any]] = field(default_factory=list)
    last_intent_summary: str = ""
    last_telos: str = ""
    last_operation_kind: str = ""
    context_transduction_ids: tuple[str, ...] = ()
    recognition_state: dict[str, Any] = field(default_factory=dict)
    provenance: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_public(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "context_version": self.context_version,
            "space_id": self.space_id,
            "scene_id": self.scene_id,
            "branch_id": self.branch_id,
            "space_registry": self.space_registry.to_public(),
            "scene_registry": self.scene_registry.to_public(),
            "active_contract_id": self.active_contract_id,
            "contract_history": list(self.contract_history),
            "last_intent_summary": self.last_intent_summary,
            "last_telos": self.last_telos,
            "last_operation_kind": self.last_operation_kind,
            "context_transduction_ids": list(self.context_transduction_ids),
            "recognition_state": dict(self.recognition_state),
            "provenance": self.provenance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_json(self) -> str:
        payload = self.to_public()
        payload["_snapshot_version"] = CONTEXT_SNAPSHOT_VERSION
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str, *, context_id: str) -> SocratesContext:
        data = json.loads(raw)
        version = int(data.get("context_version") or data.get("_snapshot_version") or 0)
        if version != CONTEXT_SNAPSHOT_VERSION:
            raise ValueError(
                f"unsupported context snapshot version {version!r}; "
                f"expected {CONTEXT_SNAPSHOT_VERSION}")
        sr = SpaceRegistry()
        for sid, sdata in (data.get("space_registry") or {}).items():
            from .epistemic_model import EpistemicSpace, MemoryValidityScope
            sr.register(EpistemicSpace(
                space_id=sdata["space_id"],
                version=sdata.get("version", ""),
                name=sdata.get("name", sid),
                telos_scope=sdata.get("telos_scope", ""),
                corpus_namespaces=tuple(sdata.get("corpus_namespaces") or ()),
                retrieval_policy=sdata.get("retrieval_policy", "default"),
                memory_default_scope=MemoryValidityScope(
                    sdata.get("memory_default_scope", "PROJECT")),
                status=sdata.get("status", "active"),
            ))
        sc_reg = SceneRegistry()
        scenes = (data.get("scene_registry") or {}).get("scenes") or {}
        branches = (data.get("scene_registry") or {}).get("branches") or {}
        from .epistemic_model import SceneRef, SceneBranch, MemoryValidityScope
        for sdata in scenes.values():
            sc_reg.add_scene(SceneRef(
                scene_id=sdata["scene_id"],
                space_id=sdata.get("space_id", ""),
                parent_scene_id=sdata.get("parent_scene_id", ""),
                branch_id=sdata.get("branch_id", ""),
                version=sdata.get("version", ""),
            ))
        for bdata in branches.values():
            sc_reg.add_branch(SceneBranch(
                branch_id=bdata["branch_id"],
                scene_id=bdata["scene_id"],
                parent_scene_id=bdata.get("parent_scene_id", ""),
                hypothesis=bdata.get("hypothesis", ""),
                status=bdata.get("status", "active"),
                local_facts=tuple(bdata.get("local_facts") or ()),
                local_commitments=tuple(bdata.get("local_commitments") or ()),
                memory_scope=MemoryValidityScope(
                    bdata.get("memory_scope", "BRANCH")),
            ))
        return cls(
            context_id=context_id,
            context_version=version,
            space_id=data.get("space_id", ""),
            scene_id=data.get("scene_id", ""),
            branch_id=data.get("branch_id", ""),
            space_registry=sr,
            scene_registry=sc_reg,
            active_contract_id=data.get("active_contract_id", ""),
            contract_history=list(data.get("contract_history") or []),
            last_intent_summary=data.get("last_intent_summary", ""),
            last_telos=data.get("last_telos", ""),
            last_operation_kind=data.get("last_operation_kind", ""),
            context_transduction_ids=tuple(
                data.get("context_transduction_ids") or ()),
            recognition_state=dict(data.get("recognition_state") or {}),
            provenance=data.get("provenance", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ContextStore(Protocol):
    """Host adapter protocol — replaceable persistence backend."""

    def create(self) -> SocratesContext: ...

    def load(self, context_id: str) -> SocratesContext | None: ...

    def save(self, context: SocratesContext) -> None: ...

    def exists(self, context_id: str) -> bool: ...


class InMemoryContextStore:
    """Non-durable store for unit tests inside socrates_runtime only."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def create(self) -> SocratesContext:
        cid = _new_context_id()
        now = _now_iso()
        ctx = SocratesContext(
            context_id=cid, created_at=now, updated_at=now,
            provenance="test_created")
        self.save(ctx)
        return ctx

    def load(self, context_id: str) -> SocratesContext | None:
        raw = self._data.get(context_id)
        if raw is None:
            return None
        try:
            return SocratesContext.from_json(raw, context_id=context_id)
        except (json.JSONDecodeError, ValueError, KeyError):
            return None

    def save(self, context: SocratesContext) -> None:
        context.updated_at = _now_iso()
        if not context.created_at:
            context.created_at = context.updated_at
        self._data[context.context_id] = context.to_json()

    def exists(self, context_id: str) -> bool:
        return context_id in self._data


__all__ = [
    "CONTEXT_SNAPSHOT_VERSION",
    "ContextStore",
    "InMemoryContextStore",
    "SocratesContext",
    "new_context_id",
]

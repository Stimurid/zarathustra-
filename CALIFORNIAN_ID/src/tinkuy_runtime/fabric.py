"""`fabric.query` — the native semantic-fabric seam.

This module owns NO data and NO logic about semantic fabric. It opens the
existing :class:`californian_id.fabric.FabricStore` and returns the existing
fabric dataclasses. That constraint is the point: the G-S26 blocker is not
"nobody can compute a fabric", it is "no callable endpoint reaches the real
one", and a second implementation would leave the blocker in place while
appearing to close it.

Objects returned are the canonical ones:
    FabricUnit      ← canon 017 SemanticUnit
    FabricBlock     ← canon 018 SemanticBlock
    FabricRelation  ← canon 019 SemanticRelation
    FabricThread    ← canon 020 SemanticThread
    FabricSnapshot  ← canon 021 SemanticSnapshot
    FabricSceneState← canon 022 SceneState (carries open_loops)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .identity import BindingResult, identify

ORGAN = "semantic_fabric"


@dataclass
class FabricQuery:
    """What to ask the fabric for. Deliberately narrow.

    Every field maps onto something the stored fabric already distinguishes;
    nothing here invents a query dimension the substrate does not have.
    """
    snapshot_id: str | None = None
    source_id: str | None = None
    unit_intentions: list[str] = field(default_factory=list)
    block_types: list[str] = field(default_factory=list)
    relation_types: list[str] = field(default_factory=list)
    thread_types: list[str] = field(default_factory=list)
    include_scene: bool = True
    include_evidence: bool = False
    limit: int = 200


@dataclass
class FabricQueryResult:
    """Typed slice of the real fabric — not a rendering of it."""
    snapshot_id: str
    source_id: str
    source_version: str
    units: list[Any] = field(default_factory=list)
    blocks: list[Any] = field(default_factory=list)
    relations: list[Any] = field(default_factory=list)
    threads: list[Any] = field(default_factory=list)
    evidence: list[Any] = field(default_factory=list)
    scene: Any = None
    open_loops: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    truncated: bool = False

    def counts(self) -> dict[str, int]:
        return {"units": len(self.units), "blocks": len(self.blocks),
                "relations": len(self.relations), "threads": len(self.threads),
                "evidence": len(self.evidence), "open_loops": len(self.open_loops)}


def _open_store(db_path: Path):
    from californian_id.fabric import FabricStore

    return FabricStore(db_path)


def list_snapshots(db_path: Path | str, source_id: str | None = None) -> BindingResult:
    """Enumerate what the real store holds. Read-only."""
    from californian_id.fabric.store import FabricStore

    path = Path(db_path)
    ident = identify(ORGAN, FabricStore.list_snapshots)
    if not path.exists():
        return BindingResult(ORGAN, "fabric.list_snapshots", False,
                             reason=f"хранилище ткани не найдено: {path}",
                             identity=ident)
    store = _open_store(path)
    try:
        rows = store.list_snapshots(source_id)
    finally:
        store.close()
    return BindingResult(ORGAN, "fabric.list_snapshots", True, value=rows,
                         identity=ident,
                         provenance={"db_path": str(path), "count": len(rows)})


def query(db_path: Path | str, q: FabricQuery) -> BindingResult:
    """`fabric.query` — typed read of the native semantic fabric.

    Delegates to ``FabricStore.load_snapshot`` and filters the returned
    dataclasses in memory. No SQL of our own: the moment this module writes its
    own query against the fabric tables it has started becoming a second fabric.
    """
    from californian_id.fabric.store import FabricStore

    path = Path(db_path)
    ident = identify(ORGAN, FabricStore.load_snapshot)

    if not path.exists():
        return BindingResult(ORGAN, "fabric.query", False,
                             reason=f"хранилище ткани не найдено: {path}",
                             identity=ident)

    store = _open_store(path)
    try:
        snapshot_id = q.snapshot_id
        if snapshot_id is None:
            rows = store.list_snapshots(q.source_id)
            if not rows:
                return BindingResult(
                    ORGAN, "fabric.query", False,
                    reason=("в хранилище нет ни одного снимка ткани"
                            + (f" для source_id={q.source_id}" if q.source_id else "")),
                    identity=ident, provenance={"db_path": str(path)})
            snapshot_id = rows[0]["snapshot_id"]

        snap = store.load_snapshot(snapshot_id)
    finally:
        store.close()

    if snap is None:
        return BindingResult(ORGAN, "fabric.query", False,
                             reason=f"снимок не найден: {snapshot_id}",
                             identity=ident, provenance={"db_path": str(path)})

    def keep(items, attr: str, allowed: list[str]):
        return [i for i in items if not allowed or getattr(i, attr, None) in allowed]

    units = keep(snap.units, "intention", q.unit_intentions)
    blocks = keep(snap.blocks, "block_type", q.block_types)
    relations = keep(snap.relations, "relation_type", q.relation_types)
    threads = keep(snap.threads, "thread_type", q.thread_types)
    truncated = any(len(x) > q.limit for x in (units, blocks, relations, threads))

    result = FabricQueryResult(
        snapshot_id=snap.snapshot_id,
        source_id=snap.source_id,
        source_version=snap.source_version,
        units=units[:q.limit],
        blocks=blocks[:q.limit],
        relations=relations[:q.limit],
        threads=threads[:q.limit],
        evidence=(snap.evidence[:q.limit] if q.include_evidence else []),
        scene=(snap.scene if q.include_scene else None),
        open_loops=(list(snap.scene.open_loops) if (q.include_scene and snap.scene)
                    else []),
        stats=dict(snap.stats or {}),
        truncated=truncated,
    )
    return BindingResult(
        ORGAN, "fabric.query", True, value=result, identity=ident,
        provenance={"db_path": str(path), "snapshot_id": snap.snapshot_id,
                    "parser_run_id": snap.parser_run_id,
                    "counts": result.counts()})

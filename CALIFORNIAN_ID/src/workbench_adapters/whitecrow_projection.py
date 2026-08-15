"""Stage 4B — WhiteCrow field projection over the same typed Workbench objects.

Proof obligation: ``workbench_core`` must not impose a node-edge rendering. This
adapter takes the *identical* ``NodeProjection`` objects the graph is drawn from
and re-presents them as a WhiteCrow radial field, with no fork of the data model
and no branch-specific type in the core.

Geometry is ported verbatim from the real WhiteCrow implementation —
``C:\\projects\\conceptarticle\\mvp\\FIELD_KERNEL_v6_3_1.html``, function
``getFPERadial()`` (W=300, H=240, R=95, angle = i/min(8,n)·2π − π/2, active
radius 14 vs 10, centre hub r=16 labelled FIELD), specified in
``docs/FIELD_PROJECTION_ENGINE_SPEC.md``. Nothing about WhiteCrow is rewritten.

Dependency invariant is unchanged: this module may import ``workbench_core``;
``workbench_core`` may not import this one.
"""
from __future__ import annotations

from typing import Any

from workbench_core.branch import (
    BranchAdapter,
    FieldItem,
    FieldProjection,
    NodeProjection,
    PipelineProjection,
)

#: Roles from FIELD_PROJECTION_ENGINE_SPEC §Radial. The mapping is presentation
#: only — it never changes what a node *is*.
ROLE_BY_KIND = {
    "MODEL_CALL": "Синтез",
    "PROMPT": "Концепт",
    "RAG": "Источник",
    "ROUTER": "Куратор",
    "DETERMINISTIC": "Институт",
    "HUMAN_GATE": "Феномен",
    "HYBRID": "Напряжение",
    "STORE": "Поле",
}

LEVEL_BY_KIND = {
    "MODEL_CALL": "synthesis",
    "PROMPT": "synthesis",
    "RAG": "field",
    "HYBRID": "node",
}

#: Verbatim from getFPERadial().
GEOMETRY = {
    "W": 300, "H": 240, "cx": 150, "cy": 120, "R": 95,
    "max_items": 8, "start_angle": "-pi/2",
    "node_r": 10, "active_r": 14, "hub_r": 16,
    "source": "conceptarticle/mvp/FIELD_KERNEL_v6_3_1.html::getFPERadial",
}


class WhiteCrowProjectionAdapter:
    """A *presentation* adapter. It owns no pipeline and no runtime."""

    projection_branch_id = "whitecrow"
    supported = ("radial",)

    def __init__(self, source: BranchAdapter) -> None:
        #: The branch whose typed objects are being re-presented.
        self.source = source

    # ------------------------------------------------------------------

    def field_projection(self, kind: str = "radial",
                         resolved_for: dict[str, str] | None = None) -> FieldProjection:
        if kind not in self.supported:
            raise ValueError(f"projection kind not supported here: {kind}")

        proj: PipelineProjection = self.source.describe_pipeline(resolved_for)
        # Only what the runtime actually executes reaches a field projection;
        # a dead declaration is not a field object.
        runtime_nodes = [n for n in proj.nodes if n.layer == "ACTUAL_RUNTIME"]
        items = [self._item(n) for n in self._rank(runtime_nodes)]

        return FieldProjection(
            projection_id=f"{self.projection_branch_id}.radial.{proj.pipeline_id}",
            kind="radial",
            branch=self.source.branch_id,
            title="Поле пайплайна — радиальная проекция WhiteCrow",
            items=items[:GEOMETRY["max_items"]],
            center_label="FIELD",
            geometry=dict(GEOMETRY),
            source_ref=GEOMETRY["source"],
            note="Те же NodeProjection, что и в графе: item_id/asset_id/"
                 "rag_profile_id совпадают, инспектор открывает тот же ассет.",
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _rank(nodes: list[NodeProjection]) -> list[NodeProjection]:
        """Field ordering is by weight of transformation, not by call order.

        That is precisely the point of a field projection: it answers a
        different question than the graph does.
        """
        weight = {"MODEL_CALL": 0, "RAG": 1, "HYBRID": 2, "ROUTER": 3,
                  "PROMPT": 4, "DETERMINISTIC": 5, "HUMAN_GATE": 6, "STORE": 7}
        return sorted(nodes, key=lambda n: (weight.get(n.kind, 9), n.node_id))

    @staticmethod
    def _item(n: NodeProjection) -> FieldItem:
        tags = []
        if n.in_loop:
            tags.append("loop")
        if n.topology_status != "MATCH":
            tags.append(n.topology_status.lower())
        return FieldItem(
            # identity is shared with the graph — same node, same asset
            item_id=n.node_id,
            label=n.label,
            node_id=n.node_id,
            role=ROLE_BY_KIND.get(n.kind, "Поле"),
            kind=n.kind,
            asset_id=n.asset_id,
            rag_profile_id=n.rag_profile_id,
            level=LEVEL_BY_KIND.get(n.kind, "node"),
            weight=1.0 if n.kind in {"MODEL_CALL", "RAG"} else 0.6,
            tags=tags,
            note=n.note,
        )

    def to_public(self, kind: str = "radial",
                  resolved_for: dict[str, str] | None = None) -> dict[str, Any]:
        return self.field_projection(kind, resolved_for).to_public()

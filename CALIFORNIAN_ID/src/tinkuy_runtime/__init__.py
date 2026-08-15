"""Native Tinkuy runtime bindings — callable seams over the real organs.

Dependency direction, enforced by test:

    Socrates / Workbench
            ↓
    tinkuy_runtime            (this package — adapters only)
            ↓
    californian_id.fabric.FabricStore
    californian_id.pipeline._fabric_snapshot_to_unit_pack
    californian_id.narrative_memory.NarrativeStore

Nothing in ``californian_id`` imports this package, and this package implements
no organ of its own. It exists because the G-S26 blocker D-S26-001 is about
*reach*, not about absence: the fabric, the argument projector and the durable
memory store are all real executable code on disk; what was missing were named,
tested, traceable calls into them.

Store policy is frozen upstream — ``create_new_semantic_fabric_store``,
``create_new_argument_store`` and ``create_new_memory_store`` are all false — so
no module here opens a database of its own design.
"""
from __future__ import annotations

from . import argumentation, fabric, working_memory
from .identity import (
    BindingResult,
    ImplementationIdentity,
    NativeOrganUnavailable,
    identify,
)

__all__ = [
    "fabric",
    "argumentation",
    "working_memory",
    "BindingResult",
    "ImplementationIdentity",
    "NativeOrganUnavailable",
    "identify",
]

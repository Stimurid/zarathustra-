"""Fabric — собственный резчик семантической ткани Тинкуя (Пик 5).

По каноническому `TINKUY_STANDALONE_MVP_ARCHITECTURE_V1.1` §5 + документы
015-024 (schemas), 035-044 (ontologies), 045-056 (prompts).

Пайплайн:
    raw_text
      → SourceMap (детерминированный)
      → CoarseComposition (LLM)
      → MultiscaleSegmentation (LLM)
      → SemanticMoveExtraction → FabricUnit[]
      → BlockAssembly → FabricBlock[]
      → RelationExtraction → FabricRelation[]
      → ThreadInduction → FabricThread[]
      → CrossScaleReconciliation
      → FabricSnapshot (сохраняется в FabricStore)

Отдельно от UnitPack (внешний резчик по md-units формату).

Публичные экспорты:
    schemas.*                — dataclasses ткани
    parser.FabricParser      — исполнитель pipeline
    store.FabricStore        — SQLite JSON1 хранилище
"""
from __future__ import annotations

from .schemas import (
    FabricBlock,
    FabricEvidenceFragment,
    FabricRelation,
    FabricSnapshot,
    FabricSourceSpan,
    FabricThread,
    FabricUnit,
    FabricSceneState,
)
from .parser import FabricParser
from .store import FabricStore

__all__ = [
    "FabricUnit",
    "FabricBlock",
    "FabricRelation",
    "FabricThread",
    "FabricSnapshot",
    "FabricSourceSpan",
    "FabricEvidenceFragment",
    "FabricSceneState",
    "FabricParser",
    "FabricStore",
]

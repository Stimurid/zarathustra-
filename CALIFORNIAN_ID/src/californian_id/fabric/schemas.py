"""Fabric schemas — canonical Tinkuy semantic-fabric types.

Соответствие каноническим документам:
- 015 SOURCE_ARTIFACT_SCHEMA
- 016 EVIDENCE_FRAGMENT_SCHEMA           → FabricEvidenceFragment
- 017 SEMANTIC_UNIT_SCHEMA (+036 ONTOLOGY) → FabricUnit
- 018 SEMANTIC_BLOCK_SCHEMA (+037)       → FabricBlock
- 019 SEMANTIC_RELATION_SCHEMA (+038)    → FabricRelation
- 020 SEMANTIC_THREAD_SCHEMA (+040)      → FabricThread
- 021 SEMANTIC_SNAPSHOT_AND_DELTA_SCHEMA → FabricSnapshot
- 022 SCENE_STATE_SCHEMA                 → FabricSceneState
- 2.4 SourceSpan (устойчивая адресация)  → FabricSourceSpan

Префикс `Fabric` намеренный — чтобы не путать с UnitPack/SemanticUnit из
адаптера внешнего резчика (md-units формат).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Канон 036 SEMANTIC_UNIT_ONTOLOGY: типы минимальных смысловых ходов.
UNIT_INTENTIONS = (
    "claim",           # тезис
    "question",        # вопрос
    "distinction",     # различение
    "definition",      # определение
    "hypothesis",      # гипотеза
    "example",         # пример
    "evaluation",      # оценка
    "requirement",     # требование
    "commitment",      # обязательство
    "assumption",      # предпосылка
    "value",           # ценность
    "counterexample",  # контрпример
)


# Канон 037 SEMANTIC_BLOCK_ONTOLOGY: типы блоков.
BLOCK_TYPES = (
    "argument",        # структура вывода
    "position",        # оформленная точка зрения
    "problem",         # оформленная проблемная постановка
    "model",           # предметная / методическая модель
    "solution",        # решение
    "episode",         # композиционный фрагмент
    "aporia",          # структурная невозможность
    "digression",      # отступление
)


# Канон 038 SEMANTIC_RELATION_ONTOLOGY: словарь связей.
RELATION_TYPES = (
    "contains",       # содержит
    "overlaps",       # частично пересекается
    "supports",       # обосновывает
    "contradicts",    # противоречит
    "presupposes",    # предполагает
    "defines",        # определяет
    "reframes",       # переопределяет рамку
    "specifies",      # уточняет
    "generalises",    # обобщает
    "answers",        # отвечает
    "avoids",         # уходит от
    "returns_to",     # возвращается к
    "continues",      # продолжает
    "derived_from",   # выведено из
    "responds_to",    # реагирует на
    "transforms",     # преображает
)


# Канон 040 SEMANTIC_THREAD_ONTOLOGY: типы продольных линий.
THREAD_TYPES = (
    "concept",         # линия одного понятия
    "argument",        # линия одного аргумента
    "position",        # линия одной позиции
    "object",          # линия объекта / актора
    "problem",         # линия проблемы
    "conflict",        # линия конфликта
    "narrative",       # нарративная линия
    "commitment",      # линия обещания / обязательства
)


# Канон 042 INTERPRETATION_STATUS_ONTOLOGY.
INTERPRETATION_STATUS = (
    "proposed",
    "supported",
    "contested",
    "accepted",
    "rejected",
    "deferred",
    "superseded",
    "quarantined",
)


@dataclass
class FabricSourceSpan:
    """2.4 SourceSpan — устойчивая адресация точного диапазона.

    Все смысловые объекты ткани обязаны опираться хотя бы на один span,
    иначе FabricProvenanceValidator их отклонит.
    """
    span_id: str                   # хеш-подобный ID для стабильных ссылок
    source_id: str                 # какой источник (SourceArtifact.id)
    version: str = ""              # версия источника
    char_start: int = 0
    char_end: int = 0
    paragraph_ix: int | None = None
    line_ix: int | None = None
    locator: str = ""              # человекочитаемая ссылка ("§3.2 / 00:12:34")


@dataclass
class FabricEvidenceFragment:
    """016 EvidenceFragment — неизменяемый фрагмент свидетельства.

    Точная цитата с span. НЕ содержит интерпретации.
    """
    fragment_id: str
    span: FabricSourceSpan
    verbatim: str                  # точный текст диапазона
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricUnit:
    """017 SemanticUnit — минимальный смысловой ход.

    intention ∈ UNIT_INTENTIONS. Каждый юнит опирается на evidence spans.
    """
    unit_id: str                   # "u001", "u002", ...
    intention: str                 # см. UNIT_INTENTIONS
    text: str                      # реконструированная формулировка (не verbatim!)
    evidence_span_ids: list[str] = field(default_factory=list)  # ссылки на FabricSourceSpan
    scale: str = "expression"      # см. SEMANTIC_SCALE_ONTOLOGY (039): expression/…/composition/…
    speaker_ref: str = ""          # если известен спикер
    confidence: float = 0.5
    interpretation_status: str = "proposed"
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricBlock:
    """018 SemanticBlock — многомасштабная конструкция из юнитов.

    unit_ids — членство юнитов; НЕТ требования единственного родителя
    (канон 5.3: без требования единственного родителя).
    """
    block_id: str                  # "b001", ...
    block_type: str                # см. BLOCK_TYPES
    title: str = ""
    unit_ids: list[str] = field(default_factory=list)
    scale: str = "composition"     # обычно крупнее чем юнит
    interpretation_status: str = "proposed"
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricRelation:
    """019 SemanticRelation — типизированное ребро графа ткани.

    source и target — любые объекты ткани (юнит/блок/нить/сцена).
    """
    relation_id: str               # "r001", ...
    relation_type: str             # см. RELATION_TYPES
    source_id: str                 # unit_id / block_id / thread_id / …
    target_id: str
    evidence_span_ids: list[str] = field(default_factory=list)
    interpretation_status: str = "proposed"
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricThread:
    """020 SemanticThread — продольная линия."""
    thread_id: str                 # "t001", ...
    thread_type: str               # см. THREAD_TYPES
    label: str = ""
    member_ids: list[str] = field(default_factory=list)   # unit/block ids по порядку
    interpretation_status: str = "proposed"
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricSceneState:
    """022 SceneState — реконструкция происходящей сцены.

    Обновляется при каждом snapshot commit. Заратустра читает её как контекст.
    """
    scene_id: str
    participants: list[str] = field(default_factory=list)   # speaker refs
    question: str = ""                                       # предмет собрания
    positions: list[dict] = field(default_factory=list)     # [{who, position_text}]
    stakes: list[str] = field(default_factory=list)
    tensions: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)     # незакрытые вопросы
    phase: str = "exploration"     # см. DRAMATURGICAL_PHASE_ONTOLOGY (069)
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FabricSnapshot:
    """021 SemanticSnapshot — полное состояние ткани на момент.

    Иммутабельно после commit. Delta между snapshots — отдельный объект
    (FabricDelta), пока не в MVP.
    """
    snapshot_id: str                                       # хеш-подобный ID
    source_id: str
    source_version: str = ""
    created_at: str = ""                                   # ISO-8601 UTC
    units: list[FabricUnit] = field(default_factory=list)
    blocks: list[FabricBlock] = field(default_factory=list)
    relations: list[FabricRelation] = field(default_factory=list)
    threads: list[FabricThread] = field(default_factory=list)
    spans: list[FabricSourceSpan] = field(default_factory=list)
    evidence: list[FabricEvidenceFragment] = field(default_factory=list)
    scene: FabricSceneState | None = None
    stats: dict[str, Any] = field(default_factory=dict)    # coverage %, unit counts, LLM tokens…
    parser_run_id: str = ""                                # какой run парсера создал


def to_plain(obj: Any) -> Any:
    """Serialise a fabric dataclass tree to plain dict/list for JSON."""
    from dataclasses import is_dataclass, asdict
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    return obj

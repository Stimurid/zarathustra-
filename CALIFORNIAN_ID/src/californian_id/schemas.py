"""Structured data schemas used by the pipeline.

Kept as plain dataclasses (no external validation lib) so the runtime can
boot without dependencies beyond PyYAML. Contract references point at
canonical Tinkuy schemas in `tinkuy canon/02_схемы_данных_и_контракты_выходов/`
so this pack can later be swapped for jsonschema-validated versions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Claim:
    text: str
    confidence: float = 0.5
    source: str | None = None
    persona_id: str | None = None


@dataclass
class Assumption:
    text: str
    persona_id: str | None = None
    exposed_by: str | None = None


@dataclass
class Value:
    text: str
    persona_id: str | None = None


@dataclass
class Attack:
    target: str  # id of a previous claim/assumption or "previous_turn"
    text: str
    persona_id: str | None = None


@dataclass
class Support:
    target: str
    text: str
    persona_id: str | None = None


@dataclass
class Action:
    text: str
    persona_id: str | None = None


@dataclass
class Question:
    text: str
    persona_id: str | None = None
    unresolved: bool = True


@dataclass
class MinorityPosition:
    persona_id: str
    text: str
    reason_for_retention: str
    would_be_lost: str  # canon: what is lost if compressed away


@dataclass
class ConflictItem:
    tension: str
    side_a: str
    side_b: str
    status: str  # unresolved | narrowed | reframed | compromised


@dataclass
class TurnRecord:
    turn_index: int
    persona_id: str
    operation: str
    utterance: str
    claims: list[Claim] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    values: list[Value] = field(default_factory=list)
    supports: list[Support] = field(default_factory=list)
    attacks: list[Attack] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    confidence: float = 0.5
    routing_reason: str = ""
    model_provider: str = ""
    model_name: str = ""
    error: str | None = None


@dataclass
class SituationAnalysis:
    topic: str
    genre: str
    stakes: list[str] = field(default_factory=list)
    horizons: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    tensions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)


@dataclass
class ArgumentMap:
    claims: list[Claim] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    values: list[Value] = field(default_factory=list)
    supports: list[Support] = field(default_factory=list)
    attacks: list[Attack] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    unresolved_conflicts: list[ConflictItem] = field(default_factory=list)


# --------- Body of the Serpent (Пик 2) ---------
#
# Восемь голов работают с ОДНИМ телом. Тело — не Заратустра. Это общая
# семантическая и событийная среда, куда фиксируются все ходы.
# Каждая голова получает срез тела перед своим ходом, а не только
# пользовательский вопрос.

@dataclass
class FutureImage:
    """Один образ будущего, построенный головой (ход build_future_image)."""
    persona_id: str
    utterance: str
    horizon: str = "unspecified"
    price: str = ""


@dataclass
class OntologicalPremise:
    """Скрытое допущение, вскрытое ходом attack_presupposition."""
    exposed_by: str
    text: str
    target: str = "previous_turn"


@dataclass
class RiskItem:
    """Риск/цена, названный ходом show_cost."""
    named_by: str
    text: str
    borne_by: str = "не указано"


@dataclass
class ProjectAction:
    """Практическое следствие, предложенное ходом draw_practical_implication."""
    proposed_by: str
    action: str


@dataclass
class PositionChange:
    """Голос сменил рамку или основание внутри run."""
    persona_id: str
    from_state: str
    to_state: str
    reason: str = ""


@dataclass
class TransformationRecord:
    """Ход преображения вопроса (shift_ontology / problematize_question)."""
    performed_by: str
    from_question: str
    to_question: str
    what_reveals: str = ""


@dataclass
class ChorusReflection:
    """Хор (греч. трагедии) как режим общего тела.

    Не голос, не решение. Периодическая рефлексия сцены: температура спора,
    кто молчит, где ложное согласие, где спор ушёл в разные онтологические
    уровни. Пишется Заратустрой каждые N ходов.
    """
    at_turn_index: int
    scene_temperature: str  # "quiet" | "productive" | "heating" | "stuck" | "false_consensus"
    who_speaks_most: str = ""
    who_is_silent: list[str] = field(default_factory=list)
    signals_observed: list[str] = field(default_factory=list)
    suggested_next_move: str = ""


@dataclass
class BodyProjection:
    """Общее тело Змея. Изменяется каждым ходом.

    Голова видит эту проекцию перед своим ходом и реагирует на текущее
    состояние тела, а не на копию исходного пользовательского ввода.
    """
    topic: str = ""
    argument_map: ArgumentMap = field(default_factory=ArgumentMap)
    futures: list[FutureImage] = field(default_factory=list)
    ontological_premises: list[OntologicalPremise] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    projects: list[ProjectAction] = field(default_factory=list)
    position_changes: list[PositionChange] = field(default_factory=list)
    transformations: list[TransformationRecord] = field(default_factory=list)
    alliances_proposed: list[dict] = field(default_factory=list)
    alliances_refused: list[dict] = field(default_factory=list)
    voices_history: list[dict] = field(default_factory=list)   # [{persona_id, operation, turn_index}]
    chorus_reflections: list[ChorusReflection] = field(default_factory=list)
    seeded_from_units: list[str] = field(default_factory=list)  # unit_id из UnitPack
    pack_unresolved_questions: list[str] = field(default_factory=list)  # copy of pack-level questions

    def unresolved_questions_from_pack(self) -> list[str]:
        return list(self.pack_unresolved_questions)

    def snapshot_for_head(self, max_items: int = 4) -> dict:
        """Компактный срез тела для передачи голове перед её ходом."""
        def _last(items, n=max_items):
            return items[-n:] if items else []
        return {
            "topic": self.topic,
            "voices_history": _last(self.voices_history, max_items),
            "futures": [f"[{f.persona_id}] {f.utterance[:200]}" for f in _last(self.futures)],
            "ontological_premises": [f"[{p.exposed_by}] {p.text[:180]}" for p in _last(self.ontological_premises)],
            "risks": [f"[{r.named_by}] {r.text[:180]}" for r in _last(self.risks)],
            "projects": [f"[{p.proposed_by}] {p.action[:180]}" for p in _last(self.projects)],
            "transformations": [
                f"[{t.performed_by}] {t.from_question[:80]} → {t.to_question[:120]}"
                for t in _last(self.transformations)
            ],
            "alliances_proposed": [a.get("action", "")[:120] for a in _last(self.alliances_proposed)],
            "alliances_refused": [a.get("reason", "")[:120] for a in _last(self.alliances_refused)],
            "position_changes": [
                f"[{pc.persona_id}] {pc.from_state[:60]} → {pc.to_state[:60]}"
                for pc in _last(self.position_changes)
            ],
            "chorus_latest": (
                {
                    "at_turn_index": self.chorus_reflections[-1].at_turn_index,
                    "scene_temperature": self.chorus_reflections[-1].scene_temperature,
                    "signals": self.chorus_reflections[-1].signals_observed,
                }
                if self.chorus_reflections else None
            ),
        }


@dataclass
class SecurityEvent:
    kind: str  # jailbreak | manipulation | repetition | prompt_exfiltration | control_hijack
    level: int
    detail: str
    turn_index: int | None = None


@dataclass
class Synthesis:
    direct_position: str
    rationale: str
    practical_implications: list[str] = field(default_factory=list)
    conflict_map: list[ConflictItem] = field(default_factory=list)
    strongest_arguments: list[str] = field(default_factory=list)
    minority_positions: list[MinorityPosition] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    epistemic_status: str = "candidate"


# --------- Completion forms (Пик 1) ---------
#
# Синтез — только одна из десяти форм завершения. Заратустра выбирает форму
# по состоянию совета; синтез разрешён только когда действительно родилась
# новая конструкция, сохраняющая существенные основания сторон.

COMPLETION_FORMS = (
    "alliance",              # временный союз
    "decision_with_dissent", # решение при несогласии
    "unresolvable_conflict", # неразрешимый конфликт
    "aporia",                # апория
    "transformed_question",  # преобразованный вопрос
    "world_fork",            # развилка миров
    "delegation",            # делегирование одному голосу
    "polyphony",             # полифоническое высказывание
    "synthesis",             # синтез (только если новая конструкция)
    "refusal_to_close",      # отказ от закрытия
)


@dataclass
class WorldBranch:
    """Одна ветка в развилке миров."""
    label: str
    if_we_accept: str        # «если принять ценность/угрозу/горизонт X»
    then_world: str          # «то мир выглядит так»
    price: str = ""          # цена этой ветки
    contributing_heads: list[str] = field(default_factory=list)


@dataclass
class AllianceRecord:
    """Временный союз голов для конкретного действия."""
    action: str
    partners: list[str]
    shared_reason: str
    kept_distinct_grounds: list[str] = field(default_factory=list)


@dataclass
class DissentRecord:
    """Кто и почему остаётся против принятого действия."""
    persona_id: str
    against: str
    reason: str
    would_be_lost: str = ""


@dataclass
class CompletionOutcome:
    """Итог совета. Форма выбирается Заратустрой; поля наполняются по форме.

    Общие поля (для всех форм):
      form, rationale, conflict_map, minority_positions,
      unresolved_questions, uncertainties, epistemic_status, voices_used.

    Форма-специфичные поля наполняются только для соответствующего form.
    """
    form: str                                # см. COMPLETION_FORMS
    rationale: str = ""                      # почему выбрана именно эта форма
    voices_used: list[str] = field(default_factory=list)
    conflict_map: list[ConflictItem] = field(default_factory=list)
    minority_positions: list[MinorityPosition] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    epistemic_status: str = "candidate"

    # form=alliance
    alliance: AllianceRecord | None = None

    # form=decision_with_dissent
    decision: str = ""
    dissenting: list[DissentRecord] = field(default_factory=list)

    # form=unresolvable_conflict
    incompatible_pictures: list[dict] = field(default_factory=list)

    # form=aporia
    aporia_statement: str = ""
    why_no_honest_answer: str = ""

    # form=transformed_question
    original_question: str = ""
    transformed_question: str = ""
    what_transformation_reveals: str = ""

    # form=world_fork
    world_branches: list[WorldBranch] = field(default_factory=list)

    # form=delegation
    delegated_to: str = ""                   # persona_id
    delegated_utterance: str = ""
    accompanying_objections: list[str] = field(default_factory=list)

    # form=polyphony
    polyphonic_voices: list[dict] = field(default_factory=list)
    # каждая запись: {persona_id, utterance, kept_distinct_from: [...]}

    # form=synthesis
    synthesis: Synthesis | None = None

    # form=refusal_to_close
    refusal_reason: str = ""
    what_would_be_destroyed_by_closure: str = ""


def to_plain(obj: Any) -> Any:
    """Recursively convert dataclasses / lists to plain JSON-serialisable values."""
    from dataclasses import asdict, is_dataclass
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_plain(v) for k, v in obj.items()}
    return obj


# =============================================================================
# Semantic units — вход от чужого резчика
# =============================================================================
# Резчик Тимура (или любой другой) отдаёт нам тексты, уже разложенные на
# единицы содержания. Мы принимаем их через run_from_units и seed'им состояние
# совета уже разложенной аргументативной тканью.
#
# Никакой словарь-заточка для этого пути НЕ используется — топик и понятия
# приходят из единиц.

@dataclass
class ToulminBundle:
    """Toulmin-разбор аргумента внутри одной единицы содержания."""
    claim: str = ""
    data: str = ""              # grounds / основание
    warrant: str = ""           # implicit rule bridging data → claim
    backing: str = ""
    qualifier: str = ""
    rebuttal: str = ""
    counterclaim: str = ""
    counter_persona: str = ""


@dataclass
class UnitParticipant:
    """Участник внутри одной единицы содержания (метка + нормализованная роль + имя)."""
    label: str                 # исходная speaker-метка ("Speaker 1", "Speaker 3", …)
    normalized_role: str = ""  # "Методолог", "Ведущий", "Инженер", …
    name: str | None = None    # "Олег Гринько" — только если резчик доказал связку


@dataclass
class ThemeRheme:
    theme: str
    rheme: str
    participant_label: str = ""
    locator: str = ""          # тайм-код / индекс реплики / любой locator резчика


@dataclass
class UnitProvenance:
    """Provenance одной единицы содержания."""
    participant_label: str = ""
    participant_name: str = ""
    locator: str = ""


@dataclass
class SemanticUnit:
    """Единица содержания (U-блок), как её даёт внешний резчик."""
    unit_id: str                              # "U1", "U2", …
    title: str
    intention: str = ""                       # "сведения" | "аргументация" | "проблематизация" | …
    object_aspect: str = ""
    participants: list[UnitParticipant] = field(default_factory=list)
    position: str = ""
    theme_rheme: list[ThemeRheme] = field(default_factory=list)
    toulmin: ToulminBundle | None = None
    interventions: list[dict] = field(default_factory=list)
    provenance: list[UnitProvenance] = field(default_factory=list)
    abstract: str = ""
    key_concepts: list[str] = field(default_factory=list)
    unresolved_questions_here: list[str] = field(default_factory=list)


@dataclass
class DiarizationDefect:
    kind: str                                # "разрыв" | "склейка"
    at_label: str
    at_locator: str = ""
    description: str = ""


@dataclass
class SourceAudit:
    """Аудит источника — то, что резчик обнаружил ПРО источник, а не про его содержание.

    Всё это становится сигналами для chorus_reflection на нулевом ходу совета,
    чтобы Заратустра НЕ приписывал позиции конкретному человеку, если резчик
    честно предупредил о ненадёжности диаризации / OCR / атрибуции.
    """
    speaker_roles: list[UnitParticipant] = field(default_factory=list)
    name_evidence: list[dict] = field(default_factory=list)   # [{label, name, evidence_locator, is_hypothesis}]
    diarization_defects: list[DiarizationDefect] = field(default_factory=list)
    recognition_damage: list[dict] = field(default_factory=list)  # [{locator, verbatim, note}]
    ambiguous_vocatives: list[str] = field(default_factory=list)  # ["Саша: два лица", "Олег: два лица"]
    notes: str = ""


@dataclass
class UnitPack:
    """Пакет от резчика: единицы + необязательный аудит источника + метаданные."""
    units: list[SemanticUnit]
    source_audit: SourceAudit | None = None
    seminar_title: str = ""
    seminar_locator_span: str = ""      # "00:00:01 - 02:02:05" например
    cutter_id: str = ""                 # "personas/units-of-content-analyst.md" | другой
    cutter_model: str = ""              # "claude-opus-5" | другой
    source_path: str = ""
    unresolved_questions_pack: list[str] = field(default_factory=list)

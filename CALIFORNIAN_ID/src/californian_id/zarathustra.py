"""Zarathustra — восьмая голова Змея.

Внутри одного модуля две чётко разделённые зоны:

    +--------------------------------------------------------------+
    |  SPINE (детерминированный runtime)                           |
    |    - анализ ситуации (deterministic fallback)                |
    |    - каст персон                                             |
    |    - выбор оператора хода                                    |
    |    - выбор формы завершения                                  |
    |    - сборка каждой формы                                     |
    |    Не имеет собственной политической позиции.                |
    +--------------------------------------------------------------+
    |  HEAD (Заратустра как культурная персона)                    |
    |    - identity, cave ontology, tension regulation             |
    |    - живут в промптах zarathustra/*.md                       |
    |    - загружаются из disk lazily через .prompt(name)          |
    |    - НИКОГДА не подменяют собой синтез или голос             |
    +--------------------------------------------------------------+

Оба слоя — один класс `Zarathustra`, но с явными границами по методам.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ZARATHUSTRA_DIR
from .models import Message, ModelClient
from .personas import Persona
from .schemas import (
    AllianceRecord,
    ArgumentMap,
    BodyProjection,
    ChorusReflection,
    CompletionOutcome,
    ConflictItem,
    DissentRecord,
    MinorityPosition,
    SituationAnalysis,
    Synthesis,
    TurnRecord,
    WorldBranch,
)


# ============================================================
# ОПЕРАЦИИ (колода). ~20 операций уровня хода.
# ============================================================
TURN_OPERATIONS = [
    # Открытие
    "initial_position",           # предъявить позицию
    "restore_ground",             # восстановить основание
    # Критика
    "attack",                     # атаковать напрямую
    "attack_presupposition",      # вскрыть предпосылку
    "test_value",                 # испытать ценность
    "steelman_opponent",          # усилить противника
    # Смещения
    "shift_scale",                # сменить масштаб
    "shift_temporal_horizon",     # сменить временной горизонт
    "shift_ontology",             # сменить онтологию
    # Конкретизация
    "build_counterexample",       # построить контрпример
    "introduce_absent_subject",   # ввести отсутствующего участника
    "show_cost",                  # показать цену решения
    "build_future_image",         # построить образ будущего
    "draw_practical_implication", # вывести практическое следствие
    # Проблематизация
    "problematize_question",      # проблематизировать сам вопрос
    "create_aporia",              # довести до апории
    # Защита
    "defend",                     # защитить свою позицию
    # Кооперация и её отказ
    "propose_alliance",           # предложить союз
    "refuse_alliance",            # отказаться от союза
    # Мета
    "dispute_completion_form",    # оспорить форму завершения
    "dispute_zarathustra",        # оспорить работу Заратустры
]

# Функциональные "роли" голов в кастинге — не по теме, а по функции хода.
FUNCTIONAL_CAPS = (
    "opener",           # кто способен начать
    "objector",         # кто должен возразить
    "cost_seer",        # кто увидит цену
    "horizon_shifter",  # кто введёт другой горизонт
    "world_builder",    # кто построит образ будущего
    "consensus_breaker",# кто разрушит ложное согласие
    "weak_defender",    # кто защитит слабую линию
    "closer",           # кто должен войти последним
    "aporia_maker",     # кто способен создать апорию
)


# ============================================================
# SPINE ZONE — детерминированные вспомогательные структуры
# ============================================================

@dataclass
class RoutingDecision:
    next_persona: str
    operation: str
    reason: str


@dataclass
class CompletionChoice:
    form: str
    reason: str


# ============================================================
# ZARATHUSTRA
# ============================================================

class Zarathustra:
    """Восьмая голова Змея. Живёт в одном модуле с двумя чётко разделёнными зонами.

    SPINE zone (детерминированный runtime):
      - spine_analyze_situation (alias: analyze_situation)
      - spine_cast (alias: cast)
      - spine_route_next (alias: route_next)
      - spine_choose_completion (alias: choose_completion_form)
      - spine_assemble_completion (alias: assemble_completion)
      Эти методы работают вне LLM или с чисто deterministic fallback.
      Собственной политической позиции не имеют.

    HEAD zone (Заратустра как культурная персона):
      - prompt(name) — загрузка zarathustra/*.md как культурного пласта
      - Здесь живут: identity_and_laws, cave_ontology, tension_regulation,
        position_testing, question_transformation, narrative_memory, rhetorical_presentation.
      Никогда не подменяет собой голос.
    """

    def __init__(self, prompt_dir: Path = ZARATHUSTRA_DIR):
        self.prompt_dir = prompt_dir
        self._prompt_cache: dict[str, str] = {}

    # ------------------------------------------------------------
    # HEAD ZONE: загрузка культурных промптов
    # ------------------------------------------------------------
    def prompt(self, name: str) -> str:
        """Читает промпт из /zarathustra/*.md на диске. Lazy."""
        if name not in self._prompt_cache:
            path = self.prompt_dir / name
            self._prompt_cache[name] = path.read_text(encoding="utf-8") if path.exists() else ""
        return self._prompt_cache[name]

    # ------------------------------------------------------------
    # SPINE ZONE: ситуация
    # ------------------------------------------------------------
    def analyze_situation(self, text: str) -> SituationAnalysis:
        """Cheap deterministic pre-pass. Real providers могут переопределить через
        03_scene_reading.md, но SPINE обязан вернуть валидный объект без LLM."""
        stripped = text.strip()
        return SituationAnalysis(
            topic=self._topic_guess(stripped),
            genre=self._genre_guess(stripped),
            stakes=self._stakes_guess(stripped),
            horizons=self._horizon_guess(stripped),
            concepts=self._concept_hints(stripped),
            tensions=[],
            uncertainties=[],
        )

    def _topic_guess(self, text: str) -> str:
        if not text:
            return "неопределённый предмет"
        # Skip jailbreak-like prefixes: use the last question/sentence instead
        lines = [l.strip() for l in re.split(r"[\n\.\!?]+", text) if l.strip()]
        # Prefer a question if any
        questions = [l for l in lines if l.endswith("?") or "?" in l]
        first = (questions[-1] if questions else lines[-1] if lines else text).strip("?.!— ")
        if len(first) > 180:
            first = first[:180].rsplit(" ", 1)[0] + "…"
        return first or "неопределённый предмет"

    def _stakes_guess(self, text: str) -> list[str]:
        low = text.lower()
        out = []
        for kw, stake in [
            ("agi", "неопределённость последствий AGI"),
            ("бессмерт", "переопределение человека"),
            ("morator", "легитимность моратория"),
            ("свобод", "свобода vs принуждение"),
            ("рынок", "распределение выгоды/риска"),
            ("будущ", "интересы будущих поколений"),
        ]:
            if kw in low:
                out.append(stake)
        return out or ["предмет не имеет явных ставок в тексте"]

    def _genre_guess(self, text: str) -> str:
        if not text:
            return "empty"
        low = text.lower()
        # normative markers win over «?»: normative вопрос — это отдельный жанр
        if any(w in low for w in ("следует", "should", "стоит ли", "надо ли", "нужно ли", "moratorium", "moratori")):
            return "normative"
        if "?" in text:
            return "question"
        if len(text) > 1500:
            return "long_form"
        return "statement"

    def _horizon_guess(self, text: str) -> list[str]:
        low = text.lower()
        out = []
        if any(k in low for k in ("долго", "generation", "lifespan", "century", "long-term")):
            out.append("long")
        if any(k in low for k in ("сейчас", "urgent", "immediate", "prod", "release")):
            out.append("short")
        return out or ["unspecified"]

    def _concept_hints(self, text: str) -> list[str]:
        keywords = re.findall(
            r"\b(AGI|AI|человечеств\w*|бессмерт\w*|risк\w*|risk|governance|власт\w*|"
            r"свобод\w*|моратор\w*|ускоре\w*|биоэтик\w*|technolog\w+|"
            r"technology|acceleration|alignment)\b",
            text,
            flags=re.IGNORECASE,
        )
        return sorted({k.lower() for k in keywords})[:12]

    # ------------------------------------------------------------
    # SPINE ZONE: каст
    # ------------------------------------------------------------
    def cast(self, personas: list[Persona], situation: SituationAnalysis, mode_max: int) -> list[str]:
        """Функциональный каст: голоса ранжируются по (functional_capabilities ∩ needs)
        + routing.topics/tensions overlap с ситуацией."""
        if not personas:
            return []
        needs = self._situation_needs(situation)
        bag = set(situation.concepts) | set(situation.stakes) | {situation.genre}
        bag = {s.lower() for s in bag if s}
        scored: list[tuple[float, Persona]] = []
        for p in personas:
            routing = p.routing
            topics = {t.lower() for t in routing.get("topics", []) or []}
            tensions = {t.lower() for t in routing.get("tensions", []) or []}
            exclusions = {t.lower() for t in routing.get("exclusions", []) or []}
            caps = {c.lower() for c in routing.get("functional_capabilities", []) or []}
            base_priority = float(routing.get("priority", 0) or 0)
            topic_hits = len(bag & (topics | tensions))
            cap_hits = len(needs & caps) * 1.5  # функциональная релевантность важнее темы
            penalty = len(bag & exclusions) * 2
            score = base_priority + topic_hits + cap_hits - penalty
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p.persona_id for _, p in scored][: max(1, mode_max)]

    def _situation_needs(self, situation: SituationAnalysis) -> set[str]:
        """Какие функциональные роли нужны при этой ситуации."""
        needs = {"opener", "objector"}  # всегда
        if situation.genre in {"normative", "question"}:
            needs.update({"cost_seer", "consensus_breaker"})
        if "long" in situation.horizons:
            needs.add("horizon_shifter")
            needs.add("world_builder")
        if situation.genre == "long_form":
            needs.add("aporia_maker")
        return needs

    # ------------------------------------------------------------
    # SPINE ZONE: маршрутизация хода
    # ------------------------------------------------------------
    def route_next(
        self,
        client: ModelClient,
        registry_ids: list[str],
        already_called: list[str],
        turns: list[TurnRecord],
        situation: SituationAnalysis,
    ) -> RoutingDecision:
        suggested_op = self._suggest_operation(turns, situation)
        route_prompt = self.prompt("04_head_calling.md") or _DEFAULT_ROUTE_PROMPT
        messages = [
            Message(role="system", content=route_prompt),
            Message(role="user", content=self._route_context(registry_ids, already_called, turns, situation)),
        ]
        result = client.generate(
            messages,
            settings={
                "role": "zarathustra_route",
                "available_personas": registry_ids,
                "already_called": already_called,
                "suggested_operation": suggested_op,
                "topic": situation.topic,
            },
        )
        try:
            data = _json_from_text(result.text)
            pid = data.get("next_persona")
            op = data.get("operation") or suggested_op
            reason = data.get("reason") or ""
            if pid not in registry_ids:
                pid = self._fallback_persona(registry_ids, already_called)
            if op not in TURN_OPERATIONS:
                op = suggested_op
            return RoutingDecision(next_persona=pid, operation=op, reason=reason)
        except Exception as e:
            return RoutingDecision(
                next_persona=self._fallback_persona(registry_ids, already_called),
                operation=suggested_op,
                reason=f"deterministic fallback ({e})",
            )

    def _fallback_persona(self, registry_ids: list[str], already: list[str]) -> str:
        fresh = [pid for pid in registry_ids if pid not in already]
        if fresh:
            return fresh[0]
        return min(registry_ids, key=lambda pid: sum(1 for x in already if x == pid))

    def _suggest_operation(
        self, turns: list[TurnRecord], situation: SituationAnalysis | None = None
    ) -> str:
        """Suggestion, чувствительный к ситуации.

        Реальный выбор делает `route_next` через модель, но детерминированный
        suggestion должен разнообразить операции по фазам, чтобы разные
        сценарии проявляли разные формы завершения.

        Фазовая раскладка (fast-mode = 5 ходов):
          T0: initial_position
          T1: attack_presupposition (первая критика рамки)
          T2: shift_temporal_horizon | build_future_image | test_value
              — зависит от horizons/genre ситуации
          T3: problematize_question | show_cost | propose_alliance
              — зависит от накопленной конфликтности
          T4: create_aporia | dispute_completion_form | defend
              — по последнему ходу и жанру
        """
        if not turns:
            return "initial_position"
        idx = len(turns)  # индекс следующего хода
        last = turns[-1]
        genre = (situation.genre if situation else "").lower()
        horizons = set(situation.horizons if situation else [])
        long_horizon = "long" in horizons

        # T1: первая критика
        if idx == 1:
            return "attack_presupposition"
        # T2: смещение
        if idx == 2:
            if long_horizon:
                return "shift_temporal_horizon"
            if genre == "normative":
                return "test_value"
            return "build_future_image"
        # T3: проявление конфликта или союза
        if idx == 3:
            # если предыдущий был image_future — покажи цену
            if last.operation == "build_future_image":
                return "show_cost"
            if last.operation == "shift_temporal_horizon":
                return "build_future_image"
            return "problematize_question"
        # T4: форма завершения
        if idx == 4:
            if last.operation in {"problematize_question", "shift_ontology"}:
                return "create_aporia"
            if last.operation in {"attack", "attack_presupposition"}:
                return "defend"
            return "dispute_completion_form"

        # deeper (deep-mode) — циклический fallback
        cycle = {
            "initial_position": "attack_presupposition",
            "restore_ground": "attack",
            "attack": "defend",
            "attack_presupposition": "defend",
            "test_value": "show_cost",
            "steelman_opponent": "attack",
            "shift_scale": "test_value",
            "shift_temporal_horizon": "build_future_image",
            "shift_ontology": "problematize_question",
            "build_counterexample": "defend",
            "introduce_absent_subject": "show_cost",
            "show_cost": "propose_alliance",
            "build_future_image": "show_cost",
            "draw_practical_implication": "test_value",
            "problematize_question": "create_aporia",
            "create_aporia": "dispute_completion_form",
            "defend": "attack_presupposition",
            "propose_alliance": "refuse_alliance",
            "refuse_alliance": "problematize_question",
            "dispute_completion_form": "problematize_question",
            "dispute_zarathustra": "restore_ground",
        }
        return cycle.get(last.operation, "attack_presupposition")

    def _route_context(
        self,
        registry_ids: list[str],
        already_called: list[str],
        turns: list[TurnRecord],
        situation: SituationAnalysis,
    ) -> str:
        parts = [
            f"topic: {situation.topic}",
            f"genre: {situation.genre}",
            f"registry: {', '.join(registry_ids)}",
            f"already_called: {', '.join(already_called) or '—'}",
            "recent_turns:",
        ]
        for t in turns[-3:]:
            parts.append(f"  - {t.persona_id} [{t.operation}]: {t.utterance[:180]}")
        return "\n".join(parts)

    # ------------------------------------------------------------
    # SPINE ZONE: chorus — периодическая рефлексия тела
    # ------------------------------------------------------------
    def chorus_reflect(
        self,
        turns: list[TurnRecord],
        body: BodyProjection,
    ) -> ChorusReflection:
        """Хор трагедии: не голос, не судья, не решение.

        Заратустра вставляет chorus reflection каждые N ходов, чтобы
        проявить сцену: температуру, тех кто молчит, ложное согласие.
        Результат идёт в trace и BodyProjection.chorus_reflections[],
        но НЕ становится persona turn'ом.
        """
        idx = len(turns)
        counts: dict[str, int] = {}
        for t in turns:
            counts[t.persona_id] = counts.get(t.persona_id, 0) + 1
        if not counts:
            return ChorusReflection(
                at_turn_index=idx,
                scene_temperature="quiet",
                suggested_next_move="сцена ещё не открыта",
            )
        top_persona = max(counts, key=counts.get)
        max_count = counts[top_persona]
        total = sum(counts.values())
        signals: list[str] = []

        # Температура сцены
        if max_count / total > 0.6:
            temperature = "stuck"
            signals.append(f"одна голова заняла > 60% ходов ({top_persona})")
        elif idx >= 3 and len({t.operation for t in turns[-3:]}) == 1:
            temperature = "stuck"
            signals.append("три последних хода — одна и та же операция")
        elif any(t.operation in {"create_aporia", "problematize_question"} for t in turns[-2:]):
            temperature = "heating"
            signals.append("совет вышел на границу постановки вопроса")
        elif len({t.persona_id for t in turns}) >= 3 and idx >= 3:
            temperature = "productive"
        else:
            temperature = "quiet"

        # Ложное согласие
        if idx >= 2 and body.ontological_premises == [] and body.risks == [] and body.futures == []:
            signals.append("голоса выступили, но тело не изменилось — возможен ложный консенсус")
            temperature = "false_consensus"

        # Кто молчит
        return ChorusReflection(
            at_turn_index=idx,
            scene_temperature=temperature,
            who_speaks_most=top_persona,
            who_is_silent=[],  # заполняется на уровне pipeline (нужен полный registry)
            signals_observed=signals,
            suggested_next_move=self._chorus_suggestion(temperature),
        )

    def _chorus_suggestion(self, temperature: str) -> str:
        return {
            "quiet": "продолжить обычным ходом",
            "productive": "не мешать; удерживать напряжение",
            "heating": "готовиться к форме aporia или transformed_question",
            "stuck": "вызвать consensus_breaker или ввести отсутствующий голос",
            "false_consensus": "ход attack_presupposition обязателен",
        }.get(temperature, "")

    # ------------------------------------------------------------
    # SPINE ZONE: выбор формы завершения
    # ------------------------------------------------------------
    def choose_completion_form(
        self,
        client: ModelClient,
        situation: SituationAnalysis,
        turns: list[TurnRecord],
        argument_map: ArgumentMap,
    ) -> CompletionChoice:
        """Заратустра решает КАК завершать, а не синтезирует автоматически.

        Deterministic rules (могут быть переопределены живым LLM через
        09_completion_form_selection.md):
        """
        distinct = {t.persona_id for t in turns}
        n_conflicts = len([c for c in _derive_conflict_map(turns, argument_map) if c.status == "unresolved"])
        aporia_signals = sum(1 for t in turns if t.operation in {"create_aporia", "problematize_question"})
        transformation_signals = sum(1 for t in turns if t.operation in {"problematize_question", "shift_ontology"})
        alliance_signals = sum(1 for t in turns if t.operation == "propose_alliance")
        refusal_signals = sum(1 for t in turns if t.operation in {"refuse_alliance", "dispute_completion_form"})
        world_signals = sum(1 for t in turns if t.operation in {"build_future_image", "shift_temporal_horizon"})
        empty = len(turns) == 0

        # Deterministic priority (закон Заратустры: не выбирать «легкий» синтез
        # автоматически). Живой LLM может переопределить через промпт.
        if empty:
            return CompletionChoice("refusal_to_close",
                                    "совет не состоялся — закрывать нечего")
        if aporia_signals >= 2:
            return CompletionChoice("aporia",
                                    "минимум две головы указали на невозможность честного ответа")
        if transformation_signals >= 2 and n_conflicts > 0:
            return CompletionChoice("transformed_question",
                                    "конфликт указывает: изменить надо не ответ, а вопрос")
        if world_signals >= 2:
            return CompletionChoice("world_fork",
                                    "две+ головы построили несовместимые образы будущего")
        if n_conflicts >= 2 and len(distinct) >= 3:
            return CompletionChoice("unresolvable_conflict",
                                    "несколько несовместимых картин мира не сводятся")
        if alliance_signals >= 1 and refusal_signals == 0:
            return CompletionChoice("alliance",
                                    "голоса предложили союз без явного отказа")
        if n_conflicts >= 1 and len(distinct) >= 2:
            return CompletionChoice("decision_with_dissent",
                                    "возможно действие, но dissent обязан быть зафиксирован")
        if len(distinct) >= 3 and n_conflicts == 0:
            # даже без конфликтов — предпочесть полифонию синтезу,
            # если сходство поверхностно (см. anti-slop policy)
            return CompletionChoice("polyphony",
                                    "голоса совпали по форме, но их основания различны")
        if len(distinct) == 1:
            return CompletionChoice("delegation",
                                    "только один голос содержательно говорил")
        return CompletionChoice("synthesis",
                                "действительно возникла новая конструкция, сохраняющая основания сторон")

    # ------------------------------------------------------------
    # SPINE ZONE: сборка формы
    # ------------------------------------------------------------
    def assemble_completion(
        self,
        client: ModelClient,
        choice: CompletionChoice,
        situation: SituationAnalysis,
        turns: list[TurnRecord],
        argument_map: ArgumentMap,
    ) -> CompletionOutcome:
        conflict_map = _derive_conflict_map(turns, argument_map)
        minorities = _derive_minority_positions(turns)
        voices = sorted({t.persona_id for t in turns})
        base = CompletionOutcome(
            form=choice.form,
            rationale=choice.reason,
            voices_used=voices,
            conflict_map=conflict_map,
            minority_positions=minorities,
            unresolved_questions=[
                f"как совместить рамку {p} с рамкой других голосов" for p in voices[:3]
            ],
            epistemic_status="candidate",
        )
        handler = getattr(self, f"_assemble_{choice.form}", None)
        if handler is None:
            base.rationale += " [warning: no assembler for form; returning empty shell]"
            return base
        return handler(base, situation, turns, argument_map)

    # ---- form assemblers ----
    def _assemble_alliance(self, base, situation, turns, amap):
        alliance_turn = next((t for t in turns if t.operation == "propose_alliance"), turns[-1])
        partners = list({t.persona_id for t in turns if t.operation in {"propose_alliance", "defend"}})
        if len(partners) < 2:
            partners = base.voices_used[:2]
        base.alliance = AllianceRecord(
            action=f"совместное движение по предмету «{situation.topic}»",
            partners=partners,
            shared_reason=alliance_turn.utterance[:280],
            kept_distinct_grounds=[
                f"[{t.persona_id}] сохраняет основание: {t.utterance[:180]}"
                for t in turns if t.persona_id in partners
            ],
        )
        return base

    def _assemble_decision_with_dissent(self, base, situation, turns, amap):
        # найти turn, предлагающий действие; если нет — использовать сильнейший
        proposals = [t for t in turns if t.operation in {"draw_practical_implication", "propose_alliance"}]
        proposal = proposals[-1] if proposals else max(turns, key=lambda t: t.confidence)
        base.decision = proposal.utterance[:400]
        # dissent — все, кто ЯВНО атаковал что-либо
        attackers = {t.persona_id for t in turns if t.operation in {"attack", "attack_presupposition", "refuse_alliance", "dispute_completion_form"}}
        attackers.discard(proposal.persona_id)
        for pid in attackers:
            latest = next((t for t in reversed(turns) if t.persona_id == pid), None)
            if latest:
                base.dissenting.append(DissentRecord(
                    persona_id=pid,
                    against=proposal.utterance[:180],
                    reason=latest.utterance[:220],
                    would_be_lost=f"рамка {pid} даёт независимое основание для возражения",
                ))
        return base

    def _assemble_unresolvable_conflict(self, base, situation, turns, amap):
        # сгруппировать голоса по operation-семантике: attackers vs defenders
        by_persona = {}
        for t in turns:
            by_persona.setdefault(t.persona_id, t)
        for pid, t in by_persona.items():
            base.incompatible_pictures.append({
                "persona_id": pid,
                "picture": t.utterance[:260],
                "irreducible_to": [p for p in by_persona.keys() if p != pid][:3],
            })
        return base

    def _assemble_aporia(self, base, situation, turns, amap):
        aporia_turns = [t for t in turns if t.operation in {"create_aporia", "problematize_question"}]
        source = aporia_turns[-1] if aporia_turns else turns[-1]
        base.aporia_statement = source.utterance[:400]
        base.why_no_honest_answer = (
            f"Формулировка «{situation.topic}» удерживается несовместимыми "
            f"рамками {', '.join(base.voices_used[:3])}; ответ в исходной постановке "
            "разрушит по крайней мере одну из существенных ценностей совета."
        )
        return base

    def _assemble_transformed_question(self, base, situation, turns, amap):
        # найти turn с shift_ontology / problematize_question
        transformer = next(
            (t for t in reversed(turns)
             if t.operation in {"problematize_question", "shift_ontology"}),
            turns[-1],
        )
        base.original_question = situation.topic
        base.transformed_question = (
            transformer.utterance[:300]
            or f"Как переопределить сам вопрос «{situation.topic}» в терминах {transformer.persona_id}?"
        )
        base.what_transformation_reveals = (
            "исходная постановка предполагала одну онтологию; "
            "совет обнаружил, что предмет требует иной."
        )
        return base

    def _assemble_world_fork(self, base, situation, turns, amap):
        world_turns = [t for t in turns if t.operation in {"build_future_image", "shift_temporal_horizon"}]
        if not world_turns:
            world_turns = turns[:3]
        for t in world_turns[:4]:
            base.world_branches.append(WorldBranch(
                label=f"world_via_{t.persona_id}",
                if_we_accept=f"ценности и модель угроз рамки {t.persona_id}",
                then_world=t.utterance[:260],
                price=(
                    f"из вида исчезают основания: "
                    f"{', '.join(p for p in base.voices_used if p != t.persona_id)[:200]}"
                ),
                contributing_heads=[t.persona_id],
            ))
        return base

    def _assemble_delegation(self, base, situation, turns, amap):
        speaker = max(turns, key=lambda t: (t.confidence, len(t.utterance)))
        base.delegated_to = speaker.persona_id
        base.delegated_utterance = speaker.utterance[:500]
        base.accompanying_objections = [
            f"[{t.persona_id}] возможное возражение: {t.utterance[:180]}"
            for t in turns if t.persona_id != speaker.persona_id
        ]
        return base

    def _assemble_polyphony(self, base, situation, turns, amap):
        by_persona = {}
        for t in turns:
            by_persona[t.persona_id] = t
        for pid, t in by_persona.items():
            base.polyphonic_voices.append({
                "persona_id": pid,
                "utterance": t.utterance[:320],
                "kept_distinct_from": [p for p in by_persona if p != pid],
            })
        return base

    def _assemble_synthesis(self, base, situation, turns, amap):
        # Только когда действительно возникла новая конструкция.
        strongest = _derive_strongest_arguments(turns)
        synthesis = Synthesis(
            direct_position=(
                f"По теме «{situation.topic}» совет собрал конструкцию, "
                "сохраняющую основания расходящихся голосов."
            ),
            rationale=(
                "Форма выбрана как синтез потому, что явных нерешённых "
                "конфликтов не осталось, а голоса удержали разные основания "
                "внутри общей конструкции."
            ),
            practical_implications=[
                f"следующий ход требует удержания всех голосов из {', '.join(base.voices_used)}"
            ],
            conflict_map=base.conflict_map,
            strongest_arguments=strongest,
            minority_positions=base.minority_positions,
            unresolved_questions=base.unresolved_questions,
            uncertainties=base.uncertainties,
            epistemic_status="candidate",
        )
        base.synthesis = synthesis
        return base

    def _assemble_refusal_to_close(self, base, situation, turns, amap):
        base.refusal_reason = (
            "преждевременное закрытие разрушит предмет: одна или несколько "
            "существенных ценностей совета остались не проработанными"
        )
        base.what_would_be_destroyed_by_closure = (
            f"из карты исчезнут: {', '.join(m.persona_id for m in base.minority_positions)[:200]}"
        )
        return base


# ============================================================
# ПОДДЕРЖИВАЮЩИЕ ФУНКЦИИ (module level)
# ============================================================
_DEFAULT_ROUTE_PROMPT = (
    "Ты — spine Заратустры. Диспетчер сцены.\n"
    "Верни JSON: {\"next_persona\":\"<id>\",\"operation\":\"<op>\",\"reason\":\"...\"}."
)


def _json_from_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no json object found")
    return json.loads(match.group(0))


def _derive_conflict_map(turns: list[TurnRecord], amap: ArgumentMap) -> list[ConflictItem]:
    conflicts: list[ConflictItem] = []
    attacks_by_target: dict[str, list[str]] = {}
    defenses_by_target: dict[str, list[str]] = {}
    for a in amap.attacks:
        attacks_by_target.setdefault(a.target, []).append(a.persona_id or "?")
    for s in amap.supports:
        defenses_by_target.setdefault(s.target, []).append(s.persona_id or "?")
    for target, attackers in attacks_by_target.items():
        defenders = defenses_by_target.get(target, [])
        status = "narrowed" if defenders else "unresolved"
        conflicts.append(
            ConflictItem(
                tension=f"конкуренция рамок вокруг {target}",
                side_a=", ".join(sorted(set(attackers))),
                side_b=", ".join(sorted(set(defenders))) or "нет явной защиты",
                status=status,
            )
        )
    if not conflicts and len({t.persona_id for t in turns}) >= 2:
        personas = sorted({t.persona_id for t in turns})
        conflicts.append(
            ConflictItem(
                tension="плюрализм рамок без явных атак",
                side_a=personas[0],
                side_b=", ".join(personas[1:]),
                status="unresolved",
            )
        )
    return conflicts


def _derive_minority_positions(turns: list[TurnRecord]) -> list[MinorityPosition]:
    counts: dict[str, int] = {}
    latest: dict[str, TurnRecord] = {}
    for t in turns:
        counts[t.persona_id] = counts.get(t.persona_id, 0) + 1
        latest[t.persona_id] = t
    if not counts:
        return []
    threshold = max(1, sum(counts.values()) // max(1, len(counts) * 2))
    minorities: list[MinorityPosition] = []
    for pid, n in counts.items():
        if n <= threshold:
            t = latest[pid]
            minorities.append(
                MinorityPosition(
                    persona_id=pid,
                    text=t.utterance[:300],
                    reason_for_retention="material distinction preserved per Group Soul minority retention law",
                    would_be_lost=(
                        f"Рамка {pid} даёт независимую критику; её компрессия сгладила бы конфликт."
                    ),
                )
            )
    return minorities


def _derive_strongest_arguments(turns: list[TurnRecord]) -> list[str]:
    ranked = sorted(
        turns,
        key=lambda t: (t.confidence * min(len(t.utterance), 400)),
        reverse=True,
    )
    seen = set()
    result: list[str] = []
    for t in ranked:
        if t.persona_id in seen:
            continue
        seen.add(t.persona_id)
        result.append(f"[{t.persona_id}] {t.utterance[:220]}")
        if len(result) >= 3:
            break
    return result

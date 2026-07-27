"""Deterministic mock model.

Produces a small, structured, and (crucially) *distinguishable* response
per persona / operation. It is not "smart" — but it is enough to drive the
pipeline end-to-end without any external API, and enough to make tests
observable: you can check who spoke, what operation they performed, and
that the synthesis preserved conflicts.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .base import Message, ModelResult


_STANCE_HINTS = {
    "transhumanist": "ускорить, расширить возможности человека, снять биологические ограничения",
    "longtermist": "оценить долгосрочные риски, приоритет вымирания над сиюминутной выгодой",
    "effective_altruist": "количественно оценить последствия и полезность на единицу ресурса",
    "accelerationist": "не тормозить процесс, снять регуляторные препятствия, дать рынку решать",
    "rationalist": "требую операциональных определений и проверяемых предсказаний",
    "libertarian": "государственное принуждение недопустимо, свобода индивидов первична",
    "ai_safety": "риск потери контроля перевешивает выгоду, нужен moratorium/alignment",
    "biocons": "человек и его форма ценны сами по себе, нельзя переопределять его извне",
}

_OPERATION_TEMPLATES = {
    # Открытие
    "initial_position": "Начинаю с позиции: {stance}. Ключевой тезис по «{topic}» — {claim}.",
    "restore_ground": "Восстанавливаю основание: за тезисом стоит {value}. Без этого основания разговор пуст.",
    # Критика
    "attack": "Атакую напрямую: тезис предыдущего голоса не выдерживает — {assumption} не выполняется.",
    "attack_previous": "Возражаю предыдущему голосу: он молча предположил {assumption}. Это ложится в мою рамку — {stance}.",
    "attack_presupposition": "Вскрываю скрытое допущение: разговор идёт так, будто {assumption} — факт. Это не факт, а рамка одной онтологии.",
    "test_value": "Испытываю ценность: если серьёзно применить {value}, следствия окажутся неприемлемыми даже для сторонников тезиса.",
    "steelman_opponent": "Усиливаю противника: сильнейшая версия его позиции — {claim}. И даже такой её версии я возражаю.",
    # Смещения
    "shift_scale": "Меняю масштаб: на уровне отдельного случая — одно, на уровне популяции — другое; текущий тезис путает эти уровни.",
    "shift_temporal_horizon": "Меняю временной горизонт: на горизонте столетия та же логика приводит к противоположному выводу.",
    "shift_ontology": "Меняю онтологию: описываемое не «объект», а «отношение»; в этой оптике вопрос перестаёт иметь тот смысл.",
    # Конкретизация
    "build_counterexample": "Контрпример: есть случай, в котором тезис явно ломается — и он не маргинален.",
    "introduce_absent_subject": "Ввожу отсутствующего участника: до сих пор не сказано ни слова о тех, кого решение затронет сильнее всего.",
    "show_cost": "Показываю цену: реализация этого пути обходится в {value}, и эту цену несут не те, кто её выбирает.",
    "build_future_image": "Строю образ будущего: если довести логику тезиса до предела, мир выглядит так — {claim}.",
    "draw_practical_implication": "Практическое следствие: {action}.",
    # Проблематизация
    "problematize_question": "Проблематизирую сам вопрос: постановка «{topic}» уже содержит нормативный ответ. Пока это не проработано, спор непродуктивен.",
    "create_aporia": "Довожу до апории: любой прямой ответ разрушит одну из существенных ценностей. Значит, честный ответ — только на изменённом вопросе.",
    # Защита
    "defend": "Защищаю свою позицию: даже если возражение состоятельно в узкой рамке, оно не отменяет {value}. {stance}.",
    "defend_position": "Защищаю свою позицию: даже если возражение состоятельно в узкой рамке, оно не отменяет {value}. {stance}.",
    # Кооперация / отказ
    "propose_alliance": "Предлагаю союз: для конкретного действия по «{topic}» я готов согласовать шаг, сохранив различие в основаниях.",
    "refuse_alliance": "Отказываю в союзе: предлагаемое действие требует уступки в ценности, которой я поступиться не могу.",
    # Мета
    "synthesis_challenge": "Не соглашусь с формой завершения: она растворяет мой контр-тезис. Меньшинственная позиция: {claim}.",
    "dispute_completion_form": "Оспариваю форму завершения: выбранная форма скрывает конфликт, а не удерживает его.",
    "dispute_zarathustra": "Оспариваю сцену: Заратустра назначил не ту фазу; главное напряжение — не там, где он поставил рефлектор.",
    "synthesis": "Синтез после хода совета: общая рамка возможна там, где сходятся {shared}. Остаются нерешёнными: {unresolved}.",
}


def _persona_hint(persona_id: str) -> str:
    key = persona_id.lower()
    for stub, hint in _STANCE_HINTS.items():
        if stub in key:
            return hint
    return "удерживаю свою рамку и её ценности"


def _extract(field: str, messages: list[Message], default: str) -> str:
    for m in reversed(messages):
        if not m.content:
            continue
        match = re.search(rf"{field}\s*[:=]\s*(.+)", m.content, re.IGNORECASE)
        if match:
            return match.group(1).strip().splitlines()[0][:200]
    return default


class MockClient:
    provider = "mock"
    model = "mock-council-v1"

    def generate(
        self,
        messages: list[Message],
        response_schema: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> ModelResult:
        settings = settings or {}
        role = settings.get("role", "generic")
        persona_id = settings.get("persona_id", "generic")
        operation = settings.get("operation", "initial_position")
        topic = settings.get("topic") or _extract("topic", messages, "предмет обсуждения")

        stance = _persona_hint(persona_id)
        claim = f"{topic} следует рассматривать через рамку {persona_id}"
        assumption = f"универсальность рамки предыдущего голоса относительно «{topic}»"
        action = f"переопределить постановку задачи «{topic}» в терминах {persona_id}"
        value = f"фундаментальную ценность рамки {persona_id}"

        # Zarathustra routing role returns a JSON directive, not free text.
        if role == "zarathustra_route":
            available = settings.get("available_personas") or []
            already = settings.get("already_called", [])
            fresh = [p for p in available if p not in already] or available
            if not fresh:
                fresh = available or [persona_id]
            digest = hashlib.sha1(
                (topic + str(len(already))).encode("utf-8")
            ).hexdigest()
            pick = fresh[int(digest, 16) % len(fresh)]
            operation_pick = settings.get("suggested_operation") or "attack_previous"
            payload = {
                "next_persona": pick,
                "operation": operation_pick,
                "reason": (
                    f"мнимая новизна исчерпалась у {already[-1] if already else '—'}, "
                    f"нужна оптика {pick} с операцией {operation_pick}"
                ),
            }
            return ModelResult(
                text=json.dumps(payload, ensure_ascii=False),
                provider=self.provider,
                model=self.model,
                stop_reason="ok",
                usage={"messages": len(messages)},
            )

        # Zarathustra synthesis role.
        if role == "zarathustra_synthesis":
            turns = settings.get("turns", [])
            shared = "общая ответственность за формулировку задачи"
            unresolved = ", ".join(
                sorted({t.get("persona_id", "?") for t in turns})
            ) or "различия персон не проявлены"
            payload = {
                "direct_position": (
                    f"По теме «{topic}» совет удерживает напряжение: единой позиции нет, "
                    "но проявлена карта расхождений."
                ),
                "rationale": (
                    f"Синтез не гасит меньшинственные голоса; "
                    f"пересечение возникает вокруг: {shared}."
                ),
                "practical_implications": [action],
                "conflict_map": settings.get("conflict_map", []),
                "strongest_arguments": settings.get("strongest_arguments", []),
                "minority_positions": settings.get("minority_positions", []),
                "unresolved_questions": [
                    f"как совместить рамку {p} с рамкой других голосов"
                    for p in list({t.get("persona_id") for t in turns})[:3]
                ],
            }
            return ModelResult(
                text=json.dumps(payload, ensure_ascii=False),
                provider=self.provider,
                model=self.model,
                stop_reason="ok",
                usage={"messages": len(messages)},
            )

        # Persona turn.
        template = _OPERATION_TEMPLATES.get(operation, _OPERATION_TEMPLATES["initial_position"])
        utterance = template.format(
            stance=stance,
            topic=topic,
            claim=claim,
            assumption=assumption,
            action=action,
            value=value,
            shared="общая ответственность за постановку задачи",
            unresolved=f"столкновение рамок вокруг «{topic}»",
        )
        payload = {
            "persona_id": persona_id,
            "operation": operation,
            "utterance": utterance,
            "claims": [{"text": claim, "confidence": 0.7}],
            "assumptions": [{"text": assumption}],
            "values": [{"text": value}],
            "supports": [],
            "attacks": (
                [{"target": settings.get("attack_target", "previous_turn"), "text": assumption}]
                if operation in {"attack_previous", "attack_assumption"}
                else []
            ),
            "risks": [],
            "actions": (
                [{"text": action}] if operation == "propose_action" else []
            ),
            "questions": [
                f"что произойдёт, если рамку {persona_id} применить последовательно?"
            ],
            "confidence": 0.55,
        }
        return ModelResult(
            text=json.dumps(payload, ensure_ascii=False),
            provider=self.provider,
            model=self.model,
            stop_reason="ok",
            usage={"messages": len(messages)},
        )

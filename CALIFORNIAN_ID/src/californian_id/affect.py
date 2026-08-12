"""Runtime affect state per persona.

Аффект модулирует риторику и предпочтение операции, но НЕ отменяет
конституцию Заратустры и не отменяет форму завершения.
"""
from __future__ import annotations

from dataclasses import dataclass


AFFECT_STATES = ("neutral", "alert", "restrained_anger", "severe", "ironic")


@dataclass
class PersonaAffect:
    persona_id: str
    state: str = "neutral"
    intensity: float = 0.0        # [0, 1]
    trigger: str = ""

    def decay(self, factor: float = 0.2) -> None:
        self.intensity = max(0.0, self.intensity - factor)
        if self.intensity < 0.05:
            self.state = "neutral"
            self.trigger = ""


class AffectBook:
    """Хранилище аффектов всех голосов в run. Пересчитывается каждым turn."""

    def __init__(self) -> None:
        self._book: dict[str, PersonaAffect] = {}

    def get(self, persona_id: str) -> PersonaAffect:
        if persona_id not in self._book:
            self._book[persona_id] = PersonaAffect(persona_id=persona_id)
        return self._book[persona_id]

    def observe(self, persona_id: str, operation: str, target_persona: str | None = None) -> None:
        """Обновить аффект после хода этой персоны."""
        # Decay для ВСЕХ, кто НЕ говорил в этом ходе
        for pid, a in self._book.items():
            if pid != persona_id:
                a.decay(0.2)

        aff = self.get(persona_id)
        if operation in {"attack", "attack_presupposition"}:
            aff.state = "severe"
            aff.intensity = min(1.0, aff.intensity + 0.25)
            aff.trigger = f"атаковал (operation={operation})"
        elif operation == "defend":
            aff.state = "alert"
            aff.intensity = min(1.0, aff.intensity + 0.15)
            aff.trigger = "защищал позицию"
        elif operation == "refuse_alliance":
            aff.state = "restrained_anger"
            aff.intensity = min(1.0, aff.intensity + 0.2)
            aff.trigger = "отказал в союзе"
        elif operation == "create_aporia":
            aff.state = "ironic"
            aff.intensity = min(1.0, aff.intensity + 0.15)
            aff.trigger = "довёл до апории"
        elif operation == "dispute_zarathustra":
            aff.state = "severe"
            aff.intensity = min(1.0, aff.intensity + 0.3)
            aff.trigger = "оспорил Заратустру"
        else:
            aff.decay(0.1)

        # Атакующий заряжает target'а (если он в реестре)
        if target_persona and target_persona in self._book:
            t = self.get(target_persona)
            if operation in {"attack", "attack_presupposition"}:
                t.state = "alert"
                t.intensity = min(1.0, t.intensity + 0.2)
                t.trigger = f"был атакован голосом {persona_id}"

    def hot_personas(self, threshold: float = 0.6) -> list[str]:
        """Кто сейчас нагрет. Заратустра может предпочесть их для
        shift_ontology / create_aporia (см. правило в policy)."""
        return [pid for pid, a in self._book.items() if a.intensity >= threshold]

    def snapshot(self) -> dict[str, dict]:
        return {pid: a.__dict__ for pid, a in self._book.items()}

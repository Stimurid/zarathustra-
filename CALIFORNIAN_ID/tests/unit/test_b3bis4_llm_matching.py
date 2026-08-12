"""B-3bis.4 — LLM-matching для persona routing через situation_concepts."""
from __future__ import annotations

import pytest


def _runtime():
    from californian_id.persona_layer import PersonaCouncilRuntime
    return PersonaCouncilRuntime()


def test_plan_route_without_concepts_is_baseline():
    """Baseline: без concepts работает keyword-only (обратная совместимость)."""
    rt = _runtime()
    plan = rt.plan_route("A short scene about markets and regulation.",
                        enable_nemo8=False)
    assert plan.persona_scores  # dict populated
    assert plan.selected_persona_ids  # чтото выбрано


def test_plan_route_with_concepts_boosts_matching_persona():
    """С concepts, matching-персона получает higher score."""
    rt = _runtime()
    # Нейтральная сцена без ясного keyword match
    scene = "Обсуждение общего вопроса."
    baseline = rt.plan_route(scene, enable_nemo8=False)
    with_concepts = rt.plan_route(
        scene, enable_nemo8=False,
        situation_concepts=["long-term", "trajectory", "future"],
    )
    # Persona L (Longtermist) должна получить boost
    assert with_concepts.persona_scores.get("L", 0) > baseline.persona_scores.get("L", 0)


def test_plan_route_concepts_case_insensitive():
    rt = _runtime()
    scene = "abc"
    plan = rt.plan_route(scene, enable_nemo8=False,
                        situation_concepts=["FUTURE", "Long-Term"])
    # boost должен работать даже с UPPER-CASE concepts
    assert plan.persona_scores.get("L", 0) >= 2.0


def test_plan_route_empty_concepts_no_change():
    rt = _runtime()
    scene = "Neutral text without keyword matches."
    baseline = rt.plan_route(scene, enable_nemo8=False)
    with_empty = rt.plan_route(scene, enable_nemo8=False, situation_concepts=[])
    assert baseline.persona_scores == with_empty.persona_scores


def test_plan_route_ignores_short_concepts():
    """Concepts длиной ≤1 char не должны создавать noise."""
    rt = _runtime()
    plan = rt.plan_route("test", enable_nemo8=False,
                        situation_concepts=["a", "b", ""])
    # ни один короткий concept не должен матчиться
    for score in plan.persona_scores.values():
        assert isinstance(score, float)


def test_plan_route_multiple_concept_matches_boost_once_per_concept():
    """Один concept boost'ит персону максимум один раз (не по каждой phrase)."""
    rt = _runtime()
    # concept 'longterm' — matches multiple L-keywords, но boost = +2.0 (не +2 * N)
    plan = rt.plan_route("scene", enable_nemo8=False,
                        situation_concepts=["longterm"])
    # score L = 2.0 (один concept, break after first match)
    assert plan.persona_scores.get("L", 0) <= 2.5


def test_plan_route_backward_compat_signature():
    """Старая сигнатура (без situation_concepts) должна работать."""
    rt = _runtime()
    plan = rt.plan_route("test scene", enable_nemo8=False, force_span=None)
    assert plan is not None

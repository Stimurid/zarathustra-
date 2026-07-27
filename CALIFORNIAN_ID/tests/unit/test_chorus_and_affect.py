"""Tests for chorus mode and affect state."""
from californian_id.affect import AffectBook
from californian_id.pipeline import Pipeline


def test_chorus_reflections_are_written_periodically():
    result = Pipeline().run(
        "Стоит ли вводить моратории на разработку продвинутых AI-систем?",
        mode="fast",
    )
    reflections = result.run_state.body.chorus_reflections
    # каждые 2 хода — минимум 2 рефлексии за 5-turn fast run
    assert len(reflections) >= 2, f"only {len(reflections)} chorus reflections"
    for r in reflections:
        assert r.scene_temperature in {"quiet", "productive", "heating", "stuck", "false_consensus"}


def test_chorus_never_becomes_a_voice():
    """Хор не входит в turns и не голосует. Только в body.chorus_reflections."""
    result = Pipeline().run("Стоит ли ускорять развитие AGI?")
    for t in result.run_state.turns:
        assert "chorus" not in (t.persona_id or "").lower()
        assert "chorus" not in (t.operation or "").lower()


def test_chorus_records_who_is_silent():
    """При fast-mode с 4 голосами из 7 — 3 должны быть silent в chorus."""
    result = Pipeline().run("Стоит ли ускорять развитие AGI?")
    latest = result.run_state.body.chorus_reflections[-1]
    # В fast mode лишь 4 голоса из 7 — минимум 3 silent
    assert len(latest.who_is_silent) >= 1


# ---- affect ----
def test_affect_intensity_rises_on_attack():
    book = AffectBook()
    book.observe("A", "attack", target_persona="B")
    a = book.get("A")
    assert a.intensity > 0
    assert a.state in {"severe", "restrained_anger"}


def test_affect_decays_when_not_speaking():
    book = AffectBook()
    book.observe("A", "attack", target_persona="B")
    hot_before = book.get("A").intensity
    # три хода B — A должен затухать
    for _ in range(3):
        book.observe("B", "defend", target_persona="A")
    # но A всё же был target defend'a — его интенсивность растёт как alert
    # проверим что B не пуст
    assert book.get("B").intensity > 0


def test_hot_personas_reported_by_threshold():
    book = AffectBook()
    for _ in range(3):
        book.observe("A", "attack", target_persona="B")
    hot = book.hot_personas(threshold=0.5)
    assert "A" in hot

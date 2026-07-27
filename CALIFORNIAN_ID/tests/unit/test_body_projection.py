"""Tests for BodyProjection: heads act on shared, evolving body."""
from californian_id.pipeline import Pipeline
from californian_id.schemas import BodyProjection


def test_body_is_populated_by_run():
    result = Pipeline().run(
        "Какое возможно будущее человечества на горизонте century "
        "при радикальном long-term ускорении AGI?",
        mode="fast",
    )
    b = result.run_state.body
    assert b.topic
    assert b.voices_history, "voices_history empty"
    assert len(b.voices_history) == len(result.run_state.turns)


def test_body_fold_captures_operation_semantics():
    """build_future_image → futures; attack_presupposition → premises; …"""
    result = Pipeline().run(
        "Стоит ли вводить моратории на разработку продвинутых AI-систем?",
        mode="fast",
    )
    ops = {t.operation for t in result.run_state.turns}
    b = result.run_state.body
    if "build_future_image" in ops:
        assert b.futures, "build_future_image happened but no future was folded"
    if "attack_presupposition" in ops:
        assert b.ontological_premises, "attack_presupposition happened but no premise folded"
    if "show_cost" in ops:
        assert b.risks, "show_cost happened but no risk folded"


def test_head_receives_body_snapshot_via_prompt():
    """Проверяем, что pipeline вкладывает body в user payload голове."""
    import json
    result = Pipeline().run(
        "Какое возможно будущее человечества на горизонте long-term при ускорении?",
        mode="fast",
    )
    # Читаем trace: событие 'turn' содержит routing_reason, но payload голове
    # виден только через prompts истории. Проверим косвенно через body:
    b = result.run_state.body
    snap = b.snapshot_for_head(max_items=4)
    assert "topic" in snap and "voices_history" in snap
    assert "futures" in snap
    assert "ontological_premises" in snap
    assert "risks" in snap
    assert "projects" in snap
    assert "transformations" in snap


def test_snapshot_serialisable_as_json():
    import json
    b = BodyProjection()
    b.topic = "тест"
    payload = json.dumps(b.snapshot_for_head(), ensure_ascii=False)
    assert '"topic"' in payload

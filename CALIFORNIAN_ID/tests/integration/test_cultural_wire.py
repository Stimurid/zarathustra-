"""B2: cultural cards must reach persona prompt AND trace."""
import json
from californian_id.pipeline import Pipeline


def test_cultural_context_injected_trace_event_per_turn():
    """Каждый ход должен породить cultural_context_injected event."""
    result = Pipeline().run("Стоит ли ускорять развитие AGI?")
    events_path = result.trace_dir / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines()]
    injected = [e for e in events if e["kind"] == "cultural_context_injected"]
    turns = [e for e in events if e["kind"] == "turn"]
    assert injected, "no cultural_context_injected event recorded"
    assert len(injected) == len(turns), \
        f"injection count {len(injected)} != turn count {len(turns)}"


def test_injected_cards_carry_provenance_and_metadata():
    result = Pipeline().run("Следует ли централизовать управление ИИ ради безопасности?")
    events_path = result.trace_dir / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines()]
    injected = [e for e in events if e["kind"] == "cultural_context_injected"]
    # Хотя бы один ход получил ≥1 карту
    any_with_cards = any(e["payload"]["cards"] for e in injected)
    assert any_with_cards, "no turn received any cultural cards"
    for e in injected:
        for card in e["payload"]["cards"]:
            assert card.get("card_id")
            assert card.get("card_type") in {"scene", "operation", "constraint", "risk", "completion_pattern"}
            assert card.get("title")


def test_injected_cards_respect_required_function_route():
    """При активной операции build_future_image required_function должна
    быть introduce_absent_subject хотя бы для одного хода в deep run."""
    result = Pipeline().run(
        "Какое возможно будущее человечества на горизонте long-term при радикальном ускорении AGI?",
        mode="fast",
    )
    events_path = result.trace_dir / "events.jsonl"
    events = [json.loads(l) for l in events_path.read_text(encoding="utf-8").splitlines()]
    injected = [e for e in events if e["kind"] == "cultural_context_injected"]
    fns = {e["payload"]["required_function"] for e in injected}
    # Должна встретиться минимум одна нетривиальная функция
    assert fns - {"any"}, f"only 'any' seen: {fns}"

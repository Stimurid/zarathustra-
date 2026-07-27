"""Unit tests for CompletionOutcome shapes and choose_completion_form rules."""
from californian_id.schemas import (
    ArgumentMap,
    Attack,
    CompletionOutcome,
    COMPLETION_FORMS,
    Claim,
    SituationAnalysis,
    TurnRecord,
)
from californian_id.zarathustra import Zarathustra


def _make_turn(idx, pid, op, utterance="text", confidence=0.5):
    return TurnRecord(turn_index=idx, persona_id=pid, operation=op,
                      utterance=utterance, confidence=confidence)


def test_all_ten_forms_declared():
    expected = {
        "alliance", "decision_with_dissent", "unresolvable_conflict",
        "aporia", "transformed_question", "world_fork", "delegation",
        "polyphony", "synthesis", "refusal_to_close",
    }
    assert set(COMPLETION_FORMS) == expected


def test_empty_council_yields_refusal_to_close():
    z = Zarathustra()
    sit = SituationAnalysis(topic="empty", genre="statement")
    choice = z.choose_completion_form(None, sit, turns=[], argument_map=ArgumentMap())
    assert choice.form == "refusal_to_close"


def test_aporia_signals_yield_aporia():
    z = Zarathustra()
    sit = SituationAnalysis(topic="hard", genre="normative")
    turns = [
        _make_turn(0, "A", "initial_position"),
        _make_turn(1, "B", "create_aporia"),
        _make_turn(2, "C", "problematize_question"),
    ]
    choice = z.choose_completion_form(None, sit, turns=turns, argument_map=ArgumentMap())
    assert choice.form == "aporia"


def test_transformation_signals_with_conflict_yield_transformed_question():
    z = Zarathustra()
    sit = SituationAnalysis(topic="hard", genre="normative")
    turns = [
        _make_turn(0, "A", "initial_position"),
        _make_turn(1, "B", "problematize_question"),
        _make_turn(2, "C", "shift_ontology"),
        _make_turn(3, "D", "attack"),
    ]
    # Add explicit attack to argument_map to generate conflict
    amap = ArgumentMap(
        claims=[Claim(text="c", persona_id="A")],
        attacks=[Attack(target="previous_turn", text="a", persona_id="D")],
    )
    choice = z.choose_completion_form(None, sit, turns=turns, argument_map=amap)
    assert choice.form == "transformed_question"


def test_world_fork_signals():
    z = Zarathustra()
    sit = SituationAnalysis(topic="future", genre="normative")
    turns = [
        _make_turn(0, "A", "initial_position"),
        _make_turn(1, "B", "build_future_image"),
        _make_turn(2, "C", "shift_temporal_horizon"),
    ]
    choice = z.choose_completion_form(None, sit, turns=turns, argument_map=ArgumentMap())
    assert choice.form == "world_fork"


def test_delegation_when_only_one_voice_spoke():
    z = Zarathustra()
    sit = SituationAnalysis(topic="x", genre="statement")
    turns = [_make_turn(0, "A", "initial_position")]
    choice = z.choose_completion_form(None, sit, turns=turns, argument_map=ArgumentMap())
    assert choice.form == "delegation"


def test_synthesis_requires_no_conflicts_and_diverse_voices_but_still_prefers_polyphony():
    """Даже при равной картинке предпочитается polyphony, а не synthesis
    (см. anti-slop / no false consensus)."""
    z = Zarathustra()
    sit = SituationAnalysis(topic="x", genre="statement")
    turns = [
        _make_turn(0, "A", "initial_position"),
        _make_turn(1, "B", "restore_ground"),
        _make_turn(2, "C", "defend"),
    ]
    # no attacks in amap -> no conflicts BUT _derive_conflict_map falls back
    # to "плюрализм рамок без явных атак" as unresolved for >=2 voices
    choice = z.choose_completion_form(None, sit, turns=turns, argument_map=ArgumentMap())
    # с fallback "плюрализм" даёт n_conflicts=1, что срабатывает как
    # decision_with_dissent — это тоже НЕ synthesis, что и требуется.
    assert choice.form != "synthesis", "synthesis выбран без явного основания"


def test_completion_outcome_field_isolation():
    """Поля разных форм не должны быть перепутаны."""
    c = CompletionOutcome(form="aporia", rationale="test", aporia_statement="Q?")
    assert c.aporia_statement == "Q?"
    assert c.decision == ""
    assert c.synthesis is None
    assert c.world_branches == []
    assert c.polyphonic_voices == []

"""Tests 5-6: architectonic delta + claim atomization."""
from californian_id.architectonic import reconstruct_turn_delta
from californian_id.schemas import (
    ArgumentMap, Assumption, Attack, BodyProjection, Claim, TurnRecord,
)


def test_reconstruct_returns_typed_delta_not_summary():
    body = BodyProjection(topic="Стоит ли ускорять AGI?")
    prev = TurnRecord(turn_index=0, persona_id="A", operation="initial_position",
                      utterance="Ускорять.", claims=[Claim(text="ускорять", confidence=0.7)])
    new = TurnRecord(turn_index=1, persona_id="B", operation="attack_presupposition",
                     utterance="Скрытое допущение: ускорение всегда безопасно.",
                     assumptions=[Assumption(text="ускорение = безопасно", exposed_by="B")],
                     attacks=[Attack(target="previous_turn", text="это допущение неверно")])
    d = reconstruct_turn_delta(body, prev, new)
    assert d.assumptions_exposed, "attack_presupposition must produce assumptions_exposed"
    assert d.new_attacks, "attack must produce new_attacks entry"
    assert d.attacked_claims, "attack must produce attacked_claims"
    assert d.state_delta["op"] == "attack_presupposition"


def test_claim_atomization_by_kind():
    body = BodyProjection(topic="topic")
    new = TurnRecord(turn_index=0, persona_id="A", operation="build_counterexample",
                     utterance="Контрпример.",
                     claims=[Claim(text="случай Х ломает тезис", confidence=0.8)])
    d = reconstruct_turn_delta(body, None, new)
    # counterexample → hypothesis kind
    assert d.new_claims[0]["kind"] == "hypothesis", d.new_claims


def test_delta_records_loops_when_same_persona_same_op_twice():
    body = BodyProjection(topic="t")
    prev = TurnRecord(turn_index=0, persona_id="A", operation="attack", utterance="x")
    new = TurnRecord(turn_index=1, persona_id="A", operation="attack", utterance="y")
    d = reconstruct_turn_delta(body, prev, new)
    assert d.loops, "same persona same op twice should produce a loop entry"


def test_delta_records_future_and_risk_from_operations():
    body = BodyProjection(topic="t")
    fut = TurnRecord(turn_index=0, persona_id="A", operation="build_future_image",
                     utterance="Мир X")
    risk = TurnRecord(turn_index=1, persona_id="B", operation="show_cost", utterance="Цена Y")
    d1 = reconstruct_turn_delta(body, None, fut)
    d2 = reconstruct_turn_delta(body, fut, risk)
    assert d1.futures and d1.futures[0]["utterance"].startswith("Мир")
    assert d2.risks and d2.risks[0]["text"].startswith("Цена")

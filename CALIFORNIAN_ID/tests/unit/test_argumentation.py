"""Tests 7-9: thesis substitution, fallacy detection, dispute stopping + anti-slop."""
from californian_id.argumentation import (
    assess_turn, check_anti_slop, detect_fallacy_or_trick,
    detect_thesis_substitution,
)
from californian_id.schemas import (
    ArgumentMap, Attack, Claim, TurnRecord,
)


def _turn(idx, pid, op, utt="text", attacks=None, claims=None, supports=None):
    return TurnRecord(
        turn_index=idx, persona_id=pid, operation=op, utterance=utt,
        attacks=[Attack(**a) for a in (attacks or [])],
        claims=[Claim(**c) for c in (claims or [])],
    )


def test_thesis_substitution_flagged_when_attack_unrelated():
    turns = [
        _turn(0, "A", "initial_position", "Ускорять развитие AGI необходимо."),
        _turn(1, "B", "attack", "Погода в Лиссабоне переменчива.",
              attacks=[dict(target="previous_turn", text="погода в Лиссабоне переменчива")]),
    ]
    sub, reason = detect_thesis_substitution(turns)
    assert sub, reason


def test_no_thesis_substitution_when_shift_ontology_present():
    turns = [
        _turn(0, "A", "initial_position", "Ускорять AGI."),
        _turn(1, "C", "shift_ontology", "переопределить вопрос как вопрос о власти"),
        _turn(2, "B", "attack", "власть без демократии = захват",
              attacks=[dict(target="previous_turn", text="захват")]),
    ]
    sub, _ = detect_thesis_substitution(turns)
    assert not sub


def test_fallacy_detection_ad_hominem_and_appeal_to_majority():
    prior = [_turn(0, "A", "initial_position", "Тезис.")]
    turn = _turn(1, "B", "attack",
                 "Ты просто глупый лжец, и все согласны, что ты неправ.",
                 attacks=[dict(target="previous_turn", text="некомпетентно")])
    hits = detect_fallacy_or_trick(turn, prior)
    assert "ad_hominem" in hits
    assert "appeal_to_majority" in hits


def test_assess_turn_stops_on_high_severity_fallacy_repeat():
    prior = [
        _turn(0, "A", "initial_position", "Тезис."),
        _turn(1, "A", "defend", "Тезис верен, ибо тезис верен, ибо тезис верен."),
    ]
    turn = _turn(2, "A", "defend", "Тезис верен, ибо тезис верен, ибо тезис верен.")
    a = assess_turn(turn, prior, ArgumentMap())
    assert "proof_by_assertion" in a.fallacies_or_tricks
    assert a.continue_or_stop == "stop"


def test_anti_slop_blocks_synthesis_without_real_work():
    turns = [
        _turn(0, "A", "initial_position"),
        _turn(1, "B", "initial_position"),
        _turn(2, "C", "initial_position"),
    ]
    v = check_anti_slop("synthesis", turns, ArgumentMap())
    assert not v.passes_anti_slop
    assert v.suggested_alternative_form in {"polyphony", "decision_with_dissent"}


def test_anti_slop_allows_synthesis_when_real_work_done():
    turns = [
        _turn(0, "A", "initial_position"),
        _turn(1, "B", "attack_presupposition"),
        _turn(2, "A", "defend"),
        _turn(3, "C", "steelman_opponent"),
    ]
    v = check_anti_slop("synthesis", turns, ArgumentMap())
    assert v.passes_anti_slop

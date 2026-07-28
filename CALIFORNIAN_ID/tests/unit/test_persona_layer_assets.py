from __future__ import annotations

from collections import Counter

from californian_id.persona_layer import load_persona_layer_registry


def test_persona_layer_loads_eight_packages():
    reg = load_persona_layer_registry()
    assert not [i for i in reg.issues if i.severity == "error"], reg.issues
    assert set(reg.personas) == {"C", "T", "Ex", "S", "R", "EA", "L", "N8"}


def test_persona_layer_card_and_operation_counts_match_verified_assets():
    reg = load_persona_layer_registry()
    cards = [card for pkg in reg.personas.values() for card in pkg.cards]
    assert len(cards) == 529
    assert len({card.card_id for card in cards}) == 529
    ops = {
        str(op.get("operation_id"))
        for pkg in reg.personas.values()
        for op in pkg.operations
        if op.get("operation_id")
    }
    assert len(ops) == 141  # package discrepancy: N8 cards expose 29 exact ops, not 30


def test_no_active_seed_cards_in_runtime_packages():
    reg = load_persona_layer_registry()
    for pkg in reg.personas.values():
        seedish = [card.card_id for card in pkg.cards if "seed" in card.card_id.lower()]
        assert not seedish, (pkg.persona_id, seedish[:5])


def test_every_card_maps_to_exact_operation():
    reg = load_persona_layer_registry()
    unmapped = [card.card_id for pkg in reg.personas.values() for card in pkg.cards if not card.operation_id_exact]
    assert not unmapped, unmapped[:10]


def test_nemo8_namespace_counts_match_cards_index():
    reg = load_persona_layer_registry()
    n8 = reg.personas["N8"]
    counts = Counter(card.raw.get("namespace") for card in n8.cards)
    assert counts == {
        "N8_EVIDENCE": 42,
        "N8_CASES_AND_FAILURES": 4,
        "N8_SELF_HISTORY": 2,
        "N8_DONOR_OPERATIONS": 80,
        "N8_COUNTER_CANON": 36,
        "N8_RELATIONS": 35,
    }

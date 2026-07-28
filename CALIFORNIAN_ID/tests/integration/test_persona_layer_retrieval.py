from __future__ import annotations

from californian_id.cultural_rag import CulturalIndex
from californian_id.persona_layer import PersonaCouncilRuntime


def test_persona_layer_index_rebuilds():
    runtime = PersonaCouncilRuntime()
    manifest = runtime.index.rebuild(runtime.registry, "pytest-rebuild")
    assert manifest["card_count"] == 529
    assert manifest["personas"] == ["C", "EA", "Ex", "L", "N8", "R", "S", "T"]


def test_one_probe_per_persona_and_operation_filter():
    runtime = PersonaCouncilRuntime()
    runtime.ensure_index()
    expected = {
        "C": ("common task suffering discord", "C-OP02"),
        "T": ("morphological freedom enhancement autonomy", "T-OP05"),
        "Ex": ("experiments reversibility open systems", "EX-OP10"),
        "S": ("phase transition control intelligence", "S-OP02"),
        "R": ("calibration causal models uncertainty", "R-OP19"),
        "EA": ("effectiveness efficiency political world consequences", "EA-OP08"),
        "L": ("future lock in legitimacy generations", "L-OP05"),
        "N8": ("ability mandate authority legitimacy", "OP-N8-04"),
    }
    for persona_id, (query, op_id) in expected.items():
        hits = runtime.index.query(runtime.registry, query, persona_id=persona_id, top_k=3)
        assert hits, persona_id
        filtered = runtime.index.query(runtime.registry, query, persona_id=persona_id, operation_id_exact=op_id, top_k=3)
        assert filtered, (persona_id, op_id)
        assert all(hit.persona_id == persona_id for hit in filtered)
        assert all(hit.operation_id_exact == op_id for hit in filtered)


def test_retrieval_fallback_has_lexical_signal():
    runtime = PersonaCouncilRuntime()
    runtime.ensure_index()
    hits = runtime.index.query(runtime.registry, "ability mandate authority legitimacy", persona_id="N8", top_k=3)
    assert hits
    assert hits[0].lexical_score > 0


def test_restored_nemo8_operation_has_retrieval_link():
    runtime = PersonaCouncilRuntime()
    runtime.ensure_index()
    hits = runtime.index.query(
        runtime.registry,
        "awe decapture false proof motivational image",
        persona_id="N8",
        operation_id_exact="OP-N8-18",
        top_k=3,
    )
    assert hits
    assert any(hit.card_id == "N8-CC-019" for hit in hits)


def test_persona_namespace_isolation_is_enforced():
    runtime = PersonaCouncilRuntime()
    runtime.ensure_index()
    hits = runtime.index.query(
        runtime.registry,
        "effectiveness efficiency political world consequences",
        persona_id="EA",
        retrieval_namespace="persona.EA.canon",
        top_k=5,
    )
    assert hits
    assert all(hit.persona_id == "EA" for hit in hits)
    assert all(hit.retrieval_namespace == "persona.EA.canon" for hit in hits)


def test_cultural_rag_does_not_return_persona_cards():
    idx = CulturalIndex()
    cards, _event = idx.retrieve_cards("полифония", required_function="polyphony_at_completion", top_k=5)
    assert cards
    assert all(card.card_id.startswith("CARD_") for card in cards)
    assert all(not card.card_id.startswith("N8-") for card in cards)

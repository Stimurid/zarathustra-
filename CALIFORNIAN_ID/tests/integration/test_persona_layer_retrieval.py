from __future__ import annotations

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

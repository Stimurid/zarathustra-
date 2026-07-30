from californian_id.pipeline import _coerce_confidence


def test_coerce_confidence_accepts_semantic_labels():
    assert _coerce_confidence("high") == 0.85
    assert _coerce_confidence("strong") == 0.85
    assert _coerce_confidence("высокая") == 0.85
    assert _coerce_confidence("medium") == 0.5
    assert _coerce_confidence("средняя") == 0.5
    assert _coerce_confidence("low") == 0.25
    assert _coerce_confidence("weak") == 0.25
    assert _coerce_confidence("низкая") == 0.25


def test_coerce_confidence_clamps_and_parses_numbers():
    assert _coerce_confidence("0.8") == 0.8
    assert _coerce_confidence("85") == 0.85
    assert _coerce_confidence(2) == 1.0
    assert _coerce_confidence(-1) == 0.0


def test_coerce_confidence_falls_back_for_unknown_values():
    assert _coerce_confidence("unclear") == 0.5
    assert _coerce_confidence(None, default=0.3) == 0.3


def test_norm_list_normalizes_nested_confidence():
    from californian_id.pipeline import _norm_list

    result = _norm_list(
        [{"text": "claim", "confidence": "strong", "source": "x"}],
        {"text", "confidence", "source"},
    )

    assert result == [{"text": "claim", "confidence": 0.85, "source": "x"}]

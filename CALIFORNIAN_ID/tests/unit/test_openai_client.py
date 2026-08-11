from californian_id.models.openai_client import _strip_internal


def test_strip_internal_whitelist_and_normalize():
    """Whitelist фильтрация: SDK params нормализуются, prompt-context дропается."""
    cleaned = _strip_internal({
        "temperature": "high",       # invalid float → drop
        "top_p": "0.8",              # → float 0.8
        "presence_penalty": 0,       # → 0.0
        "frequency_penalty": "bad",  # invalid → drop
        "max_tokens": "2048",        # → int 2048
        "seed": "42",                # → int 42
        "role": "persona_turn",      # prompt-context → drop
        "custom_label": "keep-me",   # НЕ в whitelist → drop
        "dialogue_protocol": "socratic",  # prompt-context (fix из v0.10.2)
        "has_position_model": True,       # prompt-context
        "genre": "aporia",                # prompt-context
    })
    assert cleaned == {
        "top_p": 0.8,
        "presence_penalty": 0.0,
        "max_tokens": 2048,
        "seed": 42,
    }


def test_strip_internal_drops_dialogue_protocol_and_similar():
    """Регрессия v0.10.2 bug: dialogue_protocol не должен попасть в SDK."""
    cleaned = _strip_internal({
        "temperature": 0.7,
        "dialogue_protocol": "socratic",
        "has_position_model": True,
        "genre": "methodological",
    })
    assert "dialogue_protocol" not in cleaned
    assert "has_position_model" not in cleaned
    assert "genre" not in cleaned
    assert cleaned == {"temperature": 0.7}

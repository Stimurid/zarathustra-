from californian_id.models.openai_client import _strip_internal


def test_strip_internal_drops_invalid_float_settings():
    cleaned = _strip_internal({
        "temperature": "high",
        "top_p": "0.8",
        "presence_penalty": 0,
        "frequency_penalty": "bad",
        "max_tokens": "2048",
        "seed": "42",
        "role": "persona_turn",
        "custom_label": "keep-me",
    })

    assert cleaned == {
        "top_p": 0.8,
        "presence_penalty": 0.0,
        "max_tokens": 2048,
        "seed": 42,
        "custom_label": "keep-me",
    }

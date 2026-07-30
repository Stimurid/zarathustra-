from californian_id.pipeline import Pipeline


def test_pipeline_applies_separate_role_token_overrides():
    pipe = Pipeline(
        voice_max_tokens_override=768,
        closing_max_tokens_override=1536,
    )

    _, persona_cfg = pipe._role_and_cfg("persona_turn")
    _, closing_cfg = pipe._role_and_cfg("zarathustra_closing_speech")

    assert persona_cfg["settings"]["max_tokens"] == 768
    assert closing_cfg["settings"]["max_tokens"] == 1536


def test_pipeline_falls_back_to_global_max_tokens_override():
    pipe = Pipeline(max_tokens_override=2048)

    _, persona_cfg = pipe._role_and_cfg("persona_turn")
    _, closing_cfg = pipe._role_and_cfg("zarathustra_closing_speech")

    assert persona_cfg["settings"]["max_tokens"] == 2048
    assert closing_cfg["settings"]["max_tokens"] == 2048


def test_pipeline_applies_max_turns_override_to_mode_config():
    pipe = Pipeline(max_turns_override=3)

    mode_cfg = pipe._mode_cfg("deep")

    assert mode_cfg["max_turns"] == 3

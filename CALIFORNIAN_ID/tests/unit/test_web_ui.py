from californian_id.web_ui import (
    LAYER_CALIFORNIAN_ID,
    LAYER_PERSONA,
    run_web_request,
)


def test_web_ui_defaults_to_persona_layer():
    payload = run_web_request(
        "Need a Bayesian calibration update for a causal forecast.",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["runtime_layer"] == LAYER_PERSONA
    assert payload["persona_layer"]["cast_mode"] == "single_head"
    assert payload["persona_layer"]["call_nemo8"] is False


def test_web_ui_persona_layer_accepts_semantic_units():
    payload = run_web_request(
        """mode: semantic_units
run_id: web-ui-semantic
units:
  - unit_id: u-1
    text: We need to distinguish speed from controllability.
    speaker: Speaker 1
    source_refs: ["char:0-47"]
    semantic_types: [distinction, governance]
  - unit_id: u-2
    text: Acceleration without a frame increases error cost.
    speaker: Speaker 2
    source_refs: ["char:48-101"]
    semantic_types: [risk, governance]
metadata:
  title: AGI governance notes
""",
        runtime_layer=LAYER_PERSONA,
        input_mode="semantic-units",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["runtime_layer"] == LAYER_PERSONA
    assert payload["ingress_mode"] == "semantic_units"
    assert payload["persona_layer"]["unit_count"] == 2


def test_web_ui_runner_accepts_auto_slice_mode_for_californian_id():
    payload = run_web_request(
        "User: Стоит ли ускорять развитие AGI?\nAnalyst: Только с рамкой управления.",
        runtime_layer=LAYER_CALIFORNIAN_ID,
        input_mode="auto-slice",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["runtime_layer"] == LAYER_CALIFORNIAN_ID
    assert payload["input_mode"] == "auto-slice"
    assert payload["ingress_mode"] == "raw_stream"


def test_web_ui_runner_text_mode_returns_plain_text_body():
    payload = run_web_request(
        "Стоит ли ускорять развитие AGI?",
        runtime_layer=LAYER_CALIFORNIAN_ID,
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
        output_format="text",
    )
    assert payload["format"] == "text"
    assert isinstance(payload["body"], str) and payload["body"].strip()
    assert "--- meta ---" not in payload["body"]
    assert "meta" in payload


def test_web_ui_runner_accepts_separate_token_limits_and_max_turns():
    payload = run_web_request(
        "Стоит ли ускорять развитие AGI?",
        runtime_layer=LAYER_CALIFORNIAN_ID,
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
        voice_max_tokens=768,
        closing_max_tokens=1536,
        max_turns=2,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["voice_max_tokens"] == 768
    assert payload["closing_max_tokens"] == 1536
    assert payload["max_turns"] == 2


def test_web_ui_persona_layer_text_mode_can_surface_nemo8_trace():
    payload = run_web_request(
        (
            "Mandatory cognitive enhancement, AI-assisted R&D, concentrated compute and biometric data, "
            "and a century-long governance charter must balance efficiency, autonomy, reversibility, "
            "common task and intergenerational legitimacy."
        ),
        runtime_layer=LAYER_PERSONA,
        mode="deep",
        critique_regime="balanced",
        variation_regime="normal",
        debug=True,
        output_format="text",
    )
    assert payload["format"] == "text"
    assert payload["meta"]["runtime_layer"] == LAYER_PERSONA
    assert payload["meta"]["persona_layer"]["nemo8_used"] is True

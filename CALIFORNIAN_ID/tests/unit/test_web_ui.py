from californian_id import web_ui
from californian_id.web_ui import (
    LAYER_CALIFORNIAN_ID,
    LAYER_PERSONA,
    run_web_request,
)


def test_web_ui_defaults_to_persona_layer():
    web_ui._run_persona_layer_request = lambda **kwargs: {
        "status": "COMPLETED",
        "runtime_layer": LAYER_PERSONA,
        "persona_layer": {"cast_mode": "single_head", "call_nemo8": False},
        "completion": {"form": "persona_layer_llm_final_synthesis"},
        "closing_speech": "ok",
        "voices_used": ["R"],
        "turn_count": 1,
    }
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
    web_ui._run_persona_layer_request = lambda **kwargs: {
        "status": "COMPLETED",
        "runtime_layer": LAYER_PERSONA,
        "ingress_mode": "semantic_units",
        "persona_layer": {"unit_count": 2},
        "completion": {"form": "persona_layer_llm_final_synthesis"},
        "closing_speech": "ok",
        "voices_used": ["R"],
        "turn_count": 1,
    }
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
    web_ui._run_persona_layer_request = lambda **kwargs: {
        "runtime_layer": LAYER_PERSONA,
        "status": "COMPLETED",
        "completion": {"form": "persona_layer_llm_final_synthesis"},
        "closing_speech": "final speech",
        "voices_used": ["C", "N8"],
        "turn_count": 2,
        "persona_layer": {"nemo8_used": True},
        "turns": [],
    }
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


def test_web_ui_passes_council_span_to_persona_layer():
    captured = {}

    def fake_persona_runner(**kwargs):
        captured.update(kwargs)
        return {
            "status": "COMPLETED",
            "runtime_layer": LAYER_PERSONA,
            "persona_layer": {"cast_mode": "forced_pair", "call_nemo8": False, "council_span": "force_pair"},
            "completion": {"form": "persona_layer_llm_final_synthesis"},
            "closing_speech": "ok",
            "voices_used": ["T", "EA"],
            "turn_count": 2,
        }

    web_ui._run_persona_layer_request = fake_persona_runner
    payload = run_web_request(
        "Preserve autonomy while maximizing efficiency.",
        runtime_layer=LAYER_PERSONA,
        council_span="force_pair",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )

    assert payload["status"] == "COMPLETED"
    assert captured["council_span"] == "force_pair"


def test_web_ui_text_mode_can_show_orchestration_trace_without_debug():
    web_ui._run_persona_layer_request = lambda **kwargs: {
        "runtime_layer": LAYER_PERSONA,
        "status": "COMPLETED",
        "completion": {"form": "persona_layer_llm_final_synthesis"},
        "closing_speech": "final speech",
        "voices_used": ["T", "EA", "N8"],
        "turn_count": 3,
        "persona_layer": {"nemo8_used": True, "council_span": "force_triangular"},
        "orchestration_trace": {
            "council_span": "force_triangular",
            "cast_mode": "forced_triangular",
            "selected_persona_ids": ["T", "EA", "R"],
            "execution_order": ["T", "EA", "R"],
            "nemo8_used": True,
            "reopened_persona_ids": ["EA"],
            "reopen_decision": {"accepted": True, "reason": "false_consensus_risk"},
            "rationale": "UI forced a 3-head council span using the strongest topical matches.",
        },
    }
    payload = run_web_request(
        "Need a sharper council read on autonomy, efficiency, and evidence quality.",
        runtime_layer=LAYER_PERSONA,
        mode="deep",
        critique_regime="balanced",
        variation_regime="normal",
        show_orchestration_trace=True,
        debug=False,
        output_format="text",
    )

    assert payload["format"] == "text"
    assert "--- orchestration trace ---" in payload["body"]
    assert "force_triangular" in payload["body"]
    assert payload["meta"]["orchestration_trace"]["cast_mode"] == "forced_triangular"


def test_semantic_units_falls_back_to_llm_adapter(monkeypatch):
    class FakePipe:
        def run(self, *, text, mode, critique_regime, variation_regime):
            return {
                "text": text,
                "mode": mode,
                "critique_regime": critique_regime,
                "variation_regime": variation_regime,
            }

    monkeypatch.setattr(web_ui, "parse_md_units_text", lambda text: (_ for _ in ()).throw(ValueError("bad format")))
    monkeypatch.setattr(web_ui, "_adapt_semantic_units_text_via_llm", lambda pipe, text: "adapted semantic scene")

    result, ingress_mode = web_ui._run_semantic_units_request(
        FakePipe(),
        text="Claim: ... Warrant: ...",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
    )

    assert ingress_mode == "semantic_units_llm_adapter"
    assert result["text"] == "adapted semantic scene"


def test_persona_layer_semantic_units_fallback_reuses_request_pipeline(monkeypatch):
    captured = {}

    class FakePipe:
        def __init__(self, **kwargs):
            self.preset_override = kwargs.get("preset_override")
            self.model_override = kwargs.get("model_override")
            self.voice_max_tokens_override = kwargs.get("voice_max_tokens_override")
            self.closing_max_tokens_override = kwargs.get("closing_max_tokens_override")

    monkeypatch.setattr(web_ui, "Pipeline", FakePipe)
    monkeypatch.setattr(web_ui, "_pack_from_semantic_units", lambda text: (_ for _ in ()).throw(ValueError("bad format")))

    def fake_adapter(pipe, text):
        captured["preset"] = pipe.preset_override
        captured["model"] = pipe.model_override
        return "adapted semantic scene"

    monkeypatch.setattr(web_ui, "_adapt_semantic_units_text_via_llm", fake_adapter)
    scene, ingress_mode, unit_count = web_ui._scene_from_web_input(
        text="Claim: ... Warrant: ...",
        input_mode="semantic-units",
        pipe=FakePipe(preset_override="prod", model_override="gpt-4.1"),
    )

    assert scene == "adapted semantic scene"
    assert ingress_mode == "semantic_units_llm_adapter"
    assert unit_count == 0
    assert captured == {"preset": "prod", "model": "gpt-4.1"}


def test_semantic_axes_are_stabilized_for_multihead_routing():
    text = web_ui._stabilize_semantic_axes("Ключевой вопрос касается цены тезиса и границы допустимого движения вперед.")
    lowered = text.lower()
    assert "человеческой жизни" in lowered
    assert "моральный статус" in lowered
    assert "институциональную власть" in lowered
    assert "свободу" in lowered
    assert "межпоколенческие" in lowered


def test_api_access_payload_never_exposes_upstream_secrets():
    payload = web_ui._build_api_access_payload()

    assert payload["access_mode"] == "not_issued"
    assert payload["provider"] is None
    assert payload["base_url"] is None
    assert payload["api_key"] is None
    assert payload["suggested_models"] == []


def test_api_access_payload_returns_dedicated_compat_key(monkeypatch):
    monkeypatch.setenv("TINKUY_COMPAT_API_KEY", "tk-test-compat")
    payload = web_ui._build_api_access_payload()

    assert payload["access_mode"] == "tinkuy_compat_issued"
    assert payload["provider"] == "tinkuy_openai_compatible"
    assert payload["base_url"] == "https://tinkuy.mindkampf.ru/v1"
    assert payload["api_key"] == "tk-test-compat"
    assert "tinkuy-persona-fast" in payload["suggested_models"]


def test_run_compat_chat_completion_uses_model_alias(monkeypatch):
    captured = {}

    def fake_run_web_request(**kwargs):
        captured.update(kwargs)
        return {"body": "compat answer"}

    monkeypatch.setattr(web_ui, "run_web_request", fake_run_web_request)
    result = web_ui._run_compat_chat_completion({
        "model": "tinkuy-persona-roast",
        "messages": [
            {"role": "system", "content": "Be sharp."},
            {"role": "user", "content": "Analyze this thesis."},
        ],
        "max_tokens": 512,
    })

    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == "compat answer"
    assert captured["runtime_layer"] == LAYER_PERSONA
    assert captured["assembly_mode"] == "roast"
    assert captured["preset"] == "reasoning"

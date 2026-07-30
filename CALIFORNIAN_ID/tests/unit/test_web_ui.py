from californian_id.web_ui import run_web_request


def test_web_ui_runner_returns_completion_payload():
    payload = run_web_request(
        "Стоит ли ускорять развитие AGI?",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["completion"] is not None
    assert payload["regimes"]["critique_regime"] == "balanced"
    assert payload["regimes"]["variation_regime"] == "normal"
    assert payload["ingress_mode"] == "legacy_raw"


def test_web_ui_runner_accepts_md_semantic_units_mode():
    units_text = """# Demo Pack

### U1 - Test unit
- Намерение: Проверить вход units
- Объект/аспект: AGI governance
- Участники/роли внутри ЕС: Докладчик

Тема-Рема
- Тема: AGI | Рема: governance

Абстракт ЕС
Нужно понять, как обсуждать управление AGI.
"""
    payload = run_web_request(
        units_text,
        input_mode="semantic-units",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["input_mode"] == "semantic-units"
    assert payload["ingress_mode"] == "semantic_units"


def test_web_ui_runner_accepts_auto_slice_mode():
    payload = run_web_request(
        "User: Стоит ли ускорять развитие AGI?\nAnalyst: Только с рамкой управления.",
        input_mode="auto-slice",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["input_mode"] == "auto-slice"
    assert payload["ingress_mode"] == "raw_stream"


def test_web_ui_runner_accepts_canonical_semantic_units_yaml():
    payload = run_web_request(
        """mode: semantic_units
run_id: web-ui-semantic
units:
  - unit_id: u-1
    text: Нужно различить скорость и управляемость.
    speaker: Speaker 1
    source_refs: ["char:0-41"]
    semantic_types: [distinction, governance]
  - unit_id: u-2
    text: Ускорение без рамки создаёт цену ошибки.
    speaker: Speaker 2
    source_refs: ["char:42-83"]
    semantic_types: [risk, governance]
metadata:
  title: AGI governance notes
""",
        input_mode="semantic-units",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["input_mode"] == "semantic-units"
    assert payload["ingress_mode"] == "semantic_units"


def test_web_ui_runner_text_mode_returns_plain_text_body():
    payload = run_web_request(
        "Стоит ли ускорять развитие AGI?",
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


def test_web_ui_runner_accepts_separate_token_limits():
    payload = run_web_request(
        "Стоит ли ускорять развитие AGI?",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
        voice_max_tokens=768,
        closing_max_tokens=1536,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["voice_max_tokens"] == 768
    assert payload["closing_max_tokens"] == 1536

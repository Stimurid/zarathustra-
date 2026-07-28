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


def test_web_ui_runner_accepts_units_mode():
    units_text = """# Demo Pack

### U1 — Тестовый блок
- Заголовок: Тест
- Намерение: Проверить вход units
- Объект: AGI governance
- Участники: Докладчик
- Позиция: Нужна рамка
- Тема: AGI | Рема: governance
- Провенанс: source=test

Абстракт:
Нужно понять, как обсуждать управление AGI.
"""
    payload = run_web_request(
        units_text,
        input_mode="units",
        mode="fast",
        critique_regime="balanced",
        variation_regime="normal",
        debug=False,
    )
    assert payload["status"] == "COMPLETED"
    assert payload["input_mode"] == "units"

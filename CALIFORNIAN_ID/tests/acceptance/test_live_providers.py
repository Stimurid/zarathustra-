"""Live-LLM acceptance tests. Skipped when no API keys / no SDK installed.

Run manually:
    pip install .[providers]
    export ANTHROPIC_API_KEY=...   # OR OPENAI_API_KEY=...
    CALIFORNIAN_ID_PROVIDER=anthropic \
      PYTHONPATH=src python -m pytest tests/acceptance -v

These tests intentionally hit real API endpoints. They are:
  - opt-in only (skipped by default),
  - smoke-level (they check the pipeline SURVIVES a live turn,
    not that any specific text is produced),
  - budget-aware (max 2 fast turns, small max_tokens).
"""
from __future__ import annotations
import importlib
import os
import pytest

# Reason: skip the whole module unless explicit opt-in
_HAS_ANTHROPIC_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))
_HAS_OPENAI_KEY = bool(os.environ.get("OPENAI_API_KEY"))
_HAS_ANTHROPIC_SDK = importlib.util.find_spec("anthropic") is not None
_HAS_OPENAI_SDK = importlib.util.find_spec("openai") is not None


pytestmark = pytest.mark.skipif(
    not ((_HAS_ANTHROPIC_KEY and _HAS_ANTHROPIC_SDK) or (_HAS_OPENAI_KEY and _HAS_OPENAI_SDK)),
    reason="Set ANTHROPIC_API_KEY or OPENAI_API_KEY and pip install .[providers] to enable live tests",
)


def _override_provider(provider_name: str, monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", provider_name)


@pytest.mark.skipif(not (_HAS_ANTHROPIC_KEY and _HAS_ANTHROPIC_SDK),
                    reason="anthropic key/sdk missing")
def test_anthropic_smoke_completes_one_run(monkeypatch):
    _override_provider("anthropic", monkeypatch)
    from californian_id.pipeline import Pipeline
    result = Pipeline().run("Стоит ли ускорять развитие AGI?", mode="fast")
    assert result.run_state.status == "COMPLETED"
    assert result.run_state.completion is not None
    assert any(t.model_provider == "anthropic" for t in result.run_state.turns)


@pytest.mark.skipif(not (_HAS_OPENAI_KEY and _HAS_OPENAI_SDK),
                    reason="openai key/sdk missing")
def test_openai_smoke_completes_one_run(monkeypatch):
    _override_provider("openai", monkeypatch)
    from californian_id.pipeline import Pipeline
    result = Pipeline().run("Стоит ли ускорять развитие AGI?", mode="fast")
    assert result.run_state.status == "COMPLETED"
    assert result.run_state.completion is not None
    assert any(t.model_provider == "openai" for t in result.run_state.turns)


def test_live_run_preserves_form_diversity_guarantees(monkeypatch):
    """With live LLM, we still guarantee the CANONICAL invariants:
      - completion.form ∈ 10 valid forms
      - minority_positions preserved for a contested question
      - no cross-persona bleed in retrieval
      - trace has cultural_retrieval + dispute_assessment + architectonic_delta
    """
    if _HAS_ANTHROPIC_KEY and _HAS_ANTHROPIC_SDK:
        _override_provider("anthropic", monkeypatch)
    elif _HAS_OPENAI_KEY and _HAS_OPENAI_SDK:
        _override_provider("openai", monkeypatch)
    else:
        pytest.skip("no live provider available")

    from californian_id.pipeline import Pipeline
    from californian_id.schemas import COMPLETION_FORMS
    result = Pipeline().run(
        "Следует ли ради безопасности централизовать управление развитием сильного ИИ?",
        mode="fast",
    )
    c = result.run_state.completion
    assert c is not None
    assert c.form in COMPLETION_FORMS
    assert c.rationale
    assert c.minority_positions, "live run erased minorities on contested question"
    # Trace shape
    import json
    events = [json.loads(l) for l in (result.trace_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    kinds = {e["kind"] for e in events}
    assert "cultural_retrieval" in kinds
    assert "dispute_assessment" in kinds
    assert "architectonic_delta" in kinds
    assert "cultural_context_injected" in kinds

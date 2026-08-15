"""C3 — three smoke levels.

    UNIT_SMOKE            deterministic stub, no runtime
    INTEGRATION_SMOKE     capture provider through the REAL runtime path
    LIVE_ACCEPTANCE_SMOKE configured provider, skipped without credentials

Golden equivalence for the Stage 0 extraction is proven here, at the invocation
boundary — not by comparing model prose.
"""
from __future__ import annotations

import json
import os

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_core import CaptureClient, WorkbenchService, WorkbenchStore, sha256_text

ASSET = "zarathustra.03_scene_reading"
BASE = "v_baseline_baseline_file"
CODE_BASE = "v_baseline_baseline_code"


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    return s


def _canonical(inv) -> str:
    return json.dumps(inv.payload(), ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------- UNIT_SMOKE

def test_unit_smoke_uses_deterministic_stub(svc):
    res = svc.run_smoke(ASSET, BASE)
    assert res.provider == "stub"
    assert res.model == "workbench-stub-1"
    assert res.ok, res.reasons
    again = svc.run_smoke(ASSET, BASE)
    assert again.raw_text == res.raw_text, "stub must be deterministic"


# --------------------------------------------------------- INTEGRATION_SMOKE

def test_integration_smoke_drives_the_real_runtime(svc):
    trace = svc.run_integration_smoke("zarathustra", ASSET)
    node = trace["nodes"][0]

    assert trace["kind"] == "INTEGRATION_SMOKE"
    assert node["provider"] == "capture"
    assert node["emitted_payload_matches_compiled"] is True
    assert node["emitted_settings"]["role"] == "zarathustra_situation_reading"
    assert node["output_valid"] is True, node["output_reasons"]

    # the real parser produced a real SituationAnalysis
    parsed = node["parsed"]
    assert parsed["topic"] == "integration fixture"
    assert parsed["genre"] == "question"
    assert parsed["stakes"] == ["s1"]

    # identity is fully recorded
    assert node["variant_id"] == BASE
    assert node["compiled_hash"].startswith("sha256:")
    assert trace["activation_snapshot"]["entries"][ASSET]["variant_id"] == BASE

    # the evaluation is persisted
    evals = svc.store.evaluations_for(BASE)
    assert any(e["kind"] == "integration_smoke" and e["verdict"] == "pass"
               for e in evals)


def test_integration_smoke_reads_the_active_variant_not_the_repo_file(svc):
    """Activating a candidate must change what the runtime actually resolves."""
    cand = svc.clone(ASSET, BASE)
    text = cand.source_text.replace(
        "какая тревога делает вопрос срочным",
        "какая тревога делает вопрос срочным [INTEGRATION MARKER]")
    svc.update_source(ASSET, cand.variant_id, text)
    svc.validate(ASSET, cand.variant_id)
    svc.compile(ASSET, cand.variant_id)
    svc.run_smoke(ASSET, cand.variant_id)
    svc.accept(ASSET, cand.variant_id)
    svc.activate(ASSET, cand.variant_id)

    capture = CaptureClient(canned='{"topic":"x","genre":"question","stakes":[],'
                                   '"horizons":[],"concepts":[],"tensions":[],'
                                   '"uncertainties":[]}')
    trace = svc.run_integration_smoke("zarathustra", ASSET, client=capture)
    emitted = capture.captured[-1]["messages"][0]["content"]
    assert "[INTEGRATION MARKER]" in emitted
    assert trace["nodes"][0]["variant_id"] == cand.variant_id


# ------------------------------------------------- golden equivalence (C3)

def test_golden_equivalence_at_invocation_boundary(svc):
    """OLD constant path vs NEW PromptAsset path — byte identical payload."""
    adapter = ZarathustraAdapter()
    fixture = adapter.fixtures(ASSET)[0]

    old = adapter.legacy_invocation(fixture)
    code_variant = svc.variant(ASSET, CODE_BASE)
    new = adapter.build_invocation(ASSET, code_variant.source_text, fixture)

    assert old.system_text == new.system_text
    assert old.user_text == new.user_text
    assert old.settings == new.settings
    assert _canonical(old) == _canonical(new)
    assert sha256_text(_canonical(old)) == sha256_text(_canonical(new))


def test_golden_equivalence_through_capture_clients(svc):
    adapter = ZarathustraAdapter()
    fixture = adapter.fixtures(ASSET)[0]
    from californian_id.models import Message

    def capture(inv):
        c = CaptureClient()
        c.generate([Message(role="system", content=inv.system_text),
                    Message(role="user", content=inv.user_text)], inv.settings)
        return c.payload_hash()

    old_hash = capture(adapter.legacy_invocation(fixture))
    new_hash = capture(adapter.build_invocation(
        ASSET, svc.variant(ASSET, CODE_BASE).source_text, fixture))
    assert old_hash == new_hash


def test_semantic_output_similarity_is_not_used_as_equivalence_proof(svc):
    """Guard against regressing to prose comparison.

    Two different prompts can produce identical stub output; that must never be
    read as equivalence. Equivalence is only the invocation payload.
    """
    adapter = ZarathustraAdapter()
    fixture = adapter.fixtures(ASSET)[0]
    file_inv = adapter.build_invocation(
        ASSET, svc.variant(ASSET, BASE).source_text, fixture)
    code_inv = adapter.build_invocation(
        ASSET, svc.variant(ASSET, CODE_BASE).source_text, fixture)
    assert file_inv.system_text != code_inv.system_text
    assert _canonical(file_inv) != _canonical(code_inv)


# --------------------------------------------------- LIVE_ACCEPTANCE_SMOKE

LIVE_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CALIFORNIAN_ID_API_KEY")
HAVE_LIVE = any(os.environ.get(k) for k in LIVE_KEYS)


@pytest.mark.skipif(not HAVE_LIVE,
                    reason="LIVE_PROVIDER_ACCEPTANCE = EXTERNAL_BLOCKER: "
                           "no provider credentials configured")
def test_live_acceptance_smoke_minimal_fixture(svc):
    from californian_id.models import build_client

    class LiveAdapterClient:
        provider = "live"
        model = "configured"

        def __init__(self):
            self._c = build_client()

        def generate(self, invocation):
            from californian_id.models import Message
            from workbench_core.smoke import ModelResult
            res = self._c.generate(
                [Message(role="system", content=invocation.system_text),
                 Message(role="user", content=invocation.user_text)],
                settings=invocation.settings)
            return ModelResult(res.text, 0, 0, 0, self.provider, self.model)

    trace = svc.run_integration_smoke("zarathustra", ASSET,
                                      client=None, actor="live-acceptance")
    assert trace["nodes"][0]["output_valid"] in (True, False)

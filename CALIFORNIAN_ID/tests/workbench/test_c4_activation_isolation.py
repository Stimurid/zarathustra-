"""C4 — activation / cache / run-snapshot integration.

Proves the external invariant end to end, not the internal mechanism: a run that
has started never changes its prompt binding because someone activated another
variant while it was alive. The capture provider confirms the *actually emitted*
payload for both runs.
"""
from __future__ import annotations

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_core import SmokeHarness, WorkbenchService, WorkbenchStore
from workbench_core.smoke import ModelResult

ASSET = "zarathustra.03_scene_reading"
BASE = "v_baseline_baseline_file"


class RecordingProvider:
    """Captures every invocation payload actually handed to the model boundary."""

    provider = "capture"
    model = "capture-1"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(self, invocation) -> ModelResult:
        self.calls.append({
            "system": invocation.system_text,
            "user": invocation.user_text,
            "settings": dict(invocation.settings),
        })
        # A contract-shaped answer so downstream validation stays meaningful.
        return ModelResult(
            text='{"topic":"t","genre":"question","stakes":[],"horizons":[],'
                 '"concepts":[],"tensions":[],"uncertainties":[]}',
            latency_ms=1, tokens_in=10, tokens_out=10,
            provider=self.provider, model=self.model)


@pytest.fixture()
def svc(tmp_path):
    provider = RecordingProvider()
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"), SmokeHarness(provider))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    s.provider = provider          # test handle
    return s


def _accepted(svc, marker: str):
    cand = svc.clone(ASSET, BASE)
    text = cand.source_text.replace(
        "какая тревога делает вопрос срочным",
        f"какая тревога делает вопрос срочным [{marker}]")
    assert text != cand.source_text
    svc.update_source(ASSET, cand.variant_id, text)
    svc.validate(ASSET, cand.variant_id)
    svc.compile(ASSET, cand.variant_id)
    svc.run_smoke(ASSET, cand.variant_id)
    svc.accept(ASSET, cand.variant_id)
    return svc.variant(ASSET, cand.variant_id)


def test_run_keeps_its_activation_snapshot_when_activation_changes(svc):
    variant_a = _accepted(svc, "A")
    svc.activate(ASSET, variant_a.variant_id, "operator")
    revision_n = svc.store.activation_revision()

    # ---- R1 under variant A --------------------------------------------
    svc.provider.calls.clear()
    r1 = svc.start_run("zarathustra", ASSET)
    r1_node = r1["nodes"][0]
    assert r1_node["variant_id"] == variant_a.variant_id
    assert r1_node["source_hash"] == variant_a.source_hash
    assert r1["activation_snapshot"]["activation_revision"] == revision_n
    r1_payload = svc.provider.calls[-1]["system"]
    assert "[A]" in r1_payload
    r1_compiled = r1_node["compiled_hash"]

    # ---- activate B while R1's record is alive -------------------------
    variant_b = _accepted(svc, "B")
    svc.activate(ASSET, variant_b.variant_id, "operator")
    assert svc.store.activation_revision() == revision_n + 1

    # R1's persisted trace is untouched
    persisted = svc.store.read_run(r1["run_id"])
    assert persisted["nodes"][0]["variant_id"] == variant_a.variant_id
    assert persisted["nodes"][0]["compiled_hash"] == r1_compiled
    assert persisted["activation_snapshot"]["activation_revision"] == revision_n

    # ---- R2 under variant B --------------------------------------------
    svc.provider.calls.clear()
    r2 = svc.start_run("zarathustra", ASSET)
    r2_node = r2["nodes"][0]
    assert r2_node["variant_id"] == variant_b.variant_id
    assert r2_node["source_hash"] == variant_b.source_hash
    assert r2_node["compiled_hash"] != r1_compiled
    assert r2["activation_snapshot"]["activation_revision"] == revision_n + 1
    r2_payload = svc.provider.calls[-1]["system"]
    assert "[B]" in r2_payload and "[A]" not in r2_payload


def test_capture_provider_confirms_emitted_payload_matches_trace(svc):
    variant_a = _accepted(svc, "A")
    svc.activate(ASSET, variant_a.variant_id)
    svc.provider.calls.clear()
    run = svc.start_run("zarathustra", ASSET)
    emitted = svc.provider.calls[-1]
    stored = svc.variant(ASSET, run["nodes"][0]["variant_id"])
    assert emitted["system"] == stored.source_text
    assert emitted["settings"]["role"] == "zarathustra_situation_reading"


def test_cache_identity_changes_with_every_dimension(svc):
    v = svc.variant(ASSET, BASE)
    k0 = svc.cache_key(ASSET, v, "tinkuy.zarathustra.lazy").as_str()

    # different compiler profile
    k_profile = svc.cache_key(ASSET, v, "other.profile").as_str()
    assert k_profile != k0

    # different variant / source hash
    cand = svc.clone(ASSET, BASE)
    cand = svc.update_source(ASSET, cand.variant_id,
                             cand.source_text.replace("срочным", "срочным сейчас"))
    k_variant = svc.cache_key(ASSET, cand, "tinkuy.zarathustra.lazy").as_str()
    assert k_variant != k0
    assert cand.source_hash not in k0

    # different activation revision
    a = _accepted(svc, "A")
    svc.activate(ASSET, a.variant_id)
    k_rev = svc.cache_key(ASSET, v, "tinkuy.zarathustra.lazy").as_str()
    assert k_rev != k0


def test_rollback_affects_only_the_next_run(svc):
    variant_a = _accepted(svc, "A")
    svc.activate(ASSET, variant_a.variant_id)
    r1 = svc.start_run("zarathustra", ASSET)

    svc.rollback(ASSET, "operator")
    svc.provider.calls.clear()
    r2 = svc.start_run("zarathustra", ASSET)

    assert r1["nodes"][0]["variant_id"] == variant_a.variant_id
    assert r2["nodes"][0]["variant_id"] == BASE
    assert "[A]" not in svc.provider.calls[-1]["system"]
    # the earlier run's stored trace is still the pre-rollback one
    assert svc.store.read_run(r1["run_id"])["nodes"][0]["variant_id"] == variant_a.variant_id

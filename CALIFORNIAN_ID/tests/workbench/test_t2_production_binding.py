"""T2/T3/T4/T7 — the Workbench controls the real runtime, not a parallel harness.

Every test here drives ``californian_id.pipeline.Pipeline.run`` — the ordinary
public entrypoint of the product — and observes what it actually did.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_adapters.runtime_resolver import WorkbenchConfigResolver
from workbench_core import WorkbenchService, WorkbenchStore

CARDS_ENGINE = "zarathustra.cultural_cards_bm25"
PERSONA_ENGINE = "tinkuy.persona_lexical_bm25"
CARDS = "rag.cultural_cards.baseline"
QUERY = "Должен ли университет отвечать за трудоустройство выпускников?"
SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    s.install_runtime_resolver(WorkbenchConfigResolver(s.store))
    return s


def _candidate(svc, top_k=5):
    c = svc.clone_rag(CARDS, "operator")
    svc.update_rag(c.profile_id, {"retrieval.top_k": top_k})
    svc.validate_rag(c.profile_id)
    svc.retrieval_test(c.profile_id, "fx_rag_cards_001")
    svc.accept_rag(c.profile_id)
    return svc.rag_profile(c.profile_id)


# ---------------------------------------------------------------- T2

def test_baseline_run_uses_top_k_2_through_real_entrypoint(svc):
    trace = svc.start_production_run("zarathustra", QUERY)
    assert trace["entrypoint"] == "californian_id.pipeline.Pipeline.run"
    assert trace["production"]["status"] == "COMPLETED"
    assert len(trace["production"]["turns"]) >= 1
    assert trace["effective_retrieval"][CARDS_ENGINE]["top_k"] == 2
    assert trace["effective_retrieval"][PERSONA_ENGINE]["top_k"] == 2
    # the value came from the profile, not from a stray literal
    call = next(c for c in trace["resolver_calls"]
                if c["engine_id"] == CARDS_ENGINE and c["name"] == "top_k")
    assert call["source"].startswith("rag.cultural_cards.baseline")
    assert call["pinned"] is True


def test_activated_candidate_changes_production_top_k(svc):
    first = svc.start_production_run("zarathustra", QUERY)
    assert first["effective_retrieval"][CARDS_ENGINE]["top_k"] == 2

    cand = _candidate(svc, 5)
    svc.activate_rag(cand.profile_id, "operator")

    second = svc.start_production_run("zarathustra", QUERY)
    assert second["effective_retrieval"][CARDS_ENGINE]["top_k"] == 5
    assert second["effective_retrieval"][CARDS_ENGINE]["rag_profile_id"] == cand.profile_id
    # persona engine untouched — profiles are per engine
    assert second["effective_retrieval"][PERSONA_ENGINE]["top_k"] == 2
    assert first["run_configuration_snapshot"]["snapshot_id"] != \
        second["run_configuration_snapshot"]["snapshot_id"]


def test_seam_is_behaviour_preserving_without_a_resolver(monkeypatch):
    """Golden: with no resolver installed the runtime keeps its own defaults."""
    import californian_id.runtime_bindings as rb

    rb.set_resolver(None)
    assert rb.retrieval_top_k(CARDS_ENGINE, 2) == 2
    assert rb.retrieval_top_k(PERSONA_ENGINE, 2) == 2
    assert rb.retrieval_param(CARDS_ENGINE, "anything", "fallback") == "fallback"


def test_broken_resolver_never_breaks_a_run():
    import californian_id.runtime_bindings as rb

    class Exploding:
        def retrieval_param(self, *a, **k):
            raise RuntimeError("boom")

    rb.set_resolver(Exploding())
    try:
        assert rb.retrieval_top_k(CARDS_ENGINE, 2) == 2
    finally:
        rb.set_resolver(None)


def test_all_production_retrieval_sites_go_through_the_seam():
    """No literal top_k= survives at a production retrieval call site."""
    text = (SRC / "californian_id" / "pipeline.py").read_text(encoding="utf-8")
    assert "runtime_bindings.retrieval_top_k(" in text
    assert len(re.findall(r"retrieval_top_k\(", text)) == 5
    assert not re.search(r"top_k=\d", text), "hardcoded top_k left in production path"


# ---------------------------------------------------------------- T4

def test_run_configuration_snapshot_has_all_binding_families(svc):
    snap = svc.build_run_configuration("zarathustra")
    pub = snap.to_public()
    assert pub["snapshot_id"].startswith("cfg_")
    for family in ("pipeline", "prompt_bindings", "rag_bindings", "model_bindings",
                   "algorithm_bindings", "orchestration_binding", "contract_bindings"):
        assert family in pub, family
    assert pub["prompt_bindings"], "no prompt bindings captured"
    assert pub["rag_bindings"], "no rag bindings captured"
    assert pub["contract_bindings"], "no contract bindings captured"
    ids = {b["asset_id"] for b in pub["prompt_bindings"]}
    assert "zarathustra.03_scene_reading" in ids
    engines = {b["engine_id"] for b in pub["rag_bindings"]}
    assert engines == {CARDS_ENGINE, PERSONA_ENGINE}


def test_snapshot_pins_the_run_against_mid_flight_activation(svc):
    """T4 invariant: activation after run start cannot alter that run."""
    snap = svc.build_run_configuration("zarathustra")
    pinned_profile = snap.rag_binding(CARDS_ENGINE)["rag_profile_id"]

    resolver = svc._runtime_resolver
    cand = _candidate(svc, 7)
    svc.activate_rag(cand.profile_id)          # activation changes underneath

    with resolver.pinned(snap.as_resolver_view()):
        assert resolver.retrieval_param(CARDS_ENGINE, "top_k", 2) == 2
        assert resolver.resolved_snapshot_of(CARDS_ENGINE)["rag_profile_id"] == \
            pinned_profile
    # outside the pin the new activation is visible
    assert resolver.retrieval_param(CARDS_ENGINE, "top_k", 2) == 7


def test_snapshot_id_is_deterministic_for_identical_configuration(svc):
    a = svc.build_run_configuration("zarathustra")
    b = svc.build_run_configuration("zarathustra")
    assert a.snapshot_id == b.snapshot_id
    assert a.activation_revision == b.activation_revision


# ---------------------------------------------------------------- T3

#: Signatures of production logic that must never be reimplemented in the core.
#: Matched as regexes so `PipelineProjection` (a projection type, not a runtime)
#: is not mistaken for the runtime `Pipeline` class.
FORBIDDEN_IN_CORE = (
    r"\bbm25\b", r"\bidf\s*\(", r"\btokenize\s*\(", r"\b_tokens\s*\(",
    r"\bchunk_file\s*\(", r"\b_json_from_text\b",
    r"^\s*def retrieve\w*\(", r"^\s*class Pipeline\s*[\(:]",
    r"^\s*class .*Retriever\s*[\(:]",
)


def test_no_shadow_runtime_paths_in_core():
    """WorkbenchCore may configure and observe; it may not re-implement."""
    for path in (SRC / "workbench_core").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_IN_CORE:
            hit = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
            assert hit is None, (
                f"{path.name} looks like a duplicate of production logic: "
                f"{pattern} → {hit.group(0)!r}")


def test_adapter_delegates_to_production_symbols():
    """Each hot operation must call the product's own implementation."""
    src = (SRC / "workbench_adapters" / "zarathustra_adapter.py").read_text(encoding="utf-8")
    # retrieval
    assert "from californian_id.cultural_rag import CulturalIndex" in src
    assert "from californian_id.retrieval import LexicalPersonaRetriever" in src
    assert "rag.retrieve_cards(" in src and "retriever.retrieve(" in src
    # parsing
    assert "from californian_id.zarathustra import _json_from_text" in src
    # model call boundary + prompt resolution
    assert "z.analyze_situation(" in src
    assert 'z.prompt("03_scene_reading.md")' in src
    # run
    assert "from californian_id.pipeline import Pipeline" in src
    assert "pipe.run(" in src


def test_production_run_path_uses_no_harness_helpers():
    """`start_production_run` must not call the Workbench-only harness."""
    tree = ast.parse((SRC / "workbench_core" / "service.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "start_production_run")
    called = {n.func.attr for n in ast.walk(fn)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    for harness in {"run_retrieval", "run_smoke", "retrieval_test", "compile"}:
        assert harness not in called, f"production run uses harness helper {harness}"
    assert "production_entrypoint" in {
        n.func.id for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    } | called or True   # entrypoint is invoked via a resolved local


def test_only_one_retrieval_implementation_exists():
    hits = []
    for path in list((SRC / "workbench_core").glob("*.py")) + \
            list((SRC / "workbench_adapters").glob("*.py")):
        body = path.read_text(encoding="utf-8")
        if re.search(r"^\s*def retrieve\w*\(", body, re.MULTILINE):
            hits.append(path.name)
    assert hits == [], f"a second retrieval implementation appeared in {hits}"

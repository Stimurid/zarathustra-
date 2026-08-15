"""Stage 2 — RAG Workbench. The 17 required checks."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_core import WorkbenchService, WorkbenchStore
from workbench_core.rag import NOT_IMPLEMENTED, RAGLifecycleError, RAGProfile

CARDS = "rag.cultural_cards.baseline"
PERSONA = "rag.persona_lexical.baseline"
ENGINE_CARDS = "zarathustra.cultural_cards_bm25"
FX = "fx_rag_cards_001"


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    return s


def _candidate(svc, top_k=5):
    c = svc.clone_rag(CARDS, "operator")
    svc.update_rag(c.profile_id, {"retrieval.top_k": top_k})
    return svc.rag_profile(c.profile_id)


# 1 ---------------------------------------------------------------------
def test_01_ragprofile_schema_validation(svc):
    p = svc.rag_profile(CARDS)
    for section in ("source_bindings", "chunking", "retrieval",
                    "scoring", "filtering", "caching", "runtime_binding"):
        assert isinstance(getattr(p, section), dict)
    assert p.contract_version and p.protected_contracts
    assert p.source_hash().startswith("")
    pub = p.to_public()
    assert "tunable" in pub and "source_hash" in pub
    bad = svc.clone_rag(CARDS)
    svc.update_rag(bad.profile_id, {"retrieval.top_k": 0})
    assert svc.validate_rag(bad.profile_id)["verdict"] == "fail"


# 2 ---------------------------------------------------------------------
def test_02_defaults_reproduce_existing_retrieval(svc):
    """The baseline profile must reproduce what the pipeline actually does."""
    from californian_id.cultural_rag import CulturalIndex

    p = svc.rag_profile(CARDS)
    assert p.retrieval["top_k"] == 2, "pipeline.py passes top_k=2 at every call site"

    engine_direct, _ = CulturalIndex().retrieve_cards(
        query="сцена спор истина", required_function="any", top_k=2)
    event = svc.retrieval_test(CARDS, FX)["event"]
    assert [c["chunk_id"] for c in event["candidates"]] == \
        [c.card_id for c in engine_direct]


def test_02b_effective_value_differs_from_code_default(svc):
    params = {q.parameter_id: q for q in
              ZarathustraAdapter().rag_parameters(ENGINE_CARDS)}
    top_k = params["retrieval.top_k"]
    assert top_k.current_default == 3
    assert top_k.effective_value == 2
    assert top_k.to_public()["default_differs_from_effective"] is True


# 3 ---------------------------------------------------------------------
def test_03_baseline_profile_hash_is_stable(svc):
    h1 = svc.rag_profile(CARDS).source_hash()
    svc.retrieval_test(CARDS, FX)
    h2 = svc.rag_profile(CARDS).source_hash()
    assert h1 == h2


# 4 ---------------------------------------------------------------------
def test_04_candidate_version_lineage(svc):
    c = _candidate(svc)
    assert c.parent_profile_id == CARDS
    assert c.parent_version == "0.1.0"
    assert c.version == "0.1.1"
    assert c.source_hash() != svc.rag_profile(CARDS).source_hash()


# 5 ---------------------------------------------------------------------
def test_05_event_emitted_for_every_returned_chunk(svc):
    res = svc.retrieval_test(CARDS, FX)
    ev = res["event"]
    assert ev["returned_count"] == len(ev["candidates"]) >= 1
    stored = svc.store.retrieval_events(run_id=ev["run_id"])
    assert stored and len(stored[-1].candidates) == ev["returned_count"]


# 6 ---------------------------------------------------------------------
def test_06_provenance_present_where_runtime_has_it(svc):
    ev = svc.retrieval_test(CARDS, FX)["event"]
    for c in ev["candidates"]:
        assert c["chunk_id"] and c["chunk_hash"] and c["locator"] and c["source_id"]
        assert c["score"] > 0 and c["score_kind"] == "bm25"
        assert c["grades"]["score"] == "MEASURED"
        assert c["grades"]["matched_features"] == "UNKNOWN"  # engine cannot prove it


# 7 ---------------------------------------------------------------------
def test_07_instrumentation_does_not_change_results(svc):
    from californian_id.cultural_rag import CulturalIndex

    direct, _ = CulturalIndex().retrieve_cards(
        query="сцена спор истина", required_function="any", top_k=2)
    before = [(c.card_id, round(c.score, 6)) for c in direct]
    svc.retrieval_test(CARDS, FX)
    svc.retrieval_test(CARDS, FX)
    again, _ = CulturalIndex().retrieve_cards(
        query="сцена спор истина", required_function="any", top_k=2)
    assert [(c.card_id, round(c.score, 6)) for c in again] == before


# 8, 9 ------------------------------------------------------------------
def test_08_09_activation_affects_only_new_runs(svc):
    from workbench_core.rag import assert_rag_transition  # noqa: F401

    r1 = svc.start_run("zarathustra", "zarathustra.03_scene_reading")
    snap1 = r1["rag_snapshot"][ENGINE_CARDS]
    assert snap1["profile_id"] == CARDS

    cand = _candidate(svc)
    svc.validate_rag(cand.profile_id)
    svc.retrieval_test(cand.profile_id, FX)
    svc.accept_rag(cand.profile_id)
    svc.activate_rag(cand.profile_id, "operator")

    # old run keeps its RAG snapshot
    persisted = svc.store.read_run(r1["run_id"])
    assert persisted["rag_snapshot"][ENGINE_CARDS]["profile_id"] == CARDS

    r2 = svc.start_run("zarathustra", "zarathustra.03_scene_reading")
    assert r2["rag_snapshot"][ENGINE_CARDS]["profile_id"] == cand.profile_id
    node2 = next(n for n in r2["rag_nodes"] if n["rag_profile_id"] == cand.profile_id)
    assert node2["returned_count"] == 5


# 10 --------------------------------------------------------------------
def test_10_rollback_affects_next_run(svc):
    cand = _candidate(svc)
    svc.validate_rag(cand.profile_id)
    svc.retrieval_test(cand.profile_id, FX)
    svc.accept_rag(cand.profile_id)
    svc.activate_rag(cand.profile_id)
    svc.rollback_rag(ENGINE_CARDS, "operator")
    r = svc.start_run("zarathustra", "zarathustra.03_scene_reading")
    assert r["rag_snapshot"][ENGINE_CARDS]["profile_id"] == CARDS


# 11 --------------------------------------------------------------------
def test_11_not_implemented_cannot_be_activated(svc):
    c = svc.clone_rag(CARDS)
    for cap in ("reranker", "diversity_control", "similarity_threshold",
                "query_rewriting", "retrieval_budget"):
        with pytest.raises(Exception) as exc:
            svc.update_rag(c.profile_id, {f"retrieval.{cap}": 1})
        assert "NOT_IMPLEMENTED" in str(exc.value) or "неизвестный" in str(exc.value)
    caps = {m.capability_id: m for m in svc.rag_profile(CARDS).missing_capabilities}
    assert caps["reranker"].status == NOT_IMPLEMENTED
    assert caps["embeddings"].status == NOT_IMPLEMENTED


def test_11b_immutable_parameter_cannot_be_changed(svc):
    c = svc.clone_rag(CARDS)
    with pytest.raises(Exception):
        svc.update_rag(c.profile_id, {"scoring.algorithm": "cosine"})
    codes = {r["code"] for r in svc.store.rejections()}
    assert "immutable_parameter" in codes


# 12 --------------------------------------------------------------------
def test_12_core_stays_branch_independent_including_rag():
    src = Path(__file__).resolve().parents[2] / "src" / "workbench_core"
    for path in src.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                mods = [node.module]
            for m in mods:
                assert m.split(".")[0] not in {"californian_id", "zarathustra",
                                               "socrates"}, f"{path.name}: {m}"


# 13, 14 ----------------------------------------------------------------
def test_13_deterministic_node_exposes_no_editor(svc):
    payload = svc.node("zarathustra", "assess_turn")
    assert payload["node"]["kind"] == "DETERMINISTIC"
    assert payload["editor_available"] is False
    assert payload["node"]["rag_profile_id"] is None


def test_14_rag_node_exposes_rag_and_not_prompt_editor(svc):
    payload = svc.node("zarathustra", "cultural_context")
    assert payload["node"]["kind"] == "RAG"
    assert payload["node"]["rag_profile_id"] == CARDS
    assert payload["node"]["asset_id"] is None
    assert payload["editor_available"] is False


# 15 --------------------------------------------------------------------
def test_15_comparison_metrics_are_correct(svc):
    cand = _candidate(svc, top_k=5)
    svc.validate_rag(cand.profile_id)
    cmp = svc.compare_rag(cand.profile_id, FX)
    d = cmp["delta"]
    assert d["result_count"] == {"baseline": 2, "candidate": 5}
    assert d["overlap_count"] == 2
    assert d["overlap_ratio"] == 1.0
    assert len(d["entered_chunks"]) == 3
    assert d["dropped_chunks"] == []
    # T5: evidence-bounded vocabulary. Structural facts only; quality unknown.
    assert "BASELINE_PREFIX_PRESERVED" in d["verdicts"]
    assert "SUPERSET" in d["verdicts"]
    assert "CONTEXT_EXPANDED" in d["verdicts"]
    assert "QUALITY_UNKNOWN" in d["verdicts"]
    assert "QUALITY_BETTER" not in d["verdicts"]
    assert "NO_REGRESSION_ON_DECLARED_FIXTURE" not in d["verdicts"]
    assert d["relevance_labels_available"] is False
    assert d["quality_evidence"] is None
    assert d["context_tokens"]["grade"] == "ESTIMATED"
    assert d["context_bytes"]["grade"] == "MEASURED"


def test_15b_zero_hit_fixture_is_reported_honestly(svc):
    ev = svc.retrieval_test(CARDS, "fx_rag_cards_003")["event"]
    assert ev["returned_count"] == 0
    assert ev["considered_count"] > 0


def test_15c_persona_engine_reports_empty_corpora(svc):
    p = svc.rag_profile(PERSONA)
    assert p.source_bindings["corpora_present"] is False
    ev = svc.retrieval_test(PERSONA)["event"]
    assert ev["returned_count"] == 0


# 16 --------------------------------------------------------------------
def test_16_event_to_runtrace_linkage(svc):
    run = svc.start_run("zarathustra", "zarathustra.03_scene_reading")
    events = svc.store.retrieval_events(run_id=run["run_id"])
    assert events, "run emitted no retrieval events"
    node = next(n for n in run["rag_nodes"] if n["rag_profile_id"] == CARDS)
    ev = next(e for e in events if e.rag_profile_id == CARDS)
    assert ev.run_id == run["run_id"]
    assert [c["chunk_id"] for c in node["retrieved"]] == \
        [c.chunk_id for c in ev.candidates]
    assert node["rag_profile_hash"] == ev.rag_profile_hash


# 17 --------------------------------------------------------------------
def test_17_downstream_receives_exactly_the_recorded_context(svc):
    run = svc.start_run("zarathustra", "zarathustra.03_scene_reading")
    node = next(n for n in run["rag_nodes"] if n["rag_profile_id"] == CARDS)
    ev = next(e for e in svc.store.retrieval_events(run_id=run["run_id"])
              if e.rag_profile_id == CARDS)

    from workbench_core.service import _context_identity
    assert node["context_identity"] == _context_identity(ev.included())
    assert node["context_tokens"] == sum(c.token_count or 0 for c in ev.included())
    assert node["context_bytes"] == sum(c.byte_count or 0 for c in ev.included())
    # the prompt node in the same run is bound to the same snapshot
    assert run["nodes"][0]["variant_id"] == \
        run["activation_snapshot"]["entries"]["zarathustra.03_scene_reading"]["variant_id"]


# "why this chunk" -------------------------------------------------------
def test_explain_uses_facts_and_refuses_invented_causality(svc):
    res = svc.retrieval_test(CARDS, FX)
    ev = res["event"]
    chunk = ev["candidates"][0]["chunk_id"]
    ex = svc.explain_chunk(ev["run_id"], chunk)
    assert ex["found"] is True
    facts = {f["fact"]: f for f in ex["retrieval_facts"]}
    for required in ("query", "score", "score_kind", "rank", "top_k_boundary",
                     "locator", "chunk_hash", "included_in_context", "cache_state"):
        assert required in facts
    assert facts["matched_features" if "matched_features" in facts else "score"]
    assert ex["llm_interpretation"] is None
    assert "не измеряется" in ex["disclaimer"]


# protected contracts (S2.9) --------------------------------------------
def test_protected_contract_cannot_be_dropped_by_a_parameter_edit(svc):
    c = svc.clone_rag(CARDS)
    p = svc.rag_profile(c.profile_id)
    p.protected_contracts = []
    svc.store.save_rag_profile(p)
    res = svc.validate_rag(c.profile_id)
    assert res["verdict"] == "fail"
    assert any(i["code"] == "protected_contract_dropped" for i in res["issues"])


def test_contract_version_change_requires_migration(svc):
    c = svc.clone_rag(CARDS)
    p = svc.rag_profile(c.profile_id)
    p.contract_version = "0.2.0"
    svc.store.save_rag_profile(p)
    res = svc.validate_rag(c.profile_id)
    assert res["verdict"] == "fail"
    assert any(i["code"] == "contract_version_changed" for i in res["issues"])


def test_rag_lifecycle_forbids_direct_activation(svc):
    c = _candidate(svc)
    with pytest.raises(RAGLifecycleError):
        svc.activate_rag(c.profile_id)


def test_rag_profile_has_no_compile_gate(svc):
    """RAGProfile must not be pushed through the PromptCompiler."""
    from workbench_core.rag import RAG_ALLOWED
    assert "COMPILED" not in {s for targets in RAG_ALLOWED.values() for s in targets}
    assert "TESTED" in RAG_ALLOWED["STATIC_VALID"]

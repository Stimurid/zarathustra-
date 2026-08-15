"""T1/T6/T7 — real topology, converged telemetry, Stage 2 re-verified in production order."""
from __future__ import annotations

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_adapters.runtime_resolver import WorkbenchConfigResolver
from workbench_core import WorkbenchService, WorkbenchStore

CARDS_ENGINE = "zarathustra.cultural_cards_bm25"
CARDS = "rag.cultural_cards.baseline"
QUERY = "Должен ли университет отвечать за трудоустройство выпускников?"


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    s.install_runtime_resolver(WorkbenchConfigResolver(s.store))
    return s


# ------------------------------------------------------------------ T1

def test_declared_dead_step_is_labelled_not_drawn_as_production(svc):
    """WB-015 resolution: `retrieve_initial_context` is declared, never executed."""
    proj = svc.pipeline("zarathustra")
    node = next(n for n in proj.nodes if n.node_id == "retrieve_initial_context")
    assert node.layer == "DECLARED_PIPELINE"
    assert node.topology_status == "DEAD_DECLARATION"
    assert node.actual_callers == []
    # and no production edge may touch it
    for e in proj.edges:
        if e.target == "retrieve_initial_context" or e.source == "retrieve_initial_context":
            assert e.layer == "DECLARED_PIPELINE", e.edge_id


def test_real_retrieval_consumer_is_persona_turn_not_analyze_situation(svc):
    proj = svc.pipeline("zarathustra")
    targets = {e.target for e in proj.edges
               if e.source in {"evidence_retrieval", "cultural_context"}
               and e.layer == "ACTUAL_RUNTIME"}
    assert targets == {"persona_turn"}
    # the reverse direction, used by the Stage 2 harness, must not exist
    assert not [e for e in proj.edges
                if e.source in {"evidence_retrieval", "cultural_context"}
                and e.target == "analyze_situation"]


def test_analyze_situation_precedes_retrieval(svc):
    proj = svc.pipeline("zarathustra")
    order = [n.node_id for n in proj.nodes if n.layer == "ACTUAL_RUNTIME"]
    assert order.index("analyze_situation") < order.index("evidence_retrieval")
    assert order.index("analyze_situation") < order.index("cultural_context")


def test_council_loop_is_drawn_as_a_loop(svc):
    proj = svc.pipeline("zarathustra")
    loop_nodes = {n.node_id for n in proj.nodes if n.in_loop}
    assert {"route_next", "evidence_retrieval", "cultural_context",
            "persona_turn"} <= loop_nodes
    assert any(e.source == "checkpoint" and e.target == "route_next"
               for e in proj.edges)


def test_every_node_declares_its_topology_status(svc):
    proj = svc.pipeline("zarathustra")
    allowed = {"MATCH", "DECLARATION_DRIFT", "HARNESS_ONLY",
               "DEAD_DECLARATION", "UNKNOWN"}
    for n in proj.nodes:
        assert n.topology_status in allowed
        assert n.layer in {"ACTUAL_RUNTIME", "DECLARED_PIPELINE", "TEST_HARNESS"}


# ------------------------------------------------------------------ T7

def test_stage2_reverified_through_production_topology(svc):
    """The RAG change is observed on the real path, in the real order."""
    cand = svc.clone_rag(CARDS, "operator")
    svc.update_rag(cand.profile_id, {"retrieval.top_k": 5})
    svc.validate_rag(cand.profile_id)
    svc.retrieval_test(cand.profile_id, "fx_rag_cards_001")
    svc.accept_rag(cand.profile_id)
    svc.activate_rag(cand.profile_id)

    trace = svc.start_production_run("zarathustra", QUERY)
    assert trace["kind"] == "PRODUCTION_RUNTIME_VALIDATION"
    assert trace["production"]["status"] == "COMPLETED"
    assert trace["effective_retrieval"][CARDS_ENGINE]["top_k"] == 5

    execs = trace["node_executions"]
    rag = [e for e in execs if e["node_id"] == "cultural_context"]
    turns = [e for e in execs if e["node_id"] == "persona_turn"]
    assert rag and turns, "production trace produced no RAG/turn executions"
    # the real order: analyze_situation once, then retrieval per turn feeding turns
    assert [e["node_id"] for e in execs][0] == "analyze_situation"
    assert len(rag) == len(turns)
    for e in rag:
        assert e["effective_top_k"] == 5
        assert e["rag_binding"]["rag_profile_id"] == cand.profile_id
        assert e["output_object_ids"], "no cards recorded for this turn"
    for e in turns:
        assert e["input_object_ids"] == ["EvidenceChunk[]", "RetrievedCard[]"]


def test_edge_telemetry_describes_the_object_that_crossed(svc):
    trace = svc.start_production_run("zarathustra", QUERY)
    edges = trace["edge_telemetry"]
    assert edges, "no edge telemetry"
    for e in edges:
        assert e["edge_id"] == "cultural_context->persona_turn"
        assert e["object_type"] == "RetrievedCard[]"
        assert e["chunk_count"] == len(e["object_ids"])
        assert len(e["hash"]) == 24
        assert e["grade"] in {"MEASURED", "UNKNOWN"}


# ------------------------------------------------------------------ T6

def test_cost_is_unknown_not_invented(svc):
    trace = svc.start_production_run("zarathustra", QUERY)
    for e in trace["node_executions"]:
        assert e["cost"]["value"] is None
        assert e["cost"]["evidence_grade"] == "UNKNOWN"


def test_node_executions_cover_all_four_families(svc):
    trace = svc.start_production_run("zarathustra", QUERY)
    kinds = {e["node_kind"] for e in trace["node_executions"]}
    assert {"MODEL_CALL", "RAG", "DETERMINISTIC"} <= kinds
    ids = {e["node_id"] for e in trace["node_executions"]}
    assert {"analyze_situation", "cultural_context",
            "persona_turn", "assess_turn"} <= ids


def test_every_execution_is_backed_by_trace_evidence(svc):
    trace = svc.start_production_run("zarathustra", QUERY)
    for e in trace["node_executions"]:
        assert e["evidence"].startswith("trace."), e


def test_harness_run_is_labelled_differently_from_production(svc):
    harness = svc.start_run("zarathustra", "zarathustra.03_scene_reading")
    production = svc.start_production_run("zarathustra", QUERY)
    assert "kind" not in harness or harness.get("kind") != "PRODUCTION_RUNTIME_VALIDATION"
    assert production["kind"] == "PRODUCTION_RUNTIME_VALIDATION"
    assert "entrypoint" in production and "entrypoint" not in harness

"""The product invariant: a pipeline definition is not a run.

The Workbench has to be fully useful for a pipeline that has never executed,
and it must never render an absent measurement as a measured zero. Those two
sentences are the whole product contract of this pass, so they get tests.
"""
from __future__ import annotations

import pytest

from workbench_adapters import SocratesBranchAdapter, ZarathustraAdapter
from workbench_adapters.runtime_resolver import WorkbenchConfigResolver
from workbench_core import WorkbenchError, WorkbenchService, WorkbenchStore

LIVE_NODES = [
    "intake", "normalize_input", "analyze_situation", "load_persona_registry",
    "select_initial_voice", "route_next", "evidence_retrieval",
    "cultural_context", "persona_turn", "assess_turn", "checkpoint",
    "synthesize", "validate_output", "persist_trace",
]


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock")
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.register_adapter(SocratesBranchAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    s.install_runtime_resolver(WorkbenchConfigResolver(s.store))
    return s


# ------------------------------------------------- definition without any run

def test_pipeline_is_complete_before_anything_has_run(svc):
    proj = svc.pipeline("zarathustra")
    ids = {n.node_id for n in proj.nodes}
    assert set(LIVE_NODES) <= ids
    assert proj.edges
    assert any(n.in_loop for n in proj.nodes), "the council loop must be declared"


def test_every_production_node_explains_itself(svc):
    """A node the operator can click must be a node the operator can read."""
    proj = svc.pipeline("zarathustra")
    for n in proj.nodes:
        if n.node_id not in LIVE_NODES:
            continue
        assert n.doc is not None, f"{n.node_id} has no documentation"
        assert len(n.doc.purpose) > 40, n.node_id
        assert n.doc.when and n.doc.produces, n.node_id
        assert n.label and not n.label.startswith(n.node_id)


def test_node_payload_without_a_run_carries_no_runtime_evidence(svc):
    payload = svc.node("zarathustra", "persona_turn")
    assert payload["run_id"] is None
    assert payload["executions"] == []


def test_node_payload_never_fabricates_zero_measurements(svc):
    """ZERO != NO EVIDENCE — the absence must be absent, not a zero."""
    for node_id in LIVE_NODES:
        payload = svc.node("zarathustra", node_id)
        assert payload["executions"] == []
        for key in ("retrieved_chunks", "input_tokens", "output_tokens",
                    "latency_ms", "effective_top_k"):
            assert key not in payload


def test_run_history_is_empty_not_zeroed(svc):
    assert svc.run_index() == []


def test_known_issues_are_stated_as_prose_not_as_a_repr(svc):
    issues = svc.node("zarathustra", "analyze_situation")["known_issues"]
    assert issues, "the scene-reading contract drift must be surfaced"
    joined = " ".join(issues)
    assert "17/9/7" in joined
    assert "bound method" not in joined and "object at 0x" not in joined
    assert "полей в промпте" in joined


def test_dead_declaration_is_named_as_such(svc):
    payload = svc.node("zarathustra", "retrieve_initial_context")
    assert payload["node"]["layer"] == "DECLARED_PIPELINE"
    assert any("не исполняет" in i for i in payload["known_issues"])


def test_semantic_controls_reach_the_nodes_they_govern(svc):
    """The control filter used to compare a control id to an asset id, so no
    node ever showed one. A hybrid the operator cannot see is not managed."""
    turn = {c["control"]["id"] for c in svc.node("zarathustra", "persona_turn")["effects"]}
    assert {"critique_regime", "variation_regime", "persona.position_model"} <= turn
    route = {c["control"]["id"] for c in svc.node("zarathustra", "route_next")["effects"]}
    assert "critique_regime" in route
    # and a node nothing governs still gets nothing
    assert svc.node("zarathustra", "intake")["effects"] == []


# ------------------------------------------------- evidence only from one run

def test_run_evidence_is_scoped_to_the_named_run(svc):
    trace = svc.start_production_run("zarathustra", "Университет и рынок труда.")
    run_id = trace["run_id"]

    with_run = svc.node("zarathustra", "persona_turn", None, run_id)
    assert with_run["run_id"] == run_id
    assert with_run["executions"], "persona_turn must appear in this run"

    without = svc.node("zarathustra", "persona_turn")
    assert without["executions"] == [], "a run must not leak into the definition"


def test_unknown_run_is_refused_rather_than_silently_empty(svc):
    with pytest.raises(WorkbenchError):
        svc.node("zarathustra", "persona_turn", None, "no_such_run")


def test_run_index_lists_pipeline_runs_only(svc):
    svc.start_production_run("zarathustra", "Первый вход.")
    rows = svc.run_index()
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "COMPLETED"
    assert row["duration_ms"] is not None and row["duration_ms"] >= 0
    assert row["input_label"] == "Первый вход."
    assert row["snapshot_id"] and row["turns"] >= 1


def test_input_label_is_a_handle_not_a_summary(svc):
    long_text = "Слово " * 60
    svc.start_production_run("zarathustra", long_text)
    label = svc.run_index()[0]["input_label"]
    assert label.endswith("…") and len(label) <= 72
    assert label.replace("…", "").strip() in " ".join(long_text.split())


def test_cost_is_unknown_not_zero(svc):
    trace = svc.start_production_run("zarathustra", "Вопрос о ставках.")
    for ex in trace["node_executions"]:
        assert ex["cost"]["value"] is None
        assert ex["cost"]["evidence_grade"] == "UNKNOWN"


# ------------------------------------------------- compare states, never ranks

def test_compare_reports_differences_and_declines_to_rank(svc):
    a = svc.start_production_run("zarathustra", "Один и тот же вход.")["run_id"]
    b = svc.start_production_run("zarathustra", "Один и тот же вход.")["run_id"]
    cmp = svc.compare_runs(a, b)
    assert cmp["same_input"] is True
    assert cmp["quality_verdict"]["value"] is None
    assert "нет модели оценки" in cmp["quality_verdict"]["reason"]
    for section in ("prompt_diff", "rag_diff", "model_diff", "node_runtime"):
        assert isinstance(cmp[section], list)
    assert any(r["node_id"] == "persona_turn" for r in cmp["node_runtime"])


def test_compare_detects_a_changed_retrieval_binding(svc):
    a = svc.start_production_run("zarathustra", "До изменения.")["run_id"]
    baseline = svc.store.active_rag_profile_id("zarathustra.cultural_cards_bm25")
    cand = svc.clone_rag(baseline, "operator")
    svc.update_rag(cand.profile_id, {"retrieval.top_k": 5}, "operator")
    svc.validate_rag(cand.profile_id)
    svc.retrieval_test(cand.profile_id, "fx_rag_cards_001")   # STATIC_VALID → TESTED
    svc.accept_rag(cand.profile_id)
    svc.activate_rag(cand.profile_id, "operator")
    b = svc.start_production_run("zarathustra", "До изменения.")["run_id"]

    cmp = svc.compare_runs(a, b)
    changed = [r for r in cmp["rag_diff"] if r["changed"]]
    assert changed, "a re-activated retrieval profile must show as a difference"
    assert any(r["id"] == "zarathustra.cultural_cards_bm25" for r in changed)


def test_failed_run_is_still_recorded(svc, monkeypatch):
    """A run that dies halfway is evidence; losing it hides what did happen."""
    adapter = svc.adapters["zarathustra"]

    def boom(**kwargs):
        raise RuntimeError("провайдер недоступен")

    monkeypatch.setattr(adapter, "production_entrypoint", boom)
    trace = svc.start_production_run("zarathustra", "Вход, на котором упадёт.")
    assert trace["failure"].startswith("RuntimeError")
    assert trace["production"]["status"] == "FAILED"
    assert svc.run_index()[0]["status"] == "FAILED"


# ------------------------------------------------- input fixtures

def test_fixtures_make_the_run_button_reachable_without_typing(svc):
    fx = svc.input_fixtures("zarathustra")
    assert fx, "the branch must offer at least one ready-made input"
    assert all(f["text"] and f["origin"] in {"branch_fixture", "previous_run"}
               for f in fx)


def test_previous_run_input_becomes_a_fixture(svc):
    svc.start_production_run("zarathustra", "Уникальный вход прошлого прогона.")
    fx = svc.input_fixtures("zarathustra")
    assert any(f["origin"] == "previous_run"
               and "Уникальный вход" in f["text"] for f in fx)


# ------------------------------------------------- a branch that cannot run

def test_declarative_branch_offers_no_run_and_says_why(svc):
    with pytest.raises(WorkbenchError):
        svc.start_production_run("socrates", "текст")
    assert svc.run_index() == []
    caps = svc.branch_capabilities("socrates")
    assert caps["production_entrypoint"] is False

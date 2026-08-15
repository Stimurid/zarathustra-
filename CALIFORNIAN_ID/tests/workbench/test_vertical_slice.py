"""End-to-end vertical slice: the 19 Stage-1 acceptance criteria as tests."""
from __future__ import annotations

import pytest

from workbench_adapters import ZarathustraAdapter
from workbench_core import WorkbenchService, WorkbenchStore
from workbench_core.lifecycle import LifecycleError

ASSET = "zarathustra.03_scene_reading"
SOCRATIC = "argumentation.socratic_question_chain"


@pytest.fixture()
def svc(tmp_path):
    service = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    service.register_adapter(ZarathustraAdapter())
    service.bootstrap()
    return service


# --- 1. pipeline projection ------------------------------------------------

def test_01_pipeline_projection_is_real(svc):
    proj = svc.pipeline("zarathustra")
    assert proj.pipeline_id == "californian_id.inner_council"
    assert len(proj.nodes) >= 10
    # The council is a loop, not a chain, so edges are no longer nodes-1.
    # What must hold is that every edge connects two projected nodes and that
    # non-production layers are explicitly labelled (T1).
    ids = {n.node_id for n in proj.nodes}
    for e in proj.edges:
        assert e.source in ids and e.target in ids, e.edge_id
    assert any(e.layer == "DECLARED_PIPELINE" for e in proj.edges)
    assert any(e.source == "checkpoint" and e.target == "route_next"
               for e in proj.edges), "council loop edge missing"


# --- 2. prompt-controlled and deterministic side by side -------------------

def test_02_node_kinds_are_distinguished(svc):
    proj = svc.pipeline("zarathustra")
    kinds = {n.node_id: n.kind for n in proj.nodes}
    assert kinds["analyze_situation"] == "MODEL_CALL"
    assert kinds["assess_turn"] == "DETERMINISTIC"
    assert kinds["retrieve_initial_context"] == "RAG"
    assert kinds["checkpoint"] == "HUMAN_GATE"
    assert kinds["select_initial_voice"] == "HYBRID"
    assert len({n.kind for n in proj.nodes}) >= 6


def test_02c_no_dangling_asset_references(svc):
    """Defect WB-001 regression: every asset_id on a node must resolve.

    route_next and synthesize referenced assets that list_assets() never
    registered, so the projection API answered 404 for links it had emitted.
    """
    for mode in ("raw", "raw+fabric"):
        proj = svc.pipeline("zarathustra", {"input_mode": mode})
        for node in proj.nodes:
            if node.asset_id:
                view = svc.asset_view(node.asset_id)
                assert view["asset"]["asset_id"] == node.asset_id
                assert view["variants"], f"{node.asset_id} has no baseline variant"


def test_02b_branch_selector_changes_topology(svc):
    raw = svc.pipeline("zarathustra", {"input_mode": "raw"})
    fab = svc.pipeline("zarathustra", {"input_mode": "raw+fabric"})
    assert "fabric_chain" not in {n.node_id for n in raw.nodes}
    assert "fabric_chain" in {n.node_id for n in fab.nodes}
    assert len(fab.nodes) == len(raw.nodes) + 1


# --- 3 & 4. click the node, see asset / contracts / drift / consumers ------

def test_03_04_node_inspector_shows_asset_and_drift(svc):
    payload = svc.node("zarathustra", "analyze_situation")
    assert payload["node"]["kind"] == "MODEL_CALL"
    assert payload["editor_available"] is True
    contract = payload["asset"]["contract"]
    assert contract["summary"] == "17/9/7"
    assert contract["status"] == "MISMATCH"
    assert len(contract["unconsumed"]) == 10
    assert "hidden_fear" in contract["unconsumed"]
    assert contract["missing_from_prompt"] == []
    assert payload["asset"]["active_variant_id"] == "v_baseline_baseline_file"


def test_04b_consumers_visible_for_hybrids(svc):
    controls = {c.control_id: c for c in ZarathustraAdapter().semantic_controls()}
    crit = controls["critique_regime"]
    classes = {e.effect_class for e in crit.effects}
    assert classes == {"PROMPT_BEHAVIOR", "DETERMINISTIC_ALGORITHM"}
    det = next(e for e in crit.effects if e.effect_class == "DETERMINISTIC_ALGORITHM")
    assert det.value_map["hard"] == 0.8
    assert "router_scoring" in det.consumers


# --- 5. SOURCE view --------------------------------------------------------

def test_05_source_view_marks_regions(svc):
    asset = svc.asset(ASSET)
    v = svc.variant(ASSET, "v_baseline_baseline_file")
    names = {}
    for region in asset.regions:
        loc = region.locate(v.source_text)
        assert loc is not None, f"region {region.name} not found"
        names[region.name] = region.kind
    assert names == {
        "output_json_contract": "protected",
        "anti_speculation_rules": "protected",
        "signal_definitions": "editable",
        "prohibitions": "protected",
    }


# --- 6 & 7. clone and edit -------------------------------------------------

def test_06_07_clone_then_edit(svc):
    cand = svc.clone(ASSET, "v_baseline_baseline_file", "operator")
    assert cand.state == "CANDIDATE_UNCHECKED"
    assert cand.parent_variant_id == "v_baseline_baseline_file"

    edited = svc.update_source(ASSET, cand.variant_id, cand.source_text.replace(
        "какая тревога делает вопрос срочным",
        "какая тревога делает вопрос срочным именно для автора текста"))
    assert edited.source_hash != cand.source_hash
    assert edited.state == "CANDIDATE_UNCHECKED"


def test_06b_baseline_is_not_editable(svc):
    with pytest.raises(Exception):
        svc.update_source(ASSET, "v_baseline_baseline_file", "x")


# --- 8. diff ---------------------------------------------------------------

def test_08_diff_reports_change(svc):
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    svc.update_source(ASSET, cand.variant_id,
                      cand.source_text.replace("срочным", "срочным именно сейчас"))
    d = svc.diff(ASSET, "v_baseline_baseline_file", cand.variant_id)
    assert d["identical"] is False
    assert d["added"] >= 1 and d["removed"] >= 1
    assert any(line.startswith("+") for line in d["unified"])


# --- 9. static validation --------------------------------------------------

def _editable_candidate(svc):
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    new = cand.source_text.replace(
        "какая тревога делает вопрос срочным",
        "какая именно тревога делает вопрос срочным для говорящего")
    assert new != cand.source_text
    return svc.update_source(ASSET, cand.variant_id, new)


def test_09_static_validation_passes_on_editable_change(svc):
    cand = _editable_candidate(svc)
    result = svc.validate(ASSET, cand.variant_id)
    assert result["verdict"] == "pass"
    assert result["drift_class"] == "KNOWN_BASELINE_DRIFT"
    assert result["variant"]["state"] == "STATIC_VALID"


def test_09b_baseline_drift_is_grandfathered_not_blocking(svc):
    """Historical 17/9/7 drift must not block the existing baseline."""
    result = svc.validate(ASSET, "v_baseline_baseline_file")
    assert result["drift_class"] == "KNOWN_BASELINE_DRIFT"
    assert result["verdict"] != "fail"
    codes = {i["code"] for i in result["issues"]}
    assert "known_baseline_drift" in codes


def test_09c_new_candidate_drift_is_fatal(svc):
    """A candidate that asks for an extra field nobody consumes is rejected.

    Field-level edits live inside the protected contract region, so the
    candidate must declare `contract_revision` intent (C2) — which is precisely
    what subjects it to the full-force drift comparison (C1).
    """
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    injected = cand.source_text.replace(
        '"possible_transformation": "..."',
        '"possible_transformation": "...",\n  "brand_new_unused_field": "..."')
    assert injected != cand.source_text
    svc.update_source(ASSET, cand.variant_id, injected, intent="contract_revision")
    result = svc.validate(ASSET, cand.variant_id)
    assert result["drift_class"] == "NEW_CANDIDATE_DRIFT"
    assert result["verdict"] == "fail"
    detail = next(i for i in result["issues"]
                  if i["code"] == "new_candidate_drift")["detail"]
    assert any("brand_new_unused_field" in x for x in detail["introduced"])
    assert result["variant"]["state"] == "INCOMPATIBLE"


def test_09d_protected_region_edit_is_refused_by_the_server(svc):
    """C2: a plain content edit that touches a protected region never lands."""
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    broken = cand.source_text.replace('"topic": "..."', '"headline": "..."')
    assert broken != cand.source_text

    with pytest.raises(Exception) as exc:
        svc.update_source(ASSET, cand.variant_id, broken)
    assert "output_json_contract" in str(exc.value)

    # nothing was written
    assert svc.variant(ASSET, cand.variant_id).source_text == cand.source_text
    codes = {r["code"] for r in svc.store.rejections()}
    assert "protected_region_mutation" in codes


def test_09e_declared_contract_revision_still_fails_on_missing_field(svc):
    """Declaring the intent does not buy a pass: losing a consumed field is fatal."""
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    broken = cand.source_text.replace('"topic": "..."', '"headline": "..."')
    svc.update_source(ASSET, cand.variant_id, broken, intent="contract_revision")
    result = svc.validate(ASSET, cand.variant_id)
    assert result["verdict"] == "fail"
    codes = {i["code"] for i in result["issues"]}
    assert "contract_missing_field" in codes
    assert "contract_region_revised" in codes


# --- 10 & 11. compile + provenance ----------------------------------------

def test_10_11_compile_has_full_provenance(svc):
    cand = _editable_candidate(svc)
    svc.validate(ASSET, cand.variant_id)
    compiled = svc.compile(ASSET, cand.variant_id)
    assert compiled["compiled_hash"].startswith("sha256:")
    assert compiled["provenance_coverage"] == "100%"
    assert compiled["coverage_gaps"] == []
    kinds = {s["kind"] for s in compiled["source_map"]}
    assert kinds <= {"source_module", "compiler_generated"}
    assert "source_module" in kinds
    for span in compiled["source_map"]:
        if span["kind"] == "source_module":
            assert span["asset_id"] and span["variant_id"] and span["region_name"]
        else:
            assert span["rule_id"] and span["compiler_profile"]
    assert compiled["variant"]["state"] == "COMPILED"


def test_11b_compiled_equals_runtime_invocation(svc):
    """The compiled payload is what the branch runtime would actually send."""
    adapter = ZarathustraAdapter()
    v = svc.variant(ASSET, "v_baseline_baseline_file")
    fixture = adapter.fixtures(ASSET)[0]
    inv = adapter.build_invocation(ASSET, v.source_text, fixture)
    compiled = svc.compile(ASSET, "v_baseline_baseline_file", fixture.fixture_id)
    assert compiled["system_text"] == inv.system_text
    assert compiled["user_template"] == inv.user_text
    assert compiled["system_text"] == v.source_text


def test_11c_superprompt_forbidden_for_zarathustra(svc):
    profile = ZarathustraAdapter().compiler_profile(ASSET)
    assert profile.allow_superprompt is False
    assert profile.module_loading == "lazy"


# --- 12. bounded smoke -----------------------------------------------------

def test_12_smoke_runs_and_validates(svc):
    cand = _editable_candidate(svc)
    svc.validate(ASSET, cand.variant_id)
    svc.compile(ASSET, cand.variant_id)
    res = svc.run_smoke(ASSET, cand.variant_id)
    assert res.ok, res.reasons
    assert res.fixture_id == "fx_scene_reading_001"
    assert res.compiled_hash.startswith("sha256:")
    assert res.tokens_in > 0 and res.tokens_out > 0
    assert svc.variant(ASSET, cand.variant_id).state == "SMOKE_TESTED"


# --- 13. compare -----------------------------------------------------------

def test_13_compare_with_baseline(svc):
    cand = _editable_candidate(svc)
    svc.validate(ASSET, cand.variant_id)
    svc.compile(ASSET, cand.variant_id)
    svc.run_smoke(ASSET, cand.variant_id)
    cmp = svc.compare_with_baseline(ASSET, cand.variant_id)
    assert cmp["baseline"]["ok"] and cmp["candidate"]["ok"]
    assert cmp["delta"]["rollback_triggers"] == []
    assert "tokens_out" in cmp["delta"]


# --- 14. activation --------------------------------------------------------

def _accepted_candidate(svc):
    cand = _editable_candidate(svc)
    svc.validate(ASSET, cand.variant_id)
    svc.compile(ASSET, cand.variant_id)
    svc.run_smoke(ASSET, cand.variant_id)
    svc.compare_with_baseline(ASSET, cand.variant_id)
    svc.accept(ASSET, cand.variant_id)
    return svc.variant(ASSET, cand.variant_id)


def test_14_activate_switches_active_variant(svc):
    cand = _accepted_candidate(svc)
    before = svc.store.activation_revision()
    out = svc.activate(ASSET, cand.variant_id, "operator")
    assert out["variant"]["state"] == "ACTIVE"
    assert svc.store.active_variant_id(ASSET) == cand.variant_id
    assert svc.store.activation_revision() == before + 1
    # The baseline is never consumed or deprecated by activation: liveness is
    # expressed by the binding, so the baseline stays permanently restorable.
    assert svc.variant(ASSET, "v_baseline_baseline_file").state == "BASELINE"


def test_14b_cannot_activate_unchecked_candidate(svc):
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    with pytest.raises(LifecycleError):
        svc.activate(ASSET, cand.variant_id)


# --- 15 & 16. run + RunTrace ----------------------------------------------

def test_15_16_run_records_exact_identity(svc):
    cand = _accepted_candidate(svc)
    svc.activate(ASSET, cand.variant_id, "operator")
    trace = svc.start_run("zarathustra", ASSET)
    node = trace["nodes"][0]
    assert node["asset_id"] == ASSET
    assert node["variant_id"] == cand.variant_id
    assert node["source_hash"] == cand.source_hash
    assert node["compiled_hash"].startswith("sha256:")
    assert node["profile_id"] == "tinkuy.zarathustra.lazy"
    snap = trace["activation_snapshot"]
    assert snap["snapshot_id"].startswith("snap_")
    assert snap["entries"][ASSET]["variant_id"] == cand.variant_id
    assert svc.store.read_run(trace["run_id"])["run_id"] == trace["run_id"]


def test_16b_activation_snapshot_is_immutable_for_started_run(svc):
    """Switching the active variant must not retro-change a finished run."""
    cand = _accepted_candidate(svc)
    svc.activate(ASSET, cand.variant_id)
    trace = svc.start_run("zarathustra", ASSET)
    captured = trace["activation_snapshot"]["entries"][ASSET]["variant_id"]

    svc.rollback(ASSET)                       # active variant changes underneath
    again = svc.store.read_run(trace["run_id"])
    assert again["activation_snapshot"]["entries"][ASSET]["variant_id"] == captured
    assert svc.store.active_variant_id(ASSET) != captured


def test_16c_cache_identity_includes_activation_revision(svc):
    v = svc.variant(ASSET, "v_baseline_baseline_file")
    key_before = svc.cache_key(ASSET, v, "tinkuy.zarathustra.lazy").as_str()
    cand = _accepted_candidate(svc)
    svc.activate(ASSET, cand.variant_id)
    key_after = svc.cache_key(ASSET, v, "tinkuy.zarathustra.lazy").as_str()
    assert key_before != key_after, "cache key must change with activation revision"


# --- 17. rollback ----------------------------------------------------------

def test_17_rollback_restores_previous(svc):
    cand = _accepted_candidate(svc)
    svc.activate(ASSET, cand.variant_id)
    assert svc.store.active_variant_id(ASSET) == cand.variant_id
    out = svc.rollback(ASSET, "operator")
    assert out["active"]["variant_id"] == "v_baseline_baseline_file"
    assert svc.store.active_variant_id(ASSET) == "v_baseline_baseline_file"
    assert svc.variant(ASSET, cand.variant_id).state == "DEPRECATED"


def test_17b_rollback_needs_no_resmoke(svc):
    cand = _accepted_candidate(svc)
    svc.activate(ASSET, cand.variant_id)
    svc.rollback(ASSET)
    base = svc.variant(ASSET, "v_baseline_baseline_file")
    assert base.state == "BASELINE"
    assert svc.store.active_variant_id(ASSET) == base.variant_id
    assert base.source_hash == svc.baseline(ASSET).source_hash


# --- 18. deterministic node has no prompt editor ---------------------------

def test_18_deterministic_node_has_no_editor(svc):
    payload = svc.node("zarathustra", "assess_turn")
    assert payload["node"]["kind"] == "DETERMINISTIC"
    assert payload["node"]["asset_id"] is None
    assert payload["asset"] is None
    assert payload["editor_available"] is False
    assert payload["node"]["output_contract"].endswith("dispute_assessment.schema.json")


def test_18b_reference_only_asset_is_marked(svc):
    view = svc.asset_view(SOCRATIC)
    assert view["asset"]["reference_only"] is True
    assert view["asset"]["runtime_allowed"] == "false"
    assert view["asset"]["used_by_steps"] == []


# --- 19. V054 hybrid asset shows both effects ------------------------------

def test_19_v054_shows_prompt_and_deterministic_effects(svc):
    controls = {c.control_id: c for c in ZarathustraAdapter().semantic_controls()}
    v054 = controls["persona.position_model"]
    assert v054.subject == "asset"
    classes = [e.effect_class for e in v054.effects]
    assert "PROMPT_BEHAVIOR" in classes
    assert "DETERMINISTIC_ALGORITHM" in classes
    det = next(e for e in v054.effects if e.effect_class == "DETERMINISTIC_ALGORITHM")
    assert "select_initial_voice" in det.consumers
    assert "zarathustra.cast" in det.consumers


# --- invariant: no provider call as a side effect --------------------------

def test_20_editing_and_activation_never_call_a_provider(svc, monkeypatch):
    calls = {"n": 0}

    class Tripwire:
        def generate(self, invocation):
            calls["n"] += 1
            raise AssertionError("provider called as a side effect")

    svc.smoke.model = Tripwire()
    cand = svc.clone(ASSET, "v_baseline_baseline_file")
    svc.update_source(ASSET, cand.variant_id,
                      cand.source_text.replace("срочным", "срочным сейчас"))
    svc.validate(ASSET, cand.variant_id)
    svc.compile(ASSET, cand.variant_id)
    svc.diff(ASSET, "v_baseline_baseline_file", cand.variant_id)
    svc.asset_view(ASSET)
    svc.node("zarathustra", "analyze_situation")
    assert calls["n"] == 0

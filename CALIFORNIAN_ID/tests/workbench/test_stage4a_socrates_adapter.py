"""Stage 4A — Socrates G-S24 structural branch adapter.

Proves structural / contract / asset-projection portability and readiness-aware
presentation. It does NOT prove live execution: G-S24 is host-neutral and the
package README states that live host execution is G-S26.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from workbench_adapters import (
    SocratesBranchAdapter,
    WhiteCrowProjectionAdapter,
    ZarathustraAdapter,
)
from workbench_core import WorkbenchService, WorkbenchStore
from workbench_core.branch import BranchInvariant, StateProjection

SRC = Path(__file__).resolve().parents[2] / "src"
MIRROR = Path(__file__).resolve().parents[2] / "socrates_mirror"


@pytest.fixture()
def adapter():
    return SocratesBranchAdapter()


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.register_adapter(SocratesBranchAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    return s


# ------------------------------------------------------- A1 source mirror

def test_mirror_declares_read_only_provenance():
    import yaml
    man = yaml.safe_load((MIRROR / "source_manifest.yaml").read_text(encoding="utf-8"))
    assert man["owner"] == "LOCAL_SOCRATES"
    assert man["immutable_source"] is True
    assert man["generation"] == "G-S24"
    assert man["package_root_drive_id"] == "10WHFJzLZYP6JblzmZJBk1X3_sdETU4A2"
    for s in man["sources"]:
        assert s["drive_id"] and s["content_fidelity"] in {
            "BYTE_EXACT", "BYTE_EXACT_UNVERIFIED", "TEXT_EXTRACTION",
            "NOT_FETCHED"}
        # a claim of byte identity requires an authority to check it against
        if s["content_fidelity"] == "BYTE_EXACT":
            assert s["verified_against_owner_manifest"] is True
        if s["content_fidelity"] == "BYTE_EXACT_UNVERIFIED":
            assert s["owner_sha256"] is None
            assert s["verified_against_owner_manifest"] is False


def test_pipeline_mirror_is_byte_exact_against_owner_manifest():
    """The one file the adapter parses is verified against the owner's hashes."""
    import hashlib
    import yaml

    data = (MIRROR / "pipeline.yaml").read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    man = yaml.safe_load((MIRROR / "source_manifest.yaml").read_text(encoding="utf-8"))
    entry = next(s for s in man["sources"] if s["source_path"] == "pipeline.yaml")
    assert entry["content_fidelity"] == "BYTE_EXACT"
    assert digest == entry["owner_sha256"]
    assert entry["verified_against_owner_manifest"] is True


def test_source_gaps_are_precise_not_guessed():
    import yaml
    man = yaml.safe_load((MIRROR / "source_manifest.yaml").read_text(encoding="utf-8"))
    steps = man["step_contracts"]
    assert steps["bodies"] == "NOT_FETCHED"
    assert steps["enumeration_status"] == "EMPTY_FOR_THIS_ACCOUNT"
    assert len(steps["entries"]) == 11
    for e in steps["entries"]:
        assert len(e["owner_sha256"]) == 64      # known by hash, not by content
    assert man["not_fetched_from_owner_manifest"]


# ------------------------------------------------------- A2 dependency proof

def test_core_does_not_import_socrates():
    for path in (SRC / "workbench_core").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                mods = [node.module]
            for m in mods:
                assert m.split(".")[0] not in {"socrates", "socrates_adapter",
                                               "californian_id", "zarathustra"}, \
                    f"{path.name}: {m}"


def test_core_has_no_socrates_specific_identifier():
    for path in (SRC / "workbench_core").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)) and ast.get_docstring(node):
                node.body = node.body[1:] or [ast.Pass()]
        code = ast.unparse(tree)
        hit = re.search(r"socrates|G-?S2\d|S0_INTAKE|PRESERVE_APORIA", code, re.I)
        assert hit is None, f"{path.name}: {hit.group(0)!r} leaked into the core"


def test_adapter_reads_package_and_core_only():
    src = (SRC / "workbench_adapters" / "socrates_adapter.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    heads = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module and not n.level:
            heads.add(n.module.split(".")[0])
        elif isinstance(n, ast.Import):
            heads |= {a.name.split(".")[0] for a in n.names}
    assert "workbench_core" in heads
    assert "californian_id" not in heads


# ------------------------------------------------------- A3 pipeline projection

def test_all_eleven_steps_projected(adapter):
    proj = adapter.describe_pipeline()
    steps = [n.node_id for n in proj.nodes if not n.node_id.startswith("TERMINAL:")]
    assert steps == ["S0", "S1", "S2", "S3", "S4", "S5",
                     "S6", "S7", "S8", "S9", "S10"]
    assert proj.pipeline_id == "SOCRATES_FULL_PIPELINE"
    assert proj.version == "0.3.0"


def test_conditional_semantics_preserved(adapter):
    proj = adapter.describe_pipeline()
    by_id = {n.node_id: n for n in proj.nodes}
    assert by_id["S7"].optional is True
    assert by_id["S9"].conditional_on == \
        "InterventionSelection.execution_status == EXECUTE"
    # the bypass edges must exist — the pipeline is not flattened
    edges = {(e.source, e.target) for e in proj.edges}
    assert ("S6", "S8") in edges, "direct bypass of S7 lost"
    assert ("S8", "S10") in edges, "bypass of S9 lost"
    assert ("S6", "TERMINAL:PAUSED_AWAITING_HUMAN_INPUT") in edges


def test_seven_typed_terminal_outcomes(adapter):
    proj = adapter.describe_pipeline()
    terminals = {n.node_id.split(":", 1)[1] for n in proj.nodes
                 if n.node_id.startswith("TERMINAL:")}
    assert terminals == {"COMPLETED", "PROVISIONAL_COMPLETED",
                         "PAUSED_AWAITING_HUMAN_INPUT", "RETURN_OPERATION",
                         "PRESERVE_APORIA", "REFUSED", "FAILED_EXPLICIT"}


def test_non_execution_terminals_reachable_without_s9(adapter):
    """QUESTION / RETURN / DWELL / APORIA / REFUSE may finalize with no run."""
    proj = adapter.describe_pipeline()
    edges = {(e.source, e.target) for e in proj.edges}
    assert ("S8", "S10") in edges
    for outcome in ("RETURN_OPERATION", "PRESERVE_APORIA", "REFUSED"):
        assert ("S10", f"TERMINAL:{outcome}") in edges


# ------------------------------------------------------- A4 node kinds

def test_kinds_derived_from_spec_not_from_name(adapter):
    proj = adapter.describe_pipeline()
    k = {n.node_id: n.kind for n in proj.nodes}
    assert k["S6"] == "HUMAN_GATE"
    assert k["S8"] == "ROUTER"
    assert k["S9"] == "OTHER"          # execution kind not yet decidable
    assert k["S10"] == "STORE"
    assert k["S7"] == "HYBRID"
    assert all(k[s] == "HYBRID" for s in ("S0", "S1", "S2", "S3", "S4", "S5"))


def test_prompt_binding_does_not_imply_model_call(adapter):
    proj = adapter.describe_pipeline()
    s7 = next(n for n in proj.nodes if n.node_id == "S7")
    assert s7.prompt_binding is not None
    assert s7.kind != "MODEL_CALL"
    assert s7.note                      # classification evidence is recorded


# ------------------------------------------------------- A5 readiness

def test_branch_readiness_matrix_is_honest(adapter):
    r = adapter.branch_readiness()
    assert r["generation"] == "G-S24"
    assert r["canonical_claim"] is False
    m = r["matrix"]
    assert m["pipeline_structure"] == "DECLARATIVE_READY"
    assert m["state_model"] == "DECLARATIVE_READY"
    assert m["runtime_profiles"] == "DECLARATIVE_READY"
    # After G-S25R.8 bundle import, prompt bodies (CORE + B01..B10 +
    # SEM_P00..P09) are all materialised under data/socrates/current/.
    assert m["prompt_hierarchy"] == "PROMPT_BODY_READY"
    assert m["prompt_bodies"] == "PROMPT_BODY_READY"
    # Runtime is orchestration-deterministic — an LLM executor for phase
    # bodies remains outstanding (external R8 credential dependency).
    assert m["live_runtime"] == "PARTIAL_LIVE_ORCHESTRATION_DETERMINISTIC"
    assert r["live_runtime_status"] == "PARTIAL_LIVE_ORCHESTRATION_DETERMINISTIC"


def test_every_step_declares_readiness(adapter):
    for n in adapter.describe_pipeline().nodes:
        assert n.readiness is not None
        assert n.readiness.level


# ------------------------------------------------------- A6 no invented prompts

def test_no_fake_prompt_assets(adapter, svc):
    assert adapter.list_assets() == []
    proj = svc.pipeline("socrates")
    assert all(n.asset_id is None for n in proj.nodes)


def test_materialised_body_is_readable_but_not_editable(adapter, svc):
    """A14 re-check found the S7-S8 body. Readable ≠ owned."""
    proj = adapter.describe_pipeline()
    s7 = next(n for n in proj.nodes if n.node_id == "S7")
    assert s7.prompt_binding["binding"] == "MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK"
    assert s7.prompt_binding["body_status"] == "MIRRORED_READ_ONLY"
    assert s7.readiness.level == "PROMPT_BODY_READY"
    assert s7.readiness.expected_in == "G-S26"

    body = adapter.prompt_body("MODE_AND_REFLEXIVITY_GOVERNOR_PROMPT_PACK")
    assert body["editable"] is False
    assert "LOCAL_SOCRATES" in body["reason"]
    assert body["text"].startswith("# G-S23 MODE AND REFLEXIVITY GOVERNOR")
    assert len(body["text"].encode("utf-8")) == 1844      # owner-reported size
    # still not an editable asset anywhere in the service
    assert svc.node("socrates", "S7")["editor_available"] is False


def test_bodies_that_were_never_fetched_stay_honest(adapter):
    proj = adapter.describe_pipeline()
    for step, expected in (("S0", "CONTRACT_READY"), ("S9", "CONTRACT_READY"),
                           ("S10", "CONTRACT_READY")):
        n = next(x for x in proj.nodes if x.node_id == step)
        assert n.readiness.level == expected
        assert n.readiness.expected_in in {"G-S25", "G-S26"}


def test_socrates_node_offers_no_prompt_editor(svc):
    payload = svc.node("socrates", "S0")
    assert payload["editor_available"] is False
    assert payload["asset"] is None


def test_invocation_is_refused_not_faked(adapter):
    from workbench_core.branch import Fixture
    with pytest.raises(NotImplementedError):
        adapter.build_invocation("x", "y", Fixture("f", "t"))


# ------------------------------------------------------- A7 invariants

def test_branch_invariants_carry_provenance(adapter):
    inv = adapter.branch_invariants()
    assert len(inv) == 18          # 10 authority + 8 global guards
    assert all(isinstance(i, BranchInvariant) for i in inv)
    texts = " ".join(i.text for i in inv)
    for expected in ("Truth is never decided by vote",
                     "Arbitration cannot create HUMAN binding",
                     "Persona default is NO_PERSONA",
                     "NO_DUPLICATE_TINKUY_STORES",
                     "NO_COUNCIL_THEATRE"):
        assert expected in texts
    for i in inv:
        assert i.source_ref and i.source_id


# ------------------------------------------------------- A8 contracts

def test_contract_bindings_reference_real_schemas(adapter):
    contracts = adapter.contract_bindings()
    by_id = {c["contract_id"]: c for c in contracts}
    assert "pipeline_trace.schema.json" in by_id
    assert by_id["pipeline_trace.schema.json"]["in_owner_manifest"] is True
    assert "S8" in by_id["intervention_selection.schema.json"]["used_by"]
    assert "S7" in by_id["arbitration_record.schema.json"]["used_by"]
    assert "S6" in by_id["human_operation.schema.json"]["used_by"]
    for c in contracts:
        assert c["provenance"]


def test_schema_outside_owner_manifest_is_flagged(adapter):
    flagged = [c for c in adapter.contract_bindings()
               if c.get("in_owner_manifest") is False]
    assert flagged, "schemas absent from G-S24_SHA256SUMS must be visible"
    assert all("NOT_IN_G-S24_MANIFEST" in c["readiness"] for c in flagged)


# ------------------------------------------------------- A9 state model

def test_state_projection_is_separate_from_pipeline(adapter):
    sp = adapter.state_projection()
    assert isinstance(sp, StateProjection)
    kinds = {s.state_id: s.kind for s in sp.states}
    assert kinds["RETRY_PENDING"] == "dispatcher"
    assert kinds["ESCALATION_PENDING"] == "dispatcher"
    assert kinds["PRESERVE_APORIA"] == "terminal"
    assert kinds["S6_HUMAN_OPERATION_AND_OWNERSHIP"] == "active"
    assert len([s for s in sp.states if s.kind == "terminal"]) == 7
    # and it is genuinely a different object from the step graph
    step_ids = {n.node_id for n in adapter.describe_pipeline().nodes}
    assert not (set(kinds) & step_ids)


def test_retry_is_bounded_and_exact_step(adapter):
    sp = adapter.state_projection()
    assert sp.retry_budget["default"] == 1
    assert sp.retry_budget["S9_TINKUY_EXECUTION"] == 2
    assert "never advances" in sp.dispatcher_semantics["RETRY_PENDING"]
    back = [t for t in sp.transitions if t.source == "RETRY_PENDING"]
    assert len(back) >= 11


def test_forbidden_transitions_are_projected(adapter):
    sp = adapter.state_projection()
    joined = " ".join(sp.forbidden_transitions)
    assert "PAUSED_AWAITING_HUMAN_INPUT -> S9_TINKUY_EXECUTION" in joined
    assert "ArbitrationRecord -> HUMAN binding" in joined
    assert "ontology gap" in joined


def test_escalation_is_not_a_retry(adapter):
    sp = adapter.state_projection()
    targets = {t.target for t in sp.transitions if t.source == "ESCALATION_PENDING"}
    assert targets <= {"S7_REFLEXIVE_RETREAT_COUNCIL_IF_NEEDED",
                       "RETURN_OPERATION", "FAILED_EXPLICIT"}


# ------------------------------------------------------- A10 profiles

def test_six_profiles_inspectable_but_not_activatable(adapter):
    profiles = adapter.runtime_profiles()
    assert {p["profile_id"] for p in profiles} == {
        "DIRECT_ASSISTANCE", "DELIBERATE", "DWELL", "RESEARCH",
        "CONCEPT_GENESIS", "PUBLIC_TWIN_DEMO"}
    assert sum(1 for p in profiles if p["is_default"]) == 1
    for p in profiles:
        assert set(p["available_actions"]) == {
            "inspect", "compare", "clone_candidate", "validate_declaratively"}
        # Runtime profiles (DIRECT_ASSISTANCE, DELIBERATE, ...) still
        # cannot be *activated* — they influence persona casting and
        # counsel invocation, which the deterministic runtime does not
        # exercise. Live activation waits for the R8 LLM executor.
        assert p["activate_in_live_runtime"]["enabled"] is False
        assert p["activate_in_live_runtime"]["status"] == \
            "PARTIAL_LIVE_ORCHESTRATION_DETERMINISTIC"


# ------------------------------------------------------- A11/A12 no false claim

def test_snapshot_is_declarative_not_executed(adapter):
    snap = adapter.declarative_snapshot()
    assert snap["snapshot_kind"] == "DECLARATIVE_SNAPSHOT"
    assert snap["is_executed_run"] is False
    assert snap["host_binding"] == {"status": "NONE", "expected_in": "G-S26"}
    assert snap["missing_prompt_bodies"]
    assert snap["pipeline"]["hash"]


def test_socrates_has_no_workbench_entrypoint_by_design(adapter, svc):
    """SocratesRuntime takes a SocratesRunConfiguration, not (text, mode).

    The runtime is real (see :mod:`socrates_runtime` and the /api/workbench/
    socrates/run endpoint), but the branch does not adopt the generic
    Workbench entrypoint shape. LIVE_RUNTIME_STATUS reflects the change."""
    assert adapter.PRODUCTION_ENTRYPOINT is None
    assert adapter.LIVE_RUNTIME_STATUS == "PARTIAL_LIVE_ORCHESTRATION_DETERMINISTIC"
    with pytest.raises(Exception):
        svc.start_production_run("socrates", "text")


def test_no_live_execution_claim_in_adapter_source():
    src = (SRC / "workbench_adapters" / "socrates_adapter.py").read_text(encoding="utf-8")
    for banned in ("socrates runtime works", "run executed",
                   "activation verified live"):
        assert banned not in src.lower()


# ------------------------------------------------------- A13 three branches

def test_one_core_three_branches(svc):
    branches = {b["branch"]: b for b in svc.branches()}
    assert set(branches) == {"zarathustra", "socrates"}

    z = branches["zarathustra"]
    assert z["has_live_runtime"] is True
    assert z["capabilities"]["rag_profiles"] is True

    s = branches["socrates"]
    # Socrates keeps has_live_runtime=False at the WorkbenchService level —
    # its live runtime uses its own endpoint (see socrates_runtime) rather
    # than adopting the generic start_production_run signature.
    assert s["has_live_runtime"] is False
    assert s["generation"] == "G-S24"
    assert s["owner"] == "LOCAL_SOCRATES"
    assert s["capabilities"]["state_projection"] is True
    assert s["capabilities"]["rag_profiles"] is False

    # third case: a presentation projection over the SAME typed objects
    field = WhiteCrowProjectionAdapter(ZarathustraAdapter()).field_projection("radial")
    assert field.kind == "radial" and field.items


def test_three_maturity_patterns_are_distinct(svc):
    z = svc.pipeline("zarathustra")
    s = svc.pipeline("socrates")
    assert any(n.layer == "ACTUAL_RUNTIME" for n in z.nodes)
    assert all(n.layer == "DECLARED_PIPELINE" for n in s.nodes)
    assert all(n.topology_status == "UNKNOWN" for n in s.nodes)
    assert any(n.topology_status == "MATCH" for n in z.nodes)

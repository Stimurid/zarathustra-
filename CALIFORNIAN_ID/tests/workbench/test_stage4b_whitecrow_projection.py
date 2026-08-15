"""Stage 4B — the core does not impose a node-edge representation.

Acceptance: the SAME typed objects render both as a Zarathustra graph and as a
WhiteCrow radial field, with no fork of the WorkbenchCore data model and no
branch-specific type inside the core.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from workbench_adapters import WhiteCrowProjectionAdapter, ZarathustraAdapter
from workbench_core import WorkbenchService, WorkbenchStore
from workbench_core.branch import FieldItem, FieldProjection

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    return s


@pytest.fixture()
def projection():
    return WhiteCrowProjectionAdapter(ZarathustraAdapter()).field_projection("radial")


# ---------------------------------------------------------------- shape

def test_projection_is_a_field_not_a_graph(projection):
    assert isinstance(projection, FieldProjection)
    assert projection.kind == "radial"
    assert projection.items and all(isinstance(i, FieldItem) for i in projection.items)
    assert not hasattr(projection, "edges"), "a field projection has no edges"
    assert projection.center_label == "FIELD"


def test_geometry_is_ported_verbatim_from_whitecrow(projection):
    g = projection.geometry
    assert (g["W"], g["H"], g["cx"], g["cy"], g["R"]) == (300, 240, 150, 120, 95)
    assert g["max_items"] == 8
    assert g["node_r"] == 10 and g["active_r"] == 14 and g["hub_r"] == 16
    assert g["start_angle"] == "-pi/2"
    assert "FIELD_KERNEL_v6_3_1.html::getFPERadial" in g["source"]


def test_projection_respects_the_eight_item_bound(projection):
    assert len(projection.items) <= 8


# ------------------------------------------------- same underlying objects

def test_same_typed_objects_feed_both_projections(svc, projection):
    graph = svc.pipeline("zarathustra")
    graph_nodes = {n.node_id: n for n in graph.nodes if n.layer == "ACTUAL_RUNTIME"}

    for item in projection.items:
        assert item.node_id in graph_nodes, item.node_id
        node = graph_nodes[item.node_id]
        # identity keys must be literally the same values
        assert item.kind == node.kind
        assert item.asset_id == node.asset_id
        assert item.rag_profile_id == node.rag_profile_id
        assert item.label == node.label


def test_inspector_opens_the_same_asset_from_either_projection(svc, projection):
    prompt_items = [i for i in projection.items if i.asset_id]
    assert prompt_items, "field projection exposed no prompt-bearing item"
    item = prompt_items[0]

    from_graph = svc.node("zarathustra", item.node_id)
    assert from_graph["node"]["asset_id"] == item.asset_id
    view = svc.asset_view(item.asset_id)
    assert view["asset"]["asset_id"] == item.asset_id
    assert view["active_variant_id"]


def test_rag_item_keeps_rag_semantics(svc, projection):
    rag_items = [i for i in projection.items if i.kind == "RAG"]
    assert rag_items
    for i in rag_items:
        assert i.rag_profile_id
        assert i.asset_id is None
        payload = svc.node("zarathustra", i.node_id)
        assert payload["node"]["kind"] == "RAG"
        assert payload["editor_available"] is False


def test_deterministic_item_still_has_no_editor(svc, projection):
    det = [i for i in projection.items if i.kind == "DETERMINISTIC"]
    for i in det:
        assert i.asset_id is None
        assert svc.node("zarathustra", i.node_id)["editor_available"] is False


# ------------------------------------------------- ordering is genuinely different

def test_field_ordering_differs_from_call_order(svc, projection):
    graph = svc.pipeline("zarathustra")
    call_order = [n.node_id for n in graph.nodes if n.layer == "ACTUAL_RUNTIME"]
    field_order = [i.node_id for i in projection.items]
    assert field_order != call_order[:len(field_order)], (
        "the field projection just replays the graph order — no new question asked")
    assert projection.items[0].kind in {"MODEL_CALL", "RAG"}


def test_dead_declaration_is_not_a_field_object(projection):
    assert "retrieve_initial_context" not in {i.node_id for i in projection.items}


# ------------------------------------------------- no fork of the data model

def _executable_source(path: Path) -> str:
    """Source with docstrings and comments removed.

    Attribution prose ("inherits the WhiteCrow check family") is legitimate and
    must not be confused with a branch-specific *type* in the shared model.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_core_has_no_whitecrow_specific_type():
    """Executable core code must not name a branch's visual ontology."""
    for path in (SRC / "workbench_core").glob("*.py"):
        code = _executable_source(path)
        hit = re.search(r"whitecrow|mosaic|linearized|getFPE", code, re.IGNORECASE)
        assert hit is None, f"{path.name}: {hit.group(0)!r} leaked into the core"


def test_projection_adapter_imports_core_not_the_other_way():
    src = (SRC / "workbench_adapters" / "whitecrow_projection.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    heads = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            heads.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            heads |= {a.name.split(".")[0] for a in node.names}
    assert "workbench_core" in heads
    assert "californian_id" not in heads, "a presentation adapter needs no runtime"
    assert "zarathustra" not in heads


def test_projection_adapter_owns_no_pipeline_or_runtime():
    src = (SRC / "workbench_adapters" / "whitecrow_projection.py").read_text(encoding="utf-8")
    for forbidden in ("def describe_pipeline", "def run_retrieval", "Pipeline(",
                      "def production_entrypoint"):
        assert forbidden not in src, forbidden


def test_unsupported_kind_is_refused():
    a = WhiteCrowProjectionAdapter(ZarathustraAdapter())
    with pytest.raises(ValueError):
        a.field_projection("mosaic")


def test_public_payload_is_serialisable(projection):
    pub = projection.to_public()
    assert set(pub) >= {"projection_id", "kind", "branch", "items",
                        "geometry", "center_label", "source_ref"}
    assert all("node_id" in i and "role" in i for i in pub["items"])

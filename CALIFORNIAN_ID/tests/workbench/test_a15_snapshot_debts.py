"""A15 — the three Stage 3 snapshot debts, closed with regression tests.

Stage 3 shipped ``RunConfigurationSnapshot`` with three honest gaps. Each is
now paid, and each has a test that fails again if the gap reopens.

  A15-1  model_bindings said ``resolved_at_call_time`` — a placeholder, not a
         binding. Provider/model/parameters are now resolved once, at snapshot
         time, and the run is pinned to that resolution.
  A15-2  hybrid semantic controls (Critique / Variation / V054) changed what a
         run did while staying outside the frozen picture, so two materially
         different runs were indistinguishable in the record.
  A15-3  the run storage root fell back to ``CWD/runs``, so the same command
         wrote elsewhere depending on where it was invoked from, and a run was
         not locatable from its own configuration.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from workbench_adapters import SocratesBranchAdapter, ZarathustraAdapter
from workbench_core import WorkbenchService, WorkbenchStore

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"


@pytest.fixture()
def svc(tmp_path):
    s = WorkbenchService(WorkbenchStore(tmp_path / "state"))
    s.register_adapter(ZarathustraAdapter())
    s.register_adapter(SocratesBranchAdapter())
    s.bootstrap()
    s.bootstrap_rag()
    return s


# ------------------------------------------------------- A15-1 model bindings

def test_no_placeholder_left_in_model_bindings(svc):
    snap = svc.build_run_configuration("zarathustra")
    assert snap.model_bindings
    for b in snap.model_bindings:
        assert b.get("provider") != "resolved_at_call_time"
        assert b.get("model") != "resolved_at_call_time"
        assert b["resolution"] in {"RESOLVED_AT_SNAPSHOT", "UNRESOLVED"}


def test_every_production_role_is_bound(svc):
    snap = svc.build_run_configuration("zarathustra")
    roles = {b["role"] for b in snap.model_bindings}
    assert roles == {r for r, _ in ZarathustraAdapter.PRODUCTION_ROLES}
    for b in snap.model_bindings:
        assert b["call_site"], "a binding must point at the call site it governs"
        assert b["evidence_grade"] == "MEASURED"


def test_effective_parameters_come_from_config_not_from_a_note(svc):
    snap = svc.build_run_configuration("zarathustra")
    for b in snap.model_bindings:
        if b["resolution"] != "RESOLVED_AT_SNAPSHOT":
            continue
        assert "note" not in b["effective_parameters"]
        assert b["provider_kind"]
        assert b["source_ref"].startswith("config/models.yaml")


def test_unresolvable_provider_is_reported_not_defaulted(monkeypatch, tmp_path):
    """No silent mock, no invented provider — the gap is named."""
    for key in ("CALIFORNIAN_ID_PROVIDER", "API_302AI_KEY",
                "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    bindings = ZarathustraAdapter().effective_model_bindings()
    unresolved = [b for b in bindings if b["resolution"] == "UNRESOLVED"]
    assert len(unresolved) == len(bindings), \
        "with no key and no yaml provider nothing may resolve"
    for b in unresolved:
        assert b["provider"] is None and b["model"] is None
        assert "no LLM provider available" in b["reason"]


def test_snapshot_id_changes_when_the_model_binding_changes(svc, monkeypatch):
    before = svc.build_run_configuration("zarathustra").snapshot_id
    monkeypatch.setenv("CALIFORNIAN_ID_PROVIDER", "mock-variant-b")
    after = svc.build_run_configuration("zarathustra").snapshot_id
    assert before != after, "a different model resolution must be a different config"


def test_resolver_view_exposes_model_bindings(svc):
    view = svc.build_run_configuration("zarathustra").as_resolver_view()
    assert "persona_turn" in view["model_bindings"]


def test_branch_without_a_model_boundary_says_so(svc):
    snap = svc.build_run_configuration("socrates")
    assert [b["resolution"] for b in snap.model_bindings] == ["NOT_APPLICABLE"]
    assert "no model boundary" in snap.model_bindings[0]["reason"]


# --------------------------------------------------- A15-2 semantic controls

def test_hybrid_controls_are_inside_the_frozen_picture(svc):
    snap = svc.build_run_configuration("zarathustra")
    ids = {c["control_id"] for c in snap.semantic_control_bindings}
    assert ids == {"critique_regime", "variation_regime", "persona.position_model"}


def test_hybrid_control_keeps_both_effect_classes(svc):
    snap = svc.build_run_configuration("zarathustra")
    for cid in ("critique_regime", "variation_regime", "persona.position_model"):
        c = snap.semantic_control(cid)
        assert c is not None
        assert set(c["effect_classes"]) == {"PROMPT_BEHAVIOR",
                                            "DETERMINISTIC_ALGORITHM"}, \
            f"{cid} must not be flattened to a single effect in the snapshot"
        assert c["affects_nodes"]
        assert all(c["source_refs"])


def test_control_value_is_recorded_with_its_origin(svc):
    snap = svc.build_run_configuration("zarathustra")
    critique = snap.semantic_control("critique_regime")
    assert critique["value"] == "balanced"
    assert critique["value_origin"] == "DEFAULT"
    assert critique["allowed_values"] == ["gentle", "balanced", "hard"]
    v054 = snap.semantic_control("persona.position_model")
    assert v054["subject"] == "asset"
    assert v054["value_origin"] == "ASSET_RESOLVED"


def test_snapshot_is_frozen_against_control_mutation(svc):
    snap = svc.build_run_configuration("zarathustra")
    with pytest.raises(Exception):
        snap.semantic_control_bindings = []          # frozen dataclass


def test_declarative_branch_has_no_semantic_controls(svc):
    assert svc.build_run_configuration("socrates").semantic_control_bindings == []


# ------------------------------------------------------- A15-3 storage root

def test_storage_binding_is_recorded_in_the_snapshot(svc):
    sb = svc.build_run_configuration("zarathustra").storage_binding
    assert sb["runs_dir"]
    assert sb["cwd_dependent"] is False
    assert sb["resolved_from"] in {"env:CALIFORNIAN_ID_RUNS_DIR",
                                   "config:runtime.runs_dir", "package_root",
                                   "env:XDG_STATE_HOME", "home", "tempdir"}


def test_runs_dir_resolution_never_consults_cwd():
    """The rule, not just the current value: no cwd term in the resolver."""
    tree = ast.parse((SRC / "californian_id" / "config.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_resolve_runs_dir")
    body = ast.unparse(fn)
    assert "cwd" not in body.lower(), "process cwd is back in the runs-dir chain"


@pytest.mark.parametrize("subdir", ["a", "b/c"])
def test_same_command_from_two_directories_resolves_the_same_root(tmp_path, subdir):
    """The regression that motivated A15-3, executed rather than asserted."""
    workdir = tmp_path / subdir
    workdir.mkdir(parents=True)
    env = dict(os.environ, PYTHONPATH=str(SRC))
    env.pop("CALIFORNIAN_ID_RUNS_DIR", None)
    code = "from californian_id import config; print(config.RUNS_DIR)"
    here = subprocess.run([sys.executable, "-c", code], cwd=str(REPO),
                          capture_output=True, text=True, env=env, check=True)
    there = subprocess.run([sys.executable, "-c", code], cwd=str(workdir),
                           capture_output=True, text=True, env=env, check=True)
    assert here.stdout.strip() == there.stdout.strip()
    assert not (workdir / "runs").exists(), "a stray runs/ was created in the cwd"


def test_explicit_configured_path_wins(tmp_path):
    target = tmp_path / "explicit_runs"
    env = dict(os.environ, PYTHONPATH=str(SRC),
               CALIFORNIAN_ID_RUNS_DIR=str(target))
    out = subprocess.run(
        [sys.executable, "-c",
         "from californian_id import config;"
         "print(config.RUNS_DIR); print(config.RUNS_DIR_ORIGIN)"],
        cwd=str(tmp_path), capture_output=True, text=True, env=env, check=True)
    resolved, origin = out.stdout.strip().splitlines()
    assert Path(resolved) == target.resolve()
    assert origin == "env:CALIFORNIAN_ID_RUNS_DIR"


# ------------------------------------------------- the core stayed branch-free

def test_paying_the_debts_did_not_put_a_branch_into_the_core():
    for path in (SRC / "workbench_core").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                mods = [node.module]
            for m in mods:
                assert m.split(".")[0] not in {"californian_id", "zarathustra"}, \
                    f"{path.name} imports {m}"


def test_core_names_no_branch_specific_configuration():
    svc_src = (SRC / "workbench_core" / "service.py").read_text(encoding="utf-8")
    tree = ast.parse(svc_src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) \
                and ast.get_docstring(node):
            node.body = node.body[1:] or [ast.Pass()]
    code = ast.unparse(tree)
    for leaked in ("inner_council", "runtime.yaml", "0.11.1", "critique_regime"):
        assert leaked not in code, f"{leaked!r} is branch configuration, not core"
